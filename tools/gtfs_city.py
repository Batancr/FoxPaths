"""Turn a transit agency's GTFS file into a FoxPaths city data file.

GTFS is the standard schedule format agencies publish: every route, stop and stop time. This module trims a feed to one
area, picks one representative weekday, Saturday and Sunday, and writes docs/data/<city>.js in the same shape the site
uses for every city. City scripts (for example tools/build_newmarket.py) call build() with their own settings.
"""
import csv, io, json, math, os, zipfile, datetime as dt
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PALETTE = ['#2F7FC1', '#D9711C', '#1F9A66', '#9152B3', '#C93A55', '#B8901A', '#3A8C9E', '#8A6D3B', '#5C6BC0', '#7A8A99']


def read(z, name):
    if name not in z.namelist(): return []
    with z.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig')))


def service_dates(cal, cal_dates, today):
    """Pick one Wednesday, Saturday and Sunday the feed covers, starting from today, skipping holidays."""
    exceptions = defaultdict(list)
    for r in cal_dates: exceptions[r['date']].append(r)
    starts = [r['start_date'] for r in cal] + list(exceptions)
    ends = [r['end_date'] for r in cal] + list(exceptions)
    if not starts: raise SystemExit('The feed has no calendar information')
    lo = max(today, dt.datetime.strptime(min(starts), '%Y%m%d').date())
    hi = dt.datetime.strptime(max(ends), '%Y%m%d').date()
    want = {'weekday': 2, 'saturday': 5, 'sunday': 6}
    out = {}
    d = lo
    while d <= hi and len(out) < 3:
        for day, wd in want.items():
            removed = any(r['exception_type'] == '2' for r in exceptions.get(d.strftime('%Y%m%d'), []))
            if day not in out and d.weekday() == wd and not removed:  # skip holidays, which remove regular service
                out[day] = d
        d += dt.timedelta(days=1)
    return out


def active_services(cal, cal_dates, date):
    key = date.strftime('%Y%m%d'); wd = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][date.weekday()]
    on = {r['service_id'] for r in cal if r['start_date'] <= key <= r['end_date'] and r.get(wd) == '1'}
    for r in cal_dates:
        if r['date'] == key:
            (on.add if r['exception_type'] == '1' else on.discard)(r['service_id'])
    return on


def to_min(t):
    h, m, s = (int(x) for x in t.strip().split(':'))
    return round(h * 60 + m + s / 60)


def simplify(pts, tol):
    def seg_dist(p, a, b):
        vx, vy = b[0] - a[0], b[1] - a[1]; L = vx * vx + vy * vy
        t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L))
        return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dmax, idx = 0, 0
    for i in range(1, len(pts) - 1):
        dd = seg_dist(pts[i], a, b)
        if dd > dmax: dmax, idx = dd, i
    if dmax > tol: return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)
    return [a, b]


def build(city, gtfs_path, bbox, places, today=None, keep_route=None, route_label=None, stop_label=None, line_tol=0.02):
    """city: dict with id, name, cats, defaults, info (same keys as the Peterborough builder).
    bbox: (min_lon, min_lat, max_lon, max_lat) of the area to keep.
    places: [(id, name, subtitle, lon, lat, category, Google Maps search text)].
    keep_route(short_name, long_name) -> bool: optional filter (default: every route that serves the area).
    route_label(short_name, long_name) -> (badge, name): optional display names."""
    label = route_label or (lambda short, long: (short, long or short))
    today = today or dt.date.today()
    z = zipfile.ZipFile(gtfs_path)
    lon0 = (bbox[0] + bbox[2]) / 2; lat0 = (bbox[1] + bbox[3]) / 2
    kx = math.cos(math.radians(lat0)) * 111.32; ky = 110.57
    xy = lambda lon, lat: [round((lon - lon0) * kx, 3), round((lat - lat0) * ky, 3)]
    inside = lambda lon, lat: bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]

    stops = {r['stop_id']: r for r in read(z, 'stops.txt')}
    area = {sid for sid, r in stops.items() if r.get('stop_lat') and inside(float(r['stop_lon']), float(r['stop_lat']))}
    routes = {r['route_id']: r for r in read(z, 'routes.txt')}
    trips = {r['trip_id']: r for r in read(z, 'trips.txt')}
    cal, cal_dates = read(z, 'calendar.txt'), read(z, 'calendar_dates.txt')
    dates = service_dates(cal, cal_dates, today)
    services = {day: active_services(cal, cal_dates, d) for day, d in dates.items()}
    wanted_services = set().union(*services.values()) if services else set()

    # stop times for trips on the chosen days, kept only inside the area
    st = defaultdict(list)
    with z.open('stop_times.txt') as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig')):
            t = trips.get(r['trip_id'])
            if not t or t['service_id'] not in wanted_services or r['stop_id'] not in area: continue
            tm = r['departure_time'] or r['arrival_time']
            if not tm: continue
            st[r['trip_id']].append((int(r['stop_sequence']), r['stop_id'], to_min(tm)))

    patterns = {}
    used_routes = set()
    for tid, rows in st.items():
        rows.sort()
        if len(rows) < 2: continue
        t = trips[tid]; rt = routes[t['route_id']]
        short_raw = rt.get('route_short_name') or rt['route_id']
        if keep_route and not keep_route(short_raw, rt.get('route_long_name', '')): continue
        short = label(short_raw, rt.get('route_long_name', ''))[0]
        seq = tuple(r[1] for r in rows); times = [r[2] for r in rows]
        for day, svc in services.items():
            if t['service_id'] not in svc: continue
            key = (short, t.get('direction_id', ''), day, seq)
            p = patterns.setdefault(key, {'route': short, 'dir': t.get('direction_id', '') or '0', 'day': day, 'stops': list(seq),
                                          'timed': [], 'trips': [], 'label': ('toward ' + t['trip_headsign']) if t.get('trip_headsign') else None})
            p['trips'].append(times)
            used_routes.add(t['route_id'])
    for p in patterns.values(): p['trips'].sort(key=lambda x: x[0])
    plist = sorted(patterns.values(), key=lambda p: (p['route'], p['dir'], p['day']))
    used_stops = sorted({s for p in plist for s in p['stops']})

    route_out = {}
    for i, rid in enumerate(sorted(used_routes, key=lambda r: (routes[r].get('route_short_name') or r))):
        rt = routes[rid]; short, name = label(rt.get('route_short_name') or rid, rt.get('route_long_name', ''))
        color = rt.get('route_color') or ''
        route_out[short] = {'id': short, 'name': name,
                            'c': ('#' + color) if len(color) == 6 and color.upper() not in ('FFFFFF', '000000') else PALETTE[i % len(PALETTE)]}

    # route lines for the map, from shapes when the feed has them
    lines = []
    shape_route = {}
    for t in trips.values():
        rt = routes[t['route_id']]; short = label(rt.get('route_short_name') or t['route_id'], rt.get('route_long_name', ''))[0]
        if t['route_id'] in used_routes and t.get('shape_id'): shape_route.setdefault(t['shape_id'], short)
    shapes = defaultdict(list)
    for r in read(z, 'shapes.txt'):
        if r['shape_id'] in shape_route:
            shapes[r['shape_id']].append((int(r['shape_pt_sequence']), float(r['shape_pt_lon']), float(r['shape_pt_lat'])))
    seen = set()
    for sid, pts in shapes.items():
        pts.sort(); run = []
        for _, lon, lat in pts + [(None, 999, 999)]:
            if inside(lon, lat): run.append(xy(lon, lat)); continue
            if len(run) > 1:
                simp = simplify(run, line_tol); sig = (shape_route[sid], tuple(map(tuple, simp[::4])))
                if sig not in seen: seen.add(sig); lines.append({'r': shape_route[sid], 'name': shape_route[sid], 'pts': simp})
            run = []
    if not lines:  # no shapes in the feed: draw straight lines through each pattern's stops
        for p in plist:
            lines.append({'r': p['route'], 'name': p['route'], 'pts': [xy(float(stops[s]['stop_lon']), float(stops[s]['stop_lat'])) for s in p['stops']]})

    bundle = {**city, 'exact': True,
              'places': [{'id': i, 'n': n, 'sub': sub, 'p': xy(lon, lat), 'cat': cat, 'q': q} for i, n, sub, lon, lat, cat, q in places],
              'stops': {s: {'n': (stop_label or str.strip)(stops[s]['stop_name']), 'p': xy(float(stops[s]['stop_lon']), float(stops[s]['stop_lat']))} for s in used_stops},
              'patterns': plist, 'lines': lines, 'routes': route_out, 'origin': [lon0, lat0], 'k': [kx, ky],
              'serviceDates': {d: v.isoformat() for d, v in dates.items()}}
    s = json.dumps(bundle, separators=(',', ':'))
    out = os.path.join(ROOT, 'docs', 'data', city['id'] + '.js')
    with open(out, 'w') as fh:
        fh.write(f"// Generated by tools/build_{city['id']}.py from a GTFS feed. Do not edit by hand.\n")
        fh.write(f"(window.FOXPATH_CITIES=window.FOXPATH_CITIES||{{}}).{city['id']}=" + s + ';\n')
    n_trips = sum(len(p['trips']) for p in plist)
    print(f"wrote {out}: {len(s):,} bytes; {len(route_out)} routes; {len(used_stops)} stops; {len(plist)} stop patterns; {n_trips} trips")
    print('service days used:', {d: v.isoformat() for d, v in dates.items()})
    return bundle
