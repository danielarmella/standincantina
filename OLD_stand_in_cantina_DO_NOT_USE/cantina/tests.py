from datetime import date, timedelta
from django.test import TestCase
from cantina.models import User, Avail, StandIn

class AvailOverlapTests(TestCase):
    def setUp(self):
        # Create a StandIn for testing
        self.user = User.objects.create(first_name="Testo", last_name="Testerson")
        self.stand_in = StandIn.objects.create(user=self.user, height_in_inches=73)

    def test_non_overlapping_entries(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 2, 1), end_date=date(2026, 2, 15), is_available=False)
        avail.save()

        self.assertEqual(Avail.objects.count(), 2)

    def test_fully_overlapping_same_status(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 5), end_date=date(2026, 1, 10), is_available=True)
        avail.save()

        self.assertEqual(Avail.objects.count(), 1)
        merged_avail = Avail.objects.first()
        self.assertEqual(merged_avail.start_date, date(2026, 1, 1))
        self.assertEqual(merged_avail.end_date, date(2026, 1, 15))

    def test_fully_overlapping_different_status(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 5), end_date=date(2026, 1, 10), is_available=False)
        avail.save()

        self.assertEqual(Avail.objects.count(), 3)
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 1), end_date=date(2026, 1, 4), is_available=True).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 5), end_date=date(2026, 1, 10), is_available=False).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 11), end_date=date(2026, 1, 15), is_available=True).exists())

    def test_partially_overlapping_different_status(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 10), end_date=date(2026, 1, 20), is_available=False)
        avail.save()

        self.assertEqual(Avail.objects.count(), 2)
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 1), end_date=date(2026, 1, 9), is_available=True).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 10), end_date=date(2026, 1, 20), is_available=False).exists())

    def test_adjacent_entries(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 16), end_date=date(2026, 1, 31), is_available=True)
        avail.save()

        self.assertEqual(Avail.objects.count(), 1)
        merged_avail = Avail.objects.first()
        self.assertEqual(merged_avail.start_date, date(2026, 1, 1))
        self.assertEqual(merged_avail.end_date, date(2026, 1, 31))

    def test_split_existing_entry(self):
        print('Creating first avail:')
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True, notes='1st entry')
        print(f'First avail {Avail.objects.filter(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)}')
        print('Creating Second avail:')
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 5), end_date=date(2026, 1, 10), is_available=False, notes='2nd entry')
        print(f'avail = {avail}\nSaving')
        avail.save()
        print(f'Second avail saved')

        print(f'TEST: Avail.objects.count() {Avail.objects.count()}')

        avails = Avail.objects.all()
        for avail in avails:
            print(f'{avail} {avail.notes}')

        self.assertEqual(Avail.objects.count(), 3)
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 1), end_date=date(2026, 1, 4), is_available=True).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 5), end_date=date(2026, 1, 10), is_available=False).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 11), end_date=date(2026, 1, 15), is_available=True).exists())

    def test_no_overlap_different_status(self):
        Avail.objects.create(stand_in=self.stand_in, start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True)
        avail = Avail(stand_in=self.stand_in, start_date=date(2026, 1, 16), end_date=date(2026, 1, 31), is_available=False)
        avail.save()

        self.assertEqual(Avail.objects.count(), 2)
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 1), end_date=date(2026, 1, 15), is_available=True).exists())
        self.assertTrue(Avail.objects.filter(start_date=date(2026, 1, 16), end_date=date(2026, 1, 31), is_available=False).exists())