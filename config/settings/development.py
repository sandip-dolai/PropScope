from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# Email backend for development (outputs to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
