# Issue 003: feat(audit): criar servico de registro de eventos

## Contexto

Os fluxos sensiveis nao devem montar eventos manualmente de formas diferentes. Um servico central reduz inconsistencia e facilita sanitizacao.

## Escopo

- Criar servico de auditoria em `core/`.
- Padronizar assinatura para registrar evento com usuario, empresa, recurso e metadata.
- Permitir uso dentro de transacoes existentes quando possivel.
- Padronizar timestamps e valores opcionais.
- Nao criar observabilidade externa.

## Criterios de Aceite

- Fluxos podem registrar eventos por uma API unica.
- Campos opcionais sao tratados de forma consistente.
- Servico aceita metadata ja sanitizada ou chama sanitizacao central.
- Falhas seguem politica definida na issue 001.

## Testes Esperados

- Teste de registro simples.
- Teste com campos opcionais.
- Teste de uso dentro de sessao/transacao existente.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Cada rota criar auditoria de um jeito.
- Servico abrir transacoes inesperadas e quebrar atomicidade.
