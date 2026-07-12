# Space Cleaning — Pricing & Revenue Manager

An internal Streamlit tool to price services realistically (per hour, per
sq ft, flat rate, per event, per room), track competitor pricing, get
strategy-based suggestions, forecast revenue, calculate job margins, and
log job history.

## Modules

1. **📊 Dashboard** — KPIs (revenue, margin, jobs, services/competitors
   tracked), your prices vs market bar chart, revenue-by-service pie,
   monthly revenue trend line.
2. **💡 Pricing & Competitors** — one unified page: add/edit/delete your
   services and rates, add/delete competitors, log competitor prices per
   service, pick a **Budget / Market / Premium** strategy, see a 🔴🟢🟡
   status per service with an inline rate-update field and a per-service
   comparison bar chart.
3. **📈 Revenue Forecast** — compound-growth projection from your actual
   job history (or a manual baseline), optional target line, month-by-month
   table.
4. **🔧 Job Calculator** — enter a quoted price and total job cost, get a
   margin gauge, cost-vs-margin pie, break-even price, and a market
   comparison bar chart for that service.
5. **💼 Job Tracker** — log jobs (client, service, employee/crew, date,
   price, cost, status), filter history, see a weekly revenue bar chart.
6. **📤 Export** — one-click Excel workbook: Pricing Summary, Our Services,
   Competitors, Competitor Prices, Job History, Employees.

Pre-seeded with Space Cleaning's actual service list (with realistic
pricing units — e.g. Office Cleaning per sq ft, Standard/Deep Cleaning per
hour, Move-In/Out flat rate, Event Venue per event) and all 8 competitors
identified so far. Rates are left blank — fill them in as you gather real
numbers.

## Running locally

```bash
pip install -r requirements.txt
python seed_data.py      # optional, one-time pre-population
streamlit run app.py
```

Open the local URL Streamlit prints (usually http://localhost:8501).

## Deploying to Streamlit Community Cloud (free)

1. Push this folder to a GitHub repo.
2. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with
   GitHub → "New app" → pick this repo/branch, `app.py` as entry point.
3. Deploy. You'll get a shareable URL for your team.

## ⚠️ Shared data on Streamlit Community Cloud

This app stores data in a local SQLite file (`pricing_data.db`). That's
fully shared and live while the app instance stays running, but Streamlit
Community Cloud's free tier has an **ephemeral filesystem** — data not
committed to GitHub can be lost on redeploys or after long inactivity.

- **Fine for light internal use:** just export to Excel periodically as a
  backup (the Export page does this in one click).
- **Recommended for serious team use:** swap SQLite for a free hosted
  Postgres (Supabase or Neon). Only `get_connection()` in `db.py` needs to
  change — every other function and the whole app stays the same. Ask if
  you'd like this swap built out.

## File structure

```
app.py           — Streamlit UI, all 6 modules
db.py            — database layer (SQLite) — services, competitors,
                    competitor_prices, employees, jobs, settings
suggestions.py   — Budget/Market/Premium suggestion logic (unit-aware)
forecast.py      — compound-growth revenue projection + monthly history
seed_data.py     — one-time optional seed script
requirements.txt — dependencies
```

## Pricing units supported

Per hour · Per sq ft · Flat rate · Per event · Per room

Comparisons between your rate and competitor rates for a service only use
prices logged in the **same unit**, so you're never comparing an hourly
rate to a flat fee by mistake.

## Strategies

- 🟢 **Budget** — price ~10% below market average
- 🟡 **Market** — match the market average
- 🔵 **Premium** — price ~12% above market average

Each has an override field if you want a custom % instead of the default.
