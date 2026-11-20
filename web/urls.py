from django.urls import path

from . import views

urlpatterns = [
    path('', views.login_page, name='login'),
    path('register/', views.register_page, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('products/', views.products, name='products'),
    path('stock/', views.stock, name='stock'),
    path('sales/', views.sales, name='sales'),
    path('returns/', views.returns, name='returns'),
    path('documents/', views.documents, name='documents'),
    path('reports/', views.reports, name='reports'),
    path('staff/', views.staff, name='staff'),
]
