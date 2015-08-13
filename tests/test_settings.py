CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
SECRET_KEY = "123456789"
INSTALLED_APPS = (
    'tests',
)
