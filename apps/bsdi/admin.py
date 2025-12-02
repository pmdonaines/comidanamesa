from django.contrib import admin
from .models import BSDIExportacao


@admin.register(BSDIExportacao)
class BSDIExportacaoAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'import_batch',
        'total_beneficiarios',
        'status',
        'gerado_por',
        'criado_em',
    ]
    list_filter = ['status', 'criado_em']
    search_fields = ['descricao', 'import_batch__description']
    readonly_fields = [
        'import_batch',
        'gerado_por',
        'arquivo',
        'total_beneficiarios',
        'criado_em',
        'atualizado_em',
    ]
    
    def has_add_permission(self, request):
        # Não permitir criação manual pelo admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Permitir apenas exclusão
        return True

