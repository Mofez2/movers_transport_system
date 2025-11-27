from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User


# ==========================
# 🚚 VEHICLE MODEL
# ==========================
class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('van', 'Van'),
        ('truck', 'Truck'),
        ('refrigerated', 'Refrigerated Truck'),
    ]

    name = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    registration_number = models.CharField(max_length=50, unique=True)
    capacity = models.FloatField(help_text="Capacity in tons")
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_vehicle_type_display()})"


# ==========================
# 🚛 FLEET MODEL (NEW)
# ==========================
# core/models.py (modify Fleet model)
class Fleet(models.Model):
    """
    Fleet is linked to a vehicle type so the system can auto-match:
    - vans → van fleets
    - trucks → truck fleets
    - refrigerated → refrigerated fleets
    """
    FLEET_TYPES = [
        ('van', 'Van Fleet'),
        ('truck', 'Truck Fleet'),
        ('refrigerated', 'Refrigerated Fleet'),
    ]

    fleet_type = models.CharField(max_length=20, choices=FLEET_TYPES)
    name = models.CharField(max_length=100)
    driver_name = models.CharField(max_length=100)
    # NEW: driver phone
    driver_phone = models.CharField(max_length=20, blank=True, null=True)
    # NEW — REAL DRIVER model link
    driver = models.ForeignKey(
        "Driver",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fleet_driver"
    )
    loader_name = models.CharField(max_length=100, blank=True, null=True)
    # NEW: loader phone
    loader_phone = models.CharField(max_length=20, blank=True, null=True)
    vehicle_number_plate = models.CharField(max_length=50)
    departure_time = models.DateTimeField(blank=True, null=True)
    expected_arrival = models.DateTimeField(blank=True, null=True)
    route_used = models.TextField(blank=True, null=True)

    # NEW: availability flag
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_fleet_type_display()})"

class Driver(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    license_number = models.CharField(max_length=50)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


# ==========================
# 🧰 SERVICE MODEL
# ==========================
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} - KES {self.price}"


# ==========================
# 📦 BOOKING MODEL
# ==========================
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('enroute', 'En Route'),
        ('delivered', 'Delivered'),
    ]

    GOODS_TYPE_CHOICES = [
        ('small', 'Small Household Items'),
        ('large', 'Large Items / Furniture'),
        ('perishable', 'Perishable Goods'),
    ]

    # NEW: REAL DRIVER LINK
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='driver_bookings'
    )

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vehicle = models.ForeignKey('Vehicle', on_delete=models.SET_NULL, null=True, blank=True)
    service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True, blank=True)

    # AUTO-MATCHED FLEET
    fleet = models.ForeignKey('Fleet', on_delete=models.SET_NULL, null=True, blank=True)

    # FLEET SNAPSHOT
    fleet_name = models.CharField(max_length=100, blank=True, null=True)
    driver_name = models.CharField(max_length=100, blank=True, null=True)
    loader_name = models.CharField(max_length=100, blank=True, null=True)
    vehicle_plate = models.CharField(max_length=50, blank=True, null=True)
    departure_time = models.DateTimeField(blank=True, null=True)
    expected_arrival = models.DateTimeField(blank=True, null=True)
    route_used = models.TextField(blank=True, null=True)

    goods_type = models.CharField(max_length=100, choices=GOODS_TYPE_CHOICES, default='small')
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    pickup_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)

    # Coordinates
    pickup_lat = models.FloatField(null=True, blank=True)
    pickup_lng = models.FloatField(null=True, blank=True)
    dropoff_lat = models.FloatField(null=True, blank=True)
    dropoff_lng = models.FloatField(null=True, blank=True)

    # Financials
    distance = models.FloatField(null=True, blank=True)
    base_price = models.FloatField(null=True, blank=True)
    service_price = models.FloatField(null=True, blank=True)
    total_price = models.FloatField(null=True, blank=True)
    deposit_amount = models.FloatField(null=True, blank=True)
    balance_amount = models.FloatField(null=True, blank=True)

    # Mirror price
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} - {self.customer.username}"

    # AUTO CALCULATION + AUTO DRIVER ASSIGNMENT
    def save(self, *args, **kwargs):

        # 🚀 AUTO-ASSIGN DRIVER FROM FLEET
        if self.fleet and hasattr(self.fleet, "driver") and self.fleet.driver:
            self.driver = self.fleet.driver

        # PRICE LOGIC
        if self.base_price is None:
            self.base_price = 0.0

        self.service_price = float(self.service.price) if self.service else 0.0
        self.total_price = float(self.base_price) + float(self.service_price)
        self.deposit_amount = round(self.total_price * 0.3, 2)
        self.balance_amount = round(self.total_price - self.deposit_amount, 2)
        self.price = self.total_price

        super().save(*args, **kwargs)
    delivery_photo = models.ImageField(upload_to="deliveries/", null=True, blank=True)



# ==========================
# 💰 PAYMENT MODEL
# ==========================
class Payment(models.Model):
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    amount = models.FloatField()
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.amount} KES"


# ==========================
# 📍 TRACKING MODEL
# ==========================
class TrackerPing(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ping for Booking #{self.booking.id} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


# ==========================
# ✉️ CONTACT MESSAGE MODEL
# ==========================
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

    class Meta:
        ordering = ['-created_at']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.user.username
