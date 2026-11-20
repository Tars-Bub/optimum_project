from django.urls import path

from . import views

app_name = 'documents'
urlpatterns = [
    path('', views.index, name='index'),
    path('print/', views.print_doc, name='print_doc'),
    path('<int:pk>/view/', views.print_view, name='print_view'),
    path('<int:pk>/reprint/', views.reprint, name='reprint'),
]
