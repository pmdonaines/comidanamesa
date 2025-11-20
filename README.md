# comidanamesa

Sistema para cadastro e consulta dos beneficiários do programa "Comida na Mesa" — Município de Dona Inês (PB). O sistema importa a base do CECAD/CadÚnico e permite que operadores validem critérios de elegibilidade a partir da documentação apresentada.

Resumo rápido
- Linguagem: Python 3.13
- Framework: Django (>=5.2.8)
- Utilitário: python-dotenv para variáveis de ambiente

## Objetivos
- Importar e sincronizar a base CECAD/CadÚnico do município.
- Permitir que operadores validem documentos e critérios para concessão do benefício.
- Gerar relatórios e listas de beneficiários elegíveis.

## Critérios de elegibilidade
Os operadores devem avaliar os seguintes itens (pontuação e pesos podem ser configurados no sistema):

1. DOCUMENTAÇÃO (apresentação e validade dos documentos)
2. Famílias em extrema vulnerabilidade social com renda per capita de até R$ 218,00
3. Cadastro Único do município de Dona Inês/PB atualizado nos últimos 2 anos
4. Realização, nos últimos 2 anos, de exame citopatológico em mulheres (25–59 anos)
5. Atualização da caderneta de vacinação na primeira infância
6. Atualização da caderneta de vacinação de adolescentes
7. Atualização da vacinação COVID‑19
8. Alunos matriculados no EJA em 2025 (≥17 anos) ou certificado de conclusão
9. Matrícula ativa para o ano letivo 2025 (até 18 anos completos) ou certificado de conclusão
10. Frequência ≥75% da carga horária do ano/série (verificações bimestrais)

Observação: detalhar a pontuação dos critérios no módulo de configuração do sistema.

## Instalação (desenvolvimento)
1. Clonar repositório
2. Instalar o gerenciador `uv` (recomendado)
    - macOS / Linux (instalador oficial):
            ```bash
            curl -LsSf https://astral.sh/uv/install.sh | sh
            ```
    - Alternativas: `pip`, Homebrew, etc. Veja https://docs.astral.sh/uv/
3. Criar / ativar ambiente virtual
    - Criar ambiente com `uv` (cria `.venv` automaticamente):
            ```bash
            uv venv
            ```
            O comando exibirá como ativar (por exemplo: `Activate with: source .venv/bin/activate`).
    - Ou criar manualmente:
            ```bash
            python -m venv .venv
            source .venv/bin/activate   # Linux/macOS
            .venv\Scripts\activate     # Windows
            ```
4. Gerenciar dependências com `uv`
    - Instalar dependências do projeto:
            ```bash
            uv add django python-dotenv
            ```
            (O `uv add` resolve e instala os pacotes na `.venv` do projeto.)
    - Gerar/atualizar lockfile:
            ```bash
            uv lock
            ```
    - Sincronizar o ambiente a partir do lockfile:
            ```bash
            uv sync
            ```
    - Interface compatível com `pip` (opcional):
            ```bash
            uv pip sync requirements.txt
            ```
    - Quando empacotado (instalação editável):
            ```bash
            pip install -e .
            ```
    - Observação: também é possível executar scripts/comandos sem ativar a venv via `uv run`:
            ```bash
            uv run -- python manage.py migrate
            uv run -- python manage.py runserver
            ```
5. Configurar variáveis de ambiente
    - Criar arquivo `.env` com as variáveis necessárias (`DATABASE_URL`, `SECRET_KEY`, etc.)
    - Exemplo mínimo:
        - `DATABASE_URL=postgresql://user:pass@localhost:5432/comidanamesa`
        - `SECRET_KEY=<chave-secreta>`
6. Executar migrações e criar usuário admin
    - Com venv ativo ou via `uv run`:
            ```bash
            python manage.py migrate
            python manage.py createsuperuser
            ```
7. Executar servidor de desenvolvimento
    - Com venv ativo ou via `uv run`:
            ```bash
            python manage.py runserver
            ```

## Importação da base CECAD
- Fornecer utilitário/endpoint para importar arquivos fornecidos pelo CECAD (CSV, JSON, dump).
- Mapear campos mínimos (nome, CPF, endereço, renda, data atualização CadÚnico, vacinas, histórico de exames, matrícula).
- Validar duplicidade e registrar logs/auditoria.
- Após importação, os registros vão para fila de verificação onde operadores confirmam documentos e critérios.

## Fluxo de trabalho do operador
1. Carregar/atualizar base CECAD.
2. Abrir fila de validação.
3. Conferir documentação e marcar cada critério aplicável.
4. Salvar decisão (evidenciar documentos e observações).
5. Gerar listagens de beneficiários elegíveis e relatórios de controle.

## Segurança e privacidade
- Tratar dados pessoais sensíveis com criptografia em trânsito e em repouso.
- Registrar auditoria de acessos e alterações.
- Limitar acesso por função (operador, gestor, auditor).

## Desenvolvimento e contribuição
- Seguir convenções do Django e PEP8.
- Testes unitários e de integração são obrigatórios para novas funcionalidades.
- Abrir issues para bugs e features; enviar pull requests com descrição clara e testes.

## Observações e próximas etapas
- Definir esquema de pontuação dos critérios e prioridades.
- Implementar importador robusto com mapeamento configurável.
- Criar dashboard de controle e relatórios por indicadores sociais.

Licença: adicionar arquivo LICENSE conforme política do órgão/município.

**Frontend — Alpine.js vs HTMX**
- **Resumo:** este projeto usa tanto `Alpine.js` quanto `HTMX` para facilitar interfaces reativas leves sem o peso de frameworks SPA.
- **Quando usar `Alpine.js`:** lógica de UI local (dropdowns, modais, controles reativos), animações/transições, e manipulação do DOM puramente no cliente usando atributos como `x-data`, `x-show`, `@click`.
- **Quando usar `HTMX`:** comunicação cliente→servidor (AJAX via atributos HTML), atualização de fragmentos HTML retornados pelo backend (paginação, buscas "live", formulários que retornam snippets), arquitetura server-side first.
- **Usar em conjunto:** use `Alpine` para estados e interações locais e `HTMX` para buscar/atualizar HTML do servidor; eles se complementam bem (ex.: `htmx` carrega um fragmento que contém diretivas `x-data` do Alpine).

**Como estão integrados neste projeto**
- O template base está em `apps/core/templates/core/base.html` e já inclui as duas bibliotecas (htmx e alpine).
- Exemplos rápidos:

Alpine (ex.: dropdown simples):
```html
<div x-data="{ open: false }">
        <button @click="open = !open">Toggle</button>
        <div x-show="open">Conteúdo</div>
</div>
```

HTMX (ex.: carregar lista via fragmento):
```html
<button hx-get="/beneficiarios/lista/" hx-target="#lista" hx-swap="innerHTML">Carregar</button>
<div id="lista"></div>
```

**Tailwind CSS — build e arquivos**
- Arquivos relevantes:
        - `tailwindcss/input.css` — arquivo de entrada (contém `@import "tailwindcss";`).
        - `apps/core/static/tailwindcss/output.css` — arquivo CSS gerado (usado pelo `base.html`).
        - `package.json` já inclui dependências `@tailwindcss/cli` e `tailwindcss`.

- Comandos úteis (sem alterar `package.json`):
```bash
# Instalar dependências frontend (uma única vez)
npm install

# Gerar o CSS (build único)
npx @tailwindcss/cli -i ./tailwindcss/input.css -o ./apps/core/static/tailwindcss/output.css

# Rodar em modo watch (recomendado durante desenvolvimento)
npx @tailwindcss/cli -i ./tailwindcss/input.css -o ./apps/core/static/tailwindcss/output.css --watch
```

- Sugestão de scripts `package.json` (opcional):
```json
"scripts": {
        "build:css": "@tailwindcss/cli -i ./tailwindcss/input.css -o ./apps/core/static/tailwindcss/output.css",
        "watch:css": "@tailwindcss/cli -i ./tailwindcss/input.css -o ./apps/core/static/tailwindcss/output.css --watch"
}
```

**Boas práticas**
- Mantenha `input.css` (fonte) no repositório e considere adicionar `output.css` ao `.gitignore` se preferir não versionar arquivos gerados; em equipes pequenas é aceitável versionar o `output.css` para facilitar deploys sem build.
- Prefira compilar o CSS no ambiente de desenvolvimento/CI (ex.: `npm run build:css`) antes de deploy.
- Documente no README localmente qualquer passo necessário para build front-end (ex.: Node/npm/pnpm requerido).

