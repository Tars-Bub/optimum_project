# Optimum Inventory Tracking and Sales Processing System

Web app for a small retail business: products and stock, sales with drafts and payments,
returns / exchanges / voids, printing on pre-printed forms, reports, and staff accounts.
Built with Django (Python). Runs on SQLite out of the box; MySQL is supported through environment variables.

## Run it (Windows, macOS or Linux)

Needs Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo          # demo accounts, categories and products
python manage.py runserver
```

Open http://127.0.0.1:8000

| Role | Username | Password |
|---|---|---|
| Admin / Owner | `admin` | `admin12345` |
| Staff | `staff1` | `staff12345` |

Change these passwords before using real data. To start empty instead of demo data, skip `seed_demo`
and run `python manage.py createsuperuser`.

## Tests

```bash
python manage.py test            # all unit and integration tests, including payments
python manage.py test payments   # Maya integration only
```

API response tests (Postman / Newman) are in `postman/`. See `docs/api-integration.md`.

## Screens (from the wireframe) and where the code lives

| Screen | App | Process |
|---|---|---|
| Log in / Register Staff Account | `accounts` | 1.0 |
| Staff Accounts (Admin only), Pending Registrations | `accounts` | 1.0 |
| Categories & Products | `catalog` | 2.0 |
| Stock: Levels, Incoming, Adjust, Movements, Alerts | `stock` | 4.0 |
| Sales: cart, drafts, payment, finalize | `sales` | 3.0 |
| Returns & Voids | `sales` | 5.0 |
| Documents: Invoice, Delivery Receipt, Reprint | `documents` | 6.0 |
| Maya Payments: Pay with Maya, checkout link and QR, status | `payments` | 3.0 |
| Dashboard | `core` | 7.0 |
| Reports & Search: Transactions, Sales, Stock, Inventory Summary, Activity, Audit Log | `reports` (+ `core.AuditLog`) | 7.0 |

Data stores D1 to D7 map to: `accounts.Profile` (D1), `catalog` (D2), `stock.StockMovement` (D3),
`sales.Order/OrderItem` (D4), `documents.Document` (D5), `sales.ReturnRecord` and voided orders (D6),
low-stock alerts (computed live) and reports (D7).

## How it behaves

- Staff can use every operational screen. Only the Admin / Owner sees Staff Accounts and the Audit Log.
- Registering creates a Pending account. It cannot log in until the Admin / Owner approves it.
- Finalizing a sale checks stock, deducts it, and records the movements in one database transaction.
  If any item is short, nothing changes.
- Stock quantity only changes through stock movements, so the Movements tab is a full history.
- Returns put items back in stock. Exchanges swap stock and record any price difference.
  Voiding a sale puts the not-yet-returned items back.
- Document serial numbers must be filled in and unique per document type. Printing records the document;
  Reprint counts reprints.
- Printing: open the print page and use the browser's print dialog. Only the variable data is printed.
  Adjust the millimetre positions at the top of `templates/documents/print.html` to match your form
  (the paper size is set to A5 landscape; change `@page` for other forms).

## Pay with Maya (external API)

Finalized sales with a balance can be paid through **Maya Checkout** (card, Maya wallet or QR). The sale is marked paid
only after Maya confirms the payment with its API. Setup, flow, safety rules and tests: `docs/api-integration.md`.

1. Create sandbox keys in Maya Manager, then copy `.env.example` to `.env` and fill in `MAYA_PUBLIC_KEY` and `MAYA_SECRET_KEY`.
2. Run the app, open **Reports & Search → Transactions** and click **Pay with Maya** on an unpaid sale.
3. Never commit keys. `.env` is git-ignored. On the cloud host set them as environment variables.

## Limits to know about

- "Total sales" is the gross value of finalized orders; refunds from returns are shown on each order but
  are not subtracted from the sales totals.
- Currency is shown as peso (`core/templatetags/ui.py`). Time zone defaults to Asia/Manila (`DJANGO_TIME_ZONE`).
- No Excel import/export or backup screen (the updated wireframe has no Data page). Back up by copying
  `db.sqlite3`, or with `mysqldump` when using MySQL.

## Deploy notes (cloud plan)

- `Dockerfile` builds the web container (Gunicorn + WhiteNoise for static files).
  Environment: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
  `DJANGO_SECURE=1` (behind HTTPS), `MAYA_PUBLIC_KEY`, `MAYA_SECRET_KEY`, `MAYA_BASE_URL`, `SITE_URL` (public address, needed for the Maya webhook), and `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` for MySQL.
- `/health/` returns `{"status": "ok"}` for uptime checks.
- `.github/workflows/ci.yml` runs checks and tests on pull requests, and builds the image on pushes.
- `docker-compose.yml` starts the app with MySQL locally. The MySQL setup was written but not run
  during development (the tests and the demo ran on SQLite), so try it before relying on it.

## Study guides

`study-guides/` has one guide per area (core and deployment, UI/UX, accounts-products-stock,
sales-and-documents, reports-and-QA) and `docs/database-schema.md` lists every table and key.

## Deploy free on Render

1. Push this folder to a GitHub repository (`.env` and `db.sqlite3` are git-ignored).
2. On https://render.com choose **New → Blueprint**, pick the repo. `render.yaml` sets everything up.
3. In the service's **Environment** tab fill `MAYA_PUBLIC_KEY`, `MAYA_SECRET_KEY` and `SITE_URL` (your `https://<name>.onrender.com` address).
4. Open the `onrender.com` link and log in with the demo accounts above (change the passwords).

Free plan notes: the site sleeps after about 15 minutes idle (the first visit then takes ~1 minute), and the SQLite file
is wiped on each deploy or restart, so the demo data is re-created automatically by `build.sh`. For data that must
persist, create a Render Postgres database and set its `DATABASE_URL` on the web service (free ones expire after 30 days).
