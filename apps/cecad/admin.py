from django.contrib import admin
from .models import Familia, Pessoa, Beneficio, PessoaTransferHistory

@admin.register(Familia)
class FamiliaAdmin(admin.ModelAdmin):
    list_display = ('cod_familiar_fam', 'vlr_renda_media_fam', 'qtde_pessoas', 'dat_atual_fam', 'marc_pbf')
    search_fields = ('cod_familiar_fam', 'nom_logradouro_fam')
    list_filter = ('marc_pbf', 'dat_atual_fam')

@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ('nom_pessoa', 'num_nis_pessoa_atual', 'familia', 'cod_parentesco_rf_pessoa')
    search_fields = ('nom_pessoa', 'num_nis_pessoa_atual', 'num_cpf_pessoa')
    list_filter = ('cod_parentesco_rf_pessoa',)

@admin.register(Beneficio)
class BeneficioAdmin(admin.ModelAdmin):
    list_display = ('tipo_beneficio', 'valor', 'familia', 'data_referencia')
    list_filter = ('tipo_beneficio', 'data_referencia')


@admin.register(PessoaTransferHistory)
class PessoaTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'origem', 'destino', 'usuario', 'transferido_em')
    list_filter = ('usuario', 'transferido_em')
    search_fields = ('pessoa__nom_pessoa', 'origem__cod_familiar_fam', 'destino__cod_familiar_fam')
