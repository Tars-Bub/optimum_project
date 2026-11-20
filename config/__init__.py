import os

# Only needed when the app is pointed at MySQL (DB_NAME is set); SQLite needs nothing.
if os.environ.get('DB_NAME'):
    try:
        import pymysql

        pymysql.version_info = (2, 2, 1, 'final', 0)
        pymysql.install_as_MySQLdb()
    except ImportError:  # pragma: no cover
        pass
