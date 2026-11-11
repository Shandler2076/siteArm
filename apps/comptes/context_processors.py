from django.conf import settings


def site(request):
    return {"site_demo": getattr(settings, "SITE_DEMO", False)}
