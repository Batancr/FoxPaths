# 🦊 FoxPaths

A day planner for people who get around by bus. You list the places you need to be and how long you need at each
(eat for 20 to 30 minutes, study for at least 3 hours, be home between 6 and 7 pm), and FoxPaths works out the buses,
walks and waits that make the day fit. It runs entirely in the browser, and currently covers Peterborough and
Newmarket, Ontario.

- **Plans around real timetables**: compares every workable combination of buses and gives you two or three
  different plans, such as the most time at a chosen stop, the least waiting or the least walking
- **Step by step**: when to leave, which stop to walk to, which bus to board, where to get off, and how long you have
  at each place
- **Flexible days**: stops can have their own time limits, and FoxPaths can choose the order of your stops for you
- **Google Maps hand-off**: each leg of the plan has a button that opens it in Google Maps for turn-by-turn directions

The site lives in [`docs/`](docs/) and is served by GitHub Pages.

## Cities

Each city has its own tab on the site, with its own places and saved settings. A city's data loads only when you open
its tab.

### Peterborough, Ontario

Timetables for **Route 2 Chemong**, **Route 3 Park**, **Route 5 The Parkway** and **Route 6 Sherbrooke** (weekday,
Saturday, and Sunday/holiday). The other Peterborough Transit routes are drawn on the map but can't be used for trips
until their schedules are added.

The City's timetables list times only at a handful of main stops per route. FoxPaths estimates times at the stops in
between by spacing them evenly by distance, and marks those times as estimates. A few main stops aren't in the City's
stop file (Trent U Bata Library, Fleming College, Lansdowne at Memorial Centre, Fisher at Shorelines Casino and Airport
at Spillsbury), so their positions are approximate. Route 5's in-between stops are taken from stops along its route
line, because the stop file barely tags Route 5.

Data comes from the City of Peterborough:

| File in `data/raw/` | Source |
| --- | --- |
| `bus-routes.geojson` | City route map server, layer "Regular Routes" |
| `bus-stops.geojson` | City route map server, layer "Regular Bus Stop" |
| `route-*.html` | Route schedule pages on peterborough.ca |

Place locations come from the City's address locator. Check the City's open data terms before reusing this data
elsewhere.

### Newmarket, Ontario

Every York Region Transit route that serves Newmarket, including Viva Blue and Viva Yellow, with exact times at every
stop. School-day routes (the 400s) are left out. The data comes from YRT's published GTFS schedule file
(`data/raw/yrt/google_transit.zip`), which covers September 6 to October 31, 2026.

Contains public transit information made available under
[YRT's Open Data Licence](https://www.yrt.ca/en/about-us/open-data-licence-agreement.aspx). FoxPaths is not affiliated
with or endorsed by YRT.

## Rebuilding the data

```
python3 tools/build_peterborough.py
python3 tools/build_newmarket.py
```

Each script writes its city's file in `docs/data/`, which the site loads.

**Adding a Peterborough route:**

1. Save the route's schedule page from peterborough.ca into `data/raw/`.
2. In `tools/build_peterborough.py`, add the route to `ROUTES` and make sure each timetable column heading is in
   `TIMED`. The script stops with a message naming any heading it can't place.
3. Run the script and commit both the raw file and the new data file.

**Refreshing Newmarket** when YRT publishes a new schedule: download https://www.yrt.ca/google/google_transit.zip into
`data/raw/yrt/`, run `tools/build_newmarket.py`, and commit.

**Adding a city that publishes GTFS:** copy `tools/build_newmarket.py`, set the area, places and defaults, and add the
city to `CITY_LIST` in `docs/index.html`. `tools/gtfs_city.py` does the rest.

Walking times use straight-line distance with a detour allowance at about 4.8 km/h. Always check the official schedule
before you travel.

## Your data

Your day, addresses and settings save automatically in your browser (localStorage), on that device only. Nothing is
sent anywhere. Addresses are used only to build Google Maps links.
