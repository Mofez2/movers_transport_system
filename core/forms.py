from django import forms
from .models import Booking, Service
from django.utils import timezone
import datetime
from allauth.account.forms import LoginForm



class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = [
            'goods_type', 'pickup_address', 'dropoff_address',
            'pickup_time', 'service',
            'pickup_lat', 'pickup_lng', 'dropoff_lat', 'dropoff_lng'
        ]
        widgets = {
            'pickup_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'pickup_lat': forms.HiddenInput(),
            'pickup_lng': forms.HiddenInput(),
            'dropoff_lat': forms.HiddenInput(),
            'dropoff_lng': forms.HiddenInput(),
        }

    def clean_pickup_time(self):
        pickup_time = self.cleaned_data.get('pickup_time')
        now = timezone.now()  # ✅ timezone-aware current time

        if pickup_time and pickup_time < now:
            raise forms.ValidationError("Pickup time cannot be in the past.")
        return pickup_time

class ContactAdminForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)

class CustomLoginForm(LoginForm):
    def login(self, *args, **kwargs):
        # You can add custom login logic here if needed
        return super().login(*args, **kwargs)