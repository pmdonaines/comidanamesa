from django.contrib import admin
from .models import Criterio, Validacao, ValidacaoCriterio, Documento

class ValidacaoCriterioInline(admin.TabularInline):
    model = ValidacaoCriterio
    extra = 0

class DocumentoInline(admin.TabularInline):
    model = Documento
    extra = 0

@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'codigo', 'pontos', 'peso', 'ativo')
    list_editable = ('pontos', 'peso', 'ativo')
    prepopulated_fields = {'codigo': ('descricao',)}

@admin.register(Validacao)
class ValidacaoAdmin(admin.ModelAdmin):
    list_display = ('familia', 'status', 'pontuacao_total', 'operador', 'data_validacao')
    list_filter = ('status', 'data_validacao')
    search_fields = ('familia__cod_familiar_fam',)
    inlines = [ValidacaoCriterioInline, DocumentoInline]
    readonly_fields = ('pontuacao_total',)

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'validacao', 'validado')
    list_filter = ('validado', 'tipo')
