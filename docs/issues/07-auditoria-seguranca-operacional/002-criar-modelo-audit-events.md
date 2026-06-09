# Issue 002: feat(audit): criar modelo audit_events

## Contexto

A primeira versao usara uma tabela unica de eventos para rastrear acoes sensiveis e bloqueios relevantes.

## Escopo

- Criar modelo `audit_events` em `core/models.py`.
- Incluir `event_type`, `usuario_id`, `empresa_id`, `resource_type`, `resource_id`, `metadata`, `created_at`, `ip_address` e `user_agent`.
- Permitir `usuario_id` e `empresa_id` nulos quando o evento for global ou nao houver usuario valido.
- Criar migration correspondente.
- Nao criar telas de consulta nesta issue.

## Criterios de Aceite

- Tabela de auditoria existe no banco.
- Campos opcionais aceitam eventos globais e login falho.
- `metadata` aceita JSON.
- `created_at` e preenchido automaticamente.

## Testes Esperados

- Teste de criacao de evento com usuario e empresa.
- Teste de criacao de evento sem usuario.
- Teste de criacao de evento sem empresa.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Modelar auditoria de forma muito especifica e dificultar novos eventos.
- Exigir usuario em eventos que podem ocorrer antes do login.
