from django.contrib import messages
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, validate_email
from django.db import models, transaction
from django.utils.timezone import now

from datetime import date, timedelta
import imghdr
from phonenumber_field.modelfields import PhoneNumberField
from standin_cantina.settings import EMAIL_HOST_USER

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other/Non-binary'),
    ('na', 'Prefer not to say')
]
SKIN_TONE_CHOICES = [
    ('ivory', 'Ivory to pale white'),
    ('white', 'White, fair'),
    ('medium', 'Medium white to olive'),
    ('olive', 'Olive to moderate brown'),
    ('brown', 'Brown to dark brown'),
    ('dark', 'Very dark brown to black'),
]

HAIR_COLOR_CHOICES = [
    ('black', 'Black'),
    ('brown', 'Brown'),
    ('blond', 'Blond'),
    ('white/gray', 'White/Gray'),
    ('red', 'Red')
]
HAIR_LENGTH_CHOICES = [
    ('bald', 'Bald'),
    ('short', 'Short'),
    ('medium', 'Medium'),
    ('long', 'Long'),
]
INCIDENT_CHOICES = [
    ('0', 'Excused abscence or lateness'),
    ('1', 'Called out'),
    ('2', 'Late'),
    ('3', 'No call/no show'),
    ('4', 'Other. See notes')
]
MIN_HEIGHT = 20
MAX_HEIGHT = 108
MIN_WEIGHT = 10
MAX_WEIGHT = 800
HEIGHT_VALIDATORS = [MinValueValidator(MIN_HEIGHT, 'Height must be at least 20 inches.'), MaxValueValidator(MAX_HEIGHT, "Height cannot exceed 9'(feet).")]
WEIGHT_VALIDATORS = [MinValueValidator(MIN_WEIGHT, 'Weight must be at least 10 lbs.'), MaxValueValidator(MAX_WEIGHT, 'Weight cannot exceed 800 lbs.')]
MAX_MEDIA_UPLOAD_COUNT = 7


class User(AbstractUser):
    email = models.EmailField(max_length=254, unique=True, blank=False)
    is_approved = models.BooleanField('Approved', default=False)    # Admin must approve
    is_standin = models.BooleanField('Stand-in', default=False)    # Checked if the user is a stand-in
    phone = PhoneNumberField('Phone number', region='US', null=True, blank=True)
    birthday = models.DateField('Date of birth', validators=[
        MinValueValidator(date(1900, 1, 1), 'No birthdays before 1900'),
        MaxValueValidator(now().date(), 'No future birthdays')
    ], null=True, blank=True)

    def age(self):
        if self.birthday:
            today = now().date()
            return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))
        return None

    def __str__(self):
        return f'{self.first_name.capitalize()} {self.last_name.capitalize()}'

    def serialize(self):
        return {
            "id": self.id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            'phone': str(self.phone),
            'is_approved': self.is_approved,
            'is_active': self.is_active,
            'last_login': self.last_login,
            "birthday": self.birthday,
            "date_joined": self.date_joined,
            'is_standin': self.is_standin
        }

    def clean(self):
        self.email = self.email.lower()
        self.first_name = self.first_name.lower()
        self.last_name = self.last_name.lower()

        if self.email:
            self.username = self.email
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()  # Calls clean() + field validation
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['first_name', 'last_name'],
                name='unique_name',
                violation_error_message='A user with that name already exists.')
        ]
        ordering = ['last_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class Project(models.Model):
    name = models.CharField(max_length=255, blank=False, default='')
    start_date = models.DateField('Project start date', blank=True, null=True)
    end_date = models.DateField('Project end date', blank=True, null=True)
    ads = models.ManyToManyField('AD', verbose_name='Assistant Directors', related_name='projects', blank=True)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('Start date cannot be after the end date.')

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class AD(models.Model):
    first_name = models.CharField(max_length=127, blank=True, default='')
    last_name = models.CharField(max_length=127, blank=True, default='')
    email = models.EmailField(unique=True, validators=[validate_email], null=True, blank=True)
    phone = PhoneNumberField(region='US', null=True, blank=True)
    most_recent_project = models.ForeignKey('Project', on_delete=models.SET_NULL, related_name='current_ad', null=True, blank=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.most_recent_project and not self.most_recent_project.ads.filter(id=self.id).exists():
            self.most_recent_project.ads.add(self)

    class Meta:
        ordering = ['last_name']
        verbose_name = 'Assistant Director'
        verbose_name_plural = 'ADs'


def validate_image(image):
    MAX_FILE_SIZE_MB = 5
    ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png')

    # Check file size
    file_size = image.size
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:  # 5MB limit
        raise ValidationError(f'Image file too large ( > {MAX_FILE_SIZE_MB}MB ).')

    # Check file extention
    if not image.name.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValidationError(f'Unsupported file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}.')

    # Check file header
    allowed_extensions = []
    for type in ALLOWED_EXTENSIONS: # remove leading '.'
        allowed_extensions.append(type[1:])
    file_type = imghdr.what(image.file)  # Inspect file header
    if file_type not in allowed_extensions:
        raise ValidationError(f"Invalid file content. Only formats {', '.join(ALLOWED_EXTENSIONS)} allowed.")

    # Optional: Additional MIME type checks for stricter validation
    from PIL import Image
    try:
        img = Image.open(image.file)
        img.verify()  # Verifies the integrity of the image file
    except Exception:
        raise ValidationError('Corrupted or invalid image file.')

    return True


class Actor(models.Model):
    first_name = models.CharField(max_length=127, blank=False, default='')
    last_name = models.CharField(max_length=127, blank=True, default='')
    birth_year = models.PositiveSmallIntegerField('Year of birth', null=True, blank=True)
    gender = models.CharField('Gender', max_length=12, choices=GENDER_CHOICES, blank=True, default='')
    height_in_inches = models.PositiveSmallIntegerField('Height(in)',
        validators=HEIGHT_VALIDATORS, help_text='Height in feet and inches')
    weight_in_lbs = models.PositiveSmallIntegerField('Weight(lbs)',
        validators=WEIGHT_VALIDATORS, help_text='Weight in lbs', null=True, blank=True)
    skin_tone = models.CharField('Skin tone', max_length=7, choices=SKIN_TONE_CHOICES, blank=True, default='')
    hair_length = models.CharField('Hair length', max_length=10, choices=HAIR_LENGTH_CHOICES, blank=True, default='')
    headshot = models.ImageField('Headshot', upload_to='actor_headshots/', validators=[validate_image], null=True, blank=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'

    def height_cm(self):
        if self.height_in_inches:
            return round(self.height_in_inches * 2.54, 2)
        return 'Height unknown.'

    def height_ft_in(self):
        if self.height_in_inches:
            return f"{self.height_in_inches//12}' {self.height_in_inches%12}\""
        return 'Height unknown.'

    def weight_kg(self):
        if self.weight_in_lbs:
            return round(self.weight_in_lbs * 0.453592, 2)
        return 'Weight unknown.'

    def clean(self):
        super().clean()
        if self.birth_year and self.birth_year > now().year:
            raise ValidationError("Actor's birth should be in the past.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['first_name', 'last_name'],
                name='unique_actor_name',
                violation_error_message='An actor with that name already exists.')
        ]
        ordering = ['last_name']
        verbose_name = 'Actor'
        verbose_name_plural = 'Actors'


class StandIn(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='standin')
    recommended_by = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='recommendees', null=True, blank=False)
    gender = models.CharField('Gender', max_length=12, choices=GENDER_CHOICES, blank=True, default='')
    height_in_inches = models.PositiveSmallIntegerField('Height(in)',
        validators=HEIGHT_VALIDATORS, help_text='Height in inches', blank=False)
    weight_in_lbs = models.PositiveSmallIntegerField('Weight(lbs)',
        validators=WEIGHT_VALIDATORS, help_text='Weight in lbs', null=True, blank=True)
    skin_tone = models.CharField('Skin tone', max_length=7, choices=SKIN_TONE_CHOICES, blank=True, default='')
    hair_length = models.CharField('Hair length', max_length=10, choices=HAIR_LENGTH_CHOICES, blank=True, default='')
    #age_range fields will store birthday differentials not actual values so that aging will automatically update age ranges
    age_range_min = models.SmallIntegerField(help_text='Enter minimum reasonably portrayable age', null=True, blank=True)
    age_range_max = models.SmallIntegerField(help_text="Enter maximum reasonably portrayable age", null=True, blank=True)
    matched_actors = models.ManyToManyField(Actor, related_name="matches", through="ActorStandInMatch")
    reviews = models.ManyToManyField(AD, related_name="reviewed_standins", through="Review")
    incidents = models.ManyToManyField(AD, related_name="incidents", through="Incident")
    DNRs = models.ManyToManyField(AD, related_name="ad_DNRs", through="DNR")
    notes = models.TextField('Notes', help_text="Additional stand-in details", blank=True)

    def __str__(self):
        return f'{self.user.first_name.capitalize()} {self.user.last_name.capitalize()}'

    def height_cm(self):
        if self.height_in_inches:
            return round(self.height_in_inches * 2.54, 2)
        return 'Height unknown.'

    def height_ft_in(self):
        if self.height_in_inches:
            return f"{self.height_in_inches//12}' {self.height_in_inches%12}\""
        return 'Height unknown.'

    def weight_kg(self):
        if self.weight_in_lbs:
            return round(self.weight_in_lbs * 0.453592, 2)
        return 'Weight unknown.'

    def clean(self):
        super().clean()
        if self.age_range_min is not None and self.age_range_max is not None:
            if self.age_range_min > self.age_range_max:
                raise ValidationError("Minimum age cannot exceed maximum age.")

    def save(self, *args, **kwargs):
        user_age = self.user.age()
        if self.age_range_min is None and user_age is not None:
            self.age_range_min = user_age
        if self.age_range_max is None and user_age is not None:
            self.age_range_max = user_age
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['user__last_name']
        verbose_name = 'StandIn'
        verbose_name_plural = 'StandIns'
        indexes = [
            models.Index(fields=['height_in_inches', 'skin_tone'])
        ]


class HairColor(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE, related_name="hair_colors")
    hair_color = models.CharField('Hair color', max_length=15, choices=HAIR_COLOR_CHOICES, blank=False, default="")

    def  __str__(self):
        return f'{self.hair_color.capitalize()}'

    class Meta:
        verbose_name = 'Hair color'
        verbose_name_plural = 'Hair colors'
        constraints = [
            models.UniqueConstraint(
                fields=['standin', 'hair_color'],
                name='unique_hair_color',
                violation_error_message="This stand-in already has that hair color listed.")
        ]


class Incident(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE)
    complainant = models.ForeignKey(AD, on_delete=models.SET_NULL, related_name="complaints", null=True, blank=True)
    incident = models.CharField('Incident', max_length=1, choices=INCIDENT_CHOICES, blank=True, default="")
    note = models.TextField('Notes', blank=True)
    date = models.DateField('Date incident occurred', default=date.today, auto_now_add=False, help_text="What date did the incident occur?")
    needs_followup = models.BooleanField(default=False, blank=True)

    def __str__(self):
        return f'{self.date}'

    class Meta:
        ordering = ['-date']
        verbose_name = 'Incident'
        verbose_name_plural = 'Incidents'


class MediaUpload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="uploads")
    image = models.ImageField(upload_to="user_pics/", validators=[validate_image])
    is_main_image = models.BooleanField(default=False)
    time_stamp = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.image}'

    def clean(self):
        if MediaUpload.objects.filter(user=self.user).count() >= MAX_MEDIA_UPLOAD_COUNT:
            raise ValidationError(f'Upload limit reached. Max {MAX_MEDIA_UPLOAD_COUNT} images allowed.')
        super().clean()

    def save(self, *args, **kwargs):
        # Ensure only this image is marked as main
        if self.is_main_image:
            # Unset 'is_main_image' for other uploads of the same user
            MediaUpload.objects.filter(user=self.user, is_main_image=True).update(is_main_image=False)
        else:
            # Set as main if no other main image exists for this user
            if not MediaUpload.objects.filter(user=self.user, is_main_image=True).exists():
                self.is_main_image = True
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-time_stamp']
        verbose_name = 'Media upload'
        verbose_name_plural = 'Media uploads'


class Review(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE)
    ad = models.ForeignKey(AD, on_delete=models.SET_NULL, related_name="reviews_given", null=True, blank=True)
    feedback = models.TextField(blank=True)
    is_positive = models.BooleanField(null=True, blank=True)
    date = models.DateField(default=date.today)

    class Meta:
        ordering = ['-date']
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'

    def  __str__(self):
        return f'{self.date}'


class DNR(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE)
    ad = models.ForeignKey(AD, on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_DNRs")
    reason = models.TextField(blank=True)

    def __str__(self):
        if self.project:
            return f'{self.project}'
        return 'Error: DNR has no associated project'

    def clean(self):
        super().clean()  # Call parent clean method
        # Ensure at least one of AD or Project is provided
        if not self.ad and not self.project:
            raise ValidationError("A DNR must have an associated AD or Project.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['standin', 'ad'],
                name='unique_ad_DNR',
                violation_error_message="This stand-in has already been DNRed by this AD."),
            models.UniqueConstraint(
                fields=['standin', 'project'],
                name='unique_project_DNR',
                violation_error_message="This stand-in has already been DNRed on this project.")
        ]
        verbose_name = 'DNR'
        verbose_name_plural = 'DNRs'


class ActorStandInMatch(models.Model):
    actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name="standin_matches")
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE, related_name="actor_matches")

    def __str__(self):
        return f'{self.standin.user.first_name} {self.standin.user.last_name} | {self.actor.first_name} {self.actor.last_name}'

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['actor', 'standin'],
                name='unique_actor_standin_match',
                violation_error_message="This stand-in has already been matched to this actor.")
                ]
        verbose_name = 'Actor/Stand-in match'
        verbose_name_plural = 'Actor/Stand-in matches'


def validate_avail_date(day):
    if day < now().date():
        raise ValidationError("This date cannot be in the past.")


class Availability(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE, related_name="avails")
    start_date = models.DateField(validators=[
        MinValueValidator(date(2020, 1, 1), 'No ancient start dates'),
    ], help_text="yyyy-mm-dd", null=False, blank=False)
    end_date = models.DateField(validators=[validate_avail_date], help_text="yyyy-mm-dd", null=False, blank=False)
    is_available = models.BooleanField(default=True)  # True for availability, False for unavailability
    notes = models.TextField(blank=True)
    booked = models.ForeignKey('Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name="avail", help_text='Must be a booking not a project.')

    _overlap_handled = False  # Temporary private attribute to prevent recursion. Reload will reset.

    class Meta:
        db_table = 'booking_availability'
        ordering = ['-start_date']
        verbose_name = 'Availability'
        verbose_name_plural = 'Availabilities'

    def clean(self):
        super().clean()  # Call parent clean method
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise ValidationError("Please enter a date in the yyyy-mm-dd format.")
        if self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after the end date.")
        if self.booked:
            if self.is_available and self.booked:
                raise ValidationError('Cannot be booked and available.')
            if self.standin != self.booked.standin:
                raise ValidationError('Stand-in doesnt match the booking stand-in.')
            if self.start_date != self.booked.start_date or self.end_date != self.booked.end_date:
                raise ValidationError('Availability dates do not match Booking dates.')

    def resolve_overlaps(self):
        overlapping_entries = Availability.objects.filter(
            standin=self.standin,
            start_date__lte=self.end_date + timedelta(days=1),
            end_date__gte=self.start_date - timedelta(days=1),
        ).exclude(id=self.id)

        for entry in overlapping_entries:
            if entry.is_available == self.is_available and entry.booked == self.booked and entry.notes == self.notes:
                # Merge overlapping entries
                self.start_date = min(self.start_date, entry.start_date)
                self.end_date = max(self.end_date, entry.end_date)
                entry.delete()
            else:
                # Adjust overlapping entries
                if entry.start_date < self.start_date and entry.end_date > self.end_date:
                    # Split the existing entry into two non-overlapping parts
                    new_avail = Availability.objects.create(
                        standin=self.standin,
                        start_date=entry.start_date,
                        end_date=self.start_date - timedelta(days=1),
                        is_available=entry.is_available,
                        notes=entry.notes,
                    )
                    new_avail.end_date = self.start_date - timedelta(days=1)
                    new_avail._overlap_handled = True
                    super(Availability, new_avail).save()

                    entry.start_date = self.end_date + timedelta(days=1)
                    super(Availability, entry).save()
                elif entry.start_date >= self.start_date and entry.end_date <= self.end_date:
                    # Delete the fully overlapped entry
                    entry.delete()
                elif entry.start_date < self.start_date <= entry.end_date:
                    # Adjust the end date of the existing entry
                    entry.end_date = self.start_date - timedelta(days=1)
                    entry.save()
                elif entry.start_date <= self.end_date < entry.end_date:
                    # Adjust the start date of the existing entry
                    entry.start_date = self.end_date + timedelta(days=1)
                    entry.save()

    def save(self, *args, **kwargs):
        self.clean()
        if not self._overlap_handled:
            self._overlap_handled = True  # Set the flag to prevent recursion
            self.resolve_overlaps()  # Call the method to handle overlaps
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f'{self.start_date} - {self.end_date} | {status}'


class Booking(models.Model):
    standin = models.ForeignKey(StandIn, on_delete=models.CASCADE, related_name="standin_bookings")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="project_bookings")
    start_date = models.DateField('Start date', help_text="yyyy-mm-dd", null=False, blank=False)
    end_date = models.DateField('End date', help_text="yyyy-mm-dd", null=False, blank=False)
    email_reminder_sent = models.BooleanField('Email reminder sent', default=False)

    def __str__(self):
        return f'{self.start_date} - {self.end_date} | {self.standin} on {self.project.name}'

    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-start_date']

    def resolve_overlaps(self):
        # Check availability
        overlapping_avails = Availability.objects.filter(
            standin=self.standin,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
            is_available=False,
        )
        if overlapping_avails:
            unavail = ""
            for avail in overlapping_avails:
                unavail += f'{avail.start_date} to {avail.end_date}\n'
            return False, f"{self.standin} is unavailable on the following conflicting dates:\n{unavail}"

        # Check overlaping bookings
        overlapping_entries = Booking.objects.filter(
            standin=self.standin,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date,
        ).exclude(id=self.id)

        for entry in overlapping_entries:
            if entry.project == self.project:
                # Merge overlapping entries
                self.start_date = min(self.start_date, entry.start_date)
                self.end_date = max(self.end_date, entry.end_date)
                entry.delete()
            else:
                return False, f"{self.standin} is already booked from {entry.start_date} to {entry.end_date} for {entry.project.name}."
        return True, "No conflicts."

    def clean(self):
        super().clean()  # Call parent clean method

        # Check for valid dates
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise ValidationError("Please enter a date in the yyyy-mm-dd format.")

        # Check for valid start and end dates
        if self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after the end date.")

        # Check for availability and booking overlaps
        success, message = self.resolve_overlaps()
        if not success:
            raise ValidationError(message)

    def save(self, *args, **kwargs):
        with transaction.atomic():  # Ensures changes happen together
            # If updating an existing booking, handle the old Availability record
            if self.pk:
                try:
                    # Fetch the existing booking from the database
                    old_booking = Booking.objects.get(pk=self.pk)
                    if old_booking.start_date != self.start_date or old_booking.end_date != self.end_date:
                        # Booking dates have changed
                        try:
                            # Find the Availability associated with the old booking
                            old_avail = Availability.objects.create(standin=old_booking.standin, start_date=old_booking.start_date, end_date=old_booking.end_date, is_available=True, booked=None, notes=f"Booking for {old_booking.project} canceled or updated. Stand-in now available.")
                        except Availability.DoesNotExist:
                            pass  # No Availability was associated with the old booking
                except Booking.DoesNotExist:
                    # If the booking doesn't exist, it's a new booking
                    pass

            # Save the Booking normally
            super().save(*args, **kwargs)

            # Now, update or create the new Availability record for the current booking dates
            avail, created = Availability.objects.update_or_create(
                standin=self.standin,
                start_date=self.start_date,
                end_date=self.end_date,
                defaults={"is_available": False, "booked": self, "notes": f"Booked on {self.project}"}
            )


class AvailCheck(models.Model):
    standins = models.ManyToManyField(StandIn, blank=True, related_name='avail_checks')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="avails_requested", null=True, blank=True)
    start_date = models.DateField(validators=[
        MinValueValidator(date(2020, 1, 1), 'No ancient start dates'),
    ], help_text="yyyy-mm-dd", null=False, blank=False)
    end_date = models.DateField(help_text="yyyy-mm-dd", null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Avail Check for {self.project} from {self.start_date} - {self.end_date}'

    def send_email_notifications(self):
        # Send emails to the stand-ins with a link to accept or reject the request.
        from django.core.mail import send_mail
        from django.urls import reverse

        for standin in self.standins.all():
            accept_url = f"<a href='127.0.0.1:8000{reverse("booking:accept_availability", args=[self.id, standin.id])}'>Accept</a>"
            reject_url = f"<a href='127.0.0.1:8000{reverse('booking:reject_availability')}'>Reject</a>"

            message = f"""
            Hi {standin.user.first_name},

            You have a new avail check for the following dates:
            {self.start_date} to {self.end_date}

            Please respond by clicking one of the links below:
            Accept: {accept_url}
            Reject: {reject_url}
            """

            send_mail(
                subject='Stand-in Cantina: Availability Check',
                message=message,
                from_email=EMAIL_HOST_USER,
                recipient_list=[standin.user.email],
                fail_silently=False,
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.send_email_notifications()


class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('rush', 'Rush'),
        ('open', 'Open'),
        ('avail_checks', 'Avail checks'),
        ('booked', 'Booked'),
        ('closed', 'Closed'),
    ]

    ad = models.ForeignKey(AD, on_delete=models.SET_NULL, null=True, blank=True, related_name='booking_requests')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='booking_requests')
    start_date = models.DateField(validators=[MinValueValidator(date(2020, 1, 1), 'No ancient start dates')], help_text="yyyy-mm-dd", null=False, blank=False)
    end_date = models.DateField(help_text='yyyy-mm-dd')
    actors = models.ManyToManyField(Actor, blank=True, related_name='booking_requests')
    images = models.ManyToManyField('BookingRequestImage', blank=True)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def check_status(self):
        if self.start_date == now().date() and (self.status in ['open', 'avail_requested']):
            self.status = 'rush'
        return self.status

    def close(self):
        # Mark the request as closed once a booking is created.
        self.status = 'Closed'
        self.save()

    def __str__(self):
        return f'{self.project.name} ({self.start_date} - {self.end_date}) by {self.ad}'

    def clean(self):
        super().clean()  # Call parent clean method
        if not isinstance(self.start_date, date) or not isinstance(self.end_date, date):
            raise ValidationError("Please enter a date in the yyyy-mm-dd format.")
        if self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after the end date.")

class BookingRequestImage(models.Model):
    image = models.ImageField(upload_to='booking_requests/', validators=[validate_image])
    request = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='request_images')

    def __str__(self):
        return f'Image for {self.request.project.name}'