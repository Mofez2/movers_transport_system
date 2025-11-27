from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    # 👇 Default Django admin (REAL admin site)
    path('dj-admin/', admin.site.urls),

    # 👇 Custom modern admin dashboard
    path('dashboard-admin/', views.admin_dashboard, name='admin_dashboard'),

    # 👇 Core app (user, booking, etc.)
    path('', include('core.urls')),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='core/password_reset.html'
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='core/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='core/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('accounts/', include('allauth.urls')),
]

# ✅ Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
