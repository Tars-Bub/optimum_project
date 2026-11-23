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

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.

## Demo Accounts

| Role | Username | Password |
|---|---|---|
| Admin / Owner | `admin` | `admin12345` |
| Staff | `staff1` | `staff12345` |

Change these passwords before using real data. To start empty instead of demo data, skip `seed_demo` and run `python manage.py createsuperuser`.

## Tests

```bash
python manage.py test
python manage.py test payments
python manage.py test            # all unit and integration tests, including payments
python manage.py test payments   # Maya integration only
```

API response tests (Postman / Newman) are in `postman/`. See `docs/api-integration.md`.

## Screens and Where the Code Lives

| Screen | App | Process |
|---|---|---|
| Log in / Register Staff Account | `accounts` | 1.0 |
| Staff Accounts (Admin only), Pending Registrations | `accounts` | 1.0 |
| Categories & Products | `catalog` | 2.0 |
| Stock: Levels, Incoming, Adjust, Movements, Alerts | `stock` | 4.0 |
| Sales: cart, drafts, payment, finalize | `sales` | 3.0 |
| Returns & Voids | `sales` | 5.0 |
| Documents: Invoice, Delivery Receipt, Reprint | `documents` | 6.0 |
| Maya Payments | `payments` | 3.0 |
| Dashboard | `core` | 7.0 |
| Reports & Search | `reports` | 7.0 |

## How It Behaves

- Staff can use every operational screen. Only the Admin / Owner sees Staff Accounts and the Audit Log.
- Registering creates a Pending account. It cannot log in until the Admin / Owner approves it.
- Finalizing a sale checks stock, deducts it, and records the movements in one database transaction.
- Stock quantity only changes through stock movements.
- Returns put items back in stock. Exchanges swap stock and record any price difference.
- Voiding a sale puts the not-yet-returned items back.
- Document serial numbers must be filled in and unique per document type.
- Printing uses the browser's print dialog.

## Pay with Maya

Finalized sales with a balance can be paid through Maya Checkout (card, Maya wallet or QR). The sale is marked paid only after Maya confirms the payment with its API.

1. Create sandbox keys in Maya Manager.
2. Copy `.env.example` to `.env`.
3. Fill in `MAYA_PUBLIC_KEY` and `MAYA_SECRET_KEY`.
4. Never commit keys.

## Limits to Know About

- Total sales is the gross value of finalized orders.
- Refunds from returns are shown on each order but are not subtracted from sales totals.
- Currency is shown as peso.
- Time zone defaults to Asia/Manila.

## Deploy Notes

- `Dockerfile` builds the web container.
- `/health/` returns `{"status": "ok"}` for uptime checks.
- `docker-compose.yml` starts the app with MySQL locally.
- `.env` and `db.sqlite3` should not be committed.

## Deploy Free on Render

1. Push this folder to a GitHub repository.
2. On Render choose New → Blueprint.
3. Select the repository.
4. Configure the Maya environment variables and `SITE_URL`.

## SMS (PhilSMS)

Set `PHILSMS_API_TOKEN` and optionally `PHILSMS_SENDER_ID` and `SMS_OWNER_NUMBER` in `.env` or the Render environment.

- Receipt: A receipt text is sent when a sale is finalized.
- Payment link: Send an SMS from a Maya checkout page.
- Low-stock alert: The owner receives a text when an item reaches its reorder level.
- SMS Messages page lists sent messages and failed messages that can be retried.
