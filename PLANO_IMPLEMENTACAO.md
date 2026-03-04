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
- [x] Isolamento multi-tenant por `company_id` + `X-API-Key` em `transactions`, `classification` e `predict`
- [x] Endpoints de empresas, transações, classificação e feedback
- [x] Endpoint `/companies/{company_id}/predict` com suporte unitário/lote
- [x] Query param `persist` no fluxo de predição
- [x] Health check em `/health`
- [x] Documentação automática via FastAPI (`/docs` e `/redoc`)
- [x] Suíte de testes de API existente em `tests/test_api.py`
- [x] Testes cross-company para `transactions`, `classification` e `predict`
- [x] Plano atualizado para refletir estado real + backlog por risco
- [x] Completar validações de escopo por empresa (`transactions`, `classification`, `predict` e `feedback`) — concluído na issue #18
- [x] Limpar imports/dependências não usadas em `core/ml_engine.py` — resolvido; imports pesados (`matplotlib`, `plotly`, `IPython`, `joblib`) já removidos
- [x] Corrigir imports e organização dos testes — `test_api.py` não importa mais `ClassificadorContabil` da camada de rota
- [x] Atualizar ou remover `test_schema.py` — arquivo já valida os schemas atuais (`EmpresaCreate`, `TransacaoCreate`) corretamente

### Itens pendentes (priorizados)

#### Fase A - Estabilização técnica

- [ ] Documentar comando padrão de testes para Windows (`Makefile` usa `./venv/bin/python`, incompatível com Windows)
- [ ] Migrar `declarative_base` de `sqlalchemy.ext.declarative` (depreciado) para `sqlalchemy.orm.DeclarativeBase`
- [ ] Substituir `print()` por `logging` estruturado em `classification.py`, `feedback.py` e `ml_engine.py`

#### Fase B - Consistência de domínio e API

- [ ] Documentar decisão canônica `/classification` vs `/predict` para integradores (decisão já tomada, falta documentar)
- [ ] Revisar códigos HTTP e mensagens de erro para consistência de contrato (ex.: 500 para "dados insuficientes" deveria ser 422/400; mensagens misturando pt/en)
- [ ] Validar empresa ativa no endpoint `/feedback` (aceita feedback mesmo com empresa desativada)
- [ ] Adicionar `response_model` ao endpoint `/classification` (único endpoint sem schema de resposta)
- [ ] Avaliar proteção dos endpoints de empresa (`POST`, `GET`, `DELETE`) com autenticação admin

#### Fase C - Integração e operação

- [ ] Publicar workflow n8n versionado em `n8n_workflows/`
- [ ] Definir padrão mínimo de observabilidade (logs estruturados + métricas)
- [ ] Planejar migração opcional SQLite -> PostgreSQL com critérios objetivos
- [ ] Definir gatilho canônico n8n para classificação com critérios de confiança
- [ ] Criar `.env.example` com variáveis de ambiente necessárias (`DATABASE_URL`, `NGROK_AUTH_TOKEN`, `WEBHOOK_URL`)

#### Fase D - Documentação e governança

- [ ] Sincronizar `README.md` com o estado real da API (ainda descreve apenas Streamlit)
- [ ] Adicionar docstrings nos endpoints de `companies.py` e `transactions.py` para Swagger
- [ ] Validar checklist de DoD por fase com evidências (teste, código, documentação)
- [ ] Sincronizar este plano com riscos resolvidos e novas pendências

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

1. ~~`tests/test_api.py` importa `ClassificadorContabil` de `api.routes.classification`, criando acoplamento indevido com a camada de rota.~~
   - ✅ **Resolvido** — `test_api.py` usa monkeypatch para mock do classificador; importação direta de `core.ml_engine` nos testes unitários (`test_ml_engine.py`) está correta.

2. ~~`test_schema.py` está desatualizado e valida campos que não correspondem aos schemas atuais (`descricao`, `nome`, `cnpj`).~~
   - ✅ **Resolvido** — `test_schema.py` valida `EmpresaCreate` e `TransacaoCreate` com os campos atuais corretamente.

3. ~~`core/ml_engine.py` possui imports pesados não usados no runtime da API (ex.: `matplotlib`, `plotly`, `IPython`, `joblib`), elevando custo de inicialização e risco operacional.~~
   - ✅ **Resolvido** — imports pesados removidos; arquivo contém apenas dependências essenciais (`nltk`, `pandas`, `sklearn`, `sqlalchemy`).

4. Coexistência de dois fluxos funcionais (`/classification` e `/predict`) sem decisão oficial de papel canônico de cada um.
   - decisão oficial (21/02/2026): manter ambos.
   - papel de `/classification`: classificar transações pendentes já persistidas (`conta_contabil` nula), em fluxo interno/batch.
   - papel de `/predict`: inferência sob demanda (unitária/lote) para entrada de payload; com `persist=true` pode registrar a predição como nova transação classificada.
   - observação de governança: `predict` não substitui `feedback`; `feedback` continua sendo a correção humana da conta contábil atribuída.
   - risco técnico associado: ambos os fluxos atualmente treinam o modelo por requisição; otimização de reuso/cache de modelo fica no backlog de performance.
   - **pendência**: documentar essa decisão no `README.md` e nos docstrings dos endpoints para integradores.

5. ~~Execução de testes com comportamento instável no ambiente local, sem comando padrão formalizado no plano.~~
   - ⚠️ **Parcialmente resolvido** — `Makefile` tem target `test`, mas usa path Linux. Pendência: documentar comando para Windows.

6. **(NOVO)** Endpoint `/feedback` não valida se a empresa está ativa antes de aceitar correção.

7. **(NOVO)** Endpoints de empresa (`POST /companies`, `GET /companies`, `DELETE /companies/{id}`) não exigem autenticação.

8. **(NOVO)** `core/database.py` usa `declarative_base()` de `sqlalchemy.ext.declarative` (depreciado no SQLAlchemy 2.x).

9. **(NOVO)** Uso de `print()` em produção onde deveria haver `logging` estruturado (`classification.py`, `feedback.py`, `ml_engine.py`).

---

## 6) Backlog Priorizado (Próximas Fases)

### Fase A - Estabilização técnica

1. ~~Corrigir imports e organização dos testes.~~ ✅ Resolvido.
2. ~~Atualizar ou remover `test_schema.py`.~~ ✅ Resolvido — schemas validados corretamente.
3. ~~Limpar dependências/imports desnecessários de `core/ml_engine.py`.~~ ✅ Resolvido.
4. Documentar comando de testes para Windows (complementar `Makefile` com instrução cross-platform).
5. **(NOVO)** Migrar `declarative_base` para `sqlalchemy.orm.DeclarativeBase` (API depreciada).
6. **(NOVO)** Substituir `print()` por `logging` estruturado nos módulos de produção.

### Fase B - Consistência de domínio e API

1. Documentar decisão canônica `/classification` vs `/predict` para integradores no `README.md` e docstrings.
2. Revisar códigos HTTP e mensagens de erro para consistência de contrato.
3. ~~Validar e manter cobertura de regressão para escopo por empresa.~~ ✅ Resolvido na issue #18.
4. **(NOVO)** Validar empresa ativa no endpoint `/feedback`.
5. **(NOVO)** Adicionar `response_model` ao endpoint `/classification`.
6. **(NOVO)** Avaliar proteção dos endpoints de empresa com autenticação admin.

### Fase C - Integração e operação

1. Publicar workflow n8n versionado em `n8n_workflows/`.
2. Definir observabilidade mínima (logs estruturados e métricas básicas).
3. Planejar migração opcional SQLite -> PostgreSQL com gatilhos de decisão.
4. Definir gatilho canônico dos workflows n8n para classificação contábil:
   usar `/classification` (pendências já persistidas) ou `/predict` (entrada sob demanda com `persist` opcional), com critérios explícitos de volume, confiança e necessidade de revisão humana.
5. **(NOVO)** Criar `.env.example` com variáveis de ambiente necessárias.

### Fase D - Documentação e governança

1. Sincronizar `README.md` com o estado real da API (atualmente descreve apenas Streamlit).
2. **(NOVO)** Adicionar docstrings nos endpoints de `companies.py` e `transactions.py` para Swagger.
3. Validar checklist de DoD por fase com evidências (teste, código, documentação).
4. **(NOVO)** Manter sincronização contínua deste plano com o código.

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
8. Cenário de workflow n8n: decisão de gatilho entre `/classification` e `/predict` com regras de persistência (`persist=true/false`) por confiança.

---

## Matriz de Decisão n8n (Gatilho e Persistência)

| Cenário Operacional                                              | Endpoint Gatilho  | `persist`                            | Ação Pós-Predição                                                 |
| ---------------------------------------------------------------- | ----------------- | ------------------------------------ | ----------------------------------------------------------------- |
| Existe backlog de transações já salvas e não classificadas       | `/classification` | N/A                                  | Classificar pendências em lote e monitorar volume residual        |
| Entrada nova sob demanda (unitária/lote) com baixa criticidade   | `/predict`        | `true` quando `confidence >= limiar` | Persistir automaticamente e seguir fluxo normal                   |
| Entrada nova sob demanda com criticidade alta ou confiança baixa | `/predict`        | `false`                              | Encaminhar para revisão humana e aplicar `/feedback` após decisão |
| Operação em homologação/simulação                                | `/predict`        | `false`                              | Não gravar no banco; validar qualidade do modelo e regras         |

Critérios mínimos recomendados para primeira versão:

1. Definir um limiar inicial de auto-persistência (ex.: `confidence >= 0.85`).
2. Abaixo do limiar, encaminhar para revisão manual e posterior `feedback`.
3. Reavaliar limiar com métricas reais de acurácia e taxa de retrabalho.

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
