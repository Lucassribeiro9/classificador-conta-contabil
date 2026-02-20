# Plano de Implementação - Estado Real e Próximas Fases

## Resumo

Este documento consolida o plano com base no que já foi efetivamente implementado no projeto.
O foco é:

1. refletir o status real da API e do core de ML;
2. priorizar backlog por risco técnico;
3. definir próximas fases com critérios de aceite objetivos.

O plano deixa de ser aspiracional e passa a ser um guia de execução aderente ao código atual.

---

## Checklist de Acompanhamento

Use esta seção para controle de execução contínua.

### Itens já concluídos

- [x] Estrutura base em `api/`, `core/` e `tests`
- [x] Modelos SQLAlchemy `Empresa` e `Transacao`
- [x] Autenticação por `X-API-Key`
- [x] Endpoints de empresas, transações, classificação e feedback
- [x] Endpoint `/companies/{company_id}/predict` com suporte unitário/lote
- [x] Query param `persist` no fluxo de predição
- [x] Health check em `/health`
- [x] Documentação automática via FastAPI (`/docs` e `/redoc`)
- [x] Suíte de testes de API existente em `tests/test_api.py`
- [x] Plano atualizado para refletir estado real + backlog por risco

### Itens pendentes (priorizados)

#### Fase A - Estabilização técnica

- [ ] Corrigir imports e organização dos testes
- [ ] Atualizar ou remover `test_schema.py`
- [ ] Limpar imports/dependências não usadas em `core/ml_engine.py`
- [ ] Definir e documentar comando padrão de testes no `venv`

#### Fase B - Consistência de domínio e API

- [ ] Definir estratégia oficial para coexistência/convergência entre `/classification` e `/predict`
- [ ] Revisar códigos HTTP e mensagens de erro para consistência de contrato
- [ ] Completar validações de escopo por empresa em feedback/classificação

#### Fase C - Integração e operação

- [ ] Publicar workflow n8n versionado em `n8n_workflows/`
- [ ] Definir padrão mínimo de observabilidade (logs estruturados + métricas)
- [ ] Planejar migração opcional SQLite -> PostgreSQL com critérios objetivos

#### Governança e documentação

- [ ] Sincronizar `README.md` com o estado real da API
- [ ] Validar checklist de DoD por fase com evidências (teste, código, documentação)

---

## 1) Contexto e Objetivo da Migração

O projeto iniciou com uma aplicação Streamlit para classificação contábil e evoluiu para uma arquitetura API-first com FastAPI e SQLAlchemy.

Atualmente, o sistema opera em modo híbrido:

- `app.py` como interface Streamlit legada;
- API FastAPI ativa em `api/main.py` para integração com automações e clientes externos.

Objetivo desta fase do plano: estabilizar e consolidar a camada API como contrato principal sem interromper o legado.

---

## 2) Estado Atual (Implementado)

Itens implementados e disponíveis no código:

1. Estrutura de projeto com separação em `api/`, `core/` e `tests/`.
2. Persistência com SQLAlchemy e modelos `Empresa` e `Transacao`.
3. Autenticação via API key no header `X-API-Key`.
4. Endpoints de empresas, transações, classificação e feedback.
5. Endpoint de predição `/companies/{company_id}/predict` com suporte a:
   - entrada unitária ou em lote;
   - persistência opcional via query param `persist`.
6. Health check e documentação automática do FastAPI (`/docs`, `/redoc`).
7. Testes de API existentes em `tests/test_api.py`.

---

## 3) APIs/Interfaces Públicas (Estado Vigente)

Contratos atuais expostos pela API:

1. `POST /api/v1/companies`
2. `GET /api/v1/companies`
3. `GET /api/v1/companies/{company_id}`
4. `PATCH /api/v1/companies/{company_id}/deactivate`
5. `PATCH /api/v1/companies/{company_id}/activate`
6. `DELETE /api/v1/companies/{company_id}`
7. `POST /api/v1/companies/{company_id}/transactions`
8. `GET /api/v1/companies/{company_id}/transactions`
9. `GET /api/v1/companies/{company_id}/transactions/needs_review`
10. `POST /api/v1/companies/{company_id}/classification`
11. `POST /api/v1/companies/{company_id}/predict?persist={bool}`
12. `PATCH /api/v1/transactions/{transaction_id}/feedback`
13. `GET /health`
14. `GET /`

Observação: endpoints transacionais e de classificação dependem de API key válida.

---

## 4) Modelos e Schemas (Estado Vigente)

### Banco de dados

Estruturas atuais em uso:

- Tabela `empresas`
  - `id`
  - `nome_empresa`
  - `api_key`
  - `cnpj_cpf`
  - `cod_dominio`
  - `is_active`
  - `created_at`

- Tabela `transacoes`
  - `id`
  - `empresa_id`
  - `data`
  - `cod_banco`
  - `historico`
  - `valor`
  - `conta_contabil`
  - `confidence`
  - `needs_review`
  - `is_classified`
  - `created_at`
  - `updated_at`

### Schemas da API

Além dos schemas de empresa e transação, os schemas de predição já implementados são:

1. `PredictInput`
2. `PredictResult`
3. `PredictResponse`

---

## 5) Riscos Críticos e Inconsistências (Prioridade Alta)

1. `tests/test_api.py` importa `ClassificadorContabil` de `api.routes.classification`, criando acoplamento indevido com a camada de rota.
   - referência técnica recomendada: importar de `core.ml_engine`.

2. `test_schema.py` está desatualizado e valida campos que não correspondem aos schemas atuais (`descricao`, `nome`, `cnpj`).

3. `core/ml_engine.py` possui imports pesados não usados no runtime da API (ex.: `matplotlib`, `plotly`, `IPython`, `joblib`), elevando custo de inicialização e risco operacional.

4. Coexistência de dois fluxos funcionais (`/classification` e `/predict`) sem decisão oficial de papel canônico de cada um.

5. Execução de testes com comportamento instável no ambiente local, sem comando padrão formalizado no plano.

---

## 6) Backlog Priorizado (Próximas Fases)

### Fase A - Estabilização técnica

1. Corrigir imports e organização dos testes.
2. Atualizar ou remover `test_schema.py`.
3. Limpar dependências/imports desnecessários de `core/ml_engine.py`.
4. Padronizar estratégia de execução de testes no `venv` (documentar comando oficial).

### Fase B - Consistência de domínio e API

1. Definir endpoint canônico para predição/classificação (manter ambos com papéis claros ou convergir).
2. Revisar códigos HTTP e mensagens de erro para consistência de contrato.
3. Completar validações de escopo por empresa em feedback/classificação.

### Fase C - Integração e operação

1. Publicar workflow n8n versionado em `n8n_workflows/`.
2. Definir observabilidade mínima (logs estruturados e métricas básicas).
3. Planejar migração opcional SQLite -> PostgreSQL com gatilhos de decisão.

---

## 7) Critérios de Aceite (DoD) por Fase

Checklist objetivo de conclusão:

1. Testes da API executando de forma reprodutível.
2. Contratos de endpoint documentados e aderentes ao código.
3. Riscos críticos endereçados com evidência em código/testes.
4. Fluxo n8n de referência disponível e versionado.
5. `README.md` e este plano sincronizados com o estado real do projeto.

---

## 8) Cronograma Curto Sugerido

1. Semana 1: Fase A (estabilização técnica).
2. Semana 2: Fase B (consistência de domínio e API).
3. Semana 3: Fase C (integração e operação).

---

## Casos de Teste e Cenários a Registrar no Plano

1. Criar empresa, desativar e reativar.
2. Criar transações em lote com e sem API key.
3. Predição unitária e em lote.
4. Predição com `persist=false` e `persist=true`.
5. Classificação de pendentes com base em histórico.
6. Feedback em transação inexistente e em transação válida.
7. Empresa desativada tentando predizer/classificar.

---

## Assunções e Padrões Adotados

1. Documento mantido em português técnico.
2. Plano orientado por status real + próximas fases, sem redesign total.
3. Inconsistências atuais tratadas como riscos críticos com ação explícita.
4. Referência de "implementado" baseada no estado atual do código local sem mudanças pendentes.

---

## Referências Técnicas

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
