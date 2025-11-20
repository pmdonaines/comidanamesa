from django.contrib import admin
from .models import (
    Categoria, 
    Criterio, 
    Validacao, 
    ValidacaoCriterio, 
    DocumentoPessoa,
    DocumentoValidacao
)


class ValidacaoCriterioInline(admin.TabularInline):
    model = ValidacaoCriterio
    extra = 0

class DocumentoInline(admin.TabularInline):
    model = DocumentoValidacao
    extra = 0


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo', 'ordem', 'icone', 'ativo')
    list_editable = ('ordem', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'codigo')


@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'categoria', 'codigo', 'pontos', 'peso', 'ativo')
    list_editable = ('pontos', 'peso', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('descricao', 'codigo')
    prepopulated_fields = {'codigo': ('descricao',)}


@admin.register(Validacao)
class ValidacaoAdmin(admin.ModelAdmin):
    list_display = ('familia', 'status', 'pontuacao_total', 'operador', 'data_validacao')
    list_filter = ('status', 'data_validacao')
    search_fields = ('familia__cod_familiar_fam',)
    inlines = [ValidacaoCriterioInline, DocumentoInline]
    readonly_fields = ('pontuacao_total',)

@admin.register(DocumentoPessoa)
class DocumentoPessoaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'pessoa', 'numero_documento', 'validado', 'validado_por', 'created_at')
    list_filter = ('tipo', 'validado', 'created_at')
    search_fields = ('pessoa__nom_pessoa', 'pessoa__num_nis_pessoa_atual', 'numero_documento')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ['pessoa']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('pessoa', 'tipo', 'arquivo', 'numero_documento')
        }),
        ('Datas', {
            'fields': ('data_emissao', 'data_validade')
        }),
        ('Validação', {
            'fields': ('validado', 'validado_por', 'validado_em', 'observacoes')
        }),
        ('Metadados', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentoValidacao)
class DocumentoValidacaoAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'validacao', 'created_at')
    list_filter = ('created_at', 'tipo')
    search_fields = ('tipo', 'descricao', 'validacao__familia__cod_familiar_fam')

