from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment-driven settings ---------------------------------------
# These read from environment variables when present (set by Render,
# Replit, or any other host) and fall back to safe defaults for local
# development, so this file works unchanged on your local machine.
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-naub-chatbot-secret-key-change-in-production-2024'
)

# DEBUG defaults to True locally; hosts should set DEBUG=False explicitly.
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS: '*' locally; hosts should set ALLOWED_HOSTS to a comma-
# separated list of their actual domain(s), e.g. "myapp.onrender.com".
_allowed_hosts_env = os.environ.get('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',')] if _allowed_hosts_env != '*' else ['*']

# Replit and Render both put the app behind a reverse proxy on HTTPS;
# this tells Django to trust the proxy's forwarded-proto header so
# CSRF/session cookies behave correctly over HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
_csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_trusted_env.split(',') if o.strip()]

# Tighten cookie/security settings automatically once DEBUG=False is set
# by the host (Render). Left relaxed for local development and for Replit's
# default (DEBUG stays True there unless you set it as a Secret).
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'chatbot',
    'accounts',
    'dashboard',
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
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'naub_chatbot.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'naub_chatbot.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# If a DATABASE_URL is provided (Render, Replit w/ external Postgres, etc.),
# use it instead of SQLite. Local development with no DATABASE_URL set is
# completely unaffected and keeps using the SQLite file above.
_database_url = os.environ.get('DATABASE_URL')
if _database_url:
    import dj_database_url
    # conn_max_age=0 prevents stale-connection SSL errors on serverless databases
    # (e.g. Neon) that close idle connections before Django's 600-second window.
    # conn_health_checks=True makes Django verify the connection is alive before reuse.
    DATABASES['default'] = dj_database_url.parse(
        _database_url,
        conn_max_age=0,
        conn_health_checks=True,
    )

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Auth settings
SITE_ID = 1
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
LOGIN_URL = '/accounts/login/'

# Allauth settings
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': 'your-google-client-id',
            'secret': 'your-google-client-secret',
            'key': ''
        }
    }
}

# Email (console backend for dev)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Chatbot settings
CHATBOT_SIMILARITY_THRESHOLD = 0.35
CHATBOT_CLARIFICATION_MARGIN = 0.12
CHATBOT_GIBBERISH_THRESHOLD = 0.4
