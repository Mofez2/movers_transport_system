from django.core.management.base import BaseCommand
from core.models import Booking, TrackerPing
from time import sleep
import random

class Command(BaseCommand):
    help = "Simulates live GPS tracking for a booking."

    def add_arguments(self, parser):
        parser.add_argument("booking_id", type=int, help="Booking ID to simulate movement for")

    def handle(self, *args, **kwargs):
        booking_id = kwargs["booking_id"]

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Booking #{booking_id} not found."))
            return

        self.stdout.write(self.style.SUCCESS(f"🚛 Starting GPS simulation for Booking #{booking_id}"))
        base_lat, base_lng = -1.286389, 36.817223  # Start near Nairobi center

        for i in range(100):
            # Create slight random movement around the base location
            lat = base_lat + random.uniform(-0.02, 0.02)
            lng = base_lng + random.uniform(-0.02, 0.02)
            TrackerPing.objects.create(booking=booking, latitude=lat, longitude=lng)
            self.stdout.write(f"Ping {i+1}: ({lat:.5f}, {lng:.5f})")

            # Wait before next update
            sleep(3)

        self.stdout.write(self.style.SUCCESS("✅ Simulation completed!"))
