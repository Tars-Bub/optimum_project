from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'dev-only-key-change-me'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']

INSTALLED_APPS = ['django.contrib.staticfiles', 'web']
MIDDLEWARE = ['django.middleware.common.CommonMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'web.context.nav',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'
# No database yet: the group adds models and a DATABASES setting in the next phases.
DATABASES = {}
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
USE_TZ = True
TIME_ZONE = 'Asia/Manila'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
