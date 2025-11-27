from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone

from .models import Booking, TrackerPing, Payment, Fleet
from django.contrib.auth.models import User
from .models import UserProfile

import requests
import logging
import threading
import time
import random
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta

logger = logging.getLogger(__name__)

# ==========================================================
# 🌍 ACTIVE TRACKING THREAD MANAGER
# ==========================================================
ACTIVE_TRACKERS = {}

# simple haversine to compute km between two lat/lng points
def haversine_km(lat1, lon1, lat2, lon2):
    # convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    km = 6371.0 * c
    return km

def simulate_tracking(
        booking_id,
        pickup_lat=-1.2921,
        pickup_lng=36.8219,
        drop_lat=-1.3000,
        drop_lng=36.8300):

    print(f"🚛 Auto-started GPS simulation for Booking #{booking_id}")

    from .models import Booking  # avoid circular import

    step_fraction = 0.05
    current_lat, current_lng = pickup_lat, pickup_lng

    while True:
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            print(f"⚠️ Booking #{booking_id} deleted. Stopping tracker.")
            break

        # 🛑 Stop when delivered
        if booking.status.lower() == "delivered":
            print(f"✅ Booking #{booking_id} delivered. Stopping GPS updates.")
            break

        # Simulate movement
        current_lat += (drop_lat - current_lat) * step_fraction
        current_lng += (drop_lng - current_lng) * step_fraction

        # Add slight random movement
        current_lat += random.uniform(-0.0003, 0.0003)
        current_lng += random.uniform(-0.0003, 0.0003)

        # create ping with server timestamp
        ping = TrackerPing.objects.create(
            booking=booking,
            latitude=current_lat,
            longitude=current_lng,
            timestamp=timezone.now()
        )

        print(f"[AutoPing] Booking {booking_id} → ({current_lat:.5f}, {current_lng:.5f})")

        # sleep a short while between pings
        time.sleep(3)

    ACTIVE_TRACKERS.pop(booking_id, None)
    print(f"🛑 Tracker thread for Booking #{booking_id} stopped.")


# ==========================================================
# 🔄 HANDLE TRACKING LIFECYCLE
# ==========================================================
@receiver(post_save, sender=Booking)
def manage_auto_tracking(sender, instance, created, **kwargs):
    booking_id = instance.id

    if created:
        # initial ping - snapshot the pickup location (so we have at least one ping)
        TrackerPing.objects.create(
            booking=instance,
            latitude=-1.2921,
            longitude=36.8219,
            timestamp=timezone.now()
        )

        # start thread
        t = threading.Thread(target=simulate_tracking, args=(booking_id,))
        t.daemon = True
        ACTIVE_TRACKERS[booking_id] = t
        t.start()

        print(f"🎬 Tracking thread started for Booking #{booking_id}")

    else:
        # if booking was changed to delivered we don't need to do anything special here
        if instance.status.lower() == "delivered" and booking_id in ACTIVE_TRACKERS:
            print(f"🟢 Booking #{booking_id} delivered — stopping tracker.")


# ==========================================================
# 💰 PAYMENT → AUTO CONFIRM BOOKING
# ==========================================================
@receiver(post_save, sender=Payment)
def update_booking_on_payment(sender, instance, created, **kwargs):
    if created and instance.booking:
        booking = instance.booking
        if instance.amount > 0:
            # mark confirmed; final confirmation page still snapshots fleet etc.
            booking.status = "confirmed"
            booking.save(update_fields=["status"])
            print(f"✅ Booking #{booking.id} confirmed after payment.")


# ==========================================================
# 📍 TRACKER PING → UPDATE STATUS, DEPARTURE & ETA
# ==========================================================
@receiver(post_save, sender=TrackerPing)
def update_booking_on_tracker(sender, instance, created, **kwargs):
    if not created:
        return

    booking = instance.booking

    # When movement begins: set status -> enroute
    if booking.status.lower() in ["pending", "confirmed"]:
        booking.status = "enroute"
        # set departure_time when first movement is observed
        if not booking.departure_time:
            booking.departure_time = instance.timestamp
        booking.save(update_fields=["status", "departure_time"])
        print(f"🚚 Booking #{booking.id} started moving (En Route).")

    # Update expected arrival dynamically:
    # estimate remaining distance from current ping to dropoff,
    # then compute ETA using an assumed average speed (40 km/h)
    if booking.dropoff_lat and booking.dropoff_lng:
        try:
            remaining_km = haversine_km(
                instance.latitude,
                instance.longitude,
                booking.dropoff_lat,
                booking.dropoff_lng
            )
            # assumed avg speed in km/h
            avg_speed_kmh = 40.0
            if remaining_km > 0:
                hours = remaining_km / avg_speed_kmh
                eta = instance.timestamp + timedelta(seconds=int(hours * 3600))
                # update booking.expected_arrival if not present or changed significantly
                booking.expected_arrival = eta
                booking.save(update_fields=["expected_arrival"])
        except Exception as e:
            logger.exception("ETA calculation failed: %s", e)

        # Detect arrival (very near)
        lat_diff = abs(booking.dropoff_lat - instance.latitude)
        lng_diff = abs(booking.dropoff_lng - instance.longitude)

        if lat_diff < 0.001 and lng_diff < 0.001:
            booking.status = "delivered"
            booking.save(update_fields=["status"])
            print(f"🏁 Booking #{booking.id} delivered successfully.")


# ==========================================================
# 🚛 AUTO-RELEASE FLEET WHEN BOOKING COMPLETES
# ==========================================================
@receiver(post_save, sender=Booking)
def release_fleet_on_delivery(sender, instance, created, **kwargs):
    """
    When a booking is marked delivered, release the fleet.
    """
    try:
        if instance.status.lower() == "delivered" and instance.fleet:
            fleet = instance.fleet
            if not fleet.available:
                fleet.available = True
                fleet.save()
                print(f"🔓 Fleet '{fleet.name}' released — Booking #{instance.id} delivered.")
    except Exception as e:
        logger.exception(f"Error releasing fleet for Booking {instance.id}: {e}")

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_profile(sender, instance, **kwargs):
    instance.userprofile.save()
