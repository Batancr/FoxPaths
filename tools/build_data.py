"""Build FoxPaths' Peterborough data file from the City of Peterborough source files in data/raw.

Run from the repository root:  python3 tools/build_data.py
Writes docs/data/peterborough.js, which the site loads.

To add a route: save its City schedule page into data/raw, add it to SCHED, give its direction
letters in DIRS, map each timetable column name to a stop id in TIMED, and set ROUTE_NAME/ROUTE_COLOR.
"""
import json, re, html, math

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UP = os.path.join(ROOT, 'data', 'raw') + '/'
STOPS_F = UP + 'bus-stops.geojson'
ROUTES_F = UP + 'bus-routes.geojson'
SCHED = {'6': UP + 'route-6-sherbrooke.html',
         '3': UP + 'route-3-park.html'}

LON0, LAT0 = -78.32, 44.305
KX = math.cos(math.radians(44.3)) * 111.32
KY = 110.57
def xy(lon, lat): return [round((lon - LON0) * KX, 3), round((lat - LAT0) * KY, 3)]
def d(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

# ---------- stops ----------
raw = json.load(open(STOPS_F))['features']
stops = {}
for f in raw:
    p = f['properties']; lon, lat = f['geometry']['coordinates']
    sid = p['stop_id']
    if sid in stops: continue
    stops[sid] = {'id': sid, 'n': p['stop_name'].strip(), 'lines': p['lines'] or '', 'p': xy(lon, lat)}
# virtual timed stops the stop file doesn't name
stops['V_TRENT'] = {'id': 'V_TRENT', 'n': 'Trent U - Bata Library', 'lines': '', 'p': xy(-78.2916, 44.3572)}
stops['V_FLEM'] = {'id': 'V_FLEM', 'n': 'Fleming College', 'lines': '', 'p': xy(-78.3766, 44.2672)}

TIMED = {  # timetable column name -> stop id (per route/direction where it matters)
    'Trent U - Bata Library': 'V_TRENT', 'Fleming College': 'V_FLEM',
    'Hilliard at Marina': '1865', 'George at Parkhill': 'place_GeoPkh', 'Peterborough Terminal': 'place_PtboTm',
    'Water at Parkhill': '1009', 'Wolsely at Chemong': {'S': '1699', 'N': '1150'}, 'Park at Sherbrooke': '1703',
    'Chamberlain at Monaghan': '1705', 'Lansdowne at The Parkway': '1253', 'Clonsilla at Summit Plaza': '1867',
    'Monaghan at Chamberlain': '1791', 'Rubidge at Rubidge Hall': '1411', 'Marina at Hilliard': {'S': '1029', 'N': '1068'},
    'Sherbrooke at Medical': {'W': '1766', 'E': '1327'},
}
ESTIMATED_TIMED = {'Sherbrooke at Medical': 'nearest stop is Sherbrooke at Goodfellow'}

# ---------- timetables ----------
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
            if prev - v > 600: v += 1440
            t[i] = v
            if v < prev: t[i] = None; continue
        prev = t[i]
    # drop a value that jumps past the next one (typo in source)
    for i, v in enumerate(t):
        if v is None: continue
        nxt = next((x for x in t[i + 1:] if x is not None), None)
        if nxt is not None and v > nxt: t[i] = None
    return t

DAYS = ['weekday', 'saturday', 'sunday']
DIRS = {'6': ['W', 'E'], '3': ['S', 'N']}
DIRWORD = {'W': 'Westbound', 'E': 'Eastbound', 'N': 'Northbound', 'S': 'Southbound'}
ROUTE_NAME = {'6': 'Sherbrooke', '3': 'Park'}
ROUTE_COLOR = {'6': '#D9711C', '3': '#2F7FC1'}
fixes = []
patterns = []
for rid, path in SCHED.items():
    tabs = parse_tables(path)
    assert len(tabs) == 6, (rid, len(tabs))
    for ti, (head, rows) in enumerate(tabs):
        day = DAYS[ti // 2]; dr = DIRS[rid][ti % 2]
        ids = []
        for name in head:
            m = TIMED[name]; ids.append(m[dr] if isinstance(m, dict) else m)
        trips = []; offset = 0; last_first = None
        for r in rows:
            vals = [to_min(v) for v in r]
            first = next((v for v in vals if v is not None), None)
            if first is None: continue
            if last_first is not None and first + offset < last_first - 600: offset += 1440
            row = clean_row(vals, offset)
            if sum(v is not None for v in row) != sum(v is not None for v in vals):
                fixes.append((rid, day, dr, r))
            last_first = next(v for v in row if v is not None)
            trips.append(row)
        patterns.append({'route': rid, 'dir': dr, 'day': day, 'timed': ids, 'timedNames': head, 'trips': trips})

# ---------- intermediate stops ----------
def served(stop, rid, dr):
    for part in stop['lines'].split(','):
        part = part.strip()
        if not part.startswith(rid + ' '): continue
        if DIRWORD[dr] in part or '(' not in part: return True
    return False

def full_sequence(pat):
    rid, dr = pat['route'], pat['dir']
    timed = pat['timed']; tp = [stops[s]['p'] for s in timed]
    seg_members = [[] for _ in range(len(timed) - 1)]
    for s in stops.values():
        if s['id'] in timed or not served(s, rid, dr): continue
        best = None
        for k in range(len(timed) - 1):
            a, b = tp[k], tp[k + 1]
            det = d(a, s['p']) + d(s['p'], b) - d(a, b)
            if best is None or det < best[0]: best = (det, k)
        if best[0] > 1.2: continue  # too far off the line between timed stops
        seg_members[best[1]].append(s['id'])
    seq = [timed[0]]; frac = [(0, 0.0)]
    for k in range(len(timed) - 1):
        a = tp[k]
        mem = sorted(seg_members[k], key=lambda sid: d(a, stops[sid]['p']))
        # cumulative distance along a -> m1 -> m2 ... -> b
        pts = [a] + [stops[m]['p'] for m in mem] + [tp[k + 1]]
        cum = [0.0]
        for i in range(1, len(pts)): cum.append(cum[-1] + d(pts[i - 1], pts[i]))
        for i, m in enumerate(mem):
            seq.append(m); frac.append((k, cum[i + 1] / cum[-1] if cum[-1] else 0))
        seq.append(timed[k + 1]); frac.append((k + 1, 0.0))
    return seq, frac

out_patterns = []
for pat in patterns:
    seq, frac = full_sequence(pat)
    timed_idx = {sid: i for i, sid in enumerate(pat['timed'])}
    trips = []
    for row in pat['trips']:
        times = []
        for sid, (k, f) in zip(seq, frac):
            if sid in timed_idx: times.append(row[timed_idx[sid]]); continue
            a, b = row[k], row[k + 1] if k + 1 < len(row) else None
            times.append(round(a + (b - a) * f) if a is not None and b is not None else None)
        trips.append(times)
    out_patterns.append({'route': pat['route'], 'dir': pat['dir'], 'day': pat['day'], 'stops': seq,
                         'timed': pat['timed'], 'trips': trips})

used = sorted({s for p in out_patterns for s in p['stops']})
stop_out = {s: {'n': stops[s]['n'], 'p': stops[s]['p']} for s in used}

# ---------- route lines for the map ----------
rl = json.load(open(ROUTES_F))['features']
def simplify(pts, tol=0.02):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]; L = d(a, b)
        dist = abs((b[0]-a[0])*(a[1]-p[1]) - (a[0]-p[0])*(b[1]-a[1])) / L if L else d(a, p)
        if dist > dmax: dmax, idx = dist, i
    if dmax > tol:
        return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]
lines = []
for f in rl:
    p = f['properties']; g = f['geometry']
    if not g: continue
    parts = g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]
    num = (p['line_name'] or '').split(' ')[0]
    for part in parts:
        pts = simplify([xy(*c) for c in part])
        lines.append({'r': num, 'name': p['line_name'], 'pts': pts})

bundle = {'stops': stop_out, 'patterns': out_patterns, 'lines': lines,
          'routes': {r: {'id': r, 'name': ROUTE_NAME[r], 'c': ROUTE_COLOR[r]} for r in SCHED},
          'origin': [LON0, LAT0], 'k': [KX, KY]}
s = json.dumps(bundle, separators=(',', ':'))
out = os.path.join(ROOT, 'docs', 'data', 'peterborough.js')
with open(out, 'w') as fh:
    fh.write('// Generated by tools/build_data.py from City of Peterborough data. Do not edit by hand.\n')
    fh.write('window.FOXPATH_DATA=' + s + ';\n')
print('wrote', out, len(s), 'bytes;', len(stop_out), 'stops;', len(out_patterns), 'timetables;', 'row fixes:', len(fixes))
