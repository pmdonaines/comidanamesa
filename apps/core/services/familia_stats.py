"""
Serviço de Cálculos e Agregações para Relatórios de Famílias.

Fornece métodos para calcular estatísticas sobre composição familiar
com filtros por bairro, import batch, e período de análise.
"""

from django.db.models import Count, Q, Exists, OuterRef, QuerySet
from apps.cecad.models import Familia, Pessoa, ImportBatch
from apps.core.models import Validacao


class FamiliaStatsService:
    """
    Serviço para calcular estatísticas de composição familiar.
    
    Retorna dicionários padronizados com:
    - total: int (total de famílias)
    - aprovados: int (famílias aprovadas)
    - reprovados: int (famílias reprovadas)
    - percentual_aprovacao: float (percentual de aprovação)
    """
    
    def __init__(self, import_batch=None, filtros=None):
        """
        Inicializa o serviço.
        
        Args:
            import_batch: ImportBatch para filtrar, ou None (usa o mais recente)
            filtros: dict com {'bairro': str, ...} para filtros adicionais
        """
        self.import_batch = import_batch
        self.filtros = filtros or {}
        self.queryset_base = self._get_queryset_base()
    
    def _get_queryset_base(self) -> QuerySet:
        """Retorna queryset base com filtros aplicados."""
        qs = Familia.objects.all()
        
        # Filtrar por import_batch se fornecido
        if self.import_batch:
            qs = qs.filter(import_batch=self.import_batch)
        
        # Filtrar por bairro se fornecido
        if self.filtros.get('bairro'):
            qs = qs.filter(nom_localidade_fam=self.filtros['bairro'])
        
        return qs
    
    def _contar_por_status(self, familia_qs: QuerySet) -> dict:
        """
        Conta famílias por status de validação.
        
        Args:
            familia_qs: QuerySet de Familia para contar
        
        Returns:
            dict com contagens por status
        """
        familia_ids = familia_qs.values_list('id', flat=True)
        validacoes = Validacao.objects.filter(familia_id__in=familia_ids)
        
        total = familia_qs.count()
        aprovados = validacoes.filter(status='aprovado').values('familia_id').distinct().count()
        reprovados = validacoes.filter(status='reprovado').values('familia_id').distinct().count()
        
        percentual = (aprovados / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'aprovados': aprovados,
            'reprovados': reprovados,
            'percentual_aprovacao': round(percentual, 2)
        }
    
    def get_maes_solo(self) -> dict:
        """
        Calcula estatísticas de famílias com mães solo (RF feminina sem cônjuge).
        
        Definição: RF feminina (cod_sexo_pessoa='2') sem cônjuge registrado.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        # RF feminina sem cônjuge
        familias = self.queryset_base.annotate(
            tem_conjugue=Exists(
                Pessoa.objects.filter(
                    familia_id=OuterRef('id'),
                    cod_parentesco_rf_pessoa=2  # Cônjuge
                )
            ),
            rf_feminina=Exists(
                Pessoa.objects.filter(
                    familia_id=OuterRef('id'),
                    cod_parentesco_rf_pessoa=1,  # RF
                    cod_sexo_pessoa='2'  # Feminina
                )
            )
        ).filter(
            rf_feminina=True,
            tem_conjugue=False
        )
        
        return self._contar_por_status(familias)
    
    def get_unipessoa(self) -> dict:
        """
        Calcula estatísticas de famílias unipessoais.
        
        Definição: Famílias com apenas 1 membro.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        familias = self.queryset_base.annotate(
            num_pessoas=Count('membros')
        ).filter(num_pessoas=1)
        
        return self._contar_por_status(familias)
    
    def get_casal_sem_filho(self) -> dict:
        """
        Calcula estatísticas de casais sem filhos.
        
        Definição: Exatamente 2 membros (RF + cônjuge) com 0 filhos.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        familias = self.queryset_base.annotate(
            num_pessoas=Count('membros'),
            num_filhos=Count(
                'membros',
                filter=Q(membros__cod_parentesco_rf_pessoa=3)  # Filho
            )
        ).filter(num_pessoas=2, num_filhos=0)
        
        return self._contar_por_status(familias)
    
    def _contar_filhos(self, familia_id: int) -> int:
        """
        Conta o número de filhos de uma família.
        
        Args:
            familia_id: ID da família
        
        Returns:
            int com quantidade de filhos (cod_parentesco_rf_pessoa=3)
        """
        return Pessoa.objects.filter(
            familia_id=familia_id,
            cod_parentesco_rf_pessoa=3  # Filho
        ).count()
    
    def get_filhos_quantitativos(self) -> dict:
        """
        Calcula estatísticas de famílias por quantidade de filhos.
        
        Categorias: 2, 3, 4, 5+
        
        Returns:
            dict com formato:
            {
                '2': {'total': int, 'aprovados': int, ...},
                '3': {...},
                '4': {...},
                '5+': {...}
            }
        """
        resultado = {}
        categorias = ['2', '3', '4', '5+']
        
        for categoria in categorias:
            familias_ids = []
            
            # Iterar sobre famílias para contar filhos
            for familia in self.queryset_base:
                num_filhos = self._contar_filhos(familia.id)
                
                if categoria == '5+':
                    if num_filhos >= 5:
                        familias_ids.append(familia.id)
                else:
                    if num_filhos == int(categoria):
                        familias_ids.append(familia.id)
            
            # Contar por status
            if familias_ids:
                familias_qs = Familia.objects.filter(id__in=familias_ids)
                resultado[categoria] = self._contar_por_status(familias_qs)
            else:
                resultado[categoria] = {
                    'total': 0,
                    'aprovados': 0,
                    'reprovados': 0,
                    'percentual_aprovacao': 0
                }
        
        return resultado
    
    def get_por_bairro(self, min_familias=0) -> dict:
        """
        Calcula estatísticas por bairro.
        
        Args:
            min_familias: Filtro de mínimo de famílias por bairro (default: 0)
        
        Returns:
            dict com formato:
            {
                'BAIRRO1': {'total': int, 'aprovados': int, ...},
                'BAIRRO2': {...},
                ...
            }
        """
        resultado = {}
        
        # Agrupar familias por bairro
        bairros = self.queryset_base.values('nom_localidade_fam').distinct()
        
        for bairro_dict in bairros:
            bairro_nome = bairro_dict['nom_localidade_fam'] or 'Sem Bairro'
            
            # Filtrar famílias do bairro
            familias_bairro = self.queryset_base.filter(
                nom_localidade_fam=bairro_dict['nom_localidade_fam']
            )
            
            # Aplicar filtro de mínimo de famílias
            if familias_bairro.count() >= min_familias:
                resultado[bairro_nome] = self._contar_por_status(familias_bairro)
        
        return resultado
