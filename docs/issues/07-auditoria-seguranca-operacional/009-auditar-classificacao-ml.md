# Issue 009: feat(audit): auditar classificacao por ML

## Contexto

Execucoes de classificacao e predicao alteram ou sugerem dados contabilmente relevantes e devem ser rastreaveis.

## Escopo

- Registrar `classification.started`.
- Registrar `classification.completed`.
- Registrar `classification.failed`.
- Incluir usuario, empresa e recurso quando aplicavel.
- Incluir metadados seguros, como total processado e total marcado para revisao.
- Nao armazenar payload completo da predicao.

## Criterios de Aceite

- Classificacao iniciada gera evento.
- Classificacao concluida gera evento com contadores.
- Falha gera evento seguro.
- Eventos respeitam escopo por empresa.

## Testes Esperados

- Teste de classificacao iniciada.
- Teste de classificacao concluida.
- Teste de classificacao falha.
- Teste de usuario sem acesso gerando acesso negado em vez de classificacao.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Auditar previsao como decisao final.
- Gravar payloads sensiveis de classificacao.
