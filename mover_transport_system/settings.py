from pathlib import Path
from datetime import datetime
import os
import sys
import dj_database_url  # For PostgreSQL/Render compatibility

# ===========================================
# 📦 BASE DIRECTORY
# ===========================================
BASE_DIR = Path(__file__).resolve().parent.parent

# ===========================================
# 🔐 SECURITY SETTINGS
# ===========================================
SECRET_KEY = os.environ.get('SECRET_KEY', 'unsafe-default-key')
DEBUG = True  # ✅ For development; set to False in production

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'corrine-laevo-tess.ngrok-free.dev',
    'movers-transport-system-1.onrender.com',
]

# ✅ CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    "https://movers-transport-system-1.onrender.com",
]

# ✅ Ensure session cookies persist correctly on Render
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

# ✅ Render HTTPS fix and persistent session setup
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 1 week
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

# Allow dynamic Render host if provided
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# ===========================================
# 🧩 INSTALLED APPS
# ===========================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django_extensions',


    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Local app
    'core',
]

SITE_ID = 1

# ===========================================
# ⚙️ MIDDLEWARE
# ===========================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ===========================================
# 🌍 URLS / WSGI / ASGI
# ===========================================
ROOT_URLCONF = 'mover_transport_system.urls'
WSGI_APPLICATION = 'mover_transport_system.wsgi.application'
ASGI_APPLICATION = 'mover_transport_system.asgi.application'

# ===========================================
# 🗄️ DATABASE CONFIGURATION
# ===========================================
# PostgreSQL configuration for Render
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}



# ===========================================
# 🔑 PASSWORD VALIDATORS (optional dev mode)
# ===========================================
AUTH_PASSWORD_VALIDATORS = []

# ======================
# 📦 STATIC & MEDIA FILES
# ======================
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===========================================
# ✉️ EMAIL SETTINGS (Mailjet)
# ===========================================
EMAIL_BACKEND = 'core.mailjet_backend.MailjetBackend'
EMAIL_HOST = 'in-v3.mailjet.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = '9267aec548da08ffa76d5662157b3629'
EMAIL_HOST_PASSWORD = 'fab830fa421150e94fd7578b73da344f'
DEFAULT_FROM_EMAIL = 'mohamedbarikabdi6@gmail.com'
ADMIN_EMAIL = 'barikmohamedabdi@gmail.com'

DEFAULT_DOMAIN = "https://movers-transport-system-1.onrender.com"

# ======================
# ✉️ Mailjet API Settings
# ======================
EMAIL_BACKEND = 'core.mailjet_backend.MailjetBackend'

MAILJET_API_KEY = "9267aec548da08ffa76d5662157b3629"
MAILJET_SECRET_KEY = "fab830fa421150e94fd7578b73da344f"
DEFAULT_FROM_EMAIL = "mohamedbarikabdi6@gmail.com"



# Password reset redirect URLs
LOGIN_URL = 'user_login'
LOGOUT_REDIRECT_URL = 'user_login'
LOGIN_REDIRECT_URL = 'admin_dashboard'

# ===========================================
# 🧠 TEMPLATES
# ===========================================
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
                'core.context_processors.unread_messages_count',
                'core.context_processors.current_year',
                'core.context_processors.admin_email',

            ],
        },
    },
]

# ===========================================
# 🔑 AUTHENTICATION / ALLAUTH SETTINGS
# ===========================================
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ======================
# 🔐 AUTH & LOGIN SETTINGS
# ======================
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/login/'

ACCOUNT_FORMS = {
    'login': 'core.forms.CustomLoginForm',
}

# ======================
# 🔐 Django Allauth Modern Configuration
# ======================
ACCOUNT_LOGIN_METHODS = {"username", "email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_SESSION_REMEMBER = True

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': '1059544313536-77nb8l6aqf5ggas97ljpvuba57fuiqvb.apps.googleusercontent.com',
            'secret': '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',
        },
        'SCOPE': ['email', 'profile'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# ===========================================
# 🌍 MPESA CONFIGURATION
# ===========================================
MPESA_ENVIRONMENT = "sandbox"
MPESA_CONSUMER_KEY = "1CSPfTCRYz7zC0DACGNgAxM6iyJYjjRH4pzBzJLdjyt64WA7"
MPESA_CONSUMER_SECRET = "owYHmp0VoAG81OW4VwVILmeysHSmdaI0LsJQwTFcBgjvv9cOugXjV9feIGjngBHE"
MPESA_SHORTCODE = "174379"
MPESA_PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
MPESA_CALLBACK_URL = "https://corrine-laevo-tess.ngrok-free.dev/mpesa/callback/"
MPESA_BASE_URL = "https://sandbox.safaricom.co.ke"

# ===========================================
# 🛡️ CSRF TRUSTED ORIGINS
# ===========================================
CSRF_TRUSTED_ORIGINS = [
    "https://corrine-laevo-tess.ngrok-free.dev",
    "http://corrine-laevo-tess.ngrok-free.dev",
    "https://*.onrender.com",
]

# ===========================================
# 🕓 CUSTOM CONTEXT PROCESSORS
# ===========================================
def current_year(request):
    return {'current_year': datetime.now().year}

# ===========================================
# 🪵 LOGGING CONFIGURATION
# ===========================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'core': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
