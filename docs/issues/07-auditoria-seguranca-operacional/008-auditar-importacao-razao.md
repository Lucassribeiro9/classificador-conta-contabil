# Issue 008: feat(audit): auditar importacao do razao

## Contexto

Importacao do razao cria dados de treino por empresa e precisa indicar sucesso, falha ou conclusao com warnings.

## Escopo

- Registrar `ledger_import.started`.
- Registrar `ledger_import.completed`.
- Registrar `ledger_import.completed_with_warnings`.
- Registrar `ledger_import.failed`.
- Incluir usuario, empresa e lote de importacao quando existir.
- Incluir contadores e resumo de warnings.
- Nao armazenar conteudo completo da planilha.

## Criterios de Aceite

- Eventos de razao incluem empresa.
- Importacao parcial gera evento proprio.
- Falha gera evento seguro.
- Metadata contem contadores uteis sem payload sensivel.

## Testes Esperados

- Teste de inicio de importacao.
- Teste de conclusao sem warnings.
- Teste de conclusao com warnings.
- Teste de falha.
- Teste garantindo que conteudo completo da planilha nao e persistido.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Perder rastreabilidade de importacao parcial.
- Gravar historicos completos em auditoria quando nao necessario.
