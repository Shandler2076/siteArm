from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def liste(request):
    notifications = list(request.user.notifications.all()[:100])
    request.user.notifications.filter(lue=False).update(lue=True)
    return render(request, "notifications/liste.html", {"notifications": notifications})
