from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='cecad_dashboard'),
    path('importar/', views.ImportDataView.as_view(), name='cecad_import'),
    path('historico/', views.ImportBatchListView.as_view(), name='cecad_batch_list'),
    path('historico/<int:pk>/', views.ImportBatchDetailView.as_view(), name='cecad_batch_detail'),
    path('comparar/', views.ComparisonView.as_view(), name='cecad_comparison'),
    path('familias/', views.FamiliaListView.as_view(), name='cecad_familia_list'),
    path('familias/<int:pk>/', views.FamiliaDetailView.as_view(), name='cecad_familia_detail'),
]
