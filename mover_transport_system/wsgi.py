import os
from django.core.wsgi import get_wsgi_application

# Set the settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mover_transport_system.settings')

# Create WSGI application
application = get_wsgi_application()
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mover_transport_system.settings')
application = get_wsgi_application()
