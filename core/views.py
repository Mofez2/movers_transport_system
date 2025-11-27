from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django import forms
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.contrib.admin.views.decorators import staff_member_required
from requests.auth import HTTPBasicAuth
from django.contrib.auth.views import PasswordResetView
from .forms import BookingForm
from .models import Payment, Booking
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import timedelta
from core.models import Booking, Payment, ContactMessage
from core.models import Booking, TrackerPing
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from .models import Fleet
from .models import Driver
from .models import Booking, Driver
from .models import UserProfile


import random
import requests
import base64
import datetime
import json
import logging
import time
import csv
import openpyxl
import threading


from .models import Vehicle, Booking, Payment, TrackerPing, ContactMessage, Service
from .forms import BookingForm, ContactAdminForm

logger = logging.getLogger(__name__)

# ======================
# 🏠 HOME PAGE
# ======================
def home(request):
    return render(request, 'core/home.html')


# ======================
# 🔐 USER AUTHENTICATION
# ======================
def user_login(request):
    if request.method == 'POST':
        username_input = request.POST.get('username', '').strip()
        email_input = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = None

        # Try login with username
        if username_input:
            user = authenticate(request, username=username_input, password=password)

        # If failed, try login with email
        if not user and email_input:
            try:
                user_obj = User.objects.get(email__iexact=email_input)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user:
            # 🔥 Create UserProfile BEFORE login redirect / ANY ACCESS
            UserProfile.objects.get_or_create(user=user)

            login(request, user)

            # 🚚 If Driver → Driver dashboard
            if Driver.objects.filter(user=user).exists():
                return redirect('driver_schedule')

            # 👤 Normal user → User dashboard
            messages.success(request, "Logged in successfully.")
            return redirect('user_dashboard')

        else:
            messages.error(request, "Invalid credentials. Try again.")

    return render(request, 'core/user_login.html')
def user_logout(request):
    logout(request)
    return redirect('user_login')


# ======================
# 🌐 GOOGLE SIGN-IN CALLBACK
# ======================
@csrf_exempt
def google_signin_callback(request):
    """
    Handles Google Sign-In callback. In production, verify token properly.
    """
    try:
        messages.success(request, "Signed in with Google successfully.")
        return redirect('user_dashboard')
    except Exception as e:
        logger.error(f"Google Sign-In callback error: {e}")
        return redirect('user_login')

def driver_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('driver_login')  # driver login page
        if not Driver.objects.filter(user=request.user).exists():
            return redirect('home')  # block normal users
        return view_func(request, *args, **kwargs)
    return wrapper

def driver_login(request):
    """
    Driver-only login page. Accepts either 'username' or 'email'.
    Redirects to driver_schedule on success.
    """
    if request.method == "POST":
        identifier = request.POST.get("username") or request.POST.get("email") or ""
        password = request.POST.get("password", "")

        user = None

        # If identifier looks like an email → login via email
        if "@" in identifier:
            try:
                u = User.objects.get(email__iexact=identifier)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        else:
            # Normal username login
            user = authenticate(request, username=identifier, password=password)

        # Check if user is a driver
        if user and Driver.objects.filter(user=user).exists():

            # 🔥 IMPORTANT: Ensure driver has a UserProfile
            UserProfile.objects.get_or_create(user=user)

            login(request, user)
            return redirect("driver_schedule")

        return render(request, "driver/login.html", {"error": "Invalid driver credentials"})

    return render(request, "driver/login.html")
@driver_required
def driver_schedule(request):
    # Get the logged-in driver's profile
    driver = Driver.objects.get(user=request.user)

    # Fetch all bookings assigned to this driver
    jobs = Booking.objects.filter(driver=driver).order_by('-pickup_time')

    return render(request, "driver/schedule.html", {
        "driver": driver,
        "jobs": jobs
    })

@driver_required
def mark_delivered(request, booking_id):
    booking = Booking.objects.get(id=booking_id, driver=Driver.objects.get(user=request.user))
    booking.status = "delivered"
    booking.delivery_time = timezone.now()
    booking.save()
    return redirect("driver_schedule")

@driver_required
def update_status(request, booking_id, status):
    booking = Booking.objects.get(id=booking_id, driver=Driver.objects.get(user=request.user))
    
    if status in ["enroute", "delivered"]:
        booking.status = status
        if status == "delivered":
            booking.delivery_time = timezone.now()
        booking.save()

    return redirect("driver_schedule")
@driver_required
def upload_delivery_photo(request, booking_id):
    booking = Booking.objects.get(id=booking_id, driver=Driver.objects.get(user=request.user))

    if request.method == "POST" and request.FILES.get('photo'):
        booking.delivery_photo = request.FILES['photo']
        booking.status = "delivered"
        booking.delivery_time = timezone.now()
        booking.save()
        return redirect("driver_schedule")

    return render(request, "driver/upload_photo.html", {"booking": booking})



# ======================
# 🧾 USER SIGNUP
# ======================
class CustomSignupForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    mobile = forms.CharField(max_length=15, required=True, label="Mobile Number")

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return p2


def signup(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password1"])
            user.save()

            # Save phone number into UserProfile
            phone = form.cleaned_data.get("mobile")
            UserProfile.objects.filter(user=user).update(phone=phone)

            messages.success(request, "Account created successfully! You can now log in.")
            return redirect("user_login")
    else:
        form = CustomSignupForm()

    return render(request, "core/signup.html", {"form": form})

class CustomPasswordResetView(PasswordResetView):
    template_name = 'core/password_reset.html'
    email_template_name = 'core/password_reset_email.html'
    subject_template_name = 'core/password_reset_subject.txt'
    success_url = '/password-reset/done/'


# ======================
# 👤 USER DASHBOARD
# ======================
@login_required(login_url='/login/')
def user_dashboard(request):
    user = request.user
    user_bookings = Booking.objects.filter(customer=user)

    active_bookings = user_bookings.filter(status__in=['Pending', 'Confirmed', 'In Transit']).count()
    delivered_bookings = user_bookings.filter(status='Delivered').count()
    pending_bookings = user_bookings.filter(status='Pending').count()
    total_payments = (
        Payment.objects.filter(booking__customer=user)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    context = {
        'bookings': user_bookings.order_by('-created_at'),
        'active_bookings': active_bookings,
        'delivered_bookings': delivered_bookings,
        'pending_bookings': pending_bookings,
        'total_payments': total_payments,
    }
    return render(request, 'core/user_dashboard.html', context)


@login_required(login_url='/login/')
def user_dashboard_data(request):
    """AJAX endpoint for live dashboard updates."""
    user = request.user
    bookings = Booking.objects.filter(customer=user)

    active_bookings = bookings.filter(status__in=['Pending', 'Confirmed', 'In Transit']).count()
    delivered_bookings = bookings.filter(status='Delivered').count()
    pending_bookings = bookings.filter(status='Pending').count()
    total_payments = (
        Payment.objects.filter(booking__customer=user)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    return JsonResponse({
        "active_bookings": active_bookings,
        "delivered_bookings": delivered_bookings,
        "pending_bookings": pending_bookings,
        "total_payments": total_payments,
    })


# ======================
# 🚚 USER BOOKING
# ======================
@login_required(login_url='/login/')
def user_booking(request):
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            goods_type = form.cleaned_data['goods_type']

            # 🚚 Choose suitable vehicle type
            if goods_type == 'perishable':
                available_vehicles = Vehicle.objects.filter(vehicle_type='refrigerated', available=True)
            elif goods_type == 'small':
                available_vehicles = Vehicle.objects.filter(vehicle_type='van', available=True)
            else:
                available_vehicles = Vehicle.objects.filter(vehicle_type='truck', available=True)

            if not available_vehicles.exists():
                messages.warning(request, "No suitable vehicles available for your goods type.")
                return redirect('user_booking')

            # 🎯 Create booking
            booking = form.save(commit=False)
            booking.customer = request.user
            booking.vehicle = random.choice(available_vehicles)

            # 🧮 Auto price calc
            booking.base_price = round(random.uniform(1000, 5000), 2)

            # 🧰 Service price
            service = booking.service
            booking.service_price = float(service.price) if service else 0.0

            # 💵 Totals + Save
            booking.save()

            # 👇 **Removed the email popup completely**
            # ❌ messages.success(request, "Please check your email...")

            # Redirect straight to payment or to confirm page, depending on your flow
            return redirect('user_payment', booking_id=booking.id)

    else:
        form = BookingForm()

    services = Service.objects.all()
    return render(request, 'core/user_booking.html', {'form': form, 'services': services})


# ======================
# 💰 PAYMENT PAGE
# ======================
@login_required(login_url='/login/')
def user_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    return render(request, 'core/user_payment.html', {'booking': booking})


# ======================
# 📍 TRACKING
# ======================
@login_required(login_url='/login/')
def user_tracking(request, booking_id):
    """Allow users to track their own booking, and admins to track any booking."""
    if request.user.is_staff:
        # Admin/staff can access any booking
        booking = get_object_or_404(Booking, id=booking_id)
    else:
        # Regular users can only access their own bookings
        booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

    pings = TrackerPing.objects.filter(booking=booking).order_by('-timestamp')
    return render(request, 'core/user_tracking.html', {'booking': booking, 'pings': pings})


@login_required(login_url='/login/')
def user_track_booking(request, booking_id):
    """Allow users to view the latest 10 pings for their booking; admins can view any."""
    if request.user.is_staff:
        booking = get_object_or_404(Booking, pk=booking_id)
    else:
        booking = get_object_or_404(Booking, pk=booking_id, customer=request.user)

    pings = TrackerPing.objects.filter(booking=booking).order_by('-timestamp')[:10]
    return render(request, 'core/user_tracking.html', {'booking': booking, 'pings': pings})


@login_required(login_url='/login/')
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    payments = Payment.objects.filter(booking=booking).order_by('-created_at')
    pings = TrackerPing.objects.filter(booking=booking).order_by('-timestamp')
    context = {
        'booking': booking,
        'payments': payments,
        'pings': pings,
    }
    return render(request, 'core/booking_detail.html', context)
# ======================
# 🗺️ LIVE TRACKER API
# ======================
@login_required(login_url='/login/')
def tracker_api(request, booking_id):
    print(f"🔍 tracker_api called for booking {booking_id}")
    """Return all tracker pings for a booking (latest first)."""
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)

    # Get last 50 pings (or fewer if limited data)
    pings = TrackerPing.objects.filter(booking=booking).order_by('-timestamp')[:50]
    if not pings.exists():
        return JsonResponse({'error': 'No location data found'}, status=404)

    # Return all pings (reversed for correct time order)
    coordinates = [
        {
            'lat': p.latitude,
            'lng': p.longitude,
            'timestamp': p.timestamp.isoformat(),
        }
        for p in reversed(pings)
    ]

    return JsonResponse({'path': coordinates})
# ======================
# ✉️ CONTACT ADMIN (Mailjet)
# ======================
@csrf_exempt
def contact_admin(request):
    """Contact Admin via Mailjet API."""
    if request.method == "POST":
        try:
            if request.headers.get("Content-Type") == "application/json":
                data = json.loads(request.body.decode("utf-8"))
                name = data.get("name", "").strip()
                email = data.get("email", "").strip()
                subject = data.get("subject", "Contact Admin")
                message = data.get("message", "").strip()
            else:
                name = request.POST.get("name", "").strip()
                email = request.POST.get("email", "").strip()
                subject = request.POST.get("subject", "Contact Admin")
                message = request.POST.get("message", "").strip()

            if not name or not email or not message:
                return JsonResponse({"status": "error", "message": "All fields are required."}, status=400)

            api_url = "https://api.mailjet.com/v3.1/send"
            payload = {
                "Messages": [{
                    "From": {"Email": settings.DEFAULT_FROM_EMAIL, "Name": "Movers Transport System"},
                    "To": [{"Email": settings.ADMIN_EMAIL, "Name": "Admin"}],
                    "Subject": f"New Contact Message from {name}",
                    "TextPart": f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                    "HTMLPart": f"<h3>New Contact Message</h3><p><b>Name:</b> {name}</p><p><b>Email:</b> {email}</p><p>{message}</p>"
                }]
            }

            response = requests.post(api_url, auth=(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD), json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("Messages") and result["Messages"][0]["Status"] == "success":
                    return JsonResponse({"status": "success", "message": "Message sent successfully!"})
            return JsonResponse({"status": "error", "message": "Mailjet failed to send."}, status=500)
        except Exception as e:
            logger.error(f"Contact Admin error: {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    return render(request, "core/contact_admin.html")


# ======================
# 🔑 M-PESA TOKEN + STK PUSH + CALLBACK
# ======================
@require_GET
def get_mpesa_access_token(request):
    try:
        url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
        response = requests.get(url, auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))
        if response.status_code == 200:
            return JsonResponse(response.json())
        return JsonResponse({"error": "Failed to generate token"}, status=response.status_code)
    except Exception as e:
        logger.error(f"Token error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
# ================================
# 🔥 AUTO-SUCCESS FALLBACK (10 SEC)
# ================================
def auto_mark_payment_success(payment):
    def run():
        time.sleep(10)  # Wait 10 seconds

        # Only auto-complete if callback hasn't already done it
        p = Payment.objects.filter(id=payment.id, successful=False).first()
        if p:
            p.successful = True
            p.save()

            booking = p.booking
            booking.status = "Paid"
            booking.save()

            logger.info(f"Auto-success applied to Payment {p.id}")

    threading.Thread(target=run).start()


# ======================================
# 🟢 INITIATE STK PUSH (ALWAYS RETURNS OK)
# ======================================
@csrf_exempt
def initiate_stk_push(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        phone = str(data.get("phone") or "").strip()
        booking_id = data.get("booking_id")

        booking = get_object_or_404(Booking, id=booking_id)
        amount = int(round(booking.deposit_amount or 1))

        # Normalize phone to 254...
        if phone.startswith("0") and len(phone) == 10:
            phone = "254" + phone[1:]
        if phone.startswith("+"):
            phone = phone[1:]

        # 1️⃣ Create PENDING payment record
        payment = Payment.objects.create(
            booking=booking,
            phone_number=phone,
            amount=amount,
            successful=False
        )

        # Start 10s auto-mark thread
        auto_mark_payment_success(payment)

        # 2️⃣ Send actual STK push
        try:
            token_url = f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials"
            token_resp = requests.get(
                token_url,
                auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
                timeout=8
            )
            token_resp.raise_for_status()
            token = token_resp.json().get("access_token")

            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            password = base64.b64encode(
                (settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp).encode()
            ).decode()

            stk_payload = {
                "BusinessShortCode": settings.MPESA_SHORTCODE,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": amount,
                "PartyA": phone,
                "PartyB": settings.MPESA_SHORTCODE,
                "PhoneNumber": phone,
                "CallBackURL": settings.MPESA_CALLBACK_URL,
                "AccountReference": str(booking.id),
                "TransactionDesc": f"Booking {booking.id}"
            }

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            r = requests.post(
                f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
                json=stk_payload,
                headers=headers,
                timeout=8
            )
            r.raise_for_status()

            resp_json = r.json()
            checkout_id = resp_json.get("CheckoutRequestID") or f"SIM-{payment.id}"

            payment.transaction_id = checkout_id
            payment.save()

        except Exception as e:
            logger.warning(f"STK Push failed: {e}")
            payment.transaction_id = f"SIM-{payment.id}"
            payment.save()

        # 3️⃣ Always return success — frontend continues regardless of callback
        return JsonResponse({
            "success": True,
            "checkout_id": payment.transaction_id
        })

    except Exception as e:
        logger.exception(f"INITIATE_STK_ERROR: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ==============================
# 🟣 SAFARICOM CALLBACK HANDLER
# ==============================
@csrf_exempt
def mpesa_callback(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
        callback = data.get("Body", {}).get("stkCallback", {})
        result_code = callback.get("ResultCode")

        if result_code == 0:
            metadata = {i["Name"]: i.get("Value") for i in callback["CallbackMetadata"]["Item"]}
            receipt = metadata.get("MpesaReceiptNumber")
            phone = metadata.get("PhoneNumber")
            amount = metadata.get("Amount")
            checkout_id = callback.get("CheckoutRequestID")

            payment = Payment.objects.filter(transaction_id=checkout_id).first()
            if payment:
                payment.successful = True
                payment.transaction_id = receipt
                payment.amount = amount
                payment.save()

                booking = payment.booking
                booking.status = "Paid"
                booking.save()

            return JsonResponse({"ResultCode": 0, "ResultDesc": "Processed"})

        return JsonResponse({"ResultCode": 1, "ResultDesc": "Failed"})

    except Exception as e:
        logger.error(f"MPESA CALLBACK ERROR: {e}")
        return JsonResponse({"error": str(e)}, status=500)


# ==========================
# 🟡 CHECK PAYMENT STATUS API
# ==========================
@require_GET
def check_payment_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    payment = Payment.objects.filter(booking=booking).order_by('-id').first()

    if payment:
        return JsonResponse({
            "successful": payment.successful,
            "amount": float(payment.amount or 0),
            "transaction_id": payment.transaction_id,
            "phone_number": payment.phone_number,
        })

    return JsonResponse({"successful": False, "message": "No payment found."})
# Add to core/views.py (below your other views)
@login_required(login_url='/login/')
def confirm_booking_page(request, booking_id):
    """
    Final booking confirmation page.
    - Auto-assign a matching Fleet if not already assigned
    - Mark the fleet unavailable
    - Snapshot fleet data to booking
    - Confirm booking and start tracking
    """

    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    payment = Payment.objects.filter(booking=booking).order_by('-created_at').first()

    if request.method == "POST":
        try:
            # --------------------------
            # 0. Auto-assign fleet (only if not already assigned)
            # --------------------------
            if not booking.fleet:
                if booking.vehicle:
                    desired_type = booking.vehicle.vehicle_type
                else:
                    mapping = {
                        'small': 'van',
                        'large': 'truck',
                        'perishable': 'refrigerated'
                    }
                    desired_type = mapping.get(booking.goods_type, 'truck')

                fleet = Fleet.objects.filter(
                    fleet_type=desired_type,
                    available=True
                ).first()

                if not fleet:
                    fleet = Fleet.objects.filter(fleet_type=desired_type).first()

                if fleet:
                    with transaction.atomic():
                        fleet.available = False
                        fleet.save()
                        booking.fleet = fleet
                        booking.save()
                else:
                    logger.warning(f"No available fleet found for booking {booking.id} (type={desired_type})")

            # --------------------------
            # 1. Mark payment successful (if not already)
            # --------------------------
            if payment and not payment.successful:
                payment.successful = True
                payment.save()

            # --------------------------
            # 2. Update booking status to Confirmed + snapshot fleet
            # --------------------------
            if booking.status.lower() != "confirmed":
                booking.status = "confirmed"

                if booking.fleet:
                    booking.fleet_name = booking.fleet.name
                    booking.driver_name = booking.fleet.driver_name
                    booking.loader_name = booking.fleet.loader_name or ""
                    booking.vehicle_plate = booking.fleet.vehicle_number_plate
                    # keep fleet.departure_time and expected_arrival as is (they may be set later)
                    booking.departure_time = booking.fleet.departure_time
                    booking.expected_arrival = booking.fleet.expected_arrival
                    booking.route_used = booking.fleet.route_used

                booking.save()

            # --------------------------
            # 3. Start tracking thread (if not already)
            # --------------------------
            try:
                from core.signals import simulate_tracking, ACTIVE_TRACKERS

                if booking.id not in ACTIVE_TRACKERS:
                    t = threading.Thread(target=simulate_tracking, args=(booking.id,))
                    t.daemon = True
                    ACTIVE_TRACKERS[booking.id] = t
                    t.start()
            except Exception as e:
                logger.exception("TRACKING ERROR: %s", e)

            # --------------------------
            # 4. Send confirmation email (Mailjet fallback to Django email)
            # --------------------------
            try:
                email = booking.customer.email
                if email:
                    html_body = render_to_string("emails/booking_confirmation.html", {
                        "booking_id": booking.id,
                        "user": booking.customer.username,
                        "pickup_address": booking.pickup_address,
                        "dropoff_address": booking.dropoff_address,
                        "pickup_time": booking.pickup_time.strftime("%Y-%m-%d %H:%M") if booking.pickup_time else "Pending",
                        "vehicle": booking.vehicle.name if booking.vehicle else "N/A",
                        "service": booking.service.name if booking.service else "N/A",
                        "price": f"{booking.total_price:.2f}" if booking.total_price is not None else "0.00",
                        "deposit": f"{booking.deposit_amount:.2f}" if booking.deposit_amount is not None else "0.00",
                        "balance": f"{booking.balance_amount:.2f}" if booking.balance_amount is not None else "0.00",
                        "fleet_name": booking.fleet_name or "N/A",
                        "driver_name": booking.driver_name or "N/A",
                        "driver_phone": (booking.fleet.driver_phone if booking.fleet else "") or "N/A",
                        "loader_name": booking.loader_name or "N/A",
                        "loader_phone": (booking.fleet.loader_phone if booking.fleet else "") or "N/A",
                        "vehicle_plate": booking.vehicle_plate or "N/A",
                        "departure_time": booking.departure_time.strftime("%Y-%m-%d %H:%M") if booking.departure_time else "Pending",
                        "expected_arrival": booking.expected_arrival.strftime("%Y-%m-%d %H:%M") if booking.expected_arrival else "Pending",
                        "route_used": booking.route_used or "Pending",
                        "tracking_url": request.build_absolute_uri(f"/tracking/{booking.id}/"),
                        "now": timezone.now(),
                    })

                    r = requests.post(
                        "https://api.mailjet.com/v3.1/send",
                        auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
                        json={
                            "Messages": [{
                                "From": {
                                    "Email": settings.DEFAULT_FROM_EMAIL,
                                    "Name": "Movers Transport System"
                                },
                                "To": [{"Email": email}],
                                "Subject": f"Booking Confirmed — #{booking.id}",
                                "HTMLPart": html_body,
                            }]
                        },
                        timeout=10,
                    )

                    if r.status_code != 200:
                        EmailMessage(
                            subject=f"Booking Confirmed — #{booking.id}",
                            body=html_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[email],
                        ).send(fail_silently=True)

            except Exception as e:
                logger.exception("EMAIL ERROR: %s", e)

            # --------------------------
            # Redirect the user to the tracking page (immediately open tracking UI)
            # --------------------------
            return redirect('user_tracking', booking_id=booking.id)

        except Exception as e:
            logger.exception("CONFIRMATION ERROR: %s", e)
            messages.error(request, "Unable to finalize booking. Contact support.")
            return redirect('user_dashboard')

    # GET request — normal page load
    return render(request, 'core/confirm_booking.html', {
        'booking': booking,
        'payment': payment,
    })
# ======================
# 📊 DASHBOARD DATA (Admin Chart)
# ======================
@require_GET
def dashboard_data(request):
    """Provide live stats for admin dashboard charts and KPIs."""
    range_type = request.GET.get("range", "all")
    now = timezone.now()

    # Define time range filter
    if range_type == "week":
        start_date = now - timedelta(days=7)
    elif range_type == "month":
        start_date = now - timedelta(days=30)
    else:
        start_date = None

    bookings = Booking.objects.all()
    payments = Payment.objects.all()

    if start_date:
        bookings = bookings.filter(created_at__gte=start_date)
        payments = payments.filter(created_at__gte=start_date)

    # Chart data: daily revenue + bookings
    days = []
    revenue_values = []
    booking_values = []

    for i in range(7 if range_type == "week" else 30 if range_type == "month" else 10):
        day = now - timedelta(days=i)
        day_label = day.strftime("%Y-%m-%d")
        days.insert(0, day_label)

        day_revenue = payments.filter(created_at__date=day.date()).aggregate(total=Sum("amount"))["total"] or 0
        day_bookings = bookings.filter(created_at__date=day.date()).count()

        revenue_values.insert(0, float(day_revenue))
        booking_values.insert(0, day_bookings)

    # KPIs
    total_revenue = payments.aggregate(total=Sum("amount"))["total"] or 0
    pending_bookings = bookings.filter(status__iexact="pending").count()
    delivered_bookings = bookings.filter(status__iexact="delivered").count()
    unread_messages = ContactMessage.objects.filter(is_read=False).count()

    return JsonResponse({
        "revenue_labels": days,
        "revenue_values": revenue_values,
        "booking_values": booking_values,
        "total_revenue": float(total_revenue),
        "pending_bookings": pending_bookings,
        "delivered_bookings": delivered_bookings,
        "unread_messages": unread_messages,
    })

# ======================
# 🔔 DASHBOARD NOTIFICATIONS
# ======================
@require_GET
def dashboard_notifications(request):
    """Return live notification updates for the admin dashboard."""
    latest_payment = Payment.objects.order_by('-created_at').first()
    latest_booking = Booking.objects.order_by('-created_at').first()
    latest_user = User.objects.order_by('-date_joined').first()
    latest_message = ContactMessage.objects.filter(is_read=False).order_by('-created_at').first()

    data = {
        "timestamp": now().isoformat(),
        "new_payment": {
            "booking_id": latest_payment.booking.id if latest_payment and latest_payment.booking else None,
            "amount": float(latest_payment.amount) if latest_payment else None,
            "created_at": latest_payment.created_at.isoformat() if latest_payment else None,
        } if latest_payment else None,
        "new_booking": {
            "id": latest_booking.id,
            "customer": latest_booking.customer.username if latest_booking.customer else "N/A",
            "created_at": latest_booking.created_at.isoformat(),
        } if latest_booking else None,
        "new_user": {
            "id": latest_user.id,
            "username": latest_user.username,
            "email": latest_user.email,
            "joined": latest_user.date_joined.isoformat(),
        } if latest_user else None,
        "new_message": {
            "id": latest_message.id,
            "name": latest_message.name,
            "email": latest_message.email,
            "created_at": latest_message.created_at.isoformat(),
        } if latest_message else None,
    }

    # ✅ DEBUG: Log notification data to Django console
    import logging
    logger = logging.getLogger(__name__)
    logger.info("📡 Dashboard notifications fetched: %s", data)

    return JsonResponse(data)

# ======================
# 🧭 ADMIN DASHBOARD
# ======================
@staff_member_required
def admin_dashboard(request):
    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    pending_bookings = Booking.objects.filter(status__iexact='pending').count()
    delivered_bookings = Booking.objects.filter(status__iexact='delivered').count()
    unread_messages = ContactMessage.objects.filter(is_read=False).count()

    top_customers = (
        Booking.objects.values('customer__username')
        .annotate(total_bookings=Count('id'))
        .order_by('-total_bookings')[:5]
    )
    top_vehicles = (
        Booking.objects.filter(vehicle__isnull=False)
        .values('vehicle__id', 'vehicle__name')
        .annotate(total_jobs=Count('id'))
        .order_by('-total_jobs')[:5]
    )

    context = {
        'total_revenue': total_revenue,
        'pending_bookings': pending_bookings,
        'delivered_bookings': delivered_bookings,
        'unread_messages': unread_messages,
        'top_customers': top_customers,
        'top_vehicles': top_vehicles,
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def admin_payment_report(request):
    payments = Payment.objects.select_related('booking__customer').order_by('-created_at')

    total_revenue = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_deposits = Booking.objects.aggregate(total=Sum('deposit_amount'))['total'] or 0
    total_balances = Booking.objects.aggregate(total=Sum('balance_amount'))['total'] or 0

    context = {
        'payments': payments,
        'total_revenue': total_revenue,
        'total_deposits': total_deposits,
        'total_balances': total_balances,
    }
    return render(request, 'admin/payment_report.html', context)

@staff_member_required
def booking_report(request):
    bookings = Booking.objects.all().select_related('customer', 'vehicle', 'service')
    total_bookings = bookings.count()
    total_revenue = bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
    total_deposit = bookings.aggregate(Sum('deposit_amount'))['deposit_amount__sum'] or 0
    total_balance = bookings.aggregate(Sum('balance_amount'))['balance_amount__sum'] or 0

    # 🧾 CSV Export
    if 'export' in request.GET:
        export_type = request.GET['export']

        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="booking_report.csv"'
            writer = csv.writer(response)
            writer.writerow([
                'Booking ID', 'Customer', 'Service', 'Vehicle Type', 'Goods Type',
                'Pickup', 'Dropoff', 'Total', 'Deposit', 'Balance',
                'Status', 'Booking Time', 'Payment Time', 'Last Tracked'
            ])
            for b in bookings:
                latest_payment = Payment.objects.filter(booking=b).order_by('-created_at').first()
                last_ping = TrackerPing.objects.filter(booking=b).order_by('-timestamp').first()
                writer.writerow([
                    b.id, b.customer.username,
                    b.service.name if b.service else 'N/A',
                    b.vehicle.vehicle_type if b.vehicle else 'N/A',
                    getattr(b, 'goods_type', 'N/A'),
                    b.pickup_address, b.dropoff_address,
                    b.total_price, b.deposit_amount, b.balance_amount,
                    b.status,
                    b.created_at.strftime('%Y-%m-%d %H:%M'),
                    latest_payment.created_at.strftime('%Y-%m-%d %H:%M') if latest_payment else 'N/A',
                    last_ping.timestamp.strftime('%Y-%m-%d %H:%M') if last_ping else 'N/A'
                ])
            return response

        # 🧾 Excel Export
        elif export_type == 'excel':
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Booking Report'
            ws.append([
                'Booking ID', 'Customer', 'Service', 'Vehicle Type', 'Goods Type',
                'Pickup', 'Dropoff', 'Total', 'Deposit', 'Balance',
                'Status', 'Booking Time', 'Payment Time', 'Last Tracked'
            ])
            for b in bookings:
                latest_payment = Payment.objects.filter(booking=b).order_by('-created_at').first()
                last_ping = TrackerPing.objects.filter(booking=b).order_by('-timestamp').first()
                ws.append([
                    b.id, b.customer.username,
                    b.service.name if b.service else 'N/A',
                    b.vehicle.vehicle_type if b.vehicle else 'N/A',
                    getattr(b, 'goods_type', 'N/A'),
                    b.pickup_address, b.dropoff_address,
                    b.total_price, b.deposit_amount, b.balance_amount,
                    b.status,
                    b.created_at.strftime('%Y-%m-%d %H:%M'),
                    latest_payment.created_at.strftime('%Y-%m-%d %H:%M') if latest_payment else 'N/A',
                    last_ping.timestamp.strftime('%Y-%m-%d %H:%M') if last_ping else 'N/A'
                ])
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="booking_report.xlsx"'
            return response
                # 🧾 PDF Export — Professional Landscape Layout
        elif export_type == 'pdf':
            from reportlab.lib.pagesizes import landscape

            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),  # ✅ Landscape mode
                leftMargin=25,
                rightMargin=25,
                topMargin=60,
                bottomMargin=40
            )
            styles = getSampleStyleSheet()
            elements = []

            # --- LOGO ---
            from reportlab.platypus import Image
            logo_path = "core/static/images/logo.png"
            elements.append(Image(logo_path, width=80, height=50))
            elements.append(Spacer(1, 10))

            # --- HEADER ---
            header_style = styles["Heading1"]
            header_style.textColor = colors.HexColor("#007bff")
            header_style.fontSize = 18
            header_style.spaceAfter = 10
            elements.append(Paragraph("Movers Transport System", header_style))
            elements.append(Paragraph("<b>📊 Booking Report</b>", styles["Heading3"]))
            elements.append(Spacer(1, 10))

            # --- SUMMARY BOX ---
            summary_data = [
                ["Total Bookings", "Total Revenue", "Total Deposits", "Total Balances"],
                [
                    str(total_bookings),
                    f"{total_revenue:,.2f} KES",
                    f"{total_deposit:,.2f} KES",
                    f"{total_balance:,.2f} KES",
                ],
            ]
            summary_table = Table(summary_data, colWidths=[120, 150, 150, 150])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a3eb1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # --- MAIN TABLE DATA ---
            data = [[
                "ID", "Customer", "Service", "Vehicle", "Goods",
                "Total", "Deposit", "Balance", "Status",
                "Booking", "Payment", "Tracked"
            ]]

            for b in bookings:
                latest_payment = Payment.objects.filter(booking=b).order_by("-created_at").first()
                last_ping = TrackerPing.objects.filter(booking=b).order_by("-timestamp").first()
                data.append([
                    b.id,
                    b.customer.username,
                    b.service.name if b.service else "N/A",
                    b.vehicle.vehicle_type if b.vehicle else "N/A",
                    getattr(b, "goods_type", "N/A"),
                    f"{b.total_price or 0:,.2f}",
                    f"{b.deposit_amount or 0:,.2f}",
                    f"{b.balance_amount or 0:,.2f}",
                    b.status,
                    b.created_at.strftime("%Y-%m-%d"),
                    latest_payment.created_at.strftime("%Y-%m-%d") if latest_payment else "N/A",
                    last_ping.timestamp.strftime("%Y-%m-%d") if last_ping else "N/A",
                ])

            # ✅ Wider columns for landscape view
            col_widths = [30, 70, 80, 80, 80, 60, 60, 60, 70, 70, 70, 70]

            table = Table(data, colWidths=col_widths, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2a3eb1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))

            elements.append(table)
            elements.append(Spacer(1, 15))

            # --- FOOTER ---
            footer_text = f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
            elements.append(Paragraph(footer_text, styles["Normal"]))

            # --- BUILD PDF ---
            doc.build(elements)
            pdf = buffer.getvalue()
            buffer.close()

            response = HttpResponse(content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename=\"booking_report.pdf\"'
            response.write(pdf)
            return response



    context = {
        'bookings': bookings,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'total_deposit': total_deposit,
        'total_balance': total_balance,
    }
    return render(request, "admin/core/booking_report.html", context)