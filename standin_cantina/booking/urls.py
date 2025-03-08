from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

# from .admin import send_avail_checks

app_name = 'booking'

urlpatterns = [
    path("", views.index, name="index"),
    
    # path("strip", views.strip, name="strip"),
    # path("teststrip", views.teststrip, name="teststrip"),
    path("fix_booking_dates", views.fix_booking_dates, name="fix_booking_dates"),

    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register_user", views.register_user_view, name="register_user"),
    path("register_standin/<int:user_id>/", views.register_standin_view, name="register_standin"),

    # path('register', views.register_view, name="register"),
    path("login", views.login_view, name="login"),
    path("user_account", views.user_account_view, name="user_account"),
    path("standin_profile", views.standin_profile_view, name="standin_profile"),
    path("logout", views.logout, name="logout"),
    # path("register", views.UserRegistrationView.as_view(), name="register"),
    # path("register/standin/", views.StandInRegistrationView.as_view(), name="standin_registration"),
    path("registration_pending/", views.registration_pending, name="registration_pending"),
    path("availability/accept/<int:request_id>/<int:standin_id>/", views.accept_availability, name="accept_availability"),
    path("availability/reject/", views.reject_availability, name="reject_availability"),
    # path("admin/send_avail_checks/", send_avail_checks, name="send_avail_checks"),
    path("booking-requests/", views.BookingRequestListView.as_view(), name="booking_request_list"),
    path("booking-requests/new/", views.BookingRequestCreateView.as_view(), name="booking_request_create"),
    path("booking-requests/<int:pk>/edit/", views.BookingRequestUpdateView.as_view(), name="booking_request_edit"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)