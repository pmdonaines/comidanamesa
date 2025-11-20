from django.urls import path
from django.contrib.auth import views as auth_views
from apps.core.views import (
    home, DashboardView, FilaValidacaoView, ValidacaoDetailView, ValidacaoViewOnlyView, RelatoriosView,
    CriterioListView, CriterioCreateView, CriterioUpdateView, CriterioDeleteView
)

urlpatterns = [
    path('', home, name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('fila/', FilaValidacaoView.as_view(), name='fila_validacao'),
    path('relatorios/', RelatoriosView.as_view(), name='relatorios'),
    path('validacao/<int:pk>/', ValidacaoDetailView.as_view(), name='validacao_detail'),
    path('validacao/<int:pk>/visualizar/', ValidacaoViewOnlyView.as_view(), name='validacao_view'),
    
    # Gestão de Critérios
    path('criterios/', CriterioListView.as_view(), name='criterio_list'),
    path('criterios/novo/', CriterioCreateView.as_view(), name='criterio_create'),
    path('criterios/<int:pk>/editar/', CriterioUpdateView.as_view(), name='criterio_update'),
    path('criterios/<int:pk>/excluir/', CriterioDeleteView.as_view(), name='criterio_delete'),
    
    # login/logout usando views built-in do Django
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
]