# Tejo Scout

A directly coded local property-investment dashboard. No Lovable, Base44, hosted backend or account is required.

## Open
The current local preview is http://127.0.0.1:8765/.
Double-click **Start dashboard.cmd** to start it again (Python is installed on this computer). You can also open **index.html** directly. Use the same address consistently: browser storage is separate for file:// and http:// addresses.

## Included
- Overview with sourced listings, derived KPIs and a price/area chart.
- Sortable investment table and under-€200K feed.
- Editable investment analyzer with saved scenarios and sensitivity analysis.
- Listing details, advertiser photos, risk flags, notes and selected asking-price comparables.
- Interactive OpenStreetMap with approximate neighbourhood pins.
- Browser-local watchlist and price observation history.
- Validated CSV/JSON scan import, full JSON backup export and restore.

## Data and limitations
Nine real listing records cover Lisbon, Setúbal, Mafra, Torres Vedras and Lourinhã, researched on 26–27 September 2026. The Torres Vedras record uses an indexed advertiser snapshot; confirm its current price. Each links to its Idealista source. Asking prices and availability can change. Source imagery is advertiser-provided and marked AI-edited; it is not verified current condition.

The daily scan runs in GitHub Actions at **08:17 Europe/Lisbon**, independently of this computer. The workflow discovers agency listings, checks existing sources, saves dated observations, generates the static data files and deploys GitHub Pages. Public pages may be blocked or incomplete; the scan status displays errors and retains last good data. You can also import observations manually. Required import fields: title, city (Lisbon, Setúbal, Mafra, Torres Vedras or Lourinhã), price, area, sourceURL, observedAt. Optional: type, areaName, lat, lon. observedAt must be the actual observation timestamp in ISO 8601 format. Numeric fields contain plain numbers. One source URL per row. A first observation establishes a baseline; later observations detect changes. Duplicate/older timestamps are ignored. Use the same canonical listing URL across scans. Listings with different URLs are not automatically matched to the same physical property.

Comparables and resale estimates are not prefilled. Add relevant source-backed comparables in property details. These are asking prices, not completed sales. ROI requires all cost and resale assumptions. Acquisition taxes are manual inputs, not an automatic Portuguese tax assessment. Contingency (10%) and selling costs (5%) are explicitly editable assumptions. Returns exclude income / capital gains tax. Restricted assets are excluded from dashboard ROI rankings.

All changes are saved only in the current browser. Use Export data for backups. Clearing browser storage removes saved changes. No cross-device sync or authentication is included.

Internet access is needed for advertiser photos, Leaflet map assets, OpenStreetMap tiles and Google Fonts. Calculation and application code run locally. Unavailable images have labelled fallbacks. No generated or stock imagery is substituted for real listing photos.

## Source files
- index.html — application shell
- styles.css — responsive styling
- app.js — routes, interactions, storage and imports
- model.js — real listing records, financial calculations and validation
- start.ps1 / Start dashboard.cmd — local launcher

No build step or npm installation is required. These static files can be served from an ordinary web server.

## Validation
Verified calculation: €100,000 purchase, 50 m², €500/m² renovation, 10% contingency, €5,000 taxes, €1,000 fees, €2,000 holding, €4,000/m² resale and 5% selling costs produce €135,500 invested, €54,500 pre-tax profit and 40.2214% ROI.

Browser tests cover routes, watchlist/scenario reload persistence, notes, comparables, import validation, price drops, six map markers and mobile overflow. Test fixtures run in an isolated browser context and are not included in the delivered data. Progressive WebMCP hooks are feature-detected; native WebMCP is unavailable in the tested browser.


## Ocean-view land
The Land tab contains 55 candidate adverts researched on 27 September 2026 across the full Lisbon and Setúbal districts. It is a broad public-web search, not an exhaustive or live inventory. Each listing includes a source URL, paraphrased evidence of the advertised view, plot area, price and planning caveats. Sources may be cached; availability and permits are not verified. Known duplicate ads are consolidated; overlapping offerings and conflicting prices/areas are flagged. River-only, merely near-beach and projected-only view claims are excluded. No qualifying entry for a municipality does not prove none exists.

Land filters include district, municipality, view type, advertised planning status, maximum asking price, minimum area, sort order and saved-only. Land watchlists and notes remain browser-local, are included in workspace backups, and appear in Watchlist. Export land listings downloads the filtered research catalogue. Land is separate from renovation calculations so plot area is never treated as house floor area.

`land-data.js` holds the research catalogue; `land.js` renders and filters it. Agency land discovery and advert checks run through the repository scanner.

## Review 1 October 2026
64 existing advert URLs attempted: 52 source snapshots retrieved, 12 unavailable. Added two Lourinha land candidates. Capuchos price revised to EUR 490,000 from an advertised reduction; exact change date unknown. Older conflicting snapshots retained as warnings, not price updates. See refresh-report.json. Daily 08:00 update is a local Codex automation requiring the computer awake and Codex running; no cloud scanner is deployed.

## Review 2 October 2026
66 existing adverts attempted: 54 snapshots retrieved, 12 unavailable. Two new sea-view land candidates: Torres Vedras (EUR 140,000 / 5,040 m2) and Sesimbra (EUR 490,000 / 5,000 m2). No new verified price changes. Discovery is incomplete; cached pages are not live availability. Dated source reviews retained in research/.

## Independent scanner

- `.github/workflows/daily-scan.yml`: daily schedule, manual Run workflow, parser and migration tests, scan, commit observations, deploy Pages and verify live status.
- `scanner/sources.json`: six agency adapters and discovery entrypoints (Nestenn, MediPred, West Life, Atlântico, Veigas and ImoMelides). Public sitemaps and links supply candidates; no official API, search API, paid service or AI key is needed.
- `scanner/scan.py`: respects robots.txt, TLS validation, 1.2-second minimum host delay, 18-second timeouts, 3 MB response limit, at most 16 candidate details per agency per run, rotating discovery cursor. At most six hosts in parallel; each host sequential. No login, proxy, CAPTCHA workaround or certificate bypass.
- `catalog.json`: authoritative public house/land data; generated `house-data.js` and `land-data.js` feed the site. Never edit generated files without updating the catalogue.
- `refresh-report.json`: latest scan status, per-source errors, new matches, actual direct observations, rejections and duplicate review queue. `research/scan-YYYY-MM-DD.json` stores the most recent run for that day; direct observation history stays in each listing.
- `scanner/state.json`: discovery cursors. Source URLs and agency-reference/area matches merge duplicate observations; weaker price/area matches go to review rather than being counted twice.
- Browser data: new published house observations merge while preserving watch IDs, notes, scenarios, comparables and newer manual observations. Private data never enters the scanner or GitHub.

Run locally: `pip install -r scanner/requirements.txt`, `python scanner/scan.py`, `node scanner/build.cjs`. Run tests: `python -m unittest discover -s tests -p "test_*.py"` and `node tests/model.cjs`. GitHub schedules may run late and can be disabled after repository inactivity; Actions shows the enabled state and every run. A completely unusable scan publishes retained data and failure status, then fails the workflow. Infrastructure failures leave the prior report date visible.

Adding an agency requires its real public URL, discovery pages or sitemap, an allowed detail-path pattern and an adapter with explicit asking price, area and municipality evidence. A successful HTTP response without sufficient fields is rejected. Sea-view land must have an explicit sea/ocean claim; nearby beaches, river-only views and projected views do not qualify. All construction permissions remain unverified advertiser claims. Floor area never comes from the plot area.

### Advert availability
Current dashboard, house feeds, map and land feeds show only adverts fetched and parsed within the previous 48 hours. Blocked, stale or unparsed adverts are hidden by default; the availability filter reveals unverified records or the full archive. Watchlists retain all saved records and show their status. Explicit advertiser sold/reserved status or an actual advert HTTP 404/410 removes an advert from current feeds. A blocked request is never treated as sold. Prices on hidden records are last known asking prices; a live advert still requires seller confirmation. Availability-only refreshes preserve private notes, scenarios and saved IDs.

### Small-agency discovery
Daily discovery now includes PT Casas, Oeste Soluções, MCI, Ora Escolha and Acertos e Medidas (11 agencies total). House scope includes all Lisbon and Setúbal municipalities. Ordinary house URLs rotate alongside renovation keywords; houses with land remain houses. €200K is included in the budget feed. Up to four public-page browser renders per agency fill missing explicit floor areas; no login, CAPTCHA bypass or API credentials. Rendering failures retain the last good data. Advertised legal/tenancy/parcel restrictions are flagged, not presumed resolved.
