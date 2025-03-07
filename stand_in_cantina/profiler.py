from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import json

from cantina.forms import UserRegistrationForm
from cantina.models import User, Email

import pytz


def profiler(request):
    user = request.user

    if request.method == "POST":
        user_form = UserRegistrationForm(request.POST, request.FILES, instance=user)

        if not user_form.is_valid():
            return JsonResponse({'success': False, 'errors': user_form.errors})
        # if profile_pic in request.FILES and user.profile_pic:
        #     # Delete the existing profile picture
        #     if os.path.isfile(user.profile_pic.path):
        #         os.remove(user.profile_pic.path)

        user_form.save()  # Save the updated user profile
        return JsonResponse({'success': True, 'message': "User account updated successfully"})
    else:
        user_form = UserRegistrationForm(instance=user)

    user = user.serialize()
    profile_form = str(profile_form)
    data = {
        'user': user,
        'user_form': user_form,
    }

    return JsonResponse(data, safe=False)