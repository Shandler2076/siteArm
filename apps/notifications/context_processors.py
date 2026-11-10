def notifications(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"notifications_non_lues": user.notifications.filter(lue=False).count()}
