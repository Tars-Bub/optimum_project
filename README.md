# Optimum Inventory Tracking and Sales Processing System

Work in progress: stage 1 of 6.

**Included so far:** Settings, database, audit log, login and logout, Register Staff Account (pending until approved), Staff Accounts screen (Admin only), page layout and styling.

## Run it

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000. Run the tests with `python manage.py test`.
