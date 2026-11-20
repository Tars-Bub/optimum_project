# Optimum Inventory Tracking and Sales Processing System

Work in progress: stage 2 of 6.

**Included so far:** Categories and Products screens and the Stock screen (Levels, Incoming, Adjust, Movements, Alerts). Adds the demo data command.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.
