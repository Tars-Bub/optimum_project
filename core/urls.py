from django.urls import path

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('search/', views.search, name='search'),
    path('style-guide/', views.style_guide, name='style_guide'),
    path('health/', views.health, name='health'),
]
