from django.urls import path
from . import views


urlpatterns = [
    path('', views.vs_page, name="vs_page"),
]