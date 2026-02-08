from jinja2 import Environment
from django.urls import reverse
from django.contrib.staticfiles.storage import staticfiles_storage

def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'url': reverse,
        'static': staticfiles_storage.url,
    })
    return env
