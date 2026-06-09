# Issue 010: test(postgres): adicionar testes de integracao com PostgreSQL

## Contexto

Testes de integracao reais com PostgreSQL sao desejaveis, mas podem exigir setup adicional de container/CI. Esta issue fica como backlog tecnico se a primeira fase validar PostgreSQL manualmente.

## Escopo

- Definir estrategia de testes de integracao contra PostgreSQL.
- Avaliar uso de Docker local ou CI.
- Criar testes que apliquem migrations e validem `/health` contra PostgreSQL.
- Nao bloquear a migracao inicial se o ambiente ainda nao estiver pronto.

## Criterios de Aceite

- Existe comando claro para rodar testes de integracao PostgreSQL.
- Testes nao interferem nos testes unitarios existentes.
- Migrations sao validadas em banco PostgreSQL real.
- `/health` e validado contra PostgreSQL real.

## Testes Esperados

- Comando especifico de integracao a definir na propria issue.
- `.\venv\Scripts\python.exe -m pytest -q tests` continua funcionando.

## TDD

Obrigatorio quando esta issue for implementada.

## Riscos

- Deixar suite local lenta demais.
- Criar dependencia obrigatoria de Docker para todos os testes unitarios.
