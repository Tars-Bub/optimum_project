from django.urls import path

from . import views

app_name = 'sales'
urlpatterns = [
    path('', views.index, name='index'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/item/<int:item_id>/<str:op>/', views.cart_update, name='cart_update'),
    path('cart/save/', views.cart_save, name='cart_save'),
    path('drafts/<int:pk>/delete/', views.draft_delete, name='draft_delete'),
    path('orders/<int:pk>/payment/', views.payment_add, name='payment_add'),
    path('returns/', views.returns_index, name='returns_index'),
    path('returns/process/', views.returns_process, name='returns_process'),
    path('returns/void/', views.returns_void, name='returns_void'),
]
