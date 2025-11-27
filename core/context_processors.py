from datetime import datetime
from .models import ContactMessage
from django.conf import settings

def unread_messages_count(request):
    """Returns the number of unread messages."""
    try:
        count = ContactMessage.objects.filter(is_read=False).count()
        return {"unread_count": count}
    except Exception:
        return {"unread_count": 0}

def current_year(request):
    """Adds the current year to all template contexts."""
    return {"current_year": datetime.now().year}

def admin_email(request):
    return {'ADMIN_EMAIL': getattr(settings, 'ADMIN_EMAIL', 'admin@example.com')}