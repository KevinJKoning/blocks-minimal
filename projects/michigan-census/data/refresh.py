"""Retrieve public Census bulk files; this acquisition script runs in native Python.

Analysis nodes run only in Pyodide. No API key or third-party mirror is needed.
Run from any directory: python projects/michigan-census/data/refresh.py
"""
import csv
import hashlib
import io
import json
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = 'https://www2.census.gov/programs-surveys/acs/summary_file'
TABLES = {'B01001': 49, 'B03002': 21}
YEARS = (2014, 2019, 2024)


def retrieve(url, sources):
    print(f'Retrieving {url}', flush=True)
    response = urllib.request.urlopen(url, timeout=180)
    payload = response.read()
    sources.append({'url': url, 'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)})
    return payload


def number(value):
    # Census special values (including controlled-estimate MOEs) are not zero.
    try:
        n = float(value)
        return int(n) if n >= 0 else None
    except ValueError:
        return None


def historical(year, sources):
    base = f'{ROOT}/{year}'
    lookup = retrieve(f'{base}/documentation/user_tools/ACS_5yr_Seq_Table_Number_Lookup.txt', sources)
    layout = {r['Table ID']: (r['Sequence Number'], int(r['Start Position']) - 1)
              for r in csv.DictReader(io.StringIO(lookup.decode('cp1252')))
              if r['Table ID'] in TABLES and r['Start Position'].strip()}
    folder = f'{base}/data/5_year_seq_by_state/Michigan/All_Geographies_Not_Tracts_Block_Groups'
    geo = retrieve(f'{folder}/g{year}5mi.csv', sources)
    rows = {}
    for r in csv.reader(io.StringIO(geo.decode('cp1252'))):
        if r[2] in ('040', '050') and r[3] == '00':
            geoid = next(c for c in r if c.startswith(r[2] + '00US26'))
            rows[r[4]] = {'year': year, 'geoid': geoid, 'name': r[r.index(geoid) + 1], 'tables': {}}
    for table, cells in TABLES.items():
        seq, start = layout[table]
        archive = retrieve(f'{folder}/{year}5mi{seq}000.zip', sources)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            for prefix, field in [('e', 'estimate'), ('m', 'moe')]:
                with z.open(f'{prefix}{year}5mi{seq}000.txt') as f:
                    for r in csv.reader(io.TextIOWrapper(f)):
                        if r[5] in rows:
                            rows[r[5]]['tables'].setdefault(table, {})[field] = [number(x) for x in r[start:start + cells]]
    if len(rows) != 84:
        raise ValueError(f'{year}: expected Michigan and 83 counties, got {len(rows)}')
    return list(rows.values())


def current(names, sources):
    rows = {g: {'year': 2024, 'geoid': g, 'name': name, 'tables': {}} for g, name in names.items()}
    for table, cells in TABLES.items():
        url = f'{ROOT}/2024/table-based-SF/data/5YRData/acsdt5y2024-{table.lower()}.dat'
        print(f'Retrieving {url}', flush=True)
        # Stream the nationwide file to disk, then keep only the 84 Michigan rows.
        digest, size = hashlib.sha256(), 0
        with tempfile.TemporaryFile() as f:
            with urllib.request.urlopen(url, timeout=180) as response:
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    size += len(chunk)
                    f.write(chunk)
            f.seek(0)
            for r in csv.DictReader(io.TextIOWrapper(f), delimiter='|'):
                # Table-based files use a seven-digit summary-level/component prefix.
                if r['GEO_ID'][3:7] != '0000':
                    continue
                geoid = r['GEO_ID'][:3] + '00US' + r['GEO_ID'].split('US', 1)[1]
                if geoid in rows:
                    if table in rows[geoid]['tables']:
                        raise ValueError(f'Duplicate {table} / {geoid}')
                    rows[geoid]['tables'][table] = {
                        field: [number(r[f'{table}_{suffix}{i:03d}']) for i in range(1, cells + 1)]
                        for field, suffix in [('estimate', 'E'), ('moe', 'M')]}
        sources.append({'url': url, 'sha256': digest.hexdigest(), 'bytes': size})
    if any(set(r['tables']) != set(TABLES) for r in rows.values()):
        raise ValueError('Current release is missing Michigan geographies or tables')
    return list(rows.values())


def main():
    sources = []
    rows = historical(2014, sources) + historical(2019, sources)
    names = {r['geoid']: r['name'] for r in rows if r['year'] == 2019}
    rows += current(names, sources)
    snapshot = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'provider': 'U.S. Census Bureau bulk summary files',
                'product': 'ACS 5-year', 'years': list(YEARS), 'sources': sources,
                'rows': sorted(rows, key=lambda r: (r['year'], r['geoid']))}
    target = Path(__file__).parent / 'census.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, separators=(',', ':')) + '\n')
    temporary.replace(target)
    print(f'Wrote {len(rows)} geography-period records to {target}')


if __name__ == '__main__':
    main()
