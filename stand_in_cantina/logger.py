
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.shortcuts import HttpResponseRedirect
from django.urls import reverse


def logger(request, app):

    # Attempt to sign user in
    username = request.POST.get('username').lower()
    password = request.POST.get("password")
    user = authenticate(request, username=username, password=password)

    # Check if authentication successful
    if user is not None:
        login(request, user)
        return HttpResponseRedirect(reverse(f"{app}:index"), caller='logger')
    else:
        context = {}
        context['success'] = False
        if username == "":
            context['message'] = 'Must include a valid username'
            return JsonResponse(context)

        if password == "":
            context['message'] = 'Must include a password'
            return JsonResponse(context)

        context['message'] = 'Invalid username/password'
        return JsonResponse(context)