from django.urls import path
from . import views

app_name = 'bsdi'

urlpatterns = [
    path('exportacoes/', views.ExportacaoListView.as_view(), name='exportacao_list'),
    path('exportacoes/gerar/', views.gerar_exportacao, name='exportacao_gerar'),
    path('exportacoes/<int:pk>/download/', views.download_exportacao, name='exportacao_download'),
]
