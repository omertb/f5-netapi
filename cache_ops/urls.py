from django.urls import path
from . import views


urlpatterns = [
    path('', views.cache_page, name="cache_page"),
    path('stats.json', views.create_cache_stats_json, name="cache_stats_json"),
    path('delete', views.delete_cache, name="delete_cache"),
]