from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.utils import timezone
from .models import Driver
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string


from .models import Vehicle, Booking, Payment, TrackerPing, ContactMessage, Service, Fleet
from .views import booking_report

admin.site.register(Service)

User = get_user_model()


# ==========================
# 💳 INLINE ADMIN CLASSES
# ==========================
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    fields = ['phone_number', 'amount', 'transaction_id', 'successful', 'created_at']
    readonly_fields = ['created_at']
    can_delete = True
    show_change_link = True


class TrackerPingInline(admin.TabularInline):
    model = TrackerPing
    extra = 1
    fields = ['latitude', 'longitude']
    readonly_fields = ['timestamp']
    can_delete = True
    show_change_link = True


# ==========================
# 📦 BOOKING ADMIN
# ==========================
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer', 'pickup_address', 'dropoff_address',
        'status', 'price', 'total_price', 'deposit_amount', 'balance_amount',
        'payment_status', 'latest_location', 'track_link', 'report_link'
    )
    list_display_links = ['id', 'customer']
    list_editable = ['status']
    list_filter = ['status', 'customer__username', 'vehicle__name']
    search_fields = ('customer__username', 'vehicle__name', 'pickup_address', 'dropoff_address')
    list_per_page = 25
    date_hierarchy = 'pickup_time'
    readonly_fields = ['created_at', 'total_price', 'deposit_amount', 'balance_amount']
    inlines = [PaymentInline, TrackerPingInline]

    def payment_status(self, obj):
        payment = Payment.objects.filter(booking=obj).order_by('-created_at').first()
        if not payment:
            return format_html('<span style="color:red;">Unpaid</span>')
        if payment.successful:
            return format_html('<span style="color:green;">Paid</span>')
        return format_html('<span style="color:orange;">Pending</span>')
    payment_status.short_description = 'Payment Status'

    def latest_location(self, obj):
        latest_ping = TrackerPing.objects.filter(booking=obj).order_by('-timestamp').first()
        if latest_ping:
            return f"{latest_ping.latitude:.4f}, {latest_ping.longitude:.4f}"
        return 'No data'
    latest_location.short_description = 'Last Known Location'

    def track_link(self, obj):
        url = reverse('admin:core_booking_track_booking', args=[obj.pk])
        return format_html(
            '<a class="button" style="background:#007bff;color:white;padding:4px 8px;border-radius:4px;" href="{}">Track</a>',
            url
        )
    track_link.short_description = "Live Map"

    def report_link(self, obj=None):
        url = reverse('admin_booking_report')
        return format_html(
            '<a class="button" href="{}" '
            'style="background:#28a745;color:white;padding:5px 10px;'
            'border-radius:4px;text-decoration:none;">📊 Reports</a>',
            url
        )
    report_link.short_description = "Reports"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:booking_id>/track/',
                self.admin_site.admin_view(self.track_booking),
                name='core_booking_track_booking'
            ),
            path(
                '<int:booking_id>/pings/',
                self.admin_site.admin_view(self.get_tracker_pings),
                name='core_booking_get_tracker_pings'
            ),
            path(
                'report/',
                self.admin_site.admin_view(booking_report),
                name='admin_booking_report',
            ),
        ]
        return custom_urls + urls

    def track_booking(self, request, booking_id):
        booking = Booking.objects.get(pk=booking_id)
        return render(request, 'admin/core/track_booking.html', {'booking': booking})

    def get_tracker_pings(self, request, booking_id):
        booking = Booking.objects.get(pk=booking_id)
        latest_ping = TrackerPing.objects.filter(booking_id=booking_id).order_by('-timestamp').first()

        latest_lat = latest_lng = None

        if latest_ping:
            latest_lat, latest_lng = latest_ping.latitude, latest_ping.longitude

            if booking.status in ["Pending", "Confirmed"]:
                booking.status = "En Route"
                booking.save(update_fields=["status"])

            if booking.dropoff_lat and booking.dropoff_lng:
                if abs(booking.dropoff_lat - latest_lat) < 0.001 and abs(booking.dropoff_lng - latest_lng) < 0.001:
                    booking.status = "Delivered"
                    booking.save(update_fields=["status"])

        data = {
            "latitude": latest_lat,
            "longitude": latest_lng,
            "status": booking.status,
            "timestamp": latest_ping.timestamp if latest_ping else None,
        }
        return JsonResponse(data, safe=False)

    class Media:
        js = ("js/admin_live_tracker.js",)


# ==========================
# 💰 PAYMENT ADMIN
# ==========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'phone_number', 'amount', 'transaction_id', 'successful', 'created_at')
    list_filter = ('successful',)
    search_fields = ('booking__id', 'transaction_id', 'phone_number')
    readonly_fields = ['created_at']


# ==========================
# 🚚 VEHICLE ADMIN
# ==========================
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'vehicle_type', 'available')
    list_filter = ('vehicle_type', 'available')
    search_fields = ('name', 'vehicle_type')


# ==========================
# 🛻 FLEET ADMIN (NEW)
# ==========================
@admin.register(Fleet)
class FleetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'fleet_type', 'driver_name', 'vehicle_number_plate')
    list_filter = ('fleet_type',)
    search_fields = ('name', 'driver_name', 'vehicle_number_plate')

@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'vehicle')

    def save_model(self, request, obj, form, change):
        if not obj.user:
            # Auto create user account
            password = get_random_string(8)
            user = User.objects.create_user(
                username=obj.email,
                email=obj.email,
                password=password,
                first_name=obj.name
            )
            obj.user = user

        super().save_model(request, obj, form, change)


# ==========================
# 📍 TRACKER PING ADMIN
# ==========================
@admin.register(TrackerPing)
class TrackerPingAdmin(admin.ModelAdmin):
    list_display = ('booking', 'latitude', 'longitude', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('booking__id',)


# ==========================
# ✉️ CONTACT MESSAGE ADMIN
# ==========================
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('name', 'email', 'message')
