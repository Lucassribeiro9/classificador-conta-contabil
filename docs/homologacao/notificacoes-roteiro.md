# Roteiro de Homologação Manual — Notificações da Esteira (#379)

Issue: <https://github.com/Lucassribeiro9/classificador-conta-contabil/issues/379>
Branch: `feat/agent-notificacoes`

## Escopo entregue

- `core/agent/notificacoes/eventos.py` — allowlist de estados que geram alerta.
- `core/agent/notificacoes/payload.py` — sanitização (função pura, allowlist de campos).
- `core/agent/notificacoes/roteamento.py` — roteamento + disparo com falha isolada.
- `api/routes/notificacoes.py` — micro-serviço HTTP (`POST /api/v1/agent/notificacoes/rotear`).
- `tests/agent/notificacoes/*` — fixtures e testes unitários (TDD).

## Ambiente

- Python 3.11 + venv (uv).
- Sem credenciais: o disparo real em Teams/e-mail pertence ao n8n.

## Perfil do executor

- Mantenedor (Lucassribeiro9), com acesso ao n8n e aos canais.

## Serviços necessários

- n8n com o workflow da esteira (#378/PR #392) atualizado para chamar o
  micro-serviço `POST /api/v1/agent/notificacoes/rotear` antes do disparo.

## Preparação

1. Subir a API localmente (ou no host privado do runner): `uv run fastapi dev api/main.py`.
2. Confirmar a rota: `curl -X POST localhost:8000/api/v1/agent/notificacoes/rotear -d '{"state":"agent:awaiting-task-review","repository":"Lucassribeiro9/classificador-conta-contabil","issue_number":379,"title":"feat(agent): notificar gates","resumo":"Task Review pronta","acao_esperada":"Publicar /agent approve-task-review","link":"https://github.com/x/issues/379"}' -H "Content-Type: application/json"`.
3. Esperado: payload JSON com `resumo_sanitizado` e os campos allowlisted.

## Passos e resultado esperado

| Passo | Ação | Resultado esperado |
| --- | --- | --- |
| 1 | Enviar evento notificável (ex.: `agent:awaiting-task-review`) | Payload presente; n8n dispara Teams+e-mail |
| 2 | Enviar evento silencioso (ex.: `agent:running`) | Resposta `null`; n8n não dispara |
| 3 | Enviar evento com campo proibido (`secret`, `prompt`, `diff`...) | Campo ausente no payload retornado |
| 4 | Desligar o canal Teams no n8n | E-mail ainda recebe; estado do GitHub inalterado |
| 5 | Desligar ambos os canais | Nenhum disparo; execução da esteira não corrompida |

## Casos de erro

- Falha de canal: registrada privadamente no n8n; não altera `agent:*`.
- Micro-serviço indisponível: n8n mantém a esteira manual (spec 14 §Fallback).

## Evidências

- Testes unitários: `uv run pytest tests/agent/notificacoes/ -q` (6 passed).
- Regressão: `uv run pytest tests/test_agent_*.py -q` (54 passed).

## Limpeza

- Encerrar o processo da API de teste.
- Reverter qualquer webhook de teste no n8n.

## Resultado da homologação

- Resultado: APROVADO | REPROVADO | BLOQUEADO | NAO APLICAVEL
- Commit testado: <sha>
- Ambiente: <ambiente>
- Perfil: <perfil>
- Roteiro executado: este documento
- Divergências: <nenhuma ou descrição>
- Justificativa de NAO APLICAVEL: <quando aplicável>
