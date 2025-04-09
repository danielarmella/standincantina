from datetime import date, timedelta

from django.test import TestCase
from django.core.exceptions import ValidationError
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
    BookingDateRange,
    AvailCheck,
    AvailCheckDateRange,
    BookingRequest,
)

USER1 = User.objects.create(
            username='',
            first_name='Testo',
            last_name='Testerson',
            email='daniel.armella2+testo.testerson@gmail.com',
            password='p@+_@l(&4f3%%pc-',
            is_staff=False,
            is_active=True,
            is_superuser=False,
            last_login=now(),
            date_joined=now(),
            is_approved=True,
            is_standin=True,
            phone=12159177265,
            birthday=date(1991,2,3)
        )
STANDIN1 = StandIn.objects.create(
            user=USER1,
            gender='male',
            height_in_inches=73,
            skin_tone='medium'
)
PROJECT_A = Project.objects.create(name='Project A')
PROJECT_B = Project.objects.create(name='Project B')

class UserModelTest(TestCase):
    
    def setUp(self):
        self.user = USER1


class ProjectModelTest(TestCase):
    pass


class ADModelTest(TestCase):
    pass


class ActorModelTest(TestCase):
    pass


class StandInModelTest(TestCase):
    pass


class HairColorModelTest(TestCase):
    pass


class IncidentModelTest(TestCase):
    pass


class MediaUploadModelTest(TestCase):
    pass


class ReviewModelTest(TestCase):
    pass


class DNRModelTest(TestCase):
    pass


class ActorStandInMatchModelTest(TestCase):
    pass


class AvailabilityModelTest(TestCase):

    def setUp(self):
        self.standin = STANDIN1
        self.project_a = PROJECT_A
        self.project_b = PROJECT_B

    def test_create_availability(self):
        """ Test basic availability creation. """
        avail = Availability.objects.create(
            standin=self.stand_in,
            is_available=True
        )
        self.assertTrue(avail.is_available)
        self.assertEqual(avail.standin, self.stand_in)

    def test_create_availability_date_range(self):
        """ Test adding availability date ranges. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=True)
        date_range = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date(),
            end_date=now().date() + timedelta(days=2)
        )
        self.assertEqual(date_range.availability, avail)
        self.assertEqual(date_range.start_date, now().date())
        self.assertEqual(date_range.end_date, now().date() + timedelta(days=2))

    def test_merge_overlapping_availability(self):
        """ Test merging overlapping available ranges. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=True)

        range1 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date(),
            end_date=now().date() + timedelta(days=2)
        )
        range2 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date() + timedelta(days=1),
            end_date=now().date() + timedelta(days=4)
        )

        # Simulate merging logic (manually invoking resolve_overlaps)
        avail.resolve_overlaps([
            {"start_date": range1.start_date, "end_date": range2.end_date}
        ])

        merged_ranges = AvailabilityDateRange.objects.filter(availability=avail)
        self.assertEqual(merged_ranges.count(), 1)
        self.assertEqual(merged_ranges.first().start_date, range1.start_date)
        self.assertEqual(merged_ranges.first().end_date, range2.end_date)

    def test_cannot_overlap_booked_ranges(self):
        """ Test that availability cannot overlap with booked dates. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=False, booking=self.booking)

        with self.assertRaises(Exception):
            AvailabilityDateRange.objects.create(
                availability=avail,
                start_date=self.booking.start_date - timedelta(days=1),
                end_date=self.booking.end_date + timedelta(days=1)
            )

    def test_adjusts_around_booked_dates(self):
        """ Test that new availability is adjusted around booked dates. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=True)

        range1 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date(),
            end_date=self.booking.start_date - timedelta(days=1)
        )

        range2 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=self.booking.end_date + timedelta(days=1),
            end_date=now().date() + timedelta(days=10)
        )

        self.assertEqual(range1.end_date, self.booking.start_date - timedelta(days=1))
        self.assertEqual(range2.start_date, self.booking.end_date + timedelta(days=1))

    def test_bulk_update_availability(self):
        """ Test bulk update for availability date ranges. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=True)

        range1 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date(),
            end_date=now().date() + timedelta(days=2)
        )
        range2 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date() + timedelta(days=3),
            end_date=now().date() + timedelta(days=5)
        )

        # Bulk update: Extend both ranges by 1 day
        range1.end_date += timedelta(days=1)
        range2.start_date -= timedelta(days=1)
        AvailabilityDateRange.objects.bulk_update([range1, range2], ['start_date', 'end_date'])

        updated_range1 = AvailabilityDateRange.objects.get(id=range1.id)
        updated_range2 = AvailabilityDateRange.objects.get(id=range2.id)

        self.assertEqual(updated_range1.end_date, now().date() + timedelta(days=3))
        self.assertEqual(updated_range2.start_date, now().date() + timedelta(days=2))

    def test_bulk_delete_availability(self):
        """ Test bulk deletion of availability date ranges. """
        avail = Availability.objects.create(standin=self.stand_in, is_available=True)

        range1 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date(),
            end_date=now().date() + timedelta(days=2)
        )
        range2 = AvailabilityDateRange.objects.create(
            availability=avail,
            start_date=now().date() + timedelta(days=3),
            end_date=now().date() + timedelta(days=5)
        )

        # Bulk delete all date ranges
        AvailabilityDateRange.objects.filter(availability=avail).delete()

        self.assertEqual(AvailabilityDateRange.objects.count(), 0)

    def test_standins_cannot_have_adjacent_bookings(self):
        """ Test that stand-ins cannot have adjacent bookings without a gap. """
        booking1 = Booking.objects.create(
            project="Project 1",
            start_date=now().date(),
            end_date=now().date() + timedelta(days=3),
            standin=self.stand_in
        )
        with self.assertRaises(Exception):
            Booking.objects.create(
                project="Project 2",
                start_date=booking1.end_date,
                end_date=booking1.end_date + timedelta(days=2),
                standin=self.stand_in
            )

    def test_expired_availability_is_deleted(self):
        """ Test automatic deletion of availability older than 3 years. """
        old_avail = Availability.objects.create(standin=self.stand_in, is_available=True)
        old_range = AvailabilityDateRange.objects.create(
            availability=old_avail,
            start_date=now().date() - timedelta(days=1100),  # More than 3 years ago
            end_date=now().date() - timedelta(days=1000)
        )

        # Simulate scheduled cleanup job
        AvailabilityDateRange.objects.filter(
            end_date__lt=now().date() - timedelta(days=3 * 365)
        ).delete()

        self.assertFalse(AvailabilityDateRange.objects.filter(id=old_range.id).exists())


class AvailabilityDateRangeModelTest(TestCase):
    pass


class BookingModelTest(TestCase):
    
    def setUp(self):
        self.standin = STANDIN1
        self.project_a = PROJECT_A
        self.project_b = PROJECT_B
    
    def test_create_booking_creates_availability(self):
        booking = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking, start_date="2025-06-01", end_date="2025-06-05")
        booking.save()
        
        availability = Availability.objects.get(booking=booking)
        self.assertEqual(availability.status, 'booked')
        self.assertEqual(availability.standin, self.standin)
        self.assertEqual(availability.project, self.project_a)
    
    def test_overlapping_booking_same_project_fails(self):
        booking1 = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking1, start_date="2025-06-01", end_date="2025-06-05")
        booking1.save()
        
        booking2 = Booking(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking2, start_date="2025-06-03", end_date="2025-06-07")
        
        with self.assertRaises(ValidationError):
            booking2.full_clean()
    
    def test_non_overlapping_booking_same_project_succeeds(self):
        booking1 = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking1, start_date="2025-06-01", end_date="2025-06-05")
        booking1.save()
        
        booking2 = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking2, start_date="2025-06-06", end_date="2025-06-10")
        booking2.save()
        
        self.assertEqual(Booking.objects.count(), 2)
    
    def test_overlapping_booking_different_projects_fails(self):
        booking1 = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking1, start_date="2025-06-01", end_date="2025-06-05")
        booking1.save()
        
        booking2 = Booking(standin=self.standin, project=self.project_b)
        BookingDateRange.objects.create(booking=booking2, start_date="2025-06-03", end_date="2025-06-07")
        
        with self.assertRaises(ValidationError):
            booking2.full_clean()
    
    def test_booking_deletion_marks_availability_as_available(self):
        booking = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking, start_date="2025-06-01", end_date="2025-06-05")
        booking.save()
        
        availability = Availability.objects.get(booking=booking)
        booking.delete()
        
        availability.refresh_from_db()
        self.assertEqual(availability.status, 'available')
        self.assertIsNone(availability.booking)
    
    def test_cannot_have_multiple_bookings_same_day(self):
        booking1 = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking1, start_date="2025-06-01", end_date="2025-06-05")
        booking1.save()
        
        booking2 = Booking(standin=self.standin, project=self.project_b)
        BookingDateRange.objects.create(booking=booking2, start_date="2025-06-05", end_date="2025-06-07")
        
        with self.assertRaises(ValidationError):
            booking2.full_clean()
    
    def test_standin_change_updates_availability(self):
        new_standin = StandIn.objects.create(name="New StandIn")
        booking = Booking.objects.create(standin=self.standin, project=self.project_a)
        BookingDateRange.objects.create(booking=booking, start_date="2025-06-01", end_date="2025-06-05")
        booking.save()
        
        booking.standin = new_standin
        booking.save()
        
        old_availability = Availability.objects.get(standin=self.standin, project=self.project_a)
        new_availability = Availability.objects.get(standin=new_standin, project=self.project_a)
        
        self.assertEqual(old_availability.status, 'available')
        self.assertEqual(old_availability.booking, None)
        self.assertEqual(new_availability.status, 'booked')
        self.assertEqual(new_availability.booking, booking)


class BookingDateRangeModelTest(TestCase):
    pass


class AvailCheckModelTest(TestCase):
    pass


class AvailCheckDateRangeModelTest(TestCase):
    pass


class BookingRequestModelTest(TestCase):
    pass


class BookingRequestImageModelTest(TestCase):
    pass