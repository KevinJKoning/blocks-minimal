"""Retrieve official 2024 Census county boundaries for offline maps (native Python)."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from refresh import retrieve

SERVICE = 'https://tigerweb.geo.census.gov/arcgis/rest/services/Generalized_ACS2024/State_County/MapServer/11/query'


def main():
    url = SERVICE + '?' + urlencode({'where': "GEOID LIKE '26%'", 'outFields': 'GEOID,BASENAME',
                                    'returnGeometry': 'true', 'outSR': '5070',
                                    'maxAllowableOffset': 250, 'geometryPrecision': 0, 'f': 'json'})
    sources = []
    response = json.loads(retrieve(url, sources))
    if 'error' in response or response.get('exceededTransferLimit'):
        raise ValueError(f'Census boundary query failed or was truncated: {response.get("error")}')
    features = response['features']
    if len(features) != 83 or len({f['attributes']['GEOID'] for f in features}) != 83:
        raise ValueError('Expected 83 distinct Michigan counties')
    if response['spatialReference'].get('latestWkid', response['spatialReference'].get('wkid')) != 5070:
        raise ValueError('Expected EPSG:5070 projected coordinates')
    data = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sources': sources,
            'crs': 'EPSG:5070', 'vintage': 2024, 'simplification_m': 250,
            'features': sorted(features, key=lambda f: f['attributes']['GEOID'])}
    target = Path(__file__).parent / 'boundaries.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    temporary.replace(target)
    print(f'Wrote 83 county boundaries to {target}')


if __name__ == '__main__':
    main()
