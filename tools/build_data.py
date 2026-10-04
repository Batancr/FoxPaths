"""Build FoxPaths' Peterborough data file from the City of Peterborough source files in data/raw.

Run from the repository root:  python3 tools/build_data.py
Writes docs/data/peterborough.js, which the site loads.

To add a route:
  1. Save the route's schedule page from peterborough.ca into data/raw/.
  2. Add an entry to ROUTES below: the file, a name and colour, and the direction letter of each timetable
     (the City pages list weekday, Saturday, then Sunday/holiday, two directions each).
  3. Make sure every timetable column heading appears in TIMED (stop ids come from data/raw/bus-stops.geojson;
     add a VIRTUAL stop when the City's stop file has no stop with that name).
  4. Run this script and commit the raw file together with docs/data/peterborough.js.
"""
import json, re, html, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
OUT = os.path.join(ROOT, 'docs', 'data', 'peterborough.js')

LON0, LAT0 = -78.32, 44.305
KX = math.cos(math.radians(44.3)) * 111.32
KY = 110.57
def xy(lon, lat): return [round((lon - LON0) * KX, 3), round((lat - LAT0) * KY, 3)]
def d(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

# ---------------------------------------------------------------- routes
# stops: how to find the stops between timed stops
#   'tag'      stops whose `lines` field lists this route and travel direction
#   'any-tag'  stops whose `lines` field lists this route in any direction (for loop routes)
#   'line'     stops within LINE_RADIUS km of the route line (for routes the stop file barely tags)
ROUTES = {
    '2': {'name': 'Chemong', 'color': '#9152B3', 'file': 'route-2-chemong.html', 'dirs': ['N', 'S'],
          'stops': 'any-tag', 'max_detour': 0.3,
          'labels': {'N': 'Northbound loop via Trent U', 'S': 'Southbound loop via Lansdowne Place'}},
    '3': {'name': 'Park', 'color': '#2F7FC1', 'file': 'route-3-park.html', 'dirs': ['S', 'N'], 'stops': 'tag'},
    '5': {'name': 'The Parkway', 'color': '#1F9A66', 'file': 'route-5-the-parkway.html', 'dirs': ['S', 'N'],
          'stops': 'line'},
    '6': {'name': 'Sherbrooke', 'color': '#D9711C', 'file': 'route-6-sherbrooke.html', 'dirs': ['W', 'E'], 'stops': 'tag'},
}
DAYS = ['weekday', 'saturday', 'sunday']
DIRWORD = {'W': 'Westbound', 'E': 'Eastbound', 'N': 'Northbound', 'S': 'Southbound'}
LINE_RADIUS = 0.03  # km

# Timed stops the City's stop file doesn't name. Locations are approximate.
VIRTUAL = {
    'V_TRENT': ('Trent U - Bata Library', -78.2916, 44.3572),
    'V_FLEM': ('Fleming College', -78.3766, 44.2672),
    'V_MEMC': ('Lansdowne at Memorial Centre', -78.315845, 44.288928),   # 151 Lansdowne St W (City locator)
    'V_CASINO': ('Fisher at Shorelines Casino', -78.345257, 44.269559),  # route 5 line beside 1400 Crawford Dr
    'V_AIRPORT': ('Airport at Spillsbury', -78.3616, 44.2556),           # corner where the route 5 line turns
}

# Timetable column heading -> stop id, or {direction letter: stop id} where the two sides of the road differ
TIMED = {
    'Trent U - Bata Library': 'V_TRENT', 'Fleming College': 'V_FLEM',
    'Lansdowne at Memorial Centre': 'V_MEMC', 'Fisher at Shorelines Casino': 'V_CASINO',
    'Airport at Spillsbury': 'V_AIRPORT',
    'Peterborough Terminal': 'place_PtboTm', 'George at Parkhill': 'place_GeoPkh',
    'Hilliard at Marina': '1865', 'Water at Parkhill': '1009',
    'Marina at Hilliard': {'S': '1029', 'N': '1068'},
    'Wolsely at Chemong': {'S': '1699', 'N': '1150'},
    'Park at Sherbrooke': '1703', 'Chamberlain at Monaghan': '1705', 'Monaghan at Chamberlain': '1791',
    'Rubidge at Rubidge Hall': '1411', 'Clonsilla at Summit Plaza': '1867',
    'Lansdowne at The Parkway': '1253', 'The Parkway at Lansdowne': {'S': '1253', 'N': '1385'},
    # the stop file has no "Sherbrooke at Medical"; Sherbrooke at Goodfellow is the stop at that corner
    'Sherbrooke at Medical': {'W': '1766', 'S': '1766', 'E': '1327', 'N': '1327'},
    'Chemong at Walmart': '1152', "Chemong at Shopper's Drug Mart": '1672',
    'Lansdowne Place at Borden': '1682', 'Lansdowne at George': '1530', 'George at Townsend': '1853',
    'George at Rink': '1498', 'Reid at Parkhill': {'N': '1132', 'S': '1132'},
}

# ---------------------------------------------------------------- stops and route lines
stops = {}
for f in json.load(open(os.path.join(RAW, 'bus-stops.geojson')))['features']:
    p = f['properties']; sid = p['stop_id']
    if sid in stops or not f['geometry']: continue
    stops[sid] = {'id': sid, 'n': p['stop_name'].strip(), 'lines': p['lines'] or '', 'p': xy(*f['geometry']['coordinates'])}
for sid, (n, lon, lat) in VIRTUAL.items():
    stops[sid] = {'id': sid, 'n': n, 'lines': '', 'p': xy(lon, lat)}

route_parts = []  # (route number, line name, [xy points])
for f in json.load(open(os.path.join(RAW, 'bus-routes.geojson')))['features']:
    p = f['properties']; g = f['geometry']
    if not g: continue
    parts = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
    for part in parts:
        route_parts.append(((p['line_name'] or '').split(' ')[0], p['line_name'], [xy(*c) for c in part]))

def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]; L = vx * vx + vy * vy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)

def near_line(p, rid):
    for r, _, pts in route_parts:
        if r != rid: continue
        for i in range(len(pts) - 1):
            if seg_dist(p, pts[i], pts[i + 1]) <= LINE_RADIUS: return True
    return False

# ---------------------------------------------------------------- timetables
def parse_tables(path):
    h = open(path, encoding='utf-8', errors='replace').read()
    txt = lambda s: html.unescape(re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', s))).strip()
    out = []
    for t in re.findall(r'<table.*?</table>', h, re.S):
        rows = [[txt(c) for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)] for r in re.findall(r'<tr.*?</tr>', t, re.S)]
        out.append((rows[0], rows[1:]))
    return out

def to_min(s):
    m = re.match(r'^(\d{1,2}):(\d{2})$', s.strip())
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None

def clean_row(vals, day_offset):
    t = [None if v is None else v + day_offset for v in vals]
    prev = None
    for i, v in enumerate(t):
        if v is None: continue
        if prev is not None and v < prev:
            if prev - v > 600: v += 1440   # passes midnight
            t[i] = v
            if v < prev: t[i] = None; continue
        prev = t[i]
    for i, v in enumerate(t):  # drop a value that jumps past the next one (typo in the source)
        if v is None: continue
        nxt = next((x for x in t[i + 1:] if x is not None), None)
        if nxt is not None and v > nxt: t[i] = None
    return t

def served(stop, rid, dr, mode):
    if mode == 'line': return near_line(stop['p'], rid)
    for part in stop['lines'].split(','):
        part = part.strip()
        if not part.startswith(rid + ' '): continue
        if mode == 'any-tag' or DIRWORD[dr] in part or '(' not in part: return True
    return False

def full_sequence(rid, dr, timed, cfg):
    """Timed stops plus the stops between them, in travel order.
    Returns [(stop id, timed column index or None, segment k, fraction along segment)]."""
    tp = [stops[s]['p'] for s in timed]
    max_det = cfg.get('max_detour', 1.2)
    members = [[] for _ in range(len(timed) - 1)]
    for s in stops.values():
        if s['id'] in timed or not served(s, rid, dr, cfg['stops']): continue
        best = None
        for k in range(len(timed) - 1):
            a, b = tp[k], tp[k + 1]
            det = d(a, s['p']) + d(s['p'], b) - d(a, b)
            if best is None or det < best[0]: best = (det, k)
        if best and best[0] <= max_det: members[best[1]].append(s['id'])
    seq = [(timed[0], 0, 0, 0.0)]
    for k in range(len(timed) - 1):
        a = tp[k]
        mem = sorted(members[k], key=lambda sid: d(a, stops[sid]['p']))
        pts = [a] + [stops[m]['p'] for m in mem] + [tp[k + 1]]
        cum = [0.0]
        for i in range(1, len(pts)): cum.append(cum[-1] + d(pts[i - 1], pts[i]))
        for i, m in enumerate(mem): seq.append((m, None, k, cum[i + 1] / cum[-1] if cum[-1] else 0))
        seq.append((timed[k + 1], k + 1, k + 1, 0.0))
    return seq

patterns, fixes = [], []
for rid, cfg in ROUTES.items():
    tabs = parse_tables(os.path.join(RAW, cfg['file']))
    assert len(tabs) == 6, (rid, len(tabs))
    for ti, (head, rows) in enumerate(tabs):
        day, dr = DAYS[ti // 2], cfg['dirs'][ti % 2]
        timed = []
        for name in head:
            if name not in TIMED: raise SystemExit(f'Route {rid}: add "{name}" to TIMED')
            m = TIMED[name]; timed.append(m[dr] if isinstance(m, dict) else m)
        seq = full_sequence(rid, dr, timed, cfg)
        trips, offset, last_first = [], 0, None
        for r in rows:
            vals = [to_min(v) for v in r]
            first = next((v for v in vals if v is not None), None)
            if first is None: continue
            if last_first is not None and first + offset < last_first - 600: offset += 1440
            row = clean_row(vals, offset)
            if sum(v is not None for v in row) != sum(v is not None for v in vals): fixes.append((rid, day, dr, r))
            last_first = next(v for v in row if v is not None)
            times = []
            for sid, ti_col, k, f in seq:
                if ti_col is not None: times.append(row[ti_col]); continue
                a = row[k]; b = row[k + 1] if k + 1 < len(row) else None
                times.append(round(a + (b - a) * f) if a is not None and b is not None else None)
            trips.append(times)
        pat = {'route': rid, 'dir': dr, 'day': day, 'stops': [s[0] for s in seq], 'timed': timed, 'trips': trips}
        if cfg.get('labels'): pat['label'] = cfg['labels'][dr]
        patterns.append(pat)

used = sorted({s for p in patterns for s in p['stops']})
stop_out = {s: {'n': stops[s]['n'], 'p': stops[s]['p']} for s in used}

def simplify(pts, tol=0.02):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        dist = seg_dist(pts[i], a, b)
        if dist > dmax: dmax, idx = dist, i
    if dmax > tol: return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]
lines = [{'r': r, 'name': name, 'pts': simplify(pts)} for r, name, pts in route_parts]

bundle = {'stops': stop_out, 'patterns': patterns, 'lines': lines,
          'routes': {r: {'id': r, 'name': c['name'], 'c': c['color']} for r, c in sorted(ROUTES.items(), key=lambda x: int(x[0]))},
          'origin': [LON0, LAT0], 'k': [KX, KY]}
s = json.dumps(bundle, separators=(',', ':'))
with open(OUT, 'w') as fh:
    fh.write('// Generated by tools/build_data.py from City of Peterborough data. Do not edit by hand.\n')
    fh.write('window.FOXPATH_DATA=' + s + ';\n')
print('wrote', OUT, len(s), 'bytes;', len(stop_out), 'stops;', len(patterns), 'timetables;', 'source typos skipped:', len(fixes))
for p in patterns:
    print(f"  route {p['route']} {p['dir']} {p['day']:8} {len(p['stops']):3} stops {len(p['trips']):3} trips")
