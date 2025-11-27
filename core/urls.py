from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .views import admin_payment_report
from .views import booking_report
from .views import driver_login, driver_schedule, mark_delivered


urlpatterns = [
    # 🏠 HOME + AUTH
    path('', views.home, name='home'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('signup/', views.signup, name='signup'),

    # 👤 USER
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/user-data/', views.user_dashboard_data, name='user_dashboard_data'),
    path('book/', views.user_booking, name='user_booking'),
    path('payment/<int:booking_id>/', views.user_payment, name='user_payment'),
    path('tracking/<int:booking_id>/', views.user_tracking, name='user_tracking'),
    path('booking/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:booking_id>/track/', views.user_track_booking, name='user_track_booking'),
    path('confirm-booking/<int:booking_id>/', views.confirm_booking_page, name='confirm_booking'),
    
    # DRIVER PORTAL
    path("driver/login/", driver_login, name="driver_login"),
    path("driver/schedule/", driver_schedule, name="driver_schedule"),
    path("driver/mark-delivered/<int:booking_id>/", mark_delivered, name="mark_delivered"),
    path("driver/update-status/<int:booking_id>/<str:status>/", views.update_status, name="update_status"),
    path("driver/upload-photo/<int:booking_id>/", views.upload_delivery_photo, name="upload_delivery_photo"),



    

    # 🗺️ TRACKER API
    path('api/tracker/<int:booking_id>/', views.tracker_api, name='tracker_api'),


    # ✉️ CONTACT ADMIN
    path('contact-admin/', views.contact_admin, name='contact_admin'),
    path('dashboard-admin/payments/', admin_payment_report, name='admin_payment_report'),
    path('dashboard-admin/reports/', booking_report, name='admin_booking_report'),



    # 💳 M-PESA
    path('mpesa/token/', views.get_mpesa_access_token, name='get_mpesa_access_token'),
    path('mpesa/stkpush/', views.initiate_stk_push, name='initiate_stk_push'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

    # 💵 PAYMENT STATUS API
    path('api/check_payment_status/<int:booking_id>/', views.check_payment_status, name='check_payment_status'),

    # 🧭 ADMIN DASHBOARD
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/admin-data/', views.dashboard_data, name='dashboard_data'),
    path('dashboard/notifications/', views.dashboard_notifications, name='dashboard_notifications'),
    # 🔑 GOOGLE SIGN-IN CALLBACK
    path('google/callback/', views.google_signin_callback, name='google_signin_callback'),

     # Password reset URLs
path('password-reset/',
     auth_views.PasswordResetView.as_view(
         template_name='core/password_reset.html',
         email_template_name='core/password_reset_email.html',
         subject_template_name='core/password_reset_subject.txt',
         success_url='/password-reset/done/'
     ), name='password_reset'),

path('password-reset/done/',
     auth_views.PasswordResetDoneView.as_view(
         template_name='core/password_reset_done.html'
     ), name='password_reset_done'),

path('reset/<uidb64>/<token>/',
     auth_views.PasswordResetConfirmView.as_view(
         template_name='core/password_reset_confirm.html',
         success_url='/reset/complete/'
     ), name='password_reset_confirm'),

path('reset/complete/',
     auth_views.PasswordResetCompleteView.as_view(
         template_name='core/password_reset_complete.html'
     ), name='password_reset_complete'),


]
