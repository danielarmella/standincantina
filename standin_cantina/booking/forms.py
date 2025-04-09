
import json
from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget, AutocompleteSelect
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.forms import MultiWidget, MultiValueField, IntegerField, inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.timezone import now
from .models import (
    User,
    AD,
    Actor,
    Project,
    StandIn,
    HairColor,
    Incident,
    MediaUpload,
    Review,
    DNR,
    ActorStandInMatch,
    Availability,
    AvailabilityDateRange,
    Booking,
    AvailCheck,
    BookingRequest,
    BookingRequestImage,
    GENDER_CHOICES,
    SKIN_TONE_CHOICES,
    HAIR_COLOR_CHOICES,
    HAIR_LENGTH_CHOICES,
    INCIDENT_CHOICES,
)
from standin_cantina.settings import EMAIL_HOST_USER


# class CustomCheckboxWidget(forms.CheckboxInput):
#     def render(self, name, value, attrs=None, renderer=None):
#         checkbox_html = super().render(name, value, attrs, renderer)
#         checkbox_label, checkbox_input = checkbox_html.split('<input')
#         checkbox_input = '<input' + checkbox_input
#         checkbox_html = f'{checkbox_input}{checkbox_label}'
#         return checkbox_html

class HeightWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = [
            forms.NumberInput(attrs={'placeholder': 'Feet', 'min': 1, 'max': 9}),
            forms.NumberInput(attrs={'placeholder': 'Inches', 'min': 0, 'max': 11})
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            feet = value // 12
            inches = value % 12
            return [feet, inches]
        return [None, None]


class HeightField(MultiValueField):
    def __init__(self, *args, **kwargs):
        fields = (
            IntegerField(min_value=1, max_value=9, error_messages={'min_value': 'Feet must be between 1-9.', 'max': 'Feet must be between 1-9.'}),
            IntegerField(min_value=0, max_value=11, error_messages={'min_value': 'Inches must be 0 or greater.', 'max_value': 'Inches must be less than 12.'}),
        )
        widget = HeightWidget()
        super().__init__(fields=fields, widget=widget, *args, **kwargs)

    def compress(self, data_list):
        if data_list:
            try:
                feet = int(data_list[0]) if data_list[0] is not None else 0
                inches = int(data_list[1]) if data_list[1] is not None else 0
                return feet * 12 + inches
            except (ValueError, TypeError):
                raise forms.ValidationError("Enter valid numbers for feet and inches.")
        return None


class UserRegistrationForm(UserCreationForm):
    # Override the email field to be required
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email', "password1", "password2",'birthday', "is_standin"]
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Enter your first name', 'required': True}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Enter your last name', 'required': True}),
            'phone': forms.TextInput(attrs={'placeholder': 'e.g., +1 123-456-7890', 'type': 'tel', 'required': True}),
            'email': forms.EmailInput(attrs={'placeholder': 'example@domain.com', 'type': 'email'}),
            'password1': forms.PasswordInput(attrs={'placeholder': 'Enter your password', 'required': True}),
            'password2': forms.PasswordInput(attrs={'placeholder': 'Confirm your password', 'required': True}),
            'birthday': forms.DateInput(attrs={'type': 'date'}),
            'is_standin': forms.CheckboxInput()
        }
        help_texts = {
            'phone': "Include your country code (e.g., +1 for the US).",
            'password1': "Must be at least 8 characters and contain a mix of letters and numbers.",
            'password2': "Re-enter your password for confirmation.",
            'is_standin': '<ul><li>Check to register as a stand-in.</li><li>Leave unchecked to register as staff only</li></ul>'
        }

    def serialize(self):
        """Returns a JSON-compatible dictionary representation of the form's cleaned data."""
        if not self.is_valid():
            return json.dumps({"error": "Form is not valid", "errors": self.errors})

        return json.dumps({
            "first_name": self.cleaned_data.get("first_name", ""),
            "last_name": self.cleaned_data.get("last_name", ""),
            "phone": self.cleaned_data.get("phone", ""),
            "email": self.cleaned_data.get("email", ""),
            "birthday": self.cleaned_data.get("birthday").isoformat() if self.cleaned_data.get("birthday") else None,
            "is_standin": self.cleaned_data.get("is_standin", False),
        }, indent=4)


class ADForm(forms.ModelForm):
    class Meta:
        model = AD
        fields = ['first_name', 'last_name', 'email', 'phone']


class ActorAdminForm(forms.ModelForm):
    height_in_inches = HeightField(label="Height (feet and inches)")

    class Meta:
        model = StandIn
        fields = '__all__'


class ActorForm(forms.ModelForm):
    class Meta:
        model = Actor
        fields = [
            'first_name', 'last_name', 'birth_year', 'gender',
            'height_in_inches', 'weight_in_lbs', 'skin_tone', 'hair_length', 'headshot'
        ]
        widgets = {
            'gender': forms.Select(choices=GENDER_CHOICES),
            'skin_tone': forms.Select(choices=SKIN_TONE_CHOICES),
            'hair_length': forms.Select(choices=HAIR_LENGTH_CHOICES),
        }


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'ads']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'gender': "Select your gender identity.",
            'height_in_inches': "Enter your height in inches (e.g., 72 for 6 feet).",
            'weight_in_lbs': "Enter your weight in pounds (optional).",
            'skin_tone': "Select your skin tone from the available options.",
            'hair_length': "Select your current hair length.",
            'age_range_min': "Enter the youngest age you can reasonably portray.",
            'age_range_max': "Enter the oldest age you can reasonably portray.",
            'matched_actors': "Select actors you have previously stood in for (if any).",
            'notes': "Include any additional details relevant to your stand-in profile.",
        }


class StandInAdminForm(forms.ModelForm):
    height_in_inches = HeightField(label="Height (feet and inches)")

    class Meta:
        model = StandIn
        fields = '__all__'


class StandInForm(forms.ModelForm):
    height_in_inches = HeightField()
    recommended_by = forms.ModelChoiceField(
        queryset=StandIn.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label="Endorsed by",
        help_text="Select the stand-in who recommended you."
    )

    class Meta:
        model = StandIn
        fields = [
            'user', 'recommended_by', 'gender', 'height_in_inches', 'weight_in_lbs',
            'skin_tone', 'hair_length', 'age_range_min', 'age_range_max', 'matched_actors'
        ]
        widgets = {
            'gender': forms.Select(choices=GENDER_CHOICES),
            'skin_tone': forms.Select(choices=SKIN_TONE_CHOICES),
            'hair_length': forms.Select(choices=HAIR_LENGTH_CHOICES),
        }

        user = forms.CharField(disabled=True)
        recommended_by = forms.ModelChoiceField(queryset=StandIn.objects.all(), empty_label="Stand-in list")


class HairColorForm(forms.ModelForm):
    class Meta:
        model = HairColor
        fields = ['standin', 'hair_color']
        widgets = {
            'hair_color': forms.Select(choices=HAIR_COLOR_CHOICES),
        }


class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = ['standin', 'complainant', 'incident', 'note', 'needs_followup']
        widgets = {
            'incident': forms.Select(choices=INCIDENT_CHOICES),
            'note': forms.Textarea(attrs={'rows': 4}),
        }


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = MediaUpload
        fields = ['user', 'image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'}),
        }


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['standin', 'ad', 'feedback', 'is_positive']
        widgets = {
            'feedback': forms.Textarea(attrs={'rows': 4}),
        }


class DNRForm(forms.ModelForm):
    class Meta:
        model = DNR
        fields = ['standin', 'ad', 'project', 'reason']
        widgets = {
            'reason': forms.Textarea(attrs={'rows': 4}),
        }


class ActorStandInMatchForm(forms.ModelForm):
    class Meta:
        model = ActorStandInMatch
        fields = ['actor', 'standin']


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['standin', 'status', 'notes', 'avail_check', 'booking']  # Include other relevant fields
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class AvailabilityDateRangeForm(forms.ModelForm):
    class Meta:
        model = AvailabilityDateRange
        fields = ['start_date', 'end_date']

    def clean(self):
        super().clean()
        start_date = self.cleaned_data.get("start_date")
        end_date = self.cleaned_data.get("end_date")

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date must be after start date.")
            if (end_date - start_date).days > 365:
                raise forms.ValidationError("Date range cannot exceed 1 year.")
            
        # widgets = {
        #     'start_date': forms.DateInput(attrs={'type': 'date'}),
        #     'end_date': forms.DateInput(attrs={'type': 'date'}),
        # }


AvailabilityDateRangeFormSet = inlineformset_factory(
    Availability,
    AvailabilityDateRange,
    form=AvailabilityDateRangeForm,
    extra=1,
    min_num=1,
    validate_min=True,
    can_delete=True
)


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['standin', 'project', 'email_reminder_sent']
        # widgets = {
        #     'start_date': forms.DateInput(attrs={'type': 'date'}),
        #     'end_date': forms.DateInput(attrs={'type': 'date'}),
        # }


# Might be Deprecated since stand-in field was changed to ManyToManyField
# For use with the Create AvailCheck action
# class AvailCheckForm(forms.ModelForm):
#     # project = forms.ModelChoiceField(
#     #     queryset=Project.objects.all(),
#     #     widget=AutocompleteSelect(AvailCheck.project.field.remote_field, admin.site)
#     #     )

#     start_date = forms.DateField(
#         input_formats=['%Y-%m-%d'],
#         widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
#         )
#     end_date = forms.DateField(
#         input_formats=['%Y-%m-%d'],
#         widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
#         )

#     class Meta:
#         model = AvailCheck
#         fields = ['project', 'start_date', 'end_date']
#         autocomplete_fields = ('project',)
#         # widgets = {
#         #     # 'project': AutocompleteSelect(AvailCheck._meta.get_field('project').remote_field, admin.site),
#         #     'start_date': AdminDateWidget(attrs={'type': 'date', 'class': 'form-control'}),
#         #     'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#         # }


class MultiStandInAvailCheckForm(forms.ModelForm):
    standins = forms.ModelMultipleChoiceField(
        queryset=StandIn.objects.all(),
        widget=forms.SelectMultiple,  # You can also use an autocomplete widget if desired
        label="Stand-ins"
    )

    class Meta:
        model = AvailCheck
        fields = ['standins', 'project']
        widgets = {
            'project': AutocompleteSelect(AvailCheck._meta.get_field('project').remote_field, admin.site),
            'start_date': AdminDateWidget(),
            'end_date': AdminDateWidget(),
        }
        help_texts = {
            'start_date': "yyyy-mm-dd",
            'end_date': "yyyy-mm-dd",
        }


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ["project", "start_date", "end_date", "actors", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            'notes': forms.Textarea(attrs={'rows': 2, 'cols': 80, 'style': 'width: 100%;'})
        }

    def __init__(self, *args, **kwargs):
        super(BookingRequestForm, self).__init__(*args, **kwargs)

        # Check if the form is associated with an existing BookingRequest instance
        if self.instance and self.instance.pk:
            # If the BookingRequest instance has an ID, include it in the text field's id
            booking_request_id = self.instance.pk
            self.fields['notes'].widget.attrs['id'] = f'formText{booking_request_id}'

    def save(self, commit=True):
        booking_request = super().save(commit=False)
        if commit:
            booking_request.save()
            self.save_m2m()  # Save the many-to-many field (actors)

            # Handle multiple image uploads
            images = self.files.getlist("images")
            for image in images:
                BookingRequestImage.objects.create(request=booking_request, image=image)

        return booking_request


class BookingRequestImageForm(forms.ModelForm):
    class Meta:
        model = BookingRequestImage
        fields = ["image"]