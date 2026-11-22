from django.urls import path

from . import views

app_name = 'payments'
urlpatterns = [
    path('', views.index, name='index'),
    path('maya/pay/<int:order_id>/', views.pay, name='maya_pay'),
    path('maya/<int:pk>/', views.detail, name='maya_detail'),
    path('maya/<int:pk>/check/', views.check, name='maya_check'),
    path('maya/<int:pk>/status/', views.status_json, name='maya_status'),
    path('maya/return/<str:reference>/', views.maya_return, name='maya_return'),
    path('maya/webhook/', views.maya_webhook, name='maya_webhook'),
]
