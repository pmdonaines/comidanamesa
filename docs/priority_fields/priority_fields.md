# Campos prioritários

Esta pasta contém documentação e mapeamento dos campos que terão prioridade no importador e nas interfaces operacionais.

Campos priorizados (ordem sugerida de ingestão e validação):

- `d.cod_familiar_fam` — Código familiar
- `d.dat_atual_fam` — Data da última atualização da família
- `d.nom_localidade_fam` — Nome da localidade
- `d.nom_tip_logradouro_fam` — Tipo de logradouro
- `d.nom_logradouro_fam` — Nome do logradouro
- `d.num_logradouro_fam` — Número do logradouro
- `p.nom_pessoa` — Nome da pessoa
- `p.num_nis_pessoa_atual` — NIS
- `p.nom_apelido_pessoa` — Apelido / Nome social
- `p.cod_sexo_pessoa` — Sexo (choices)
- `p.dta_nasc_pessoa` — Data de nascimento
- `p.num_cpf_pessoa` — CPF da pessoa
- `p.ref_cad` — Referência Cadastro Único
- `p.ref_pbf` — Referência Programa Bolsa Família

## Objetivos para estes campos
- Garantir identidade mínima da pessoa: `p.num_cpf_pessoa` (quando presente), `p.num_nis_pessoa_atual`, `p.nom_pessoa`, `p.dta_nasc_pessoa`.
- Garantir vínculo família↔pessoa: `d.cod_familiar_fam` e `p.ref_cad`/`p.ref_pbf` para mapear programa/registro.
- Endereço mínimo para triagem local: `d.nom_localidade_fam`, `d.nom_tip_logradouro_fam`, `d.nom_logradouro_fam`, `d.num_logradouro_fam`.
- Metadados de recência: `d.dat_atual_fam` — importante para elegibilidade por atualização cadastral.

## Validações e tratamentos recomendados
- `p.num_cpf_pessoa`:
  - Normalizar (remover pontuação) e validar dígitos; armazenar criptografado em campo `CharField`/camada de criptografia.
  - Em listagens, exibir com mascaramento (ex.: `***.***.***-12`) salvo para usuários com permissão.

- `p.num_nis_pessoa_atual`:
  - Normalizar e indexar; usar para deduplicação quando CPF ausente.

- `p.dta_nasc_pessoa` / `d.dat_atual_fam`:
  - Aceitar formatos comuns: ISO (`YYYY-MM-DD`) e `DDMMAAAA`; registrar erro/linha quando data inválida.

- Campos de endereço (`nom_localidade`, `nom_logradouro`, `num_logradouro`):
  - Normalizar espaços, remover caracteres inválidos, consolidar abreviações (R., Av., etc.) para facilitar matching.

- `p.cod_sexo_pessoa`:
  - Mapear para `choices` com valores documentados (`1` → Masculino, `2` → Feminino). Tratar valores desconhecidos como `null`.

- `d.cod_familiar_fam`:
  - Usar como chave externa para associar `Person` → `Family`. Indexar.

## Observações sobre PII e privacidade
- Campos sensíveis: `p.num_cpf_pessoa`, `p.nom_pessoa`, `p.num_nis_pessoa_atual`.
- Política sugerida: criptografia em repouso para CPF e NIS; mascaramento em UIs e exports; logs de acesso para qualquer visualização completa.

## Próximo passo operacional
- Gerar `priority_fields.json` com o mapeamento detalhado (campo → descrição → tipo sugerido → PII → exemplo). Esse arquivo já foi gerado automaticamente ao lado (veja `priority_fields.json`).

---

Se quiser, agora eu:
- gero um `models.py` parcial contendo somente esses campos (Family + Person minimal), ou
- crio um `management/command` inicial para importar apenas esses campos e testar validações.
Diga qual prefere.