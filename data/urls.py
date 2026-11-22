from django.urls import path

from . import views

app_name = 'data'
urlpatterns = [
    path('', views.index, name='index'),
    path('import/upload/', views.import_upload, name='import_upload'),
    path('import/confirm/', views.import_confirm, name='import_confirm'),
    path('export/', views.export_xlsx, name='export'),
    path('backup/', views.backup_now, name='backup_now'),
    path('restore/', views.restore, name='restore'),
]
