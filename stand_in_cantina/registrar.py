from django.contrib.auth import login
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render
import re
from cantina.models import User
import phonenumbers
from datetime import datetime

from cantina.models import (
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
)



def registrar(request, app):
    context = {}
    context['status'] = 'error'

    email = request.POST.get("email").lower()
    if not email:
        context['message'] = 'Must include a valid email address'
        context['bungler'] = 'email'
        return JsonResponse(context)

    if User.objects.filter(email=email).exists():
        context['message'] = 'That email address is already registered.'
        context['bungler'] = 'email'
        return JsonResponse(context)

    username = email.split('@')[0]
    if request.POST.get("username"):
        username = request.POST.get("username").lower()

    if not re.match(r'^[a-z0-9_.+]+$', username):
        context['message'] = 'Username can only contain letters, numbers, underscores, and dots.'
        context['bungler'] = 'username'
        return JsonResponse(context)

    if User.objects.filter(username=username).exists():
        context['message'] = 'That username is already taken.'
        context['bungler'] = 'username'
        return JsonResponse(context)

    password1 = request.POST.get("password1")

    # Ensure password length
    if len(password1) < 8:
        context['message'] = 'Password must be at least 8 characters long.'
        context['bungler'] = 'password1'
        return JsonResponse(context)

    # Ensure password matches confirmation
    if not password1:
        context['message'] = 'Please include a password'
        context['bungler'] = 'password1'
        return JsonResponse(context)

    password2 = request.POST.get("password2")
    if not password2:
        context['message'] = 'Please confirm the password'
        context['bungler'] = 'password2'
        return JsonResponse(context)

    if password1 != password2:
        context['message'] = 'Passwords do not match.'
        context['bungler'] = 'password2'
        return JsonResponse(context)

    if request.POST.get("phone"):
        phone = request.POST.get("phone")
        parsed_phone = phonenumbers.parse(phone, "US")
        if not phonenumbers.is_valid_number(parsed_phone) or not phonenumbers.is_possible_number(parsed_phone):
            context['message'] = 'Please enter a valid phone number.'
            context['bungler'] = 'phone'
            return JsonResponse(context)
    else:
        phone = None

    print(f'{request.POST = }')
    if request.POST.get("birthday"):
        birthday = request.POST.get("birthday")
        date_format = "%Y-%m-%d"
        try:
            datetime.strptime(birthday, date_format)
        except ValueError:
            context['message'] = 'Please enter a valid birthday date.'
            context['bungler'] = 'birthday'
            return JsonResponse(context)
    else:
        birthday = None

    first_name = request.POST.get("first_name").lower()
    last_name = ''
    if not first_name:
        parts = username.split('.')
        num_parts = len(parts)
        if num_parts > 1:
            first_name = ""
            for i in range(num_parts - 1):
                if first_name:
                    first_name += " "
                first_name += parts[i]
            last_name = parts[num_parts - 1]
        else:
            first_name = username
            last_name = ""
    if request.POST.get("last_name"):
        last_name = request.POST.get("last_name").lower()

    is_stand_in = False
    if request.POST.get("is_standin"):
        is_stand_in = True
    else:
        is_stand_in = False

    # Attempt to create new user
    try:
        user = User.objects.create_user(username=username, password=password1, email=email, first_name=first_name, last_name=last_name, is_stand_in=is_stand_in, phone=phone, birthday=birthday)
    except IntegrityError as e:
        print(e)
        context['message'] = f'An error occurred. Make sure the email address or username is not already taken and your first and last name together are unique. ({e})'
        context['bungler'] = 'IntegrityError'
        return JsonResponse(context)
    return user


def registrar2(request, app, user_id):
    context = {}
    context['status'] = 'error'

    user = User.objects.get(pk=user_id)

    recommended_by = request.POST.get('recommended_by', '')
    if not recommended_by:
        context['message'] = 'To join the Stand-in Cantina you must be recommended by another stand-in.'
        context['bungler'] = 'recommended_by'
        return JsonResponse(context)

    if not StandIn.objects.filter(pk=recommended_by).exists():
        context['message'] = 'To join the Stand-in Cantina you must be recommended by another stand-in.'
        context['bungler'] = 'recommended_by'
        return JsonResponse(context)

    si_sponsor = StandIn.objects.filter(pk=recommended_by)[0]

    gender = request.POST.get("gender", '').lower()

    # height_feet = request.POST.get("height_feet", None)
    # except KeyError:
    #     context['message'] = 'Please enter your height'
    #     context['bungler'] = 'height_feet'
    #     return JsonResponse(context)


    feet = request.POST.get("height_in_inches_0")
    inches = request.POST.get("height_in_inches_1")
    if not feet or not inches:
        context['message'] = 'You must enter a height.'
        context['bungler'] = 'height_in_inches'
        return JsonResponse(context)

    try:
        feet = int(feet)
        inches = int(inches)
        height_in_inches = feet * 12 + inches
    except ValueError:
        context['message'] = 'Enter a valid height.'
        context['bungler'] = 'height_in_inches'
        return JsonResponse(context)
    if not 1 <= feet <= 9 and not 0 <= inches <= 11:
        context['message'] = 'Enter a valid height.'
        context['bungler'] = 'height_in_inches'
        return JsonResponse(context)

    weight_in_lbs = request.POST.get("weight_in_lbs")
    if not weight_in_lbs:
        weight_in_lbs = None

    skin_tone = request.POST.get("skin_tone", '')

    hair_length = request.POST.get("hair_length", "")

    age_range_min_input = request.POST.get("age_range_min", "").strip()
    age_range_min = age_range_min_input if age_range_min_input else user.age()

    age_range_max_input = request.POST.get("age_range_max", "").strip()
    age_range_max = age_range_max_input if age_range_max_input else user.age()

    if age_range_max and age_range_min:
        if age_range_max < age_range_min:
            age_range_max, age_range_min = age_range_min, age_range_max

        if age_range_max - age_range_min > 10:
            context['message'] = 'The maximum portrayable age range should be no more than 10 years.'
            context['bungler'] = 'age_range_max'
            return JsonResponse(context)

    matched_actors = request.POST.getlist("matched_actors", [])

    # print(f'{request.POST = }')
    # print(f'{user = }')
    # print(f'{si_sponsor = }')
    # print(f'{gender = }')
    # print(f'{height_in_inches = }')
    # print(f'{weight_in_lbs = }')
    # print(f'{skin_tone = }')
    # print(f'{hair_length = }')
    # print(f'{age_range_min = }')
    # print(f'{age_range_max = }')
    # print(f'{request.POST.getlist("matched_actors", []) = }')
    # print(f'{matched_actors = }')

    # Attempt to create Stand-in
    try:
        standin = StandIn.objects.create(user=user, recommended_by=si_sponsor, gender=gender, height_in_inches=height_in_inches if height_in_inches else None, weight_in_lbs=weight_in_lbs, skin_tone=skin_tone, hair_length=hair_length, age_range_min=age_range_min, age_range_max=age_range_max)
        for actor_id in matched_actors:
            print(f'{actor_id = }')
            print(f'{Actor.objects.filter(id=actor_id)[0] = }')
            actor = Actor.objects.filter(id=int(actor_id))[0]
            if actor:
                ActorStandInMatch.objects.create(stand_in=standin, actor=actor)
    except IntegrityError as e:
        print(e)
        context['message'] = f'An error occurred. ({e})'
        return JsonResponse(context)
    return user