from .base import *

DEBUG = False

# Security settings
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Production allowed hosts should be set via env
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['propscope.com'])
