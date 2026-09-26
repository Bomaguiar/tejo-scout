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
Six real listing records were researched on 26 September 2026. Each links to its Idealista source. Asking prices and availability can change. Source imagery is advertiser-provided and marked AI-edited; it is not verified current condition.

The daily scan is **not connected**. Import observations manually from your existing scan; the app never pretends to have refreshed live listings. Required import fields: title, city (Lisbon or Setúbal), price, area, sourceURL, observedAt. Optional: type, areaName, lat, lon. observedAt must be the actual observation timestamp in ISO 8601 format. Numeric fields contain plain numbers. One source URL per row. A first observation establishes a baseline; later observations detect changes. Duplicate/older timestamps are ignored. Use the same canonical listing URL across scans. Listings with different URLs are not automatically matched to the same physical property.

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

