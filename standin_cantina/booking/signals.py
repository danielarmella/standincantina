from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import User, StandIn, Booking, MediaUpload, Actor, Availability
from .admin import UserAdmin

import os
from standin_cantina.settings import EMAIL_HOST_USER

# Send booking reminders
@receiver(post_save, sender=Booking)
def send_booking_reminder(sender, instance, created, **kwargs):
    if created and not instance.email_reminder_sent:
        # Compose the email
        subject = "Stand-in Cantina - Booking Reminder"
        message = f"Hi {instance.standin.user.first_name},\n\nYou have a new booking for {instance.project} on {instance.start_date} to {instance.end_date}. Casting will send you the details."
        recipient = instance.standin.user.email

        # Send the email
        send_mail(subject, message, EMAIL_HOST_USER, [recipient])

        # Mark reminder as sent
        instance.email_reminder_sent = True
        instance.save()

# Handled in Booking save method
# # Deleting a Booking will make stand-in available
# @receiver(post_delete, sender=Booking)
# def make_standin_available(sender, instance, **kwargs):
#     availability = Availability.objects.create(standin=instance.standin, start_date=instance.start_date, end_date=instance.end_date, status='available', booked=None, notes=f"Booking for {instance.project} canceled. Stand-in released and is showing available.")
#     print(availability)


#Send SMS meggases
# from twilio.rest import Client

# @receiver(post_save, sender=Booking)
# def send_sms_reminder(sender, instance, created, **kwargs):
#     if created and not instance.['SMS']:
#         # Twilio configuration
#         client = Client(account_sid, auth_token)
#         message = f"Stand-in Cantina: You have a booking for {instance.project} on {instance.start_date}. Details will be emailed"

#         # Send SMS
#         client.messages.create(
#             to=instance.standin.user.phone,  # Assuming a phone number field exists
#             from_="+12159177265",
#             body=message
#         )

#         # Mark as sent
#         instance.['SMS'] = True
#         instance.save()


import logging
logger = logging.getLogger(__name__)


def delete_all_media(instance, caller, **kwargs):
    image = None

    if caller == 'Actor' and instance.headshot:
        image = instance.headshot
    elif caller == 'MediaUpload' and instance.image:
        image = instance.image
        # Mark an image as main
        if instance.user.uploads:
            if not instance.user.uploads.filter(is_main_image=True).exists():
                # Order uploads by 'time_stamp' and get the first one
                main_image = instance.user.uploads.order_by('time_stamp').first()
                if main_image:
                    main_image.is_main_image = True
                    main_image.save()


    if image and image.path:
        image_path = image.path
        try:
            if os.path.isfile(image_path):
                os.remove(image_path)
        except Exception as e:
            logger.error(f"Error deleting {caller} photo {instance.id}: {e}")


@receiver(post_delete, sender=Actor)
def delete_actor_headshot(instance, **kwargs):
    delete_all_media(instance, caller='Actor')


@receiver(post_delete, sender=MediaUpload)
def delete_media_upload_image(instance, **kwargs):
    delete_all_media(instance, caller='MediaUpload')