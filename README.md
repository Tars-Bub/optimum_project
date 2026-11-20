# Optimum Inventory Tracking and Sales Processing System

Work in progress: stage 4 of 6.

**Included so far:** Invoice and Delivery Receipt screens, unique serial numbers, Reprint, and the print page.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.
