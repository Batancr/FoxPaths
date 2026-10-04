"""Build FoxPaths' Newmarket data file from York Region Transit's GTFS file.

Run from the repository root:  python3 tools/build_newmarket.py
Reads data/raw/yrt/google_transit.zip and writes docs/data/newmarket.js.

To refresh when YRT publishes a new schedule (each file covers a board period of a few months), download
https://www.yrt.ca/google/google_transit.zip into data/raw/yrt/ and run this script again.
YRT data is used under YRT's Open Data Licence: https://www.yrt.ca/en/about-us/open-data-licence-agreement.aspx
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtfs_city import build, ROOT

GTFS = os.path.join(ROOT, 'data', 'raw', 'yrt', 'google_transit.zip')
BBOX = (-79.515, 44.020, -79.405, 44.085)  # roughly the Town of Newmarket: Bathurst St to Hwy 404, St John's Sdrd to Green Lane

# Locations are YRT stop positions next to each place, unless noted. "Example" places are neutral stand-ins.
PLACES = [
    # (id, name, subtitle, lon, lat, category, Google Maps search text)
    ('home', 'Home', 'Example: near Yonge and Mulock', -79.4761, 44.0362, 'home', 'Yonge St and Mulock Dr, Newmarket, ON'),
    ('work', 'Work', 'Example: near Davis and Leslie', -79.4316, 44.0660, 'work', 'Davis Dr and Leslie St, Newmarket, ON'),
    ('terminal', 'Newmarket Terminal', 'Bus terminal, Yonge and Davis', -79.4866, 44.0529, 'transit', 'Newmarket Bus Terminal, Newmarket, ON'),
    ('ucm', 'Upper Canada Mall', 'Yonge and Davis', -79.4878, 44.0556, 'shop', 'Upper Canada Mall, Newmarket, ON'),
    ('mainst', 'Main Street', 'Historic downtown, cafés and restaurants', -79.4574, 44.0532, 'food', 'Main Street South, Newmarket, ON'),
    ('lib', 'Newmarket Public Library', '438 Park Ave (approximate spot)', -79.4642, 44.0524, 'study', 'Newmarket Public Library, 438 Park Avenue, Newmarket, ON'),
    ('southlake', 'Southlake Regional Health Centre', 'Hospital, Davis Dr', -79.4514, 44.0613, 'health', 'Southlake Regional Health Centre, Newmarket, ON'),
]
CITY = {
    'id': 'newmarket', 'name': 'Newmarket',
    'cats': {},
    'defaults': {
        # On Sundays, Main Street and the library are 11 to 12 minutes' walk from the nearest stop with service
        'maxWalk': 15,
        'addr': {'home': 'Yonge St and Mulock Dr, Newmarket, ON', 'work': 'Davis Dr and Leslie St, Newmarket, ON'},
        'acts': [{'id': 'a1', 'label': 'Lunch', 'place': 'mainst', 'min': 30, 'max': 45, 'after': '', 'by': ''},
                 {'id': 'a2', 'label': 'Study', 'place': 'lib', 'min': 180, 'max': '', 'after': '', 'by': ''}],
    },
    'info': {
        'pill': 'All YRT routes in Newmarket · exact stop times',
        'source': "Routes, stops and stop-by-stop times come from York Region Transit's published schedule data, "
                  "September 6 to October 31, 2026. Contains public transit information made available under YRT's "
                  "Open Data Licence. FoxPaths is not affiliated with or endorsed by YRT.",
    },
    'mapTitle': 'YRT routes in Newmarket',
    'mapNote': 'Route lines from York Region Transit',
}

def keep_route(short, long):
    # school-day routes (400s) only run a trip or two around bell times
    return not (short.isdigit() and 400 <= int(short) <= 499)

def route_label(short, long):
    badge = '/'.join(part.lstrip('0') or part for part in short.split('|'))
    if badge.lower() in ('blue', 'purple', 'orange', 'yellow', 'pink', 'green'): badge = badge.capitalize()
    name = ' '.join(w if w.isupper() and len(w) <= 3 and w not in ('THE', 'AND') else w.capitalize() for w in long.split()) if long else badge
    return badge, name.replace('(late Night)', '(Late Night)')

SMALL = {'AV': 'Ave', 'ST': 'St', 'DR': 'Dr', 'RD': 'Rd', 'CRES': 'Cres', 'CRT': 'Crt', 'BLVD': 'Blvd', 'PKWY': 'Pkwy',
         'SDRD': 'Sdrd', 'CIR': 'Cir', 'NB': 'NB', 'SB': 'SB', 'EB': 'EB', 'WB': 'WB', 'GO': 'GO', 'YRT': 'YRT'}
def stop_label(name):
    # YRT publishes stop names in capitals: "YONGE / MULOCK" -> "Yonge / Mulock"
    words = []
    for w in name.strip().split(' '):
        words.append(SMALL.get(w, w if not w.isalpha() else w.capitalize()) if w.isupper() or not w.isalpha() else w)
    return ' '.join(words).replace("'S ", "'s ").replace(' And ', ' and ')

if __name__ == '__main__':
    b = build(CITY, GTFS, BBOX, PLACES, keep_route=keep_route, route_label=route_label, stop_label=stop_label)
    print('routes:', ', '.join(f"{r['id']} {r['name']}" for r in b['routes'].values()))
