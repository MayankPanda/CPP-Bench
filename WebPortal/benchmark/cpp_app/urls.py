from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('previous_benchmarks/', views.previous_benchmarks, name='previous_benchmarks'),
    path('download_csv/<int:benchmark_id>/', views.download_csv, name='download_csv'),
]
