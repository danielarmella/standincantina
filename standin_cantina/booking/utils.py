

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