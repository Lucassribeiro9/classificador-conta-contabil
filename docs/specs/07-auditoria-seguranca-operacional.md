# Spec: Auditoria e Seguranca Operacional Interna

## Objetivo

Garantir rastreabilidade e seguranca operacional para a primeira entrega interna. Mesmo restrito a rede do escritorio, o sistema deve registrar acoes sensiveis e impedir acesso indevido por usuario ou empresa.

Sucesso significa que importacoes, feedbacks, classificacoes e alteracoes relevantes podem ser atribuidas a usuario, empresa, data e acao.

## Tech Stack

- FastAPI dependencies para contexto de usuario.
- SQLAlchemy para eventos de auditoria.
- PostgreSQL como banco principal.
- Pytest para cenarios de seguranca.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`

## Project Structure

- `core/models.py`: modelo de auditoria.
- `api/dependencies.py`: usuario atual e contexto de seguranca.
- `api/routes/`: endpoints administrativos de consulta de auditoria.
- `api/schemas.py`: schemas de resposta para eventos de auditoria.
- `core/`: servico de auditoria.
- `tests/`: testes de eventos e bloqueios de acesso.

## Code Style

Eventos devem ter nomes consistentes e payload sem segredos.

Exemplo de evento:

```python
{
    "event_type": "ledger_import.completed",
    "usuario_id": 10,
    "empresa_id": 3,
    "resource_type": "import_batch",
    "resource_id": 22,
    "metadata": {"linhas_importadas": 583},
}
```

## Testing Strategy

- Testar evento de importacao iniciada/concluida/falha.
- Testar evento de feedback.
- Testar evento de classificacao.
- Testar eventos de login, acesso negado e usuario inativo bloqueado.
- Testar eventos de gestao de usuarios e permissoes.
- Testar consulta administrativa de auditoria com filtros e paginacao.
- Testar que metadata nao inclui senha, token ou conteudo sensivel desnecessario.
- Testar bloqueios de acesso por empresa.
- Testar usuario inativo sem acesso.

## Boundaries

- Sempre: registrar usuario e empresa quando a acao envolver dados de cliente.
- Sempre: evitar dados sensiveis desnecessarios em logs e auditoria.
- Sempre: manter banco sem exposicao publica.
- Sempre: usar tabela unica de eventos de auditoria na primeira versao.
- Sempre: manter logs tecnicos separados de eventos de auditoria.
- Sempre: registrar eventos de auditoria para login, acesso negado, importacao, classificacao, feedback e gestao de usuarios/permissoes.
- Sempre: restringir consulta de auditoria a usuarios `admin`.
- Sempre: consultar auditoria com paginacao e filtros por usuario, empresa, tipo de evento e periodo.
- Sempre: tornar auditoria de acoes sensiveis de escrita transacional quando possivel.
- Sempre: manter historico de auditoria por tempo indeterminado na primeira versao.
- Perguntar antes: registrar conteudo completo de planilhas ou payloads.
- Perguntar antes: adicionar ferramenta externa de observabilidade.
- Perguntar antes: criar rotina automatica de limpeza/retencao.
- Nunca: gravar senha, token ou API key em log/auditoria.
- Nunca: expor aplicacao contabil permanentemente via ngrok nesta fase.

## Success Criteria

- Acoes sensiveis geram eventos de auditoria.
- Eventos incluem usuario, empresa, tipo de evento e timestamp.
- Eventos podem incluir recurso afetado e metadata segura.
- Logs/auditoria nao armazenam segredos.
- Admin consegue consultar eventos de auditoria com filtros e paginacao.
- Testes cobrem eventos e bloqueios.
- Regras de acesso interno estao alinhadas ao PRD.

## Decisoes Aprovadas

- Auditoria sera uma tabela unica de eventos chamada `audit_events`.
- O modelo ORM base sera `AuditEvent`.
- Eventos terao `timestamp`, `event_type`, `user_id` opcional, `empresa_id` opcional, `resource_id` opcional e `metadata` JSON.
- `user_id` sera opcional porque login falho ou evento de background pode nao estar associado a usuario valido.
- `empresa_id` sera opcional para eventos globais como login ou gestao de usuario.
- A primeira versao registrara eventos de autenticacao, acesso negado, importacao do plano, importacao do razao, classificacao, feedback e gestao de usuarios/permissoes.
- A primeira versao ira expor consulta administrativa de auditoria em endpoint restrito a `admin`.
- A consulta administrativa suportara filtros por `user_id`, `empresa_id`, `event_type`, `data_inicio` e `data_fim`.
- A consulta administrativa sera paginada e retornara eventos mais recentes primeiro.
- O contexto do executor sera propagado por `contextvars`, preenchido durante requests HTTP autenticadas e ausente por padrao em execucoes fora de request.
- O servico de auditoria podera usar o usuario do contexto quando `user_id` nao for informado explicitamente.
- Eventos iniciais de autenticacao: `auth.login.success`, `auth.login.failed`, `auth.user.inactive_blocked`, `auth.access.denied`.
- Eventos iniciais de plano de contas: `plan.imported`, `plan.import_failed`.
- Eventos iniciais de edicao pontual de contas: `account.updated`, `account.deactivated`.
- Eventos iniciais de razao: `ledger.imported`, `ledger.import_failed`, `ledger.import_denied`.
- Eventos iniciais de delecao sensivel: `company.deleted`, `ledger.deleted`.
- Eventos iniciais de classificacao: `classification.started`, `classification.completed`, `classification.failed`.
- Eventos iniciais de modelo ML: `model.trained`, `model.exported`, `model.train_failed`.
- Eventos iniciais de feedback: `feedback.created`, `feedback.updated`.
- Eventos iniciais de usuarios/permissoes: `user.created`, `user.deactivated`, `user_company_permission.changed`.
- `metadata` nao pode conter senha, token, API key, conteudo completo de planilhas ou payload sensivel.
- Auditoria sera retida por tempo indeterminado na primeira versao.
- Acoes sensiveis de escrita devem registrar auditoria de forma transacional quando possivel.
- Logs tecnicos e auditoria sao conceitos separados.
- Nenhuma ferramenta externa de observabilidade sera adicionada nesta fase.
- Aplicacao permanece restrita a rede do escritorio, sem ngrok permanente.
- Banco permanece sem exposicao publica.

## Open Questions

- Eventos de login falho devem armazenar o email/login tentado em metadata mascarada?
- Falha de auditoria em login falho sera best-effort ou deve bloquear a resposta?
