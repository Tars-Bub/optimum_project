# Optimum: UI base (Phase 1)

A simple clickable UI for the Optimum Inventory Tracking and Sales Processing System.
Every screen from the wireframe opens and links together, but nothing is saved yet:
all numbers and rows are sample data written in `web/views.py`.

## Run it

Needs Python 3.10 or newer.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

Open http://127.0.0.1:8000 and click "Log in" (no real login yet). Run the check with `python manage.py test`.

## Screens

Log in, Register Staff Account, Dashboard, Categories & Products, Stock (Levels, Incoming, Adjust,
Movements, Alerts), Sales (New Sale, Drafts), Returns & Voids, Documents (Invoice, Delivery Receipt,
Reprint), Reports & Search, Staff Accounts (Admin). Pages and tabs are in `web/templates/web/`.

## What comes next

See `TASKS.md` for what each member builds on top of this base, and `CONTRIBUTING.md` for the
branch and pull request rules.
