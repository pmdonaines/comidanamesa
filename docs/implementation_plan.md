# Plano de Implementação - Comida na Mesa

Este documento descreve o plano de implementação para o sistema "Comida na Mesa", focado na importação de dados do CECAD, validação de critérios de elegibilidade e gestão de beneficiários.

## Objetivos
- Estruturar o banco de dados para armazenar informações de famílias e beneficiários.
- Criar mecanismo de importação de dados do CECAD.
- Implementar regras de negócio para validação de elegibilidade.
- Desenvolver interface para operadores realizarem a validação documental.

## User Review Required
> [!IMPORTANT]
> **Definição de Pontuação**: O sistema precisa de uma tabela de pontuação configurável para os critérios. A implementação inicial usará valores padrão que podem ser ajustados via Django Admin.

## Proposed Changes

### 1. Modelagem de Dados (`apps/cecad` e `apps/core`)

#### [MODIFY] [cecad/models.py](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/cecad/models.py)
- Criar modelos para refletir a estrutura do CadÚnico/CECAD:
    - `Familia`: Dados socioeconômicos, renda per capita, endereço.
    - `Pessoa`: Dados pessoais (NIS, CPF, Nome), vínculo com família.
    - `Beneficio`: Histórico de benefícios recebidos.

#### [MODIFY] [core/models.py](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/models.py)
- Criar modelos para gestão do programa local:
## UI Redesign Plan

### Design System
- **Layout**: Switch from Top Navbar to **Sidebar Layout** for better scalability.
- **Typography**: Adopt **Inter** font for a modern, clean look.
- **Color Palette**:
    - Primary: Emerald (600) for actions and branding (matching the "Comida" theme).
    - Secondary: Slate (gray-500/900) for text and structure.
    - Background: Gray-50 for the main app area.
- **Components**:
    - **Cards**: White background, `shadow-sm`, `border-gray-200`.
    - **Tables**: Clean, spacious, with status badges and action menus.
    - **Buttons**: Rounded-lg, clear hierarchy (Primary, Secondary, Ghost).

### Files to Modify
#### [MODIFY] [base.html](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/templates/core/base.html)
- Implement Sidebar + Topbar structure.
- Add Alpine.js logic for mobile sidebar toggle.
- Import Google Fonts (Inter).

#### [MODIFY] [dashboard.html](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/templates/core/dashboard.html)
- Reorganize into a Grid layout.
- Add "Recent Activity" or "Quick Stats" section.

#### [MODIFY] [fila_validacao.html](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/templates/core/fila_validacao.html)
- Implement a full-width data table design.
- Improve filters and search bar.

#### [MODIFY] [validacao_detail.html](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/templates/core/validacao_detail.html)
- Two-column layout: Family Profile (Left) vs Validation Checklist (Right).
- Sticky header for actions.

## Verification Plan
- Verify responsive behavior (mobile sidebar).
- Check visual consistency across all pages.
- Ensure HTMX interactions (search, pagination) still work seamlessly.

### 2. Importação de Dados

#### [NEW] `apps/cecad/services/importer.py`
- Implementar serviço para ler arquivos (CSV/JSON) exportados do CECAD.
- Processar e normalizar dados para os modelos `Familia` e `Pessoa`.
- Logar inconsistências e duplicidades.

#### [NEW] `apps/cecad/management/commands/import_cecad.py`
- Comando Django para executar a importação via terminal.

### 3. Lógica de Validação e Elegibilidade

#### [NEW] `apps/core/services/eligibility.py`
- Implementar motor de regras que verifica:
    1. Renda per capita <= R$ 218,00.
    2. CadÚnico atualizado (últimos 2 anos).
    3. Exames e Vacinação (baseado em input do operador ou dados cruzados).
    4. Frequência escolar.
- Calcular pontuação final da família.

### 4. Interface do Usuário (Views & Templates)

#### [MODIFY] [core/views.py](file:///home/marcos/Ws/projects-python/pmdonaines/comidanamesa/apps/core/views.py)
- `DashboardView`: Visão geral (total de famílias, pendentes de validação, aprovados).
- `FilaValidacaoView`: Lista de famílias que requerem análise.
- `ValidacaoDetailView`: Tela principal do operador para checar documentos e marcar critérios.

#### [NEW] Templates
- `apps/core/templates/core/dashboard.html`: Dashboard com gráficos simples.
- `apps/core/templates/core/fila_validacao.html`: Tabela com filtros (HTMX).
- `apps/core/templates/core/validacao_detail.html`: Formulário de validação (Alpine.js para interatividade).

## Verification Plan

### Automated Tests
- **Unit Tests**:
    - Testar parser de importação com arquivos de exemplo (mock).
    - Testar cálculo de elegibilidade com diferentes cenários de renda e composição familiar.
    - Comando: `pytest`

### Manual Verification
1. **Importação**:
    - Executar comando de importação com arquivo de teste.
    - Verificar se dados aparecem no Django Admin.
2. **Fluxo de Validação**:
    - Acessar sistema como operador.
    - Selecionar uma família na fila.
    - Marcar critérios (vacina, escola) e salvar.
    - Verificar se status da família mudou para "Elegível" ou "Inelegível".
