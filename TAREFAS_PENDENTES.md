# Tarefas Pendentes — Classificador de Contas Contábeis

Relatório de análise gerado em 04/03/2026.
Para contexto completo das decisões, ver `PLANO_IMPLEMENTACAO.md`.

---

## Fase A — Estabilização Técnica (Prioridade Alta)

1. **Documentar comando padrão de testes no Windows**
   - O `Makefile` usa `./venv/bin/python` (Linux). Incluir `.\venv\Scripts\python` para Windows.
   - Documentar no `README.md` ou criar script cross-platform.
   - Arquivos: `Makefile`, `README.md`

2. **Migrar `declarative_base` para API atual do SQLAlchemy**
   - `core/database.py` importa de `sqlalchemy.ext.declarative` (depreciado).
   - Migrar para `sqlalchemy.orm.DeclarativeBase`.
   - Arquivos: `core/database.py`

3. **Substituir `print()` por logging estruturado**
   - Rotas de classificação e feedback usam `print()` para debug.
   - Trocar por `logging.getLogger()` com formato estruturado para produção.
   - Arquivos: `api/routes/classification.py`, `api/routes/feedback.py`, `core/ml_engine.py`

---

## Fase B — Consistência de Domínio e API (Prioridade Média)

1. **Documentar decisão canônica `/classification` vs `/predict`**
   - Decisão já tomada (ambos coexistem com papéis distintos), falta documentar para integradores.
   - Arquivos: `README.md`, `api/routes/classification.py`

2. **Padronizar códigos HTTP e mensagens de erro**
   - `/classification` retorna 500 para "dados insuficientes" (deveria ser 422 ou 400).
   - Mensagens misturam português e inglês ("API Key is required" vs "Empresa não encontrada").
   - Arquivos: `api/routes/classification.py`, `api/dependencies.py`

3. **Validar empresa ativa no endpoint `/feedback`**
   - O feedback valida `empresa_id` da transação, mas não impede feedback em empresa desativada.
   - Arquivos: `api/routes/feedback.py`

4. **Adicionar `response_model` ao endpoint `/classification`**
   - Endpoint sem `response_model` definido, diferente dos demais.
   - Criar schema de resposta.
   - Arquivos: `api/routes/classification.py`, `api/schemas.py`

5. **Proteger endpoints de empresa com autenticação**
   - `GET /companies`, `POST /companies`, `DELETE /companies/{id}` não exigem API key.
   - Avaliar se devem exigir autenticação admin/root.
   - Arquivos: `api/routes/companies.py`

---

## Fase C — Integração e Operação (Prioridade Média)

1. **Publicar workflow n8n versionado**
   - `docker-compose.yml` já sobe n8n, mas não existe workflow exportado.
   - Criar diretório `n8n_workflows/` com workflow de referência.

2. **Configurar observabilidade mínima**
   - Sem logs estruturados nem métricas. Implementar logging JSON.
   - Enriquecer `/health` com diagnósticos de dependências.
   - Arquivos: `api/main.py`

3. **Planejar migração SQLite → PostgreSQL**
   - Definir critérios de migração (volume, concorrência).
   - Atualizar `core/config.py` e `docker-compose.yml`.

4. **Definir gatilho canônico n8n para classificação**
   - Decidir no workflow n8n se usa `/classification` (batch) ou `/predict` (sob demanda).
   - Aplicar critérios de confiança para persistência automática.

5. **Criar `.env.example` com variáveis de ambiente**
   - Listar: `DATABASE_URL`, `NGROK_AUTH_TOKEN`, `WEBHOOK_URL`.

---

## Fase D — Documentação e Governança (Prioridade Baixa)

1. **Atualizar `README.md` para refletir a API**
   - README ainda descreve apenas o Streamlit (`app.py`).
   - Incluir seção de API FastAPI, Docker, endpoints e testes.

2. **Criar `.env.example`**
   - Listar variáveis necessárias para execução local e Docker.

3. **Sincronizar `PLANO_IMPLEMENTACAO.md`**
   - Riscos sobre imports pesados no `ml_engine.py` e `test_schema.py` desatualizado já foram resolvidos.
   - Atualizar checklist e seção de riscos.

4. **Adicionar docstrings aos endpoints**
   - Endpoints de `companies.py` e `transactions.py` com comentários simples.
   - Faltam docstrings que apareçam no Swagger (`/docs`).

---

## Resumo

| Fase              | Tarefas | Prioridade |
| ----------------- | ------- | ---------- |
| A — Estabilização | 3       | Alta       |
| B — Consistência  | 5       | Média      |
| C — Integração    | 5       | Média      |
| D — Documentação  | 4       | Baixa      |
| **Total**         | **17**  | —          |
