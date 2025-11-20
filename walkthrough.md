# Walkthrough - Implementação de Critérios Condicionais

## Visão Geral
Implementamos a funcionalidade que permite definir condições para a aplicação de critérios de validação. Agora é possível configurar se um critério deve ser ignorado para:
- Famílias sem crianças/adolescentes (menores de 18 anos).
- Famílias onde o Responsável Familiar (RF) é homem.
- Famílias unipessoais (apenas 1 membro).

## Alterações Realizadas

### 1. Modelo `Pessoa` e Importação
- **Adicionado campo `cod_sexo_pessoa`**: Agora o sistema armazena o sexo das pessoas (1=Masculino, 2=Feminino).
- **Atualizado Importador**: O processo de importação agora lê o campo `cod_sexo_pessoa` do arquivo CSV.
    - *Nota*: Para atualizar os dados existentes, basta reimportar o arquivo CSV.

### 2. Modelo `Criterio`
- Adicionados campos booleanos para controle de aplicação:
    - `aplica_se_a_sem_criancas` (Padrão: Sim)
    - `aplica_se_a_rf_homem` (Padrão: Sim)
    - `aplica_se_a_unipessoais` (Padrão: Sim)
- **Novos Campos Avançados**:
    - `idade_minima`: Idade mínima de um membro para o critério aplicar.
    - `idade_maxima`: Idade máxima de um membro para o critério aplicar.
    - `sexo_necessario`: Sexo específico (M/F) que um membro deve ter.

### 3. Interface de Gestão de Critérios
- Atualizado o formulário de criação/edição de critérios para incluir a seção "Condições de Aplicação" e "Condições Avançadas".

### 4. Lógica de Validação
- Atualizado serviço `CriteriaAssociator` para verificar idade e sexo dos membros da família.
- Se um critério tem `idade_maxima=18`, ele só será aplicado se a família tiver alguém com 18 anos ou menos.
- Se tem `sexo_necessario='F'` e `idade_minima=25`, só aplica se houver mulher com 25+ anos.

## Como Testar

1. **Reimportar Dados (Recomendado)**:
   - Vá em "Importar Dados" e envie o arquivo CSV novamente para atualizar o campo "Sexo" das pessoas.

2. **Configurar Critérios**:
   - Vá em "Gestão de Critérios".
   - Edite um critério (ex: "Carteira de Vacinação").
   - Na seção "Condições de Aplicação", desmarque "Aplica-se a famílias unipessoais" ou "Aplica-se a famílias sem crianças".
   - Salve.

4. **Popular Critérios Padrão**:
   - O comando `uv run python manage.py popular_criterios` foi atualizado para incluir os critérios oficiais de 2026 com as regras condicionais já configuradas.
   - Execute-o para atualizar a base de dados com os novos textos e regras.

## Arquivos Modificados
- `apps/cecad/models.py`
- `apps/cecad/services/importer.py`
- `apps/core/models.py`
- `apps/core/views.py`
- `apps/core/signals.py`
- `apps/core/management/commands/associar_criterios.py`
- `apps/core/management/commands/popular_criterios.py`
- `apps/core/templates/core/criterio_form.html`
- `apps/core/services/criteria_logic.py` (Novo)
