
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect, get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, CreateView, UpdateView, ListView

import datetime
from logger import logger
from registrar import registrar, registrar2
from standin_cantina.settings import EMAIL_HOST_USER

from .forms import UserRegistrationForm, StandInForm, BookingRequestForm
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
    Booking,
    AvailCheck,
    BookingRequest,
    BookingRequestImage
)


def index(request, **kwargs):
    print('STEP 01')

    user = request.user
    print(f'{user}')

    if request.method == "POST": # Booking request
        booking_request_form = BookingRequestForm(request.POST, instance=BookingRequest(
            date_posted=datetime.datetime.now()
            ))
        if booking_request_form.is_valid():
            booking_request_form.save()  # Save the post

    if not request.user.is_authenticated:
        print('User not logged in. Going to home.html')
        return render(request, "booking/home.html", {
        'title': 'Home',
        'user': user,
    })

    print(f'User is logged in as {user}')

    message = ""
    try:
        if kwargs['message']:
            message = kwargs['message']
    except KeyError:
        pass

    print('FINAL STEP')
    if user.is_standin:
        standin = user.standin
        print(f'User logged in as stand in {standin}. Going to standin.html')

        # Get Availabilities
        today = datetime.date.today()
        three_months_later = today + datetime.timedelta(days=90)

        availabilities = Availability.objects.filter(standin=standin).filter(
            Q(start_date__gte=today, start_date__lte=three_months_later) |
            Q(end_date__gte=today, end_date__lte=three_months_later))

        # Get AvailChecks
        avail_checks = AvailCheck.objects.filter(standins=standin)

        # Get Bookings
        bookings = Booking.objects.filter(standin=standin)
        for booking in bookings:
            print(f'{booking.standin = }')
            print(f'{booking.project = }')
            print(f'{booking.start_date = }')
            print(f'{booking.end_date = }')

        return render(request, "booking/standin.html", {
            'title': f'{user.first_name.capitalize()} {user.last_name.capitalize()}',
            'user': user,
            'availabilities': availabilities,
            'avail_checks': avail_checks,
            'bookings': bookings,
            'message': message
        })

    print('user.html')
    return render(request, "booking/user.html", {
        'title': f'{user.first_name} {user.last_name}',
        'user': user,
        'message': message
    })


def register_user_view(request):
    app = 'booking'
    message = None

    if request.method == "POST":
        reg = registrar(request, app=app)
        if isinstance(reg, JsonResponse): #Registration failed
            return reg
        return JsonResponse({'user': reg.serialize(), 'status': 'success', 'message': 'User created successfully'}, safe=False)

    user_reg_form = str(UserRegistrationForm())
    print(f'{user_reg_form = }')
    data = {
        'user_reg_form': user_reg_form,
        'message': message,
        }
    return JsonResponse(data, safe=False)


def register_standin_view(request, user_id):
    app = 'booking'
    message = None

    if request.method == "POST":
        reg = registrar2(request, app=app, user_id=user_id)
        if isinstance(reg, JsonResponse): #Registration failed
            return reg
        return JsonResponse({'user': reg.serialize(), 'status': 'success', 'message': 'Stand-in was created successfully'}, safe=False)

    user = User.objects.get(pk=user_id)
    standin_reg_form = str(StandInForm(initial={'user': user}))
    data = {
        'ok': True,
        'standin_reg_form': standin_reg_form,
        'message': message,
        }
    return JsonResponse(data, safe=False)


def login_view(request):
    app = 'booking'
    if request.method == "POST":
        return logger(request, app=app)
    return render(request, f'{app}/index.html')


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("booking:index"))


@login_required
def user_account_view(request):
    user = request.user
    message = ""
    return render(request, "booking/index.html", {
        'title': 'Home',
        'user': user,
        'message': message
    })


@login_required
def standin_profile_view(request):
    user = request.user
    message = ""
    return render(request, "booking/index.html", {
        'title': 'Home',
        'user': user,
        'message': message
    })


@login_required
def logout(request):
    user = request.user
    message = ""
    return render(request, "booking/index.html", {
        'title': 'Home',
        'user': user,
        'message': message
    })


# class UserRegistrationView(FormView):
#     model = User
    # template_name = "booking/registration_step1.html"
    # form_class = UserRegistrationForm
    # success_url = reverse('standin_registration') if form['is_standin'] else reverse('registration_pending')

    # def form_valid(self, form):
    #     user = form.save(commit=False)
    #     user.is_active = False  # Prevent login until approved
    #     user.save()

    #     send_mail(
    #         "New Registration Pending Approval",
    #         f"A new user {user.username} has registered and needs approval.",
    #         EMAIL_HOST_USER,
    #         [EMAIL_HOST_USER],
    #         fail_silently=False,
    #     )

    #     if form.cleaned_data["is_standin"]:
    #         self.request.session["pending_user_id"] = user.id  # Store user ID for next step
    #         return redirect("standin_registration")

    #     return redirect("registration_pending")


# class StandInRegistrationView(FormView):
#     template_name = "booking/registration_step2.html"
#     form_class = StandInForm

#     def dispatch(self, request, *args, **kwargs):
#         if "pending_user_id" not in request.session:
#             return redirect("register")  # Redirect if Step 1 wasn't completed
#         return super().dispatch(request, *args, **kwargs)

#     def form_valid(self, form):
#         user = User.objects.get(id=self.request.session["pending_user_id"])
#         standin = form.save(commit=False)
#         standin.user = user
#         standin.save()

#         return redirect("registration_pending")


@login_required
def registration_pending(request):
    return render(request, "registration_pending.html")


@login_required
def accept_availability(request, availcheck_id, standin_id):
    standin = get_object_or_404(StandIn, id=standin_id)
    avail_check = get_object_or_404(AvailCheck, id=availcheck_id)

    # Create an Availability entry with is_available=True
    Availability.objects.create(
        standin=standin,
        start_date=avail_check.start_date,
        end_date=avail_check.end_date,
        is_available=True,
        notes=f'Accepted AvailCheck for {avail_check.project}. ID# {availcheck_id}'
    )

    return HttpResponse("Thank you for accepting the avail check. Your availability has been updated. This is NOT A BOOKING.")

@login_required
def reject_availability(request):
    return HttpResponse("Please update your availability directly if necessary.")


class BookingRequestCreateView(CreateView):
    def get(self, request):
        form = BookingRequestForm()
        return render(request, "booking/booking_request_form.html", {"form": form})

    def post(self, request):
        form = BookingRequestForm(request.POST)
        files = request.FILES.getlist("images")  # Get multiple files

        if form.is_valid():
            booking_request = form.save(commit=False)
            booking_request.ad = request.ad  # Assign AD
            booking_request.save()
            form.save_m2m()  # Save ManyToMany actors

            # Save uploaded images
            for file in files:
                BookingRequestImage.objects.create(request=booking_request, image=file)

            return redirect("index")

        return render(request, "booking_request_form.html", {"form": form, "message": "Form invalid"})


class BookingRequestUpdateView(UpdateView):
    model = BookingRequest
    form_class = BookingRequestForm
    template_name = "booking_request_form.html"
    success_url = reverse_lazy("booking_request_list")

    def test_func(self):
        """Only allow ADs to edit their own BookingRequests unless it's closed."""
        booking_request = self.get_object()
        return self.request.user == booking_request.ad and booking_request.status != "Closed"


class BookingRequestListView(ListView):
    model = BookingRequest
    template_name = "booking/booking_request_list.html"
    context_object_name = "booking_requests"

    # def get_queryset(self):
    #     """Show only the booking requests submitted by the logged-in AD."""
    #     return BookingRequest.objects.filter(ad=self.request.user)


def strip(request):
    users = User.objects.all()
    for user in users:
        print(f'{user = }')
        user.password = user.password.strip()
        if not user.date_joined:
            user.date_joined = datetime.datetime.now()
        user.phone = '1-215-917-7265'
        user.username = user.username.strip()
        user.first_name = user.first_name.strip()
        user.last_name = user.last_name.strip()
        user.email = user.email.strip()
        user.save()
    return HttpResponse('done')


def teststrip(request):
    dan = User.objects.get(id=1)
    print(f'|{dan.id}|')
    print(f'|{dan.password}|')
    print(f'|{dan.last_login}|')
    print(f'|{dan.is_superuser}|')
    print(f'|{dan.username}|')
    print(f'|{dan.first_name}|')
    print(f'|{dan.last_name}|')
    print(f'|{dan.is_staff}|')
    print(f'|{dan.is_active}|')
    print(f'|{dan.date_joined}|')
    print(f'|{dan.phone}|')
    print(f'|{dan.birthday}|')
    print(f'|{dan.is_approved}|')
    print(f'|{dan.is_standin}|')
    print(f'|{dan.email}|')

    return HttpResponse('Done Testing strip')


def fix_booking_dates(request):
    bookings = Booking.objects.all()
    print(f'{bookings = }')

    for booking in bookings:
        print(f'{booking = }')
        print(f'{booking.id = }')
        print(f'{type(booking.start_date) = }')
        match booking.id:
            case 3:
                booking.start_date = datetime.date(2024, 10, 6)
                booking.end_date = datetime.date(2024, 10, 15)
            case 4:
                booking.start_date = datetime.date(2025, 1, 29)
                booking.end_date = datetime.date(2025, 2, 28)
            case 5:
                booking.start_date = datetime.date(2024, 3, 10)
                booking.end_date = datetime.date(2024, 10 ,5)
            case 15:
                booking.start_date = datetime.date(2025, 4, 12)
                booking.end_date = datetime.date(2025, 4, 12)
            case 16:
                booking.start_date = datetime.date(2025, 2, 15)
                booking.end_date = datetime.date(2025, 2, 15)
            case 17:
                booking.start_date = datetime.date(2025, 3, 20)
                booking.end_date = datetime.date(2025, 3, 20)
            case _:
                continue  # Skip cases that don't match
        booking.save()

    return HttpResponse('fix_booking_dates')