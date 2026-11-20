# Optimum Inventory Tracking and Sales Processing System

Work in progress: stage 3 of 6.

**Included so far:** Sales cart with drafts and payments, Finalize Sale, Returns & Voids, and the full Dashboard.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.
