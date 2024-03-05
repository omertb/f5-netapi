from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect
import logging


logger = logging.getLogger(__name__)


def get_user_ip(req):
    x_forwarded_for = req.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        user_ip = x_forwarded_for.split(',')[-1]
    else:
        user_ip = req.META.get('REMOTE_ADDR')
    return user_ip


def user_login(request):
    return render(request, 'login.html')


def user_logout(request):
    user_ip = get_user_ip(request)
    logger.info(f"{user_ip} - Logout Success: {str(request.user)}")
    logout(request)
    return HttpResponseRedirect('/user/login')
