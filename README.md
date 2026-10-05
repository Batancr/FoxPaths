# 🦊 FoxPaths

A day planner for people who get around by bus. You list the places you need to be and how long you need at each
(eat for 20 to 30 minutes, study for at least 3 hours, be home between 6 and 7 pm), and FoxPaths works out the buses,
walks and waits that make the day fit. It runs entirely in the browser, and currently covers Peterborough,
Newmarket and Waterloo, Ontario.

- **Plans around real timetables**: compares every workable combination of buses and gives you two or three
  different plans, such as the most time at a chosen stop, the least waiting or the least walking
- **Step by step**: when to leave, which stop to walk to, which bus to board, where to get off, and how long you have
  at each place
- **Flexible days**: stops can have their own time limits, and FoxPaths can choose the order of your stops for you
- **Google Maps hand-off**: each leg of the plan has a button that opens it in Google Maps for turn-by-turn directions
- **Type your day**: write it the way you'd say it, like "leave home 10-11am, lunch at Uptown 30-45 min, study at UW
  3h+, home by 7pm", and FoxPaths fills in the plan. It's a rule-based reader in `docs/dayparse.js` (no AI): it picks
  out times, durations, day words and place names, including nicknames like "uw", and looks up places it doesn't know
- **Search inside every stop**: each stop's "Where" box searches the city's places, your saved places and addresses
- **Quick durations**: tap 30-45m, 1h, 3h+ and so on, or type them
- **Live plans**: plans update as you change anything; on phones a bar at the bottom shows the best plan
- **Leave when it's best**: tap "Leave now" and tick "No set arrival time", or type something like "I'm at UW now, eat
  on the way, then home". FoxPaths picks the times that waste the least time waiting at stops or sitting idle, and
  tells you how much longer you can stay where you are ("you have 18 min more at the library")
- **A place to eat on your way**: FoxPaths loads restaurants, cafés and fast food from OpenStreetMap (through the
  Overpass API, cached for a week in your browser) and picks the one with the smallest detour that fits your buses
- **Your places, your names**: save any place with your own name and a type (restaurant, work, school, friend or
  family, groceries, gym and so on). With two or more of a type, stops can use "One of my saved restaurants" and
  FoxPaths picks the one that fits. Restaurants FoxPaths picks for you can be saved straight from the plan
- **Recent places first** in every Where box, and **Use my location** as a starting point
- **Pick a date**: FoxPaths chooses the weekday, Saturday or Sunday schedule, treats Ontario holidays as Sunday service,
  and warns when a date is past the end of the schedules on file
- **Saved days**: save a day you plan often and load it in one tap. Drag stops by their number to reorder them, and
  tap a chip under "Here's what I understood" to jump to that part of the form
- **Take it with you**: add a plan to your calendar (.ics file), copy it as text, or copy a share link that opens the
  same day for someone else. Share links carry the day inside the link, after the `#`, so nothing is uploaded; Home
  and Work open as the other person's own places, and "your location" is never included
- **Backup and example mode**: download your places, saved days and settings as a file and restore them in another
  browser. Open the site with `?demo` (the "See an example day" link) to try it without changing your saved data
- **Changing buses**: allow bus changes, at most one, or none (one bus per trip, walking further to it instead).
  Under More options, or say "no transfers" or "one bus only" in Type your day
- **Which side of the street**: for every bus, which way it's heading, which side of the street to wait on (buses
  drive on the right, so the stop is on the right-hand side of travel), and a Street View link to the stop. For the
  ION light rail it names the platform direction instead
- **Address search**: type part of an address or a business name and pick from suggestions, closest first. Picked
  places go on the planner's map and can be used as Home, Work or any stop

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

### Waterloo, Ontario

Waterloo and Kitchener: every Grand River Transit bus route that serves them, including the iXpress routes, plus the ION
light rail, with exact times at every stop. Cambridge is left out to keep the data file small. The data comes from GRT's
published GTFS schedule (`data/raw/grt/`), as copied by [Transitous](https://transitous.org), which splits buses and
the ION into two files. The bus schedule covers September 30 to December 20, 2026.

Places include the University of Waterloo (shown as "School"), ICON and Society 145 student residences, and the No
Frills on Forwell Creek Rd for groceries.

Contains information provided by the Regional Municipality of Waterloo under licence. FoxPaths is not affiliated with
or endorsed by GRT or the Region of Waterloo.

## Rebuilding the data

```
python3 tools/build_peterborough.py
python3 tools/build_newmarket.py
python3 tools/build_waterloo.py
```

Each script writes its city's file in `docs/data/`, which the site loads.

**Adding a Peterborough route:**

1. Save the route's schedule page from peterborough.ca into `data/raw/`.
2. In `tools/build_peterborough.py`, add the route to `ROUTES` and make sure each timetable column heading is in
   `TIMED`. The script stops with a message naming any heading it can't place.
3. Run the script and commit both the raw file and the new data file.

**Refreshing Newmarket** when YRT publishes a new schedule: download https://www.yrt.ca/google/google_transit.zip into
`data/raw/yrt/`, run `tools/build_newmarket.py`, and commit.

**Refreshing Waterloo:** download GRT's file from https://webapps.regionofwaterloo.ca/api/grt-routes/ ("Bus + LRT
Combined"), or both Grand-River-Transit files from https://api.transitous.org/gtfs/, into `data/raw/grt/`, adjust the
file list at the top of `tools/build_waterloo.py` if the names differ, and run it.

**Adding a city that publishes GTFS:** copy `tools/build_newmarket.py`, set the area, places and defaults, and add the
city to `CITY_LIST` in `docs/index.html`. `tools/gtfs_city.py` does the rest.

Walking times use straight-line distance with a detour allowance at about 4.8 km/h. Always check the official schedule
before you travel.

## Your data

Restaurant suggestions are loaded once per city from the [Overpass API](https://overpass-api.de) (OpenStreetMap
data); the request contains only the city's map area. Address search sends what you type in the search boxes to [Photon](https://photon.komoot.io), a free search service run
by Komoot, using © OpenStreetMap contributors data. Nothing else leaves your browser.

Your day, addresses and settings save automatically in your browser (localStorage), on that device only. Nothing is
sent anywhere. Addresses are used only to build Google Maps links.
