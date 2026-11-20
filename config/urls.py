from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('stock/', include('stock.urls')),
    path('sales/', include('sales.urls')),
    path('', include('core.urls')),
]
