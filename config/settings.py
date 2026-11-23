import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')   # must run before any os.environ read below


def env_bool(name, default):
    return os.environ.get(name, '1' if default else '0') == '1'


DEBUG = env_bool('DJANGO_DEBUG', True)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-only-key-change-me')
if not DEBUG and SECRET_KEY == 'dev-only-key-change-me':
    raise RuntimeError('Set DJANGO_SECRET_KEY when DJANGO_DEBUG=0.')

ALLOWED_HOSTS = [h for h in os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',') if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]

# Render sets this automatically (e.g. optimum.onrender.com): allow it without extra setup.
RENDER_HOST = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_HOST}')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'catalog',
    'stock',
    'sales',
    'documents',
    'reports',
    'payments',
    'data',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        'core.context.layout',
    ]},
}]

WSGI_APPLICATION = 'config.wsgi.application'

if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=600)}
elif os.environ.get('DB_NAME'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'core:dashboard'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'Asia/Manila')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Maya Checkout (https://developers.maya.ph). Keys come from the environment, never from the code.
# Sandbox is the default; for live payments set MAYA_BASE_URL=https://pg.paymaya.com with live keys.
MAYA_PUBLIC_KEY = os.environ.get('MAYA_PUBLIC_KEY', '').strip()
MAYA_SECRET_KEY = os.environ.get('MAYA_SECRET_KEY', '').strip()
MAYA_BASE_URL = os.environ.get('MAYA_BASE_URL', 'https://pg-sandbox.paymaya.com').strip()
MAYA_TIMEOUT = int(os.environ.get('MAYA_TIMEOUT', '15'))
# Public address of this site (no trailing slash). Maya sends customers back here and calls the webhook here.
SITE_URL = os.environ.get('SITE_URL', '').strip().rstrip('/')
# DEMO_PAYMENTS=1: when Maya cannot be reached (e.g. its sandbox is down), create a simulated
# checkout page instead of failing, so the payment flow can still be shown. Leave it off for real use.
DEMO_PAYMENTS = env_bool('DEMO_PAYMENTS', False)

# Turn on behind HTTPS in production (cloud host): DJANGO_SECURE=1
if env_bool('DJANGO_SECURE', bool(RENDER_HOST)):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# SMS through PhilSMS (https://app.philsms.com/developers/documentation).
PHILSMS_API_TOKEN = os.environ.get('PHILSMS_API_TOKEN', '').strip()
PHILSMS_SENDER_ID = os.environ.get('PHILSMS_SENDER_ID', 'PhilSMS').strip()
PHILSMS_BASE_URL = os.environ.get('PHILSMS_BASE_URL', 'https://app.philsms.com/api/v3').strip().rstrip('/')
SMS_OWNER_NUMBER = os.environ.get('SMS_OWNER_NUMBER', '').strip()       # gets low-stock alerts
SMS_ENABLED = env_bool('SMS_ENABLED', True)
