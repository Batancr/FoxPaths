# How FoxPaths was built

This file is for anyone picking up FoxPaths, including a new Claude chat that has just been connected to this folder.
It records how the project went from an idea to a working website, how changes are made and shipped, the decisions
behind it, and what's still open. The README describes what the site does; this file describes how it got there.

A sibling project, **Fox Chess Lab** (`~/fox-chess-lab`, github.com/Batancr/fox-chess-lab), was built the same way a
few days earlier. FoxPaths copied its repository layout, and several FoxPaths features (share links, backup and
restore, example mode) were borrowed from it on purpose.

## The idea

The starting request: "a maps app like Google Maps, but for planning a whole day around specific times." For example,
take the bus to a restaurant, eat for 20 to 30 minutes, take a bus with little waiting to the library, study for at
least 3 hours, and be home between 6 and 7 pm. The app should work out the buses, walks and waits, and say things
like "at 10:33 walk 3 minutes to this stop, the bus takes 15 minutes, you have 24 minutes to eat."

Before building, we checked whether this already existed (October 2026):

- Google Maps doesn't support multiple destinations for public transit, and its directions links have no departure
  time parameter.
- Transit apps (Transit, Moovit, Citymapper) plan one trip from A to B at a time.
- Multi-stop route optimizers (OptimoRoute, RouteXL, Spoke) handle time windows but are built for delivery drivers.
- Day-planner apps (Motion, Reclaim) schedule time but know nothing about travel.
- A later search for University of Waterloo student projects found transit and mapping work (Mappedin, a TTC speed
  tracker, GRT bus apps) but nothing that chains timed stops against real bus schedules.

The gap: **a day plan with time limits, solved against real bus timetables.** The planned use is personal, and as a
prototype to show a few people. There were no launch plans unless it proved useful.

## Timeline

### 1. Prototype on made-up data (Oct 4, before the repository existed)

Peterborough, Ontario was the first city. Peterborough Transit doesn't publish a public GTFS schedule file, and the
free routing service Transitous doesn't cover it. Rather than wait on data, the first version was a single-page
prototype (a Claude artifact) running on an **invented** bus network loosely placed on Peterborough. The point was to
test the planning idea and the step-by-step format before any data work.

The planning engine from that prototype is still the core of the site:

- a connection-scan router for bus trips between two places,
- a depth-first search over every combination of trips that fits each stop's time limits,
- two or three plans that differ in a meaningful way, each tagged with a goal (most time at a stop, least waiting,
  least walking and so on).

A Google Maps button on each leg came next. Google Maps can't take a multi-stop transit trip, so each leg opens on
its own.

### 2. Real Peterborough data, gathered by hand

With no GTFS file available, the data was pieced together from the City's own sources:

- The City's interactive route map is an ArcGIS web app. Saving the page only kept an empty shell, but its
  configuration pointed to the City's map server (`citymaps.peterborough.ca/arcgis/rest/services/TransitRoutes/`).
  Claude's sandbox couldn't reach that server, so Claude wrote out query URLs and the person downloaded the GeoJSON
  for route lines (layer 3) and stops (layer 2).
- Timetables came from each route's schedule page on peterborough.ca, saved as HTML and parsed by
  `tools/build_peterborough.py`.
- Those timetables list times only at five or six main stops ("timepoints"). Times at the stops in between are
  estimated by spacing them by distance, and the site marks them as estimates.
- Some timepoint names don't match any stop in the City's stop file, so a few "virtual" stops are placed with the
  City's address locator or the route line. The README lists them.

Routes 3 and 6 came first; Routes 2 and 5 followed. Route 2 is a pair of loops, and Route 5's stops are barely
tagged in the stop file, so the builder learned to find stops along a route line instead.

### 3. A real website (Oct 4)

The project moved from a preview page to a GitHub repository, laid out like Fox Chess Lab: the site in `docs/`,
served by GitHub Pages, raw data in `data/raw/`, and build scripts in `tools/`. It was renamed from FoxPath to
FoxPaths shortly after. The person pushes from their own Terminal (see "How changes are made" below).

### 4. More cities from GTFS files

- **Newmarket** uses York Region Transit's GTFS file. YRT's download page asks for a name, phone and company. The
  person didn't want to give personal details, so we checked the licence (YRT Open Data Licence: anyone may use it in
  apps, credit optional) and used YRT's direct download link instead. `tools/gtfs_city.py` is a general GTFS reader:
  it trims a feed to one area, picks a representative weekday, Saturday and Sunday, and keeps exact stop times.
- **Waterloo** (with Kitchener) uses Grand River Transit's GTFS. The Region of Waterloo's server timed out for the
  person, a community copy on GitHub turned out to be from 2016, and an archive site was paid-only, so the files came
  from Transitous's copies, which split buses and the ION light rail into two files. The reader learned to merge
  several files.

Each city became its own tab with its own places, example day and saved settings, and its data file loads only when
the tab opens.

### 5. Making it quick to use (Oct 4–5)

Most later work was about making it easy to describe a day, driven by the person using the site and naming what felt
slow:

- **Address search** with suggestions (Photon, OpenStreetMap data), sorted by distance.
- **Type your day**: a sentence reader in `docs/dayparse.js`. It's deliberately rule-based, not AI, because the site
  is static. It reads times, durations, day words, "any order", "no transfers", "on the way", "now" and place
  nicknames, then shows what it understood as chips.
- **Search inside every stop** instead of dropdowns. The person had a vague complaint about the old form that this
  turned out to name exactly.
- Duration chips, plans that update as you type, and a summary bar on phones.
- **Which side of the street** to wait on for each bus, with a Street View link to the stop. This came from thinking
  about riders who find north, south, east and west confusing.
- **Leave when it's best**: no set arrival time, a "least time wasted" goal, and "stay 18 more minutes" advice.
- **A place to eat on your way**: restaurants from OpenStreetMap (Overpass API), narrowed to the ones with the
  smallest detour.
- A limit on changing buses.
- Named and typed saved places, saved days, recent places, "use my location", a date picker with Ontario holidays,
  calendar export, copy as text, share links, backup and restore, and an example mode.

### 6. A bug found late

When the site moved from the preview page to GitHub Pages, it lost the doctype, charset and viewport tags the preview
had added automatically. Phones most likely showed a shrunken desktop layout, and some hidden rows still showed. It
was caught on Oct 5 while testing at phone width over a local web server, and fixed. Lesson: test the real hosting
setup, not only the preview.

## How changes are made

1. In a chat, the person asks Claude to connect `~/FoxPaths` (Claude requests folder access and the person approves).
2. Claude edits the files and rebuilds data with the scripts in `tools/` when data changes.
3. Claude tests before committing:
   - the planning engine in Node, by pulling the `<script id="engine">` block out of `docs/index.html` together with
     the city data files;
   - the page in a headless browser (Playwright) at desktop and phone widths, with Photon and Overpass answers
     simulated, because Claude's sandbox can't reach those services.
4. Claude commits in the person's folder, with a commit message describing the change for a reader.
5. The person runs `cd ~/FoxPaths && git push`. GitHub Pages updates a few minutes later at
   https://batancr.github.io/FoxPaths/.
6. Claude confirms the push with `git ls-remote` and checks the live page.

Notes on this routine:

- The Claude GitHub app is connected to a different GitHub account, so pushing from the person's Terminal is the
  chosen route.
- Deleting is off by default in connected folders. Git briefly creates `.git/index.lock` files, so Claude asks for
  delete permission in the repository folder before running git there, and checks that no lock file is left behind.
  A stray lock file blocks the person's next git command.
- Large raw data (the GTFS zips) is committed so the data can always be rebuilt.

## Decisions and why

| Decision | Why |
| --- | --- |
| Static site, no server | Free hosting on GitHub Pages, nothing to run or pay for, and fits a personal prototype. |
| Everything saves in the browser (localStorage) | No accounts and no personal data leaves the device. Backup and restore covers moving between devices. |
| Home address kept out of the repository | The repository is public. Examples use neutral spots (an intersection, a student residence). |
| Rule-based sentence reader, not AI | The site is static, and a predictable reader that shows what it understood is easier to trust and fix. |
| Peterborough times estimated between timepoints | It's the only public data. Marked as estimates on the site. |
| GTFS cities use exact stop times | The data allows it. |
| Holidays treated as Sunday service | Simple and usually right. The site says to check, since some agencies run a separate holiday schedule. |
| Side of the street from the route's direction | Buses drive on the right, so the stop is on the right of travel. Terminals and one-way streets can differ, so a Street View link is the backup. |
| Restaurants from OpenStreetMap | Free and open. Coverage is volunteer-made and can be incomplete. |
| Each city's data loads with its tab | Waterloo's file is about 1.2 MB, so other cities shouldn't pay for it. |

## Data, licences and credit

- Peterborough: City of Peterborough route map server and schedule pages. Check the City's open data terms before
  reusing.
- Newmarket: York Region Transit GTFS, YRT Open Data Licence. Credit line on the site.
- Waterloo: Grand River Transit GTFS (via Transitous), Region of Waterloo Open Data Licence. Credit line on the site.
- Address search: Photon by Komoot, © OpenStreetMap contributors. Restaurants: Overpass API, © OpenStreetMap
  contributors.
- The site says it isn't affiliated with or endorsed by any transit agency.

## Open items

- **Untested on the live site:** address search (Photon), restaurant loading (Overpass), "use my location" and
  calendar files on an iPhone. All were tested only with simulated answers. If Photon or Overpass block requests
  from GitHub Pages, the fallback is to build those lists into the data files at build time.
- **Schedule expiry:** YRT's file runs to Oct 31, 2026 and GRT's bus file to Dec 20, 2026. Refresh steps are in the
  README.
- **Peterborough:** ask the City (705-745-0525) for its GTFS file, which would replace the estimates. Routes other
  than 2, 3, 5 and 6 still need schedules.
- **Ideas not built yet:** a per-trip "no bus changes" toggle, restaurant opening hours, Cambridge in the Waterloo
  tab, and Toronto, whose GTFS is too large to load whole in a phone browser and would need trimming.

## Where things are

| Path | What it is |
| --- | --- |
| `docs/index.html` | The whole site: styles, the planning engine (`<script id="engine">`) and the interface. |
| `docs/dayparse.js` | The "Type your day" sentence reader. |
| `docs/data/<city>.js` | Generated city data. Don't edit by hand. |
| `tools/build_peterborough.py` | Builds Peterborough from the City's files, with timepoint interpolation. |
| `tools/gtfs_city.py` | General GTFS reader used by the other city builders. |
| `tools/build_newmarket.py`, `tools/build_waterloo.py` | Per-city settings: area, places, defaults, credit text. |
| `data/raw/` | The original source files. |

## Working with this person

Things the person has asked for or shown during this project:

- Say clearly when something is uncertain, don't invent sources, and flag numbers that need checking.
- Explain in plain language. They're comfortable running a few Terminal commands when told exactly what to type.
- They test on the live site, often on a phone, and come back with what felt slow or confusing. That feedback has
  driven most of the improvements.
- They care about privacy: no personal details on forms that don't need them, and no home address in public files.
- They like cross-pollinating between projects. Fox Chess Lab is a good reference for features and layout.
