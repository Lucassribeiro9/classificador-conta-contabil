# Spec: Visao e Fluxo SDD da Evolucao Contabil

## Objetivo

Definir como o PRD sera quebrado em specs, planos, tarefas, testes e pull requests. Esta spec orienta o trabalho e impede que a evolucao vire uma serie de mudancas soltas.

O objetivo da primeira entrega e criar uma fundacao API-first para PostgreSQL, usuarios internos, permissoes por empresa, importacao de plano de contas, importacao do razao, dataset de treino e classificacao de contrapartida.

## Tech Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL em Docker para o alvo da evolucao
- SQLite apenas como legado/teste onde fizer sentido
- Pandas, openpyxl e scikit-learn para importacao e ML
- Pytest para testes automatizados

## Comandos

- Testes Windows: `.\venv\Scripts\python.exe -m pytest -q tests`
- Testes Linux: `./venv/bin/python -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`
- Migrar banco: `.\venv\Scripts\python.exe -m alembic upgrade head`
- Docker: `docker compose up -d --build`

## Project Structure

- `api/`: aplicacao FastAPI, rotas, dependencias e schemas.
- `core/`: modelos, banco, configuracao, ML e servicos de dominio.
- `alembic/`: migrations de banco.
- `tests/`: testes automatizados.
- `docs/prd/`: PRDs aprovados.
- `docs/specs/`: specs derivadas de PRDs.
- `.github/`: templates de issues, PR e branching.

## Code Style

As mudancas devem seguir o estilo atual de FastAPI, SQLAlchemy e Pydantic. Rotas devem delegar regra de negocio para servicos quando o comportamento crescer.

Exemplo de formato esperado para uma dependencia de permissao:

```python
def require_company_access(
    company_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = DB_DEPENDENCY,
) -> Empresa:
    ...
```

## Testing Strategy

As specs devem gerar issues testaveis. Cada issue funcional deve comecar por teste falhando no maior seam possivel:

- API para autenticacao, autorizacao, importacao e feedback.
- Parser para planilhas e normalizacao.
- Persistencia para idempotencia, lotes e vinculos.
- Dataset para filtros de banco/caixa e alvo de contrapartida.
- ML para formato de predicao, confianca e revisao.

## Boundaries

- Sempre: escrever ou atualizar spec antes de mudancas grandes.
- Sempre: criar testes antes ou junto de implementacoes de comportamento.
- Sempre: manter escopo de PR pequeno e ligado a issue.
- Perguntar antes: mudar mecanismo de autenticacao, adicionar dependencia grande, mudar schema principal ou remover compatibilidade relevante.
- Nunca: expor credenciais, dados sensiveis ou banco publicamente.
- Nunca: deixar Streamlit acessar diretamente o banco na arquitetura-alvo.

## Success Criteria

- PRD principal esta salvo em `docs/prd/`.
- Specs derivadas estao salvas em `docs/specs/`.
- Cada spec tem criterios de sucesso e estrategia de teste.
- Specs conseguem ser convertidas em issues pequenas.
- Nenhuma implementacao foi iniciada antes da aprovacao das specs.

## Decisoes Aprovadas

- A primeira spec a virar plano/issues sera `01-postgresql-migracao`.
- A segunda spec a virar plano/issues sera `02-auth-usuarios-permissoes`.
- A migracao para PostgreSQL deve preservar pelo menos as empresas ja cadastradas no banco atual.
- A migracao das transacoes/classificacoes existentes sera decidida durante a revisao da spec de PostgreSQL.
- A autenticacao inicial para usuarios internos sera JWT bearer na API.
- API keys ficam reservadas para integracoes futuras, como n8n.

## Open Questions

- A migracao das transacoes/classificacoes existentes sera obrigatoria ou opcional?
- O fluxo JWT tera refresh token ou apenas access token com expiracao curta?
- O guia de fluxo PRD -> spec -> issue -> TDD -> PR ficara nesta spec ou em documento proprio?
