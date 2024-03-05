from django.urls import path
from . import views


urlpatterns = [
    path('', views.cert_page, name="cert_page"),
    path('sslprofiles.json', views.get_ssl_profiles, name="ssl_profiles_json"),
]