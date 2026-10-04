"""Build FoxPaths' Waterloo data file (Waterloo and Kitchener) from Grand River Transit's GTFS files.

Run from the repository root:  python3 tools/build_waterloo.py
Reads data/raw/grt/grt-bus.gtfs.zip and data/raw/grt/grt-ion.gtfs.zip and writes docs/data/waterloo.js.

GRT publishes its schedule at https://webapps.regionofwaterloo.ca/api/grt-routes/ ("Bus + LRT Combined", GFTS.zip).
These copies came from Transitous (https://api.transitous.org/gtfs/), which splits buses and the ION light rail into
two files. To refresh, download both Grand-River-Transit files from either place into data/raw/grt/ and run this again.
Data is used under the Region of Waterloo's Open Data Licence.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtfs_city import build, ROOT

GTFS = [os.path.join(ROOT, 'data', 'raw', 'grt', 'grt-bus.gtfs.zip'),
        os.path.join(ROOT, 'data', 'raw', 'grt', 'grt-ion.gtfs.zip')]
BBOX = (-80.62, 43.38, -80.40, 43.53)  # Waterloo and Kitchener; Cambridge is left out to keep the file small

# Locations are GRT stop or ION station positions next to each place. "Example" places are neutral stand-ins.
PLACES = [
    # (id, name, subtitle, lon, lat, category, Google Maps search text, aliases the day reader understands)
    ('home', 'Home', 'Example: ICON student residence, 330 Phillip St', -80.5397, 43.4766, 'home', 'ICON, 330 Phillip Street, Waterloo, ON', ['icon', 'res', 'residence']),
    ('work', 'University of Waterloo', 'School: main campus, by the ION station', -80.5413, 43.4734, 'study', 'University of Waterloo, Waterloo, ON',
     ['uw', 'uwaterloo', 'waterloo', 'school', 'campus', 'class', 'classes', 'uni', 'university']),
    ('society', 'Society 145', 'Student residence, 145 Columbia St W (approximate spot)', -80.5405, 43.4768, 'residence', 'Society 145, 145 Columbia Street West, Waterloo, ON', ['society']),
    ('laurier', 'Wilfrid Laurier University', 'Waterloo campus', -80.5280, 43.4753, 'study', 'Wilfrid Laurier University, Waterloo, ON', ['wlu']),
    ('uptown', 'Uptown Waterloo', 'Waterloo Public Square, restaurants and cafés', -80.5223, 43.4643, 'food', 'Waterloo Public Square, Waterloo, ON'),
    ('nofrills', 'No Frills, Forwell Creek Rd', 'Groceries: 24 Forwell Creek Rd (approximate spot)', -80.4360, 43.4730, 'groceries', "No Frills, 24 Forwell Creek Road, Waterloo, ON", ['nofrills', 'no frills']),
    ('conestoga', 'Conestoga Mall', 'King St N, by the ION station', -80.5296, 43.4983, 'shop', 'Conestoga Mall, Waterloo, ON'),
    ('fairview', 'Fairview Park Mall', 'Kitchener, by Fairway ION station', -80.4426, 43.4224, 'shop', 'Fairview Park Mall, Kitchener, ON'),
    ('central', 'Kitchener Central Station', 'Transit hub, King and Victoria', -80.4984, 43.4530, 'transit', 'Kitchener Central Station, Kitchener, ON'),
    ('grh', 'Grand River Hospital', 'King St W, Kitchener', -80.5116, 43.4572, 'health', 'Grand River Hospital, Kitchener, ON'),
]
CITY = {
    'id': 'waterloo', 'name': 'Waterloo',
    'workLabel': 'School',  # most people planning around Waterloo are heading to campus
    'cats': {'study': 'Any university campus'},
    'defaults': {
        'addr': {'home': 'ICON, 330 Phillip Street, Waterloo, ON', 'work': 'University of Waterloo, Waterloo, ON'},
        'acts': [{'id': 'a1', 'label': 'Class', 'place': 'work', 'min': 180, 'max': '', 'after': '', 'by': ''},
                 {'id': 'a2', 'label': 'Lunch', 'place': 'uptown', 'min': 30, 'max': 45, 'after': '', 'by': ''},
                 {'id': 'a3', 'label': 'Groceries', 'place': 'nofrills', 'min': 20, 'max': 40, 'after': '', 'by': ''}],
    },
    'info': {
        'pill': 'Waterloo and Kitchener · all GRT buses and ION · exact stop times',
        'source': "Routes, stops and stop-by-stop times come from Grand River Transit's published schedule data (buses "
                  "September 30 to December 20, 2026, plus the ION light rail), covering Waterloo and Kitchener. "
                  "Contains information provided by the Regional Municipality of Waterloo under licence. "
                  "FoxPaths is not affiliated with or endorsed by GRT or the Region of Waterloo.",
    },
    'mapTitle': 'GRT routes in Waterloo and Kitchener',
    'mapNote': 'Route lines from Grand River Transit',
}

def route_label(short, long):
    if short == '301': return 'ION', 'ION light rail'
    return short, long or short

if __name__ == '__main__':
    b = build(CITY, GTFS, BBOX, PLACES, route_label=route_label)
    print('routes:', ', '.join(f"{r['id']} {r['name']}" for r in b['routes'].values()))
