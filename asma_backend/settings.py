"""
Django settings for the Asma Store backend.

This is a lean, real, runnable configuration (SQLite, no external services)
so the project runs immediately with `python manage.py runserver` — no
Postgres/Redis/Celery setup required for local development. Swap the
DATABASES block for Postgres in production; everything else is unaffected.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: replace this before deploying, and load it from an
# environment variable rather than committing it to source control.
SECRET_KEY = 'django-insecure-change-this-before-deploying-asma-store-2026'

DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',       # compresses every HTML/CSS/JS response
    'whitenoise.middleware.WhiteNoiseMiddleware',   # serves + compresses + cache-busts static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'asma_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'store' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.ensure_csrf',
                'store.context_processors.cart_drawer_context',
                'store.context_processors.cart_summary',
                'store.context_processors.wishlist_summary',
                'store.context_processors.nav_categories',
            ],
        },
    },
]

WSGI_APPLICATION = 'asma_backend.wsgi.application'

# SQLite for zero-setup local development / demo purposes.
# For production, point this at PostgreSQL instead:
#   DATABASES = {'default': dj_database_url.config(default=os.environ['DATABASE_URL'])}
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kathmandu'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'store' / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Whitenoise: serves gzip/brotli-compressed static files with far-future
# cache headers and content-hashed filenames (cache-busting on deploy).
# This is real static-file compression/caching, not a config placeholder —
# run `python manage.py collectstatic` before deploying to generate the
# compressed + hashed copies this storage backend serves.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Caching ---
# LocMemCache needs zero setup and works immediately for local dev / small
# deployments. For multi-process production (gunicorn with several workers),
# swap this for Redis by installing django-redis and changing BACKEND +
# LOCATION — the cache_page/cache calls in views.py don't need to change.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'asma-store-cache',
    }
}
CACHE_MIDDLEWARE_SECONDS = 300

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'store:login'
LOGIN_REDIRECT_URL = 'store:account'
LOGOUT_REDIRECT_URL = 'store:home'
