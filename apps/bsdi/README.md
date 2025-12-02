# Módulo BSDI - Banco Social de Dona Inês

## 📋 Descrição

O módulo BSDI (Banco Social de Dona Inês) é responsável por gerar listas de beneficiários aprovados no programa Comida na Mesa, no formato exigido pelo Banco Social para abertura de contas.

## 🎯 Funcionalidades

- ✅ Exportação automática de beneficiários aprovados
- ✅ Geração de arquivo XLS no formato padrão BSDI
- ✅ Histórico de exportações realizadas
- ✅ Download de arquivos anteriormente gerados
- ✅ Integração com o sistema de validações

## 📂 Estrutura

```
apps/bsdi/
├── models.py              # Modelo BSDIExportacao
├── views.py               # Views para listagem e exportação
├── admin.py               # Configuração do Django Admin
├── urls.py                # URLs do módulo
├── services/
│   ├── __init__.py
│   └── exporter.py        # Serviço de geração de XLS
├── templates/
│   └── bsdi/
│       └── exportacao_list.html
└── migrations/
    └── 0001_initial.py
```

## 🚀 Como Usar

### Interface Web

1. Acesse o menu lateral e clique em **"Exportar Lista BSDI"**
2. Clique no botão **"Gerar Nova Lista"**
3. Aguarde o processamento
4. Clique em **"Download"** para baixar o arquivo XLS

### Programaticamente

```python
from apps.bsdi.services import BSDIExporter

# Criar exportador (usa o último batch por padrão)
exporter = BSDIExporter()

# Ou especificar um batch específico
from apps.cecad.models import ImportBatch
batch = ImportBatch.objects.get(pk=1)
exporter = BSDIExporter(import_batch=batch)

# Gerar arquivo
content_file, nome_arquivo, total = exporter.gerar_arquivo()

# content_file: ContentFile pronto para salvar
# nome_arquivo: Nome do arquivo gerado
# total: Total de beneficiários incluídos
```

## 📝 Formato do Arquivo

O arquivo XLS gerado segue o template padrão do BSDI com as seguintes colunas:

1. **ORDEM** - Número sequencial
2. **TELEFONE** - Telefone do RF
3. **DATA DE NASCIMENTO** - Data de nascimento do RF
4. **CPF** - CPF do RF
5. **NOME COMPLETO** - Nome completo do RF
6. **ENDEREÇO DE E-MAIL** - Email do RF
7. **CEP DA RESIDÊNCIA** - CEP da residência
8. **ENDEREÇO** - Logradouro
9. **NÚMERO DA CASA** - Número residencial
10. **COMPLEMENTO** - Complemento do endereço
11. **BAIRRO** - Bairro/Localidade
12. **CIDADE / UF** - Cidade e UF (fixo: Dona Inês/PB)

## 🔄 Regras de Negócio

### Critérios de Inclusão

Uma família é incluída na lista BSDI se:
- Pertence à **última importação CECAD** realizada
- Possui validação com status **"aprovado"**
- Possui um **Responsável Familiar** (RF) cadastrado

### Dados Exportados

- São extraídos os dados do **Responsável Familiar** de cada família
- Se não houver RF, usa o primeiro membro da família
- Endereço é obtido do cadastro da família
- Cidade/UF é fixo: **Dona Inês / PB**

## 🗄️ Modelo de Dados

### BSDIExportacao

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `import_batch` | FK | Lote CECAD de origem |
| `gerado_por` | FK | Usuário que gerou |
| `arquivo` | File | Arquivo XLS gerado |
| `status` | Char | processando/concluido/erro |
| `total_beneficiarios` | Int | Total de beneficiários |
| `descricao` | Char | Descrição da exportação |
| `mensagem_erro` | Text | Mensagem de erro (se houver) |
| `criado_em` | DateTime | Data de criação |
| `atualizado_em` | DateTime | Data de atualização |

## 🔗 URLs

- `/bsdi/exportacoes/` - Lista de exportações
- `/bsdi/exportacoes/gerar/` - Gerar nova exportação (POST)
- `/bsdi/exportacoes/<pk>/download/` - Download de exportação

## 🧪 Testes

Para testar o exportador:

```bash
uv run python apps/bsdi/test_exporter.py
```

## 📦 Dependências

- `xlwt` - Geração de arquivos XLS (formato antigo Excel)

## ⚙️ Configurações

As informações da instituição são definidas em `apps/bsdi/services/exporter.py`:

```python
INSTITUICAO_NOME = "Banco Solidário de Dona Inês"
ENTIDADE_NOME = "Prefeitura Municipal de Dona Inês"
RESPONSAVEL_NOME = "Julhio Arthur de Araújo Rodrigues"
RESPONSAVEL_TELEFONE = "(83) 98192-5590"
RESPONSAVEL_EMAIL = "bancosolidario@pmdonaines.pb.gov.br"
```

Para alterar essas informações, edite as constantes no arquivo ou mova para as configurações do Django.

## 🔐 Permissões

- Requer autenticação (`@login_required`)
- Todas as operações estão disponíveis para usuários autenticados
- Exclusão de exportações disponível apenas no Django Admin

## 📊 Admin

No Django Admin, você pode:
- ✅ Visualizar todas as exportações
- ✅ Ver detalhes de cada exportação
- ✅ Excluir exportações antigas
- ❌ Criar exportações manualmente (bloqueado)

## 🐛 Troubleshooting

### "Nenhum lote de importação encontrado"
- Execute uma importação CECAD primeiro
- Verifique se o status do lote é "completed"

### "Total de beneficiários: 0"
- Verifique se há validações aprovadas
- Execute validações na fila de validação
- Aprove algumas famílias

### Erro ao gerar arquivo
- Verifique os logs de erro
- Confirme que a biblioteca `xlwt` está instalada
- Verifique permissões de escrita no diretório `media/exports/`

## 📝 TODO / Melhorias Futuras

- [ ] Adicionar campo de telefone no cadastro de pessoas
- [ ] Adicionar campo de email no cadastro de pessoas
- [ ] Permitir selecionar batch específico para exportação
- [ ] Adicionar filtros avançados (período, quantidade)
- [ ] Enviar email automático com o arquivo gerado
- [ ] Validação de CPF antes da exportação
- [ ] Exportação em outros formatos (XLSX, CSV)
