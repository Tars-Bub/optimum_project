# Optimum Inventory Tracking and Sales Processing System

Work in progress: stage 5 of 6.

**Included so far:** Reports & Search: Transactions, Sales, Stock, Inventory Summary, Activity, Audit Log.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.
