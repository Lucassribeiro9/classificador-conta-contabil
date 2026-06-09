# Issue 005: feat(audit): capturar contexto de request

## Contexto

Quando disponivel, eventos devem registrar `ip_address` e `user_agent`, alem do usuario atual e empresa envolvida.

## Escopo

- Criar helper/dependency para extrair IP e user agent da request.
- Integrar contexto de usuario atual quando existir.
- Permitir eventos sem request em scripts ou tarefas internas.
- Evitar confiar cegamente em headers de proxy sem configuracao explicita.

## Criterios de Aceite

- Eventos de API podem receber IP e user agent.
- Eventos fora de request continuam possiveis.
- Ausencia de user agent ou IP nao quebra auditoria.
- Codigo fica reutilizavel por rotas diferentes.

## Testes Esperados

- Teste com request contendo user agent.
- Teste sem user agent.
- Teste de chamada sem contexto de request.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Quebrar scripts internos que nao possuem request.
- Registrar IP incorreto se houver proxy sem configuracao clara.
