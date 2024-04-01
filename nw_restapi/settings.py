"""
Django settings for nw_restapi project.

Generated by 'django-admin startproject' using Django 4.2.10.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os
#import ldap
#from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion
import configparser

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

COMMON_CONFIG_FILE = os.path.join(BASE_DIR, 'common.config')
config = configparser.ConfigParser()
config.read(COMMON_CONFIG_FILE)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*b1!0=@bm%hg&)d+%tq=t-o8i_m373+gkb81y^!h=f#b5t!@ld'

# SESSION SETTINGS 
SESSION_COOKIE_AGE = 900
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # change to True if behind ssl-proxy
CSRF_COOKIE_TRUE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = False  # change to True if behind ssl-proxy

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True


SERVER_IP = config.get('COMMON', 'server_ip')
ALLOWED_HOSTS = ['127.0.0.1', SERVER_IP]
CSRF_TRUSTED_ORIGINS = ["http://127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cache_ops.apps.CacheOpsConfig',
    'user_ops.apps.UserOpsConfig',
    'cert_ops.apps.CertOpsConfig',
    'vs_ops.apps.VsOpsConfig',
#    'django_auth_ldap',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nw_restapi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

WSGI_APPLICATION = 'nw_restapi.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # user_added

MEDIA_URL = '/media/'  # user_added
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # user_added

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Ldap Login
LDAP_HOST = config.get('LDAP', 'host')
SEARCH_DN = config.get('LDAP', 'search_dn')
GROUP_DN = config.get('LDAP', 'group_dn')


AUTHENTICATION_BACKENDS = (
#    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
)

#AUTH_LDAP_CONNECTION_OPTIONS = {
#    ldap.OPT_PROTOCOL_VERSION: 3,
#    ldap.OPT_REFERRALS: 0,
#}
AUTH_LDAP_SERVER_URI = f'ldap://{LDAP_HOST}:389'
AUTH_LDAP_BIND_DN = config.get('LDAP', 'bind_dn')
AUTH_LDAP_BIND_PASSWORD = config.get('LDAP', 'bind_pass')
#AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(
#    LDAPSearch(SEARCH_DN, ldap.SCOPE_SUBTREE, f"(&(uid=%(user)s)(memberOf={GROUP_DN},o=BU))")
#)

AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "cn",
    "last_name": "sn",
    "email":"mail"
}

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} - {message}',
            'style': '{',
        },
        'special': {
            'format': '{levelname} {asctime} {module} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO', #INFO
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'{BASE_DIR}/admin.log',
            'formatter': 'special',
            'maxBytes': 1000000000, # 1G
            'backupCount': 200,
        },
    },
    'loggers': {
       'cache_ops': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'cert_ops': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'vs_ops': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        #"django_auth_ldap": {"level": "DEBUG", "handlers": ["console"]}
    }
}

