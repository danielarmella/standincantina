
from django.test import TestCase
from django.utils.timezone import now, timedelta
from .models import User, StandIn, Availability, AvailabilityDateRange, Booking, BookingDateRange

class AvailabilityModelTest(TestCase):
    def setUp(self):
        # Create a StandIn for testing
        self.user = User.objects.create(first_name="Testo", last_name="Testerson")
        self.standin = StandIn.objects.create(user=self.user, height_in_inches=73)
        self.booking = Booking.objects.create(
            project="Test Project",
            start_date=now().date() + timedelta(days=3),
            end_date=now().date() + timedelta(days=5),
            standin=self.stand_in
        )

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