from django.urls import path

from . import views

app_name = 'notifications'
urlpatterns = [
    path('', views.index, name='index'),
    path('send/', views.send_manual, name='send'),
    path('<int:pk>/resend/', views.resend, name='resend'),
]
