# 🦊 FoxPaths

A day planner for people who get around by bus. You list the places you need to be and how long you need at each
(eat for 20 to 30 minutes, study for at least 3 hours, be home between 6 and 7 pm), and FoxPaths works out the buses,
walks and waits that make the day fit. It runs entirely in the browser.

- **Plans around real timetables**: compares every workable combination of buses and gives you two or three
  different plans, such as the most time at a chosen stop, the least waiting or the least walking
- **Step by step**: when to leave, which stop to walk to, which bus to board, where to get off, and how long you have
  at each place
- **Flexible days**: stops can have their own time limits, and FoxPaths can choose the order of your stops for you
- **Google Maps hand-off**: each leg of the plan has a button that opens it in Google Maps for turn-by-turn directions

The site lives in [`docs/`](docs/) and is served by GitHub Pages.

## Coverage

FoxPaths currently covers **Peterborough, Ontario**, with timetables for **Route 3 Park** and **Route 6 Sherbrooke**
(weekday, Saturday, and Sunday/holiday). The other Peterborough Transit routes are drawn on the map but can't be used
for trips until their schedules are added.

The City's timetables list times only at a handful of main stops per route. FoxPaths estimates times at the stops in
between by spacing them evenly by distance, and marks those times as estimates. Walking times use straight-line
distance with a detour allowance at about 4.8 km/h. Always check the official schedule before you travel.

## Data

All transit data comes from the City of Peterborough:

| File in `data/raw/` | Source |
| --- | --- |
| `bus-routes.geojson` | City route map server, layer "Regular Routes" |
| `bus-stops.geojson` | City route map server, layer "Regular Bus Stop" |
| `route-3-park.html`, `route-6-sherbrooke.html` | Route schedule pages on peterborough.ca |

Place locations (home, work, the library and so on) come from the City's address locator.

Check the City of Peterborough's open data terms before reusing this data elsewhere.

## Rebuilding the data

```
python3 tools/build_data.py
```

This reads `data/raw/` and writes `docs/data/peterborough.js`, which the site loads.

To add a route:

1. Save the route's schedule page from peterborough.ca into `data/raw/`.
2. In `tools/build_data.py`, add the file to `SCHED`, its two direction letters to `DIRS`, its name and colour to
   `ROUTE_NAME` and `ROUTE_COLOR`, and map each timetable column heading to a stop ID in `TIMED`.
3. Run the build script and commit both the raw file and the new data file.

## Your data

Your day, addresses and settings save automatically in your browser (localStorage), on that device only. Nothing is
sent anywhere. Addresses are used only to build Google Maps links.
