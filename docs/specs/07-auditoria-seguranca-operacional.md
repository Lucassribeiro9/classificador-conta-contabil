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
- Testes cobrem eventos e bloqueios.
- Regras de acesso interno estao alinhadas ao PRD.

## Decisoes Aprovadas

- Auditoria sera uma tabela unica de eventos chamada `audit_events`.
- O modelo ORM base sera `AuditEvent`.
- Eventos terao `timestamp`, `event_type`, `user_id` opcional, `empresa_id` opcional, `resource_id` opcional e `metadata` JSON.
- `user_id` sera opcional porque login falho ou evento de background pode nao estar associado a usuario valido.
- `empresa_id` sera opcional para eventos globais como login ou gestao de usuario.
- A primeira versao registrara eventos de autenticacao, acesso negado, importacao do plano, importacao do razao, classificacao, feedback e gestao de usuarios/permissoes.
- Eventos iniciais de autenticacao: `auth.login.success`, `auth.login.failed`, `auth.user.inactive_blocked`, `auth.access.denied`.
- Eventos iniciais de plano de contas: `chart_import.started`, `chart_import.completed`, `chart_import.failed`.
- Eventos iniciais de razao: `ledger_import.started`, `ledger_import.completed`, `ledger_import.completed_with_warnings`, `ledger_import.failed`.
- Eventos iniciais de classificacao: `classification.started`, `classification.completed`, `classification.failed`.
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
