from django.apps import AppConfig
import sys
import threading


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        """
        Load signals and restart tracking threads ONLY when the server starts.
        Avoid running during migrations or collectstatic.
        """

        # Prevent signals during migration/static processes
        if any(cmd in sys.argv for cmd in ["migrate", "makemigrations", "collectstatic", "shell"]):
            return

        # Load signals safely
        try:
            import core.signals
        except Exception:
            return

        # Restart active trackers
        try:
            from .models import Booking
            from .signals import simulate_tracking, ACTIVE_TRACKERS

            # Resume bookings that should still be tracked
            pending = Booking.objects.filter(status__in=["pending", "confirmed", "enroute"])

            for booking in pending:
                if booking.id not in ACTIVE_TRACKERS:
                    t = threading.Thread(target=simulate_tracking, args=(booking.id,))
                    t.daemon = True
                    ACTIVE_TRACKERS[booking.id] = t
                    t.start()
                    print(f"♻️ Tracking restarted for Booking #{booking.id}")

        except Exception:
            pass
