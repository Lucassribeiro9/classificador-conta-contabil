# Issue 011: feat(audit): registrar evento auditavel de feedback

## Contexto

Correcoes humanas precisam ser rastreaveis por usuario, empresa e recurso alterado. A spec de auditoria define a estrutura geral.

## Escopo

- Registrar evento de auditoria ao aplicar feedback.
- Incluir usuario, empresa, tipo de recurso e identificador do lancamento.
- Incluir metadados minimos, como conta anterior e conta corrigida, sem payload sensivel.
- Garantir que feedback e auditoria sejam consistentes transacionalmente quando possivel.
- Nao criar sistema completo de auditoria se a spec 07 ainda nao foi implementada; neste caso, deixar integracao preparada.

## Criterios de Aceite

- Feedback bem-sucedido gera evento auditavel.
- Evento identifica usuario e empresa.
- Evento nao armazena senha, token ou payload sensivel.
- Se a persistencia do feedback falhar, evento nao fica indicando sucesso falso.

## Testes Esperados

- Teste de evento criado no feedback.
- Teste de metadados permitidos.
- Teste de ausencia de evento quando feedback falha.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Auditoria registrar dados sensiveis.
- Auditoria ficar fora de sincronia com a correcao real.
