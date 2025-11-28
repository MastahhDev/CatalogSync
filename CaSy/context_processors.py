# myapp/context_processors.py
from django.conf import settings

def facebook_pixel(request):
    return {
        'FACEBOOK_PIXEL_ID': settings.FACEBOOK_PIXEL_ID
    }