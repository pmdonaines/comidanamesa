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

### 3. Interface de Gestão de Critérios
- Atualizado o formulário de criação/edição de critérios para incluir a seção "Condições de Aplicação".

### 4. Lógica de Validação
- Criado serviço `CriteriaAssociator` em `apps/core/services/criteria_logic.py`.
- Atualizado `ValidacaoDetailView` para associar critérios dinamicamente ao abrir a validação, respeitando as condições configuradas.
- Atualizado comando `associar_criterios` para aplicar as regras em massa.
- Atualizado `signals.py` para respeitar as regras ao criar novos critérios.

## Como Testar

1. **Reimportar Dados (Recomendado)**:
   - Vá em "Importar Dados" e envie o arquivo CSV novamente para atualizar o campo "Sexo" das pessoas.

2. **Configurar Critérios**:
   - Vá em "Gestão de Critérios".
   - Edite um critério (ex: "Carteira de Vacinação").
   - Na seção "Condições de Aplicação", desmarque "Aplica-se a famílias unipessoais" ou "Aplica-se a famílias sem crianças".
   - Salve.

3. **Verificar Validação**:
   - Abra uma validação de uma família que se encaixe na condição (ex: unipessoal).
   - O critério configurado NÃO deve aparecer na lista de avaliação.
   - Abra uma validação de uma família que NÃO se encaixe (ex: família com crianças).
   - O critério DEVE aparecer.

## Arquivos Modificados
- `apps/cecad/models.py`
- `apps/cecad/services/importer.py`
- `apps/core/models.py`
- `apps/core/views.py`
- `apps/core/signals.py`
- `apps/core/management/commands/associar_criterios.py`
- `apps/core/templates/core/criterio_form.html`
- `apps/core/services/criteria_logic.py` (Novo)
