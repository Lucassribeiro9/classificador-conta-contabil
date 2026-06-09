# Issue 010: feat(audit): auditar feedback humano

## Contexto

Feedback humano corrige dado usado em treino futuro. A acao precisa ser atribuivel ao usuario e empresa.

## Escopo

- Registrar `feedback.created`.
- Registrar `feedback.updated` quando houver alteracao posterior.
- Incluir usuario, empresa e lancamento/classificacao afetada.
- Incluir metadata segura com conta anterior e conta corrigida quando aplicavel.
- Garantir consistencia transacional quando possivel.

## Criterios de Aceite

- Feedback novo gera evento.
- Atualizacao de feedback gera evento.
- Evento identifica usuario e empresa.
- Evento nao contem payload sensivel.

## Testes Esperados

- Teste de feedback criado.
- Teste de feedback atualizado.
- Teste de ausencia de evento quando feedback falha.
- Teste de metadata segura.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Correcoes humanas ficarem sem trilha.
- Auditoria divergir da alteracao persistida.
