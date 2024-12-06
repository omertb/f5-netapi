from django.urls import path
from . import views


urlpatterns = [
    path('', views.vs_page, name="vs_page"),
    path('virtuals.json', views.virtuals, name="virtuals_page"),
    path('show', views.show_vs, name="show_vs"),
    path('member_states.json', views.retrieve_member_states, name="member_states_json"),
    path('member_states_diff', views.member_states_diff, name="member_states_diff"),
]