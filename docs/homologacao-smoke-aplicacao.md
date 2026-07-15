# Smoke da Aplicacao em Homologacao

Execute este gate antes de liberar a rodada descrita em
`docs/frontend-homologacao-mvp-ux.md`. Use somente o ambiente HML
interno e a massa sanitizada. O checklist tecnico continua em
`docs/homologacao-checklist-tecnico.md`.

## Pre-condicoes

- stack `classificador-hml` saudavel e separada de producao;
- seed sanitizado concluido;
- estacao com acesso a rede interna e confianca na CA interna;
- branch ou commit candidato identificado.

## 1. Backend

Na raiz do repositorio, execute os mesmos recortes do CI:

```bash
python -m pytest -q tests \
  --ignore=tests/test_frontend_login_contract.py \
  --ignore=tests/test_frontend_shell_routes.py \
  --deselect=tests/test_razao_import_api.py::test_duplicate_razao_file_hash_creates_failed_audit_event

python -m pytest -q \
  tests/test_razao_import_api.py::test_duplicate_razao_file_hash_creates_failed_audit_event
```

Falhas conhecidas devem permanecer justificadas no CI. Qualquer nova falha e
bloqueante.

## 2. Frontend

Em `frontend/`, execute:

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run test:e2e
```

O Playwright usa o modo demo local para validar o fluxo do MVP. Ele nao substitui
o probe live do ambiente HML.

## 3. Smoke Live de HML

Na raiz do repositorio, execute:

```bash
python -m scripts.smoke_homologacao --base-url https://classificador-hml.interno
```

O comando valida a API `/health`, incluindo o banco, e o shell HTML da tela
`/login`. O processo retorna codigo diferente de zero se qualquer probe falhar.
HTTP e aceito somente em loopback para os testes automatizados do proprio CLI.

Saida esperada:

```text
Executado em UTC: <timestamp>
Git: <branch>@<commit>
Base HML: https://classificador-hml.interno
API /health: APROVADO
Tela /login: APROVADO
```

## Evidencia e Decisao

Anexe a saida resumida dos comandos ao PR ou ao registro controlado da rodada.
Informe data, branch/commit, responsavel e eventuais falhas conhecidas. Nao
registre senhas, tokens ou segredos, nem corpos de resposta com dados reais.

- Resultado: Liberado / Bloqueado
- Responsavel:
- Evidencia dos testes backend:
- Evidencia dos testes frontend:
- Evidencia do smoke HML:
- Falhas bloqueantes:
- Melhorias futuras:

API ou banco offline, login inacessivel, falha nova de teste/build ou mistura
com producao bloqueia a rodada. Melhoria cosmetica sem impacto operacional deve
ser registrada separadamente e nao bloqueia a liberacao.
