from .models import Notification


def notify_users(users, title, message="", link=""):
    """Create in-app notifications for a list of users."""
    objs = [
        Notification(user=user, title=title, message=message, link=link)
        for user in users
    ]
    return Notification.objects.bulk_create(objs)
