# Register your models here.
from datetime import date, timedelta
# from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, FloatField, ExpressionWrapper
from django import forms
from django.forms import BaseInlineFormSet, ValidationError
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from .forms import StandInAdminForm, ActorAdminForm, MultiStandInAvailCheckForm, AvailabilityForm
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
    AvailCheck,
    Booking,
    BookingRequest,
)
from standin_cantina.settings import EMAIL_HOST_USER


class BaseAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('/static/admin/css/custom.css',),  # Add your custom CSS files
        }
        js = ('/static/admin/js/custom.js',)  # Add your custom JavaScript files if needed


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'first_name', 'last_name',)

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()
        return user


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm  # Used for adding users
    # form = CustomUserChangeForm  # Used for editing users
    model = User  # Custom user model (if applicable)

    actions = ["approve_users", 'reject_users']
    list_display = ('__str__', 'phone', 'email', 'birthday', "approval_status", "is_standin",)
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('is_active', 'birthday',)
    list_per_page = 12

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name',),
        }),
    )

    fieldsets = (
        (None, {'fields': ('display_main_image', 'username', 'password',)}),  # 'username' will be auto-generated
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone', 'email', 'birthday', "is_standin",)}),
        (_('Permissions'), {
            'classes': ['wide', 'collapse'],
            'fields': ('is_approved', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ('username', 'display_main_image', 'password',)

    def get_search_results(self, request, queryset, search_term):
        # Check if the autocomplete request is for the 'user' field
        # This information is passed via the GET parameter 'field_name'
        if request.GET.get('field_name') == 'user':
            queryset = queryset.filter(is_standin=True)
        return super().get_search_results(request, queryset, search_term)

    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green;">Approved</span>')
        else:
            return format_html('<span style="color: red;">Pending/Rejected</span>')
    approval_status.short_description = "Status"

    @admin.action(description="Approve selected users")
    def approve_users(self, request, queryset):
        queryset.update(is_approved=True, is_active=True)
        for user in queryset:
            self.send_approval_email(user)

    @admin.action(description="Reject selected users")
    def reject_users(self, request, queryset):
        queryset.update(is_approved=False, is_active=False)
        for user in queryset:
            self.send_rejection_email(user)

    def send_approval_email(self, user):
        subject = "Your Account Has Been Approved"
        message = (
            f"Dear {user.first_name},\n\n"
            "We are pleased to inform you that your account has been approved. "
            "You can now log in to our platform.\n\n"
            "Best regards,\nStand-in Cantina Booking"
        )
        send_mail(subject, message, EMAIL_HOST_USER, [user.email], fail_silently=False)

    def send_rejection_email(self, user):
        subject = "Your Account Registration"
        message = (
            f"Dear {user.first_name},\n\n"
            "We regret to inform you that your registration has not been approved at this time.\n\n"
            "Best regards,\nStand-in Cantina Booking"
        )
        send_mail(subject, message, EMAIL_HOST_USER, [user.email], fail_silently=False)

    def display_main_image(self, obj):
        """Displays the main image in the list view"""
        if obj.uploads:
            try:
                main_image = obj.uploads.filter(is_main_image=True).get()
                return mark_safe(f'<img src="/media/{main_image.image}" height="300" />')
            except obj.uploads.model.DoesNotExist:
                return "User has not marked a main image."
        return "No image"

    display_main_image.short_description = 'Main image'

    def custom_add_view(self, request):
        if request.method == "POST":
            form = UserCreationForm(request.POST)
            if form.is_valid():
                form.save()
                # Redirect after successful submission
                self.message_user(request, "User created successfully!")
                return redirect("admin:app_label_user_changelist")
        else:
            form = CustomUserCreationForm(request.POST or None)

        context = self.admin_site.each_context(request)  # Default admin context
        context.update({
            'opts': self.model._meta,
            'form': form,
            'add': True,
            'change': False,
            'is_popup': False,
            'save_as': False,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'has_view_permission': self.has_view_permission(request),
            'has_editable_inline_admin_formsets': False,  # Explicitly set this variable
            'has_delete_permission': self.has_delete_permission(request),
        })
        return TemplateResponse(request, "admin/custom_user_form.html", context)

    # The save_model method is given the HttpRequest, a model instance, a ModelForm instance, and a boolean value based on whether it is adding or changing the object. Overriding this method allows doing pre- or post-save operations. Call super().save_model() to save the object using Model.save().
    def save_model(self, request, obj, form, change):
        if not obj.username:
            obj.username = f"{obj.first_name.lower()}{obj.last_name.lower()}"
        # Only update the password if it's been changed
        if not obj.password:
            obj.password = None
        super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('/static/admin/css/custom.css',),  # Add your custom CSS files
        }
        js = ('/static/admin/js/custom.js',)  # Add your custom JavaScript files if needed


@admin.register(Project)
class ProjectAdmin(BaseAdmin):
    list_display = ('name', 'start_date', 'end_date',)
    search_fields = ('name', 'ads__first_name', 'ads__last_name',)
    list_filter = ('name', 'ads',)

    filter_horizontal = ('ads',)


@admin.register(AD)
class ADAdmin(BaseAdmin):
    list_display = ('__str__', 'email', 'phone', 'most_recent_project',)
    search_fields = ('first_name', 'last_name', 'email', 'most_recent_project',)
    list_filter = ('most_recent_project',)
    list_editable = ('phone', 'most_recent_project',)

    autocomplete_fields = ('most_recent_project',)
    fieldsets = (
        ('Contact', {'fields': ('first_name', 'last_name', 'email', 'phone',)}),
        ('Projects', {'fields': ('most_recent_project', 'list_projects',)}),
    )
    readonly_fields = ('list_projects',)

    def list_projects(self, obj):
        projects = obj.projects.all()

        project_html = " \n".join([
            format_html('<a class="project_link" href="{}">{}</a>', reverse('admin:booking_project_change', args=[project.id]), str(project))
            for project in projects
        ]) if projects else 'No projects listed.'

        return mark_safe(f"{project_html}")

    list_projects.short_description = "Project list"


@admin.register(Actor)
class ActorAdmin(BaseAdmin):
    form = ActorAdminForm
    list_display = ('__str__', 'gender', 'height_in_feet', 'skin_tone',)
    search_fields = ('first_name', 'last_name')
    list_filter = ('first_name', 'last_name', 'gender',)

    fieldsets = (
        ('', {'fields': ('display_headshot', 'first_name', 'last_name',)}),
        ('Appearance', {'fields': ('gender', ('birth_year', 'age',), ('height_in_inches', 'height_in_feet'), 'skin_tone', 'hair_length')}),
        ('Matched StandIns', {'fields': ('matchies',)}),
        ('Headshot', {'fields': ('headshot',)}),
    )
    readonly_fields = ('display_headshot', 'age', 'matchies', 'height_in_feet',)

    def display_headshot(self, obj):
        """Displays the main image in the list view"""
        if obj.headshot:
            headshot = obj.headshot
            return mark_safe(f'<img src="/media/{headshot}" height="300" />')
        return "Actor has no headshot."

    display_headshot.short_description = 'Headshot'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            height_in_feet_calc=ExpressionWrapper(F('height_in_inches') / 12.0, output_field=FloatField())
        )

    def height_in_feet(self, obj):
        return obj.height_ft_in()
    height_in_feet.admin_order_field = 'height_in_feet_calc'  # Enable sorting
    height_in_feet.short_description = 'Height'

    def age(self, obj):
        if obj.birth_year:
            return now().year - obj.birth_year
        return 'Unknown birth year.'

    age.short_description = 'Age'

    def matchies(self, obj):
        # Assuming `matched_standins` is a many-to-many relationship with Actor
        matched_standins = obj.standin_matches.all()

        add_link = reverse('admin:booking_actorstandinmatch_add')  # URL for the ActorStandInMatch add form
        prefill_link = f"{add_link}?actor={obj.id}"  # Pass Actor ID as a query parameter

        # # TESTING
        # print(f'obj = {obj}')
        # for matched_standin in matched_standins:
        #     print(f'matched_standin = {matched_standin}')
        #     match = ActorStandInMatch.objects.filter(standin=matched_standin).first()
        #     print(f'match = {match}')

        matched_standins_html = " \n".join([format_html('<a class="actor_standin_link" href="{}">{}</a>',
                reverse('admin:booking_actorstandinmatch_change', args=[ActorStandInMatch.objects.get(actor=obj, standin=matched_standin.standin).id]), str(matched_standin.standin)) for matched_standin in matched_standins]) if matched_standins else 'No stand-in matches listed.'

        print(f'matched_standins_html = {matched_standins_html}')

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Stand-in Match</a>', prefill_link)

        print(f"{matched_standins_html} {add_button_html}")

        return mark_safe(f"{matched_standins_html} {add_button_html}")

    matchies.short_description = "Matched Stand-ins"


#TODO Each AvailCheck can have multiple standins looks like this creates a separate AvailCheck for each standin instead
@admin.action(description="Create Avail Checks for selected Stand-in(s)")
def create_avail_checks(modeladmin, request, queryset):
    print('in create_avail_checks')
    # If the form is submitted (POST with 'apply' in request.POST)
    if request.method == "POST" and "apply" in request.POST:
        print('POST')
        form = MultiStandInAvailCheckForm(request.POST)
        if form.is_valid():
            print('form is valid')
            project = form.cleaned_data["project"]
            start_date = form.cleaned_data["start_date"]
            end_date = form.cleaned_data["end_date"]
            # notes = form.cleaned_data["notes"]

            # For each selected stand-in, create an AvailCheck
            for standin in queryset:
                avail_check = AvailCheck.objects.create(
                    standin=standin,
                    project=project,
                    is_accepted=False,  # Defaults to not accepted
                    # notes=notes,
                )

                # Send an email notification to the stand-in
                send_mail(
                    subject="New Availability Request",
                    message=(
                        f"Hello {standin.user.first_name},\n\n"
                        f"You have received a new availability request for {project.name}"
                        f"from start_date to end_date.\n"
                        "Please log in to your account to respond."
                    ),
                    from_email=EMAIL_HOST_USER,
                    recipient_list=[standin.user.email],
                    fail_silently=False,
                )
            modeladmin.message_user(request, "Avail Checks created and emails sent.")
            return HttpResponseRedirect(request.get_full_path())
    else:
        # Not a POST submission: instantiate a blank form with defaults
        form = MultiStandInAvailCheckForm(initial={})

    context = {
        "standins": queryset,
        "form": form,
        "title": "Create Avail Checks for selected Stand-ins",
        # include any other context variables your template might need
    }
    print(f'{context =}')
    return render(request, "admin/avail_check_form.html", context)


@admin.register(StandIn)
class StandInAdmin(BaseAdmin):
    list_display = ('__str__', 'user__phone', 'user__email', 'gender', 'height_in_feet', 'skin_tone',)
    actions = [create_avail_checks]
    search_fields = ('user__first_name', 'user__last_name', 'gender', 'height_in_inches', 'user__email', 'skin_tone',)
    list_filter = ('gender', 'height_in_inches', 'skin_tone', 'hair_length',)

    form = StandInAdminForm
    autocomplete_fields = ('user', 'recommended_by',)
    fieldsets = (
        ('', {'classes': ['wide', 'col col6'],'fields': ('display_main_image', 'list_uploads', ('user','recommended_by'),)}),
        ('Appearance', {'classes': ['col col3'],'fields': ('gender', ('height_in_inches', 'height_in_feet',), 'skin_tone', 'hair_length')}),
        ('Notes', {'classes': ['col col3'],'fields': ('notes',)}),
        ('Hair Colors', {'classes': ['col col2'], 'fields': ('list_hair_colors',)}),
        ('Matched Actors', {'classes': ['col col4'],'fields': ('list_matches',)}),
        ('Reviews', {'classes': ['col col2'],'fields': ('list_reviews',)}),
        ('Incidents', {'classes': ['col col2'],'fields': ('list_incidents',)}),
        ('Do Not Recalls', {'classes': ['col col2'],'fields': ('list_DNRs',)}),
        ('Bookings', {'classes': ['col col3'],'fields': ('list_bookings',)}),
        ('Availability', {'classes': ['col col3'],'fields': ('list_availability',)}),
    )
    readonly_fields = ('display_main_image', 'list_uploads', 'height_in_feet', 'list_hair_colors', 'list_matches', 'list_reviews', 'list_incidents', 'list_DNRs', 'list_bookings', 'list_availability',)


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            height_in_feet_calc=ExpressionWrapper(F('height_in_inches') / 12.0, output_field=FloatField())
        )

    def display_main_image(self, obj):
        """Displays the main image in the list view"""

        if obj.user.uploads:
            try:
                main_image = obj.user.uploads.filter(is_main_image=True).get()
                return mark_safe(f'<a class="media_upload_link" href="{reverse('admin:booking_mediaupload_change', args=[MediaUpload.objects.get(image=main_image.image, user=obj.user).id])}"><img src="/media/{main_image.image}" height="300" /></a>')
            except obj.user.uploads.model.DoesNotExist:
                return "Stand-in has not marked a main image."
        return "No image"

    display_main_image.short_description = 'Main image'

    def height_in_feet(self, obj):
        return obj.height_ft_in()
    
    height_in_feet.admin_order_field = 'height_in_feet_calc'  # Enable sorting
    height_in_feet.short_description = 'Height'

    def list_uploads(self, obj):
        uploads = obj.user.uploads.all()

        add_link = reverse('admin:booking_mediaupload_add')  # URL for the MediaUpload add form
        prefill_link = f"{add_link}?user={obj.user.id}"  # Pass StandIn ID as a query parameter
        media_upload_html = ""

        if uploads:
            for upload in uploads:
                if not upload.is_main_image:
                    media_upload_html += " \n".join([format_html('<a class="media_upload_link" href="{}"><img class="media_upload" src="/media/{}" height="150" /></a>', reverse('admin:booking_mediaupload_change', args=[MediaUpload.objects.get(image=upload.image, user=obj.user).id]), upload.image)])
        else:
            'No media had been uploaded yet.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Image</a>', prefill_link)

        return mark_safe(f"{media_upload_html} {add_button_html}")

    list_uploads.short_description = "Images"

    def list_hair_colors(self, obj):
        hair_colors = obj.hair_colors.all()
        add_link = reverse('admin:booking_haircolor_add')  # URL for the HairColor add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        hair_colors_html = " \n".join([
            format_html('<a class="hair_color_link" href="{}">{}</a>', reverse('admin:booking_haircolor_change', args=[hair_color.id]), str(hair_color))
            for hair_color in hair_colors
        ]) if hair_colors else 'No hair colors listed.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Hair Color</a>', prefill_link)

        return mark_safe(f"{hair_colors_html} {add_button_html}")

    list_hair_colors.short_description = "Hair Colors"

    def list_matches(self, obj):
        matched_actors = obj.matched_actors.all()

        add_link = reverse('admin:booking_actorstandinmatch_add')  # URL for the ActorStandInMatch add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        matched_actors_html = " \n".join([
            format_html('<a class="actor_standin_link" href="{}">{}</a>', reverse('admin:booking_actorstandinmatch_change', args=[ActorStandInMatch.objects.get(actor=matched_actor, standin=obj).id]), str(matched_actor))
            for matched_actor in matched_actors
        ]) if matched_actors else 'No actor matches listed.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Actor Match</a>', prefill_link)

        return mark_safe(f"{matched_actors_html} {add_button_html}")

    list_matches.short_description = "Matched Actors"

    def list_reviews(self, obj):
        reviews = Review.objects.filter(standin=obj)

        add_link = reverse('admin:booking_review_add')  # URL for the Review add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        reviews_html = " \n".join([
            format_html('<a class="review_link" href="{}">{}</a>', reverse('admin:booking_review_change', args=[review.id]), str(review))
            for review in reviews
        ]) if reviews else 'No reviews yet.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Review</a>', prefill_link)

        return mark_safe(f"{reviews_html} {add_button_html}")

    list_reviews.short_description = "Reviews"

    def list_incidents(self, obj):
        incidents = Incident.objects.filter(standin=obj)

        add_link = reverse('admin:booking_incident_add')  # URL for the Incident add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        incidents_html = " \n".join([
            format_html('<a class="incident_link" href="{}">{}</a>', reverse('admin:booking_incident_change', args=[incident.id]), str(incident))
            for incident in incidents
        ]) if incidents else 'No incidents reported.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Incident</a>', prefill_link)

        return mark_safe(f"{incidents_html} \n{add_button_html}")

    list_incidents.short_description = "Incidents"

    def list_DNRs(self, obj):
        DNRs = DNR.objects.filter(standin=obj)

        add_link = reverse('admin:booking_dnr_add')  # URL for the Incident add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        DNRs_html = " \n".join([
            format_html('<a class="DNR_link" href="{}">{}</a>', reverse('admin:booking_dnr_change', args=[DNR.id]), str(DNR))
            for DNR in DNRs
        ]) if DNRs else 'No DNRs reported.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add DNR</a>', prefill_link)

        return mark_safe(f"{DNRs_html} \n{add_button_html}")

    list_DNRs.short_description = "DNRs"

    def list_bookings(self, obj):
        bookings = Booking.objects.filter(standin=obj)

        add_link = reverse('admin:booking_booking_add')  # URL for the Booking add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        bookings_html = " \n".join([
            format_html('<a class="booking_link" href="{}">{}</a>', reverse('admin:booking_booking_change', args=[booking.id]), str(booking))
            for booking in bookings
        ]) if bookings else 'No bookings yet.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Booking</a>', prefill_link)

        return mark_safe(f"{bookings_html} \n{add_button_html}")

    list_bookings.short_description = "Bookings"

    def list_availability(self, obj):

        availabilities = Availability.objects.filter(standin=obj, date_ranges__end_date__gte=now().date())

        add_link = reverse('admin:booking_availability_add')  # URL for the Availability add form
        prefill_link = f"{add_link}?standin={obj.id}"  # Pass StandIn ID as a query parameter

        availability_html = " \n".join([
            format_html('<a class="avail_link" style="color: {}" href="{}">{}</a>', 'green' if availability.status == 'available' else 'red',reverse('admin:booking_availability_change', args=[availability.id]), str(availability))
            for availability in availabilities
        ]) if availabilities else 'Unknown availability.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Availability</a>', prefill_link)

        return mark_safe(f"{availability_html} \n{add_button_html}")

    list_availability.short_description = "Availability"


@admin.register(HairColor)
class HairColorAdmin(BaseAdmin):
    list_display = ('standin', 'hair_color')
    search_fields = ('standin__user__first_name', 'standin__user__last_name',)
    list_filter = ('standin', 'hair_color',)

    autocomplete_fields = ('standin',)

    def add_view(self, request, form_url='', extra_context=None):
        standin_id = request.GET.get('standin')  # Get the query parameter
        if standin_id:
            # Set initial data for the form
            self.initial = {'standins': standin_id}  # Pre-fill the form
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


@admin.register(Incident)
class IncidentAdmin(BaseAdmin):
    list_display = ('standin', 'complainant', 'incident', 'date', 'needs_followup')
    search_fields = ('standin__user__first_name', 'standin__user__last_name', 'complainant__first_name', 'complainant__last_name', 'date')
    list_filter = ('standin', 'complainant', 'needs_followup', 'date')

    autocomplete_fields = ('standin', 'complainant',)

    def add_view(self, request, form_url='', extra_context=None):
        standin_id = request.GET.get('standin')  # Get the query parameter
        if standin_id:
            # Set initial data for the form
            self.initial = {'standins': standin_id}  # Pre-fill the form
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


@admin.register(MediaUpload)
class MediaUploadAdmin(BaseAdmin):
    list_display = ('user', 'image', 'is_main_image',)
    search_fields = ('user__first_name', 'user__last_name')
    list_filter = ('is_main_image', 'user',)

    autocomplete_fields = ('user',)

    def save_model(self, request, obj, form, change):
        if obj.is_main_image:
            # Ensure only this image is marked as main
            obj.user.uploads.exclude(pk=obj.pk).update(is_main_image=False)
        elif not obj.user.uploads.filter(is_main_image=True).exists():
            # Ensure at least one image is main
            obj.is_main_image = True
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(BaseAdmin):
    list_display = ('standin', 'ad', 'is_positive', 'date')
    search_fields = ('standin__user__first_name', 'standin__user__last_name', 'ad__first_name', 'ad__last_name')
    list_filter = ('standin', 'ad', 'is_positive',)

    autocomplete_fields = ('standin', 'ad',)
    fieldsets = (
        ('', {'fields': ('standin', 'ad', 'feedback', 'is_positive', 'date')}),
    )

    def add_view(self, request, form_url='', extra_context=None):
        standin_id = request.GET.get('standin')  # Get the query parameter
        if standin_id:
            # Set initial data for the form
            self.initial = {'standins': standin_id}  # Pre-fill the form
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


@admin.register(DNR)
class DNRAdmin(BaseAdmin):
    list_display = ('standin', 'ad', 'project', 'reason')
    search_fields = ('standin__user__first_name', 'standin__user__last_name', 'ad__first_name', 'ad__last_name', 'project__name')
    list_filter = ('standin', 'ad', 'project',)

    autocomplete_fields = ('standin', 'ad', 'project',)

    def add_view(self, request, form_url='', extra_context=None):
        standin_id = request.GET.get('standin')  # Get the query parameter
        if standin_id:
            # Set initial data for the form
            self.initial = {'standins': standin_id}  # Pre-fill the form
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


@admin.register(ActorStandInMatch)
class ActorStandInMatchAdmin(BaseAdmin):
    list_display = ('actor', 'standin')
    search_fields = ('actor__first_name', 'actor__last_name', 'standin__user__first_name', 'standin__user__last_name')
    list_filter = ('actor', 'standin',)

    autocomplete_fields = ('actor', 'standin',)

    def add_view(self, request, form_url='', extra_context=None):
        standin_id = request.GET.get('standin')  # Get the query parameter
        if standin_id:
            # Set initial data for the form
            self.initial = {'standins': standin_id}  # Pre-fill the form
        return super().add_view(request, form_url=form_url, extra_context=extra_context)


class AvailabilityDateRangeInline(admin.StackedInline):
    model = AvailabilityDateRange
    extra = 1


class AvailabilityAdminForm(forms.ModelForm):
    # Include Booking fields manually
    standin = forms.ModelChoiceField(queryset=StandIn.objects.all(), required=False)
    project = forms.ModelChoiceField(queryset=Booking._meta.get_field('project').related_model.objects.all(), required=False)
    notes_booking = forms.CharField(required=False, widget=forms.Textarea)

    class Meta:
        model = Availability
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.booking:
            self.fields['project'].initial = self.instance.booking.project
            self.fields['notes_booking'].initial = self.instance.booking.notes

        # Hide booking fields unless status is 'booked'
        if self.data.get('status', self.instance.status) != 'booked':
            self.fields['project'].widget = forms.HiddenInput()
            self.fields['notes_booking'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')

        if status == 'booked':
            project = cleaned_data.get('project')
            notes_booking = cleaned_data.get('notes_booking')

            if not project:
                raise forms.ValidationError("Project is required for a Booking.")
            
            cleaned_data['booking_data'] = {
                'project': project,
                'notes': notes_booking,
            }

        return cleaned_data
    

@admin.register(Availability)
class AvailabilityAdmin(BaseAdmin):
    list_display = ('standin', 'status', 'booking',)
    search_fields = ('standin__user__first_name', 'standin__user__last_name',)
    list_filter = ('standin', 'status', 'booking',)

    form = AvailabilityAdminForm
    inlines = [AvailabilityDateRangeInline]
    autocomplete_fields = ('standin', 'booking',)
    fieldsets = (
        ('', {'classes': ['wide', 'col col6'],'fields': ('standin', 'list_dates', 'notes', 'status',)}),
    )
    readonly_fields = ('list_dates',)

    def list_dates(self, obj):
        dates = obj.date_ranges.all()
        add_link = reverse('admin:booking_availabilitydaterange_add')  # URL for the HairColor add form
        prefill_link = f"{add_link}?availability={obj.id}"  # Pass StandIn ID as a query parameter

        dates_html = " \n".join([
            format_html('<a class="date_link" href="{}">{}</a>', reverse('admin:booking_availabilitydaterange_change', args=[date.id]), str(date))
            for date in dates
        ]) if dates else 'No dates listed.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Date</a>', prefill_link)

        return mark_safe(f"{dates_html} {add_button_html}")
    list_dates.short_description = "Availability Dates"

    def save_model(self, request, obj, form, change):
        booking_data = form.cleaned_data.get('booking_data')
        obj.save()

        if obj.status == 'booked':
            if hasattr(obj, 'booking'):
                # Update existing booking
                booking = obj.booking
                booking.project = booking_data['project']
                booking.notes = booking_data['notes']
                booking.save()
            else:
                # Create new booking
                Booking.objects.create(
                    availability=obj,
                    standin=obj.standin,
                    project=booking_data['project'],
                    notes=booking_data['notes']
                )
        elif hasattr(obj, 'booking'):
            # If status changed *from* 'booked', delete associated booking
            obj.booking.delete()


# Inline Availability for AvailCheck creation
class AvailabilityDateRangeInlineForAvailCheck(admin.StackedInline):
    model = AvailabilityDateRange
    extra = 1


class AvailabilityInlineForAvailCheck(admin.StackedInline):
    model = Availability
    fields = ['notes']
    extra = 0
    max_num = 1
    can_delete = False
    show_change_link = False
    readonly_fields = []
    inlines = [AvailabilityDateRangeInlineForAvailCheck]

    def get_queryset(self, request):
        return super().get_queryset(request).filter(status='avail_check')

    def has_add_permission(self, request, obj=None):
        return not Availability.objects.filter(avail_check=obj).exists() if obj else True


@admin.register(AvailabilityDateRange)
class AvailabilityDateRangeAdmin(BaseAdmin):
    list_display = ('availability', 'start_date', 'end_date',)
    list_filter = ('availability', 'start_date', 'end_date',)


@admin.register(AvailCheck)
class AvailCheckAdmin(BaseAdmin):
    list_display = ('project', "send_avail_checks")
    list_filter = ('project',)
    actions = ["send_email_to_standin", 'send_avail_checks']

    # form = MultiStandInAvailCheckForm
    inlines = [AvailabilityInlineForAvailCheck]
    autocomplete_fields = ('standins', 'project',)
    fieldsets = (
        ('', {'fields': ('standins', 'project', 'list_dates',)}),
    )
    readonly_fields = ('list_dates',)

    def list_dates(self, obj):
        dates = obj.avail_check_date_ranges.all()
        add_link = reverse('admin:booking_availcheckdaterange_add')  # URL for the HairColor add form
        prefill_link = f"{add_link}?avail_check={obj.id}"  # Pass StandIn ID as a query parameter

        dates_html = " \n".join([
            format_html('<a class="date_link" href="{}">{}</a>', reverse('admin:booking_availcheckdaterange_change', args=[date.id]), str(date))
            for date in dates
        ]) if dates else 'No dates listed.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Date Range</a>', prefill_link)

        return mark_safe(f"{dates_html} {add_button_html}")

    list_dates.short_description = "Avail Check Dates"

    def send_email_to_standin(self, request, queryset):
        for avail_check in queryset:
            avail_check.send_email_notifications()
    send_email_to_standin.short_description = "Send email to stand-ins"

    def send_avail_checks(self, obj):
        return format_html('<a href="{}">Send Email</a>', reverse("admin:booking_availcheck_changelist"))
    send_avail_checks.allow_tags = True

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not Availability.objects.filter(avail_check=obj).exists():
            avail = Availability.objects.create(status='avail_check', avail_check=obj)
            # Add empty date range to inline default if needed


# utils.py (for accept flow)
def create_availability_from_availcheck(availcheck, standin):
    avail_check_avail = availcheck.availabilities.first()
    new_avail = Availability.objects.create(
        standin=standin,
        status='available',
        avail_check=availcheck,
    )
    for dr in avail_check_avail.date_ranges.all():
        AvailabilityDateRange.objects.create(
            availability=new_avail,
            start_date=dr.start_date,
            end_date=dr.end_date
        )
    return new_avail


@admin.register(Booking)
class BookingAdmin(BaseAdmin):
    list_display = ('standin', 'project', 'email_reminder_sent',)
    search_fields = ('standin__user__first_name', 'standin__user__last_name', 'project__name',)
    list_filter = ('standin', 'project',)

    autocomplete_fields = ('standin', 'project',)
    fieldsets = (
        ('', {'fields': ('standin', 'project',)}),
        ('Dates', {'fields': ('list_dates',)}),
        ('Reminders', {'fields': ('email_reminder_sent',)})
    )

    def list_dates(self, obj):
        dates = obj.booking_date_ranges.all()
        add_link = reverse('admin:booking_bookingdaterange_add')  # URL for the HairColor add form
        prefill_link = f"{add_link}?booking={obj.id}"  # Pass StandIn ID as a query parameter

        dates_html = " \n".join([
            format_html('<a class="date_link" href="{}">{}</a>', reverse('admin:booking_bookingdaterange_change', args=[date.id]), str(date))
            for date in dates
        ]) if dates else 'No dates listed.'

        # Append the "Add" button/link
        add_button_html = format_html('<a href="{}" class="button">Add Date</a>', prefill_link)

        return mark_safe(f"{dates_html} {add_button_html}")

    list_dates.short_description = "Booking Dates"


@admin.register(BookingRequest)
class BookingRequestAdmin(BaseAdmin):
    list_display = ("project", "ad", "status", "check_status",)
    list_filter = ("project", "ad", "status",)
    search_fields = ("project__name", "ad__first_name", "ad__email",)

    actions = ["approve_booking_request", "reject_booking_request"]

    autocomplete_fields = ('ad', 'project',)
    filter_horizontal = ('actors', 'images',)

    def approve_booking_request(self, request, queryset):
        for booking_request in queryset:
            if booking_request.status in ["Open", 'rush']:
                send_mail(
                    "Your Booking Request is Being Processed",
                    "An admin has reviewed your request, and we are searching for stand-ins.",
                    EMAIL_HOST_USER,
                    [booking_request.ad.email],
                )

                # TODO: Create an AvailCheck

                booking_request.status = "Avail Checked"
                booking_request.save()

    approve_booking_request.short_description = "Approve booking requests"

    def reject_booking_request(self, request, queryset):
        for booking_request in queryset:
            if booking_request.status == "Open":
                booking_request.status = "Closed"
                booking_request.save()

                send_mail(
                    "Your Booking Request Has Been Closed",
                    "Unfortunately, we are unable to fulfill your request at this time.",
                    EMAIL_HOST_USER,
                    [booking_request.ad.email],
                )

    reject_booking_request.short_description = "Reject booking requests. (CLOSE)"