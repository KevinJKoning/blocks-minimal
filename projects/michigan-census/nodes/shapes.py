"""Michigan's 83 county outlines, checked and read as GeoJSON geometry.

The Census Bureau's generalized [2024 county polygons](https://tigerweb.geo.census.gov/arcgis/rest/services/Generalized_ACS2024/State_County/MapServer/11), simplified to 250 metres and
projected in EPSG:5070 (CONUS Albers equal area). They arrive as Esri JSON, where a
county is a list of rings: clockwise rings are outlines (the mainland and each island),
the others holes in the outline that holds them.
"""
import json
import math

from blocks import ui


def _signed_area(ring):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:])) / 2


def _inside(point, ring):
    x, y = point
    crossings = [(x0, y0, x1, y1) for (x0, y0), (x1, y1) in zip(ring, ring[1:]) if (y0 > y) != (y1 > y)]
    return sum(x < x0 + (y - y0) * (x1 - x0) / (y1 - y0) for x0, y0, x1, y1 in crossings) % 2 == 1


def _multipolygon(rings):
    polygons = [[r] for r in rings if _signed_area(r) < 0]
    for hole in (r for r in rings if _signed_area(r) >= 0):
        # Simplification can flip a tiny island's ring; one inside no outline is an outline.
        holder = next((p for p in polygons if _inside(hole[0], p[0])), None)
        if holder:
            holder.append(hole)
        else:
            polygons.append([hole[::-1]])
    return {'type': 'MultiPolygon', 'coordinates': polygons}


def shapes(boundaries):
    with open(boundaries) as f:
        snapshot = json.load(f)
    if snapshot['crs'] != 'EPSG:5070':
        raise ValueError('Expected boundaries projected in EPSG:5070')
    counties = {}
    for feature in snapshot['features']:
        geoid, rings = '05000US' + feature['attributes']['GEOID'], feature['geometry']['rings']
        if not rings or any(len(r) < 4 or r[0] != r[-1] for r in rings):
            raise ValueError(f'Invalid boundary rings: {geoid}')
        if any(not math.isfinite(v) for r in rings for p in r for v in p):
            raise ValueError(f'Invalid boundary coordinates: {geoid}')
        counties[geoid] = _multipolygon(rings)
    if len(counties) != 83 or len(snapshot['features']) != 83:
        raise ValueError('Expected 83 distinct Michigan counties')
    return {'counties': counties, 'sources': snapshot['sources'], 'retrieved_at': snapshot['retrieved_at']}


def view(out):
    return [ui.download('county-boundary-sources.json', {'sources': out['sources'], 'retrieved_at': out['retrieved_at']}),
            ui.map(list(out['counties'].values()), title='Michigan counties')]
