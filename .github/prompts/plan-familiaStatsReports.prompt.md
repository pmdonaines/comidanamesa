# Plan: Implementar Relatórios de Famílias (Total e Aprovados)

## Overview

Criar 5 tipos de relatórios de composição familiar com estatísticas de total e aprovados. Será implementado um serviço de cálculos (`FamiliaStatsService`), views de relatório com filtros, e templates com tabelas/gráficos. Todos os relatórios seguirão o padrão CBV e agregações Django existente.

## Requirements

### Relatórios a Implementar

1. **Relatórios de famílias com mães solo (Sem conjugue)**
   - Contagem de famílias onde RF é feminina E não há cônjuge
   - Total e Aprovados

2. **Quantitativos de famílias unipessoa**
   - Famílias com apenas 1 membro (método `is_unipessoal()` já existe)
   - Total e Aprovados

3. **Quantitativos de famílias casal sem filho**
   - Famílias com exatamente 2 membros onde ambos são cônjuges (RF + cônjuge)
   - Total e Aprovados

4. **Quantitativos de famílias com 2, 3, 4, 5 ou mais filhos**
   - Quebra por quantidade de filhos (cod_parentesco_rf_pessoa = 3)
   - 5 categorias: 2, 3, 4, 5+
   - Total e Aprovados para cada categoria

5. **Quantitativos de famílias contemplados por Bairro/áreas**
   - Agregação por `nom_bairro_fam`
   - Total e Aprovados por bairro
   - Opção de filtro: mostrar todos ou mínimo de famílias

## Technical Architecture

### 1. Serviço de Cálculos (`apps/core/services/familia_stats.py`)

**Classe:** `FamiliaStatsService`

```python
class FamiliaStatsService:
    def __init__(self, import_batch=None, filtros=None):
        # filtros: {'bairro': str, 'data_inicio': date, 'data_fim': date}
        self.import_batch = import_batch
        self.filtros = filtros or {}
        self.queryset_base = self._get_queryset_base()
    
    def _get_queryset_base(self) -> QuerySet:
        # Retorna base com filtros aplicados
    
    def get_maes_solo(self) -> dict:
        # {'total': int, 'aprovados': int, 'percentual': float}
        # RF feminina (cod_sexo_pessoa='2') sem cônjuge
    
    def get_unipessoa(self) -> dict:
        # Famílias com is_unipessoal()=True
    
    def get_casal_sem_filho(self) -> dict:
        # 2 membros: RF + cônjuge, sem filhos
    
    def get_filhos_quantitativos(self) -> dict:
        # {'2': {...}, '3': {...}, '4': {...}, '5+': {...}}
        # Contagem por quantidade de filhos
    
    def get_por_bairro(self, min_familias=0) -> dict:
        # {'BAIRRO1': {'total': int, 'aprovados': int, ...}, ...}
    
    def _contar_filhos(familia) -> int:
        # Conta filhos (cod_parentesco_rf_pessoa = 3)
    
    def _eh_aprovada(familia) -> bool:
        # Valida via status de Validacao
```

**Padrão de retorno para cada método:**
```python
{
    'total': int,
    'aprovados': int,
    'reprovados': int,
    'percentual_aprovacao': float  # aprovados/total * 100
}
```

### 2. Queries Parametrizadas

**Base de dados:**
- `Familia`: modelo principal
- `Pessoa`: membros da família (related_name='membros')
- `Validacao`: status de aprovação (OneToOne com Familia)

**Campos-chave:**
- `Pessoa.cod_parentesco_rf_pessoa`: 1=RF, 2=Cônjuge, 3=Filho
- `Pessoa.cod_sexo_pessoa`: '1'=M, '2'=F
- `Validacao.status`: 'aprovado', 'reprovado', 'pendente', 'em_analise'
- `Familia.nom_bairro_fam`: nome do bairro

**Exemplo - Mães Solo:**
```python
def get_maes_solo(self):
    # RF feminina sem cônjuge
    familias_total = self.queryset_base.annotate(
        tem_conjugue=Exists(Pessoa.objects.filter(
            familia_id=OuterRef('id'),
            cod_parentesco_rf_pessoa=2
        ))
    ).filter(
        responsavel_familiar__cod_sexo_pessoa='2',
        tem_conjugue=False
    ).count()
    
    # Mesma query com Validacao.status='aprovado'
    familias_aprovadas = self.queryset_base.filter(
        validacao__status='aprovado'
    ).annotate(...).filter(...).count()
    
    return {
        'total': familias_total,
        'aprovados': familias_aprovadas,
        'percentual_aprovacao': (familias_aprovadas / familias_total * 100) if familias_total > 0 else 0
    }
```

### 3. View de Relatório (`apps/core/views.py`)

**Classe:** `RelatoriosFamiliasView(LoginRequiredMixin, TemplateView)`

```python
class RelatoriosFamiliasView(LoginRequiredMixin, TemplateView):
    template_name = 'core/relatorios_familias.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter parametros de filtro
        bairro = self.request.GET.get('bairro', '')
        import_batch_id = self.request.GET.get('import_batch', '')
        
        # Determinar import_batch (padrão: mais recente)
        if import_batch_id:
            import_batch = ImportBatch.objects.get(id=import_batch_id)
        else:
            import_batch = ImportBatch.objects.latest('data_importacao')
        
        # Inicializar serviço
        filtros = {'bairro': bairro} if bairro else {}
        stats = FamiliaStatsService(import_batch=import_batch, filtros=filtros)
        
        # Adicionar relatórios ao contexto
        context.update({
            'maes_solo': stats.get_maes_solo(),
            'unipessoa': stats.get_unipessoa(),
            'casal_sem_filho': stats.get_casal_sem_filho(),
            'filhos_quantitativos': stats.get_filhos_quantitativos(),
            'por_bairro': stats.get_por_bairro(min_familias=0),
            
            'import_batches': ImportBatch.objects.all().order_by('-data_importacao'),
            'import_batch_selecionado': import_batch,
            'bairros': Familia.objects.values_list('nom_bairro_fam', flat=True).distinct(),
            'bairro_filtro': bairro,
        })
        
        return context
```

### 4. Template (`templates/core/relatorios_familias.html`)

**Estrutura:**
```html
{% extends 'base.html' %}

{% block title %}Relatórios de Famílias{% endblock %}

{% block content %}
<div class="container mx-auto py-6">
    <h1 class="text-3xl font-bold mb-6">Relatórios de Composição Familiar</h1>
    
    <!-- Filtros -->
    <div class="bg-gray-100 p-4 rounded mb-6">
        <form method="get" class="grid grid-cols-3 gap-4">
            <div>
                <label>Lote de Importação</label>
                <select name="import_batch">
                    <option value="">Mais Recente</option>
                    {% for batch in import_batches %}
                        <option value="{{ batch.id }}" {% if batch.id == import_batch_selecionado.id %}selected{% endif %}>
                            {{ batch.data_importacao|date:"d/m/Y" }} ({{ batch.familias.count }})
                        </option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label>Bairro</label>
                <select name="bairro">
                    <option value="">Todos</option>
                    {% for bairro in bairros %}
                        <option value="{{ bairro }}" {% if bairro == bairro_filtro %}selected{% endif %}>
                            {{ bairro }}
                        </option>
                    {% endfor %}
                </select>
            </div>
            <div class="flex items-end">
                <button type="submit" class="bg-blue-500 text-white px-4 py-2 rounded">Filtrar</button>
            </div>
        </form>
    </div>
    
    <!-- Tabela de Relatórios -->
    <div class="bg-white rounded shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">Resumo por Tipo de Composição Familiar</h2>
        <table class="w-full border-collapse">
            <thead class="bg-gray-200">
                <tr>
                    <th class="border px-4 py-2 text-left">Tipo de Composição</th>
                    <th class="border px-4 py-2 text-center">Total</th>
                    <th class="border px-4 py-2 text-center">Aprovados</th>
                    <th class="border px-4 py-2 text-center">% Aprovação</th>
                </tr>
            </thead>
            <tbody>
                <!-- Mães Solo -->
                <tr class="hover:bg-gray-50">
                    <td class="border px-4 py-2 font-semibold">Mães Solo (sem cônjuge)</td>
                    <td class="border px-4 py-2 text-center">{{ maes_solo.total }}</td>
                    <td class="border px-4 py-2 text-center text-green-600">{{ maes_solo.aprovados }}</td>
                    <td class="border px-4 py-2 text-center">{{ maes_solo.percentual_aprovacao|floatformat:1 }}%</td>
                </tr>
                
                <!-- Unipessoa -->
                <tr class="hover:bg-gray-50">
                    <td class="border px-4 py-2 font-semibold">Famílias Unipessoa</td>
                    <td class="border px-4 py-2 text-center">{{ unipessoa.total }}</td>
                    <td class="border px-4 py-2 text-center text-green-600">{{ unipessoa.aprovados }}</td>
                    <td class="border px-4 py-2 text-center">{{ unipessoa.percentual_aprovacao|floatformat:1 }}%</td>
                </tr>
                
                <!-- Casal sem Filho -->
                <tr class="hover:bg-gray-50">
                    <td class="border px-4 py-2 font-semibold">Casal sem Filhos</td>
                    <td class="border px-4 py-2 text-center">{{ casal_sem_filho.total }}</td>
                    <td class="border px-4 py-2 text-center text-green-600">{{ casal_sem_filho.aprovados }}</td>
                    <td class="border px-4 py-2 text-center">{{ casal_sem_filho.percentual_aprovacao|floatformat:1 }}%</td>
                </tr>
                
                <!-- Famílias com Filhos -->
                {% for categoria, dados in filhos_quantitativos.items %}
                <tr class="hover:bg-gray-50">
                    <td class="border px-4 py-2 font-semibold">
                        {% if categoria == '5+' %}
                            5 ou mais filhos
                        {% else %}
                            {{ categoria }} filhos
                        {% endif %}
                    </td>
                    <td class="border px-4 py-2 text-center">{{ dados.total }}</td>
                    <td class="border px-4 py-2 text-center text-green-600">{{ dados.aprovados }}</td>
                    <td class="border px-4 py-2 text-center">{{ dados.percentual_aprovacao|floatformat:1 }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- Gráfico Comparativo -->
    <div class="bg-white rounded shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold mb-4">Gráfico Comparativo: Total vs Aprovados</h2>
        <canvas id="graficoComparativo"></canvas>
    </div>
    
    <!-- Tabela por Bairro -->
    <div class="bg-white rounded shadow-md p-6">
        <h2 class="text-xl font-bold mb-4">Distribuição por Bairro</h2>
        <table class="w-full border-collapse">
            <thead class="bg-gray-200">
                <tr>
                    <th class="border px-4 py-2 text-left">Bairro</th>
                    <th class="border px-4 py-2 text-center">Total</th>
                    <th class="border px-4 py-2 text-center">Aprovados</th>
                    <th class="border px-4 py-2 text-center">% Aprovação</th>
                </tr>
            </thead>
            <tbody>
                {% for bairro, dados in por_bairro.items %}
                <tr class="hover:bg-gray-50">
                    <td class="border px-4 py-2">{{ bairro|default:"Sem Bairro" }}</td>
                    <td class="border px-4 py-2 text-center">{{ dados.total }}</td>
                    <td class="border px-4 py-2 text-center text-green-600">{{ dados.aprovados }}</td>
                    <td class="border px-4 py-2 text-center">{{ dados.percentual_aprovacao|floatformat:1 }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <!-- Botão Exportar -->
    <div class="mt-6">
        <a href="{% url 'core:relatorios-familias-export' %}" class="bg-green-500 text-white px-4 py-2 rounded">
            📥 Exportar para Excel
        </a>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
<script>
    const ctx = document.getElementById('graficoComparativo').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [
                'Mães Solo',
                'Unipessoa',
                'Casal s/ Filhos',
                '2 Filhos',
                '3 Filhos',
                '4 Filhos',
                '5+ Filhos'
            ],
            datasets: [
                {
                    label: 'Total',
                    data: [
                        {{ maes_solo.total }},
                        {{ unipessoa.total }},
                        {{ casal_sem_filho.total }},
                        {{ filhos_quantitativos.2.total }},
                        {{ filhos_quantitativos.3.total }},
                        {{ filhos_quantitativos.4.total }},
                        {{ filhos_quantitativos.5+.total }}
                    ],
                    backgroundColor: 'rgba(54, 162, 235, 0.5)'
                },
                {
                    label: 'Aprovados',
                    data: [
                        {{ maes_solo.aprovados }},
                        {{ unipessoa.aprovados }},
                        {{ casal_sem_filho.aprovados }},
                        {{ filhos_quantitativos.2.aprovados }},
                        {{ filhos_quantitativos.3.aprovados }},
                        {{ filhos_quantitativos.4.aprovados }},
                        {{ filhos_quantitativos.5+.aprovados }}
                    ],
                    backgroundColor: 'rgba(75, 192, 75, 0.5)'
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Composição Familiar: Total vs Aprovados'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
</script>
{% endblock %}
```

### 5. URLs (`apps/core/urls.py`)

```python
urlpatterns = [
    # ... existing patterns ...
    path('relatorios/familias/', RelatoriosFamiliasView.as_view(), name='relatorios-familias'),
    path('relatorios/familias/export/', RelatoriosFamiliasExportView.as_view(), name='relatorios-familias-export'),
]
```

### 6. Exportação (Opcional) - `apps/core/services/familia_stats_exporter.py`

```python
class FamiliaStatsExporter:
    def __init__(self, import_batch=None, filtros=None):
        self.stats = FamiliaStatsService(import_batch, filtros)
        self.import_batch = import_batch
    
    def gerar_arquivo(self) -> bytes:
        # Criar workbook com openpyxl
        # Sheet 1: Resumo por composição
        # Sheet 2: Por bairro
        # Sheet 3: Detalhes de cada categoria
        # Retornar bytes do arquivo
```

**View de exportação:**
```python
class RelatoriosFamiliasExportView(LoginRequiredMixin, View):
    def get(self, request):
        exporter = FamiliaStatsExporter()
        file_bytes = exporter.gerar_arquivo()
        
        response = HttpResponse(
            file_bytes,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="relatorios_familias.xlsx"'
        return response
```

## Implementation Steps

1. ✅ Criar `apps/core/services/familia_stats.py` com `FamiliaStatsService`
2. ✅ Estender `apps/core/views.py` com `RelatoriosFamiliasView`
3. ✅ Criar template `templates/core/relatorios_familias.html`
4. ✅ Atualizar `apps/core/urls.py` com novas rotas
5. ✅ (Opcional) Criar `apps/core/services/familia_stats_exporter.py` e `RelatoriosFamiliasExportView`
6. ✅ Testes unitários para `FamiliaStatsService`
7. ✅ Testes de view e template

## Configuration Questions & Decisions

### Q1: Definição de "Mães Solo"
**Opções:**
- A) RF feminina sem cônjuge (independente de filhos)
- B) RF feminina com pelo menos 1 filho, sem cônjuge

**Decisão:** Opção A (RF feminina sem cônjuge, independente de filhos)

**Justificativa:** Mais abrangente, inclui idosas viúvas/divorciadas sem filhos.

### Q2: Bairros com Poucos Dados
**Opções:**
- A) Mostrar todos os bairros
- B) Filtro configurável com mínimo de famílias
- C) Padrão: mínimo 5 famílias

**Decisão:** Opção A com B (mostrar todos por padrão, com parâmetro GET `min_familias`)

**Justificativa:** Flexibilidade e transparência de dados.

### Q3: Período de Análise
**Opções:**
- A) Filtro obrigatório por import_batch
- B) Padrão: últimas 30 dias
- C) Padrão: import_batch mais recente
- D) Agregar todos

**Decisão:** Opção C (padrão: import_batch mais recente, com dropdown para alterar)

**Justificativa:** Análise focada nos dados mais atualizados, mas com flexibilidade.

### Q4: Famílias com "Filhos"
**Definição:** Contar apenas pessoas com `cod_parentesco_rf_pessoa=3`

**Nota:** Não incluir enteados (`cod_parentesco_rf_pessoa=4`) na contagem de filhos (pode ser configurável depois).

### Q5: Categorias de Filhos
**Decisão:** 5 categorias: 2, 3, 4, 5+

**Justificativa:** Cobertura ampla e fácil agregação (5+ captura tendências de famílias grandes).

### Q6: Familias "Casal sem Filho"
**Definição:** Exatamente 2 membros (RF + cônjuge) com 0 filhos

**Query:**
```python
Familia.objects.annotate(
    num_pessoas=Count('membros'),
    num_filhos=Count('membros', filter=Q(membros__cod_parentesco_rf_pessoa=3))
).filter(num_pessoas=2, num_filhos=0)
```

## Performance Considerations

1. **Índices necessários:**
   - `(familia_id, cod_parentesco_rf_pessoa)` em `Pessoa`
   - `(familia_id, status)` em `Validacao`
   - `(nom_bairro_fam)` em `Familia`

2. **Query optimization:**
   - Usar `.select_related()` e `.prefetch_related()` em FamiliaStatsService
   - Cachear resultados de agregações (redis ou timeout curto)
   - Usar `.annotate()` ao máximo em vez de processamento Python

3. **Pagination:**
   - Tabela de bairro: mostrar 20 por página se > 100 bairros
   - Não paginar tabela de composição (5 linhas)

## Testing Strategy

1. **Testes unitários** (`tests/test_familia_stats.py`):
   - Criar fixtures: famílias com diferentes composições
   - Testar cada método de `FamiliaStatsService`
   - Validar contagens e percentuais

2. **Testes de view** (`tests/test_relatorios_familias_view.py`):
   - GET sem filtros (padrão)
   - GET com filtros (bairro, import_batch)
   - Validar contexto e dados

3. **Testes de template**:
   - Renderização correta de tabelas
   - Presença de gráfico Charts.js
   - Botão de exportação

## Acceptance Criteria

- [ ] Todos os 5 relatórios exibem corretamente (total/aprovados/%)
- [ ] Filtros funcionam (bairro, import_batch)
- [ ] Gráfico comparativo renderiza
- [ ] Tabela por bairro mostra todos os bairros com dados
- [ ] Percentuais calculados corretamente
- [ ] (Opcional) Exportação XLSX funciona
- [ ] Performance aceitável (<2s para carregar)
- [ ] Testes com cobertura >80%
