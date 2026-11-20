from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('staff/', views.staff_list, name='staff'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:pk>/toggle/', views.staff_toggle, name='staff_toggle'),
    path('staff/<int:pk>/reset/', views.staff_reset, name='staff_reset'),
    path('staff/<int:pk>/approve/', views.staff_approve, name='staff_approve'),
    path('staff/<int:pk>/reject/', views.staff_reject, name='staff_reject'),
]
