# Resumo do dicionário de campos

Este documento sumariza a análise do arquivo `dicionariotudo.csv` e propõe mapeamentos, tipos e recomendações para modelagem, importação e tratamento de PII.

## Visão geral
- Origem: `docs/dicionariotudo.csv` (separador `;`, colunas `campo`;`descricao`;`resposta`).
- Convenções observadas:
  - Prefixo `d.` → dados da família / domicílio.
  - Prefixo `p.` → dados da pessoa / membro.
  - Campos globais: `uf`, `cd_ibge`.
  - Muitos campos possuem um campo `resposta` com valores enumerados no formato `valor - descrição` separados por `#`.

## Tipos sugeridos (de alto nível)
- IDs / códigos: `CharField` (se preservarem zeros à esquerda) ou `BigIntegerField` quando for claramente numérico.
- Datas: `DateField` (normalizar formatos de entrada; ex.: alguns campos usam `DDMMAAAA`).
- Valores monetários e despesas: `DecimalField(max_digits=12, decimal_places=2)`.
- Flags booleanas (`0/1`): `BooleanField` sempre que as opções forem apenas Sim/Não; caso haja valores adicionais (ex.: "Não declarou"), usar `SmallIntegerField` com `choices`.
- Telefones, CPF, NIS, títulos: `CharField` com validação e índices quando necessário (não usar `IntegerField`).
- Textos longos (referências de endereço, observações): `TextField`.
- Campos enumerados estáveis: `IntegerField` com `choices` ou tabelas de lookup quando precisar de historicidade/auditabilidade.

## PII (dados sensíveis)
- Nomes: `p.nom_pessoa`, `p.nom_completo_mae_pessoa`, `p.nom_completo_pai_pessoa`.
- Identificadores nacionais: `p.num_cpf_pessoa`, `p.num_nis_pessoa_atual`, `p.num_identidade_pessoa`.
- Contatos e endereço completo: `d.num_tel_contato_*`, `d.num_cep_logradouro_fam`, `d.nom_logradouro_fam`, `d.num_logradouro_fam`, `d.txt_referencia_local_fam`.

Recomendações: criptografia em repouso para colunas sensíveis, mascaramento em exportações, logging/auditoria de acessos e controle de acesso por função.

## Normalização e integridade
- Famílias e pessoas: modelar `Family` (unidade familiar) e `Person` com FK de `Person.family` → `Family`.
- Indexar campos de busca: `cod_familiar`, `cd_ibge`, `cpf`, `nis`.
- Regras de duplicidade: detectar por CPF/NIS e por combinação `nome + data_nasc + endereco`.

## Validação/Importação
- Normalizar e validar CPF (remoção de máscara e verificação de dígitos).
- Datas: suportar `DDMMAAAA` e ISO (`YYYY-MM-DD`) e detectar automaticamente quando possível.
- Valores monetários: aceitar `,` e `.` como separadores e converter para Decimal.
- Registrar origem e metadados da importação (arquivo, linha, hash, timestamp, operador).

## Choices (enums) — amostra extraída
O arquivo `docs/choices.json` contém um mapeamento completo dos campos enumerados extraídos do CSV. Abaixo algumas amostras:

- `d.cod_agua_canalizada_fam`: { `1`: "Sim", `2`: "Nao" }
- `d.marc_pbf`: { `0`: "Nao", `1`: "Sim" }
- `p.cod_sexo_pessoa`: { `1`: "Masculino", `2`: "Feminino" }
- `p.cod_raca_cor_pessoa`: { `1`: "Branca", `2`: "Preta", `3": "Amarela", `4": "Parda", `5": "Indigena" }

(Ver `docs/choices.json` para o mapeamento completo extraído automaticamente.)

## Modelo (esboço)
- `Family`: campos principais: `code`, `cd_ibge`, `created_at`, `updated_at`, `cep`, `renda_per_capita`, `recebe_pbf`, etc.
- `Person`: `family` FK, `name`, `nis`, `cpf`, `birth_date`, `sexo`, `grau_instrucao`, `deficiencias`, etc.

Posso gerar um `models.py` esboço com todos os campos mapeados automaticamente (usar `choices` inline ou criar tabelas lookup?).

## Próximos passos sugeridos
1. Confirmar se prefere `choices` inline (Django choices) ou tabelas lookup (melhor para mudanças futuras). 
2. Gerar `models.py` esboço a partir do CSV (posso criar commit/migração inicial).
3. Criar `management/commands/import_cecad.py` com validações básicas e logs.
4. Implementar criptografia para colunas sensíveis e testes unitários para o importador.

---

Se quiser que eu gere agora o `models.py` completo ou a primeira versão do importador, diga qual prefere primeiro.