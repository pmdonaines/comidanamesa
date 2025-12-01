from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='cecad_dashboard'),
    path('importar/', views.ImportDataView.as_view(), name='cecad_import'),
    path('importar/correcao/', views.ImportCorrectionView.as_view(), name='cecad_import_correction'),
    path('importar/progresso/<int:pk>/', views.ImportProgressView.as_view(), name='cecad_import_progress'),
    path('importar/progresso/<int:pk>/api/', views.ImportProgressAPIView.as_view(), name='cecad_import_progress_api'),
    path('historico/', views.ImportBatchListView.as_view(), name='cecad_batch_list'),
    path('historico/<int:pk>/', views.ImportBatchDetailView.as_view(), name='cecad_batch_detail'),
    path('comparar/', views.ComparisonView.as_view(), name='cecad_comparison'),
    
    # CRUD de Famílias
    path('familias/', views.FamiliaListView.as_view(), name='cecad_familia_list'),
    path('familias/nova/', views.FamiliaCreateView.as_view(), name='cecad_familia_create'),
    path('familias/<int:pk>/', views.FamiliaDetailView.as_view(), name='cecad_familia_detail'),
    path('familias/<int:pk>/editar/', views.FamiliaUpdateView.as_view(), name='cecad_familia_update'),
    path('familias/<int:pk>/excluir/', views.FamiliaDeleteView.as_view(), name='cecad_familia_delete'),
    
    # CRUD de Pessoas (nested dentro de Família)
    path('familias/<int:familia_pk>/membros/novo/', views.PessoaCreateView.as_view(), name='cecad_pessoa_create'),
    path('familias/<int:familia_pk>/membros/<int:pk>/editar/', views.PessoaUpdateView.as_view(), name='cecad_pessoa_update'),
    path('familias/<int:familia_pk>/membros/<int:pk>/excluir/', views.PessoaDeleteView.as_view(), name='cecad_pessoa_delete'),
    path('familias/<int:familia_pk>/membros/<int:pk>/', views.PessoaDetailView.as_view(), name='cecad_pessoa_detail'),

    # Transferência de Pessoa entre Famílias
    path('familias/<int:familia_pk>/membros/<int:pessoa_pk>/transferir/', views.PessoaTransferStartView.as_view(), name='cecad_pessoa_transfer_start'),
    path('transferencias/pessoas/<int:pessoa_pk>/buscar-familias/', views.PessoaTransferExistingSearchView.as_view(), name='cecad_pessoa_transfer_search_familias'),
    path('transferencias/pessoas/<int:pessoa_pk>/criar-familia/', views.PessoaTransferCreateFamilyView.as_view(), name='cecad_pessoa_transfer_create_familia'),
    path('transferencias/pessoas/<int:pessoa_pk>/confirmar/<int:dest_familia_pk>/', views.PessoaTransferConfirmView.as_view(), name='cecad_pessoa_transfer_confirm'),
]
