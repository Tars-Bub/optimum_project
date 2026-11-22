import os
from pathlib import Path


def _load_dotenv():
    """Read KEY=value lines from a local .env file (git-ignored). Real environment variables win."""
    path = Path(__file__).resolve().parent.parent / '.env'
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# Only needed when the app is pointed at MySQL (DB_NAME is set); SQLite needs nothing.
if os.environ.get('DB_NAME'):
    try:
        import pymysql

        pymysql.version_info = (2, 2, 1, 'final', 0)
        pymysql.install_as_MySQLdb()
    except ImportError:  # pragma: no cover
        pass
