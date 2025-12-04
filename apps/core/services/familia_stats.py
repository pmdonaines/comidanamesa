"""
Serviço de Cálculos e Agregações para Relatórios de Famílias.

Fornece métodos para calcular estatísticas sobre composição familiar
com filtros por bairro, import batch, e período de análise.
"""

from django.db.models import Count, Q, Exists, OuterRef, QuerySet, IntegerField, Case, When, Sum
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
    
    def get_familias_queryset(self) -> QuerySet:
        """Retorna o queryset base de famílias com filtros aplicados (para uso externo)."""
        return self.queryset_base
    
    def _contar_por_status(self, familia_qs: QuerySet) -> dict:
        """
        Conta famílias por status de validação.
        
        Args:
            familia_qs: QuerySet de Familia para contar
        
        Returns:
            dict com contagens por status
        """
        # Anotar existência de validações aprovadas/reprovadas por família e agregar no banco
        familias = familia_qs.annotate(
            has_aprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='aprovado')),
            has_reprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='reprovado')),
        )

        ag = familias.aggregate(
            total=Count('id', distinct=True),
            aprovados=Sum(Case(When(has_aprovada=True, then=1), default=0, output_field=IntegerField())),
            reprovados=Sum(Case(When(has_reprovada=True, then=1), default=0, output_field=IntegerField())),
        )

        total = ag.get('total') or 0
        aprovados = ag.get('aprovados') or 0
        reprovados = ag.get('reprovados') or 0

        percentual = (aprovados / total * 100) if total > 0 else 0

        return {
            'total': int(total),
            'aprovados': int(aprovados),
            'reprovados': int(reprovados),
            'percentual_aprovacao': round(percentual, 2)
        }
    
    def _get_maes_solo_queryset(self) -> QuerySet:
        """Retorna queryset de famílias com mães solo (RF feminina sem cônjuge)."""
        return self.queryset_base.annotate(
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

    def get_maes_solo(self) -> dict:
        """
        Calcula estatísticas de famílias com mães solo (RF feminina sem cônjuge).
        
        Definição: RF feminina (cod_sexo_pessoa='2') sem cônjuge registrado.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        return self._contar_por_status(self._get_maes_solo_queryset())
    
    def _get_unipessoa_queryset(self) -> QuerySet:
        """Retorna queryset de famílias unipessoais (1 membro)."""
        return self.queryset_base.annotate(
            num_pessoas=Count('membros')
        ).filter(num_pessoas=1)

    def get_unipessoa(self) -> dict:
        """
        Calcula estatísticas de famílias unipessoais.
        
        Definição: Famílias com apenas 1 membro.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        return self._contar_por_status(self._get_unipessoa_queryset())
    
    def _get_casal_sem_filho_queryset(self) -> QuerySet:
        """Retorna queryset de casais sem filhos (2 membros, 0 filhos)."""
        return self.queryset_base.annotate(
            num_pessoas=Count('membros'),
            num_filhos=Count(
                'membros',
                filter=Q(membros__cod_parentesco_rf_pessoa=3)  # Filho
            )
        ).filter(num_pessoas=2, num_filhos=0)

    def get_casal_sem_filho(self) -> dict:
        """
        Calcula estatísticas de casais sem filhos.
        
        Definição: Exatamente 2 membros (RF + cônjuge) com 0 filhos.
        
        Returns:
            dict com total, aprovados, reprovados e percentual_aprovacao
        """
        return self._contar_por_status(self._get_casal_sem_filho_queryset())
    
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
        from django.db.models import IntegerField

        resultado = {'2': None, '3': None, '4': None, '5+': None}

        # Anotar número de filhos e presença de validações aprovadas/reprovadas
        # Buscar uma linha por família com número de filhos e flags de aprovação
        familias_annot = self.queryset_base.annotate(
            num_filhos=Count('membros', filter=Q(membros__cod_parentesco_rf_pessoa=3)),
            has_aprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='aprovado')),
            has_reprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='reprovado')),
        ).values('id', 'num_filhos', 'has_aprovada', 'has_reprovada')

        # Inicializar zeros
        for k in resultado.keys():
            resultado[k] = {'total': 0, 'aprovados': 0, 'reprovados': 0, 'percentual_aprovacao': 0}

        # Agregar em Python (uma query retornando uma linha por família)
        for row in familias_annot:
            n = row.get('num_filhos') or 0
            key = '5+' if n >= 5 else str(n)
            if key not in resultado:
                continue
            resultado[key]['total'] += 1
            if row.get('has_aprovada'):
                resultado[key]['aprovados'] += 1
            if row.get('has_reprovada'):
                resultado[key]['reprovados'] += 1

        # Calcular percentuais
        for k, v in resultado.items():
            total = v['total']
            v['percentual_aprovacao'] = round((v['aprovados'] / total * 100) if total > 0 else 0, 2)

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

        # Anotar existência de validações por família e agregar por bairro
        # Buscar uma linha por família com flags de aprovação e bairro
        familias_annot = self.queryset_base.annotate(
            has_aprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='aprovado')),
            has_reprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='reprovado')),
        ).values('id', 'nom_localidade_fam', 'has_aprovada', 'has_reprovada')

        # Agregar em Python por bairro (uma query retornando uma linha por família)
        temp = {}
        for row in familias_annot:
            bairro_nome = row.get('nom_localidade_fam') or 'Sem Bairro'
            if bairro_nome not in temp:
                temp[bairro_nome] = {'total': 0, 'aprovados': 0, 'reprovados': 0}
            temp[bairro_nome]['total'] += 1
            if row.get('has_aprovada'):
                temp[bairro_nome]['aprovados'] += 1
            if row.get('has_reprovada'):
                temp[bairro_nome]['reprovados'] += 1

        for bairro_nome, counts in temp.items():
            total = counts['total']
            if total >= min_familias:
                aprovados = counts['aprovados']
                reprovados = counts['reprovados']
                perc = (aprovados / total * 100) if total > 0 else 0
                resultado[bairro_nome] = {
                    'total': total,
                    'aprovados': aprovados,
                    'reprovados': reprovados,
                    'percentual_aprovacao': round(perc, 2)
                }

        return resultado

    def _get_filhos_queryset(self, num_filhos: int) -> QuerySet:
        """
        Retorna queryset de famílias com determinado número de filhos.
        
        Args:
            num_filhos: Número exato de filhos (use 5 para '5+')
        """
        qs = self.queryset_base.annotate(
            num_filhos=Count('membros', filter=Q(membros__cod_parentesco_rf_pessoa=3))
        )
        if num_filhos >= 5:
            return qs.filter(num_filhos__gte=5)
        return qs.filter(num_filhos=num_filhos)

    def get_familias_para_exportacao(self, categoria: str) -> QuerySet:
        """
        Retorna queryset de famílias para uma categoria específica (para exportação).
        
        Args:
            categoria: Uma de 'maes_solo', 'unipessoa', 'casal_sem_filho', '2', '3', '4', '5+'
        
        Returns:
            QuerySet de Familia com select_related para RF
        """
        if categoria == 'maes_solo':
            qs = self._get_maes_solo_queryset()
        elif categoria == 'unipessoa':
            qs = self._get_unipessoa_queryset()
        elif categoria == 'casal_sem_filho':
            qs = self._get_casal_sem_filho_queryset()
        elif categoria in ['2', '3', '4']:
            qs = self._get_filhos_queryset(int(categoria))
        elif categoria == '5+':
            qs = self._get_filhos_queryset(5)
        elif categoria == 'todas':
            qs = self.queryset_base
        else:
            qs = self.queryset_base.none()
        
        # Anotar status de validação para exportação
        return qs.annotate(
            has_aprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='aprovado')),
            has_reprovada=Exists(Validacao.objects.filter(familia_id=OuterRef('pk'), status='reprovado')),
        ).prefetch_related('membros')
