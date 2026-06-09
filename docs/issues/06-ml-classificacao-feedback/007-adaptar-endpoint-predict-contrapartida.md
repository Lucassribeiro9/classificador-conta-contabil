# Issue 007: feat(api): adaptar endpoint /predict para contrapartida

## Contexto

`/predict` deve predizer contrapartida para entrada externa ou normalizada, sem depender de Excel.

## Escopo

- Adaptar `/predict` para usar schemas de contrapartida.
- Exigir usuario autenticado e empresa autorizada.
- Chamar classificador com dataset da empresa.
- Retornar conta prevista, confianca e `needs_review`.
- Retornar `422` para dataset insuficiente.
- Nao processar arquivo Excel neste endpoint.

## Criterios de Aceite

- Usuario sem permissao nao consegue predizer para empresa.
- Payload normalizado valido retorna predicao de contrapartida.
- Dataset insuficiente retorna `422`.
- Resposta inclui `confidence` e `needs_review`.

## Testes Esperados

- Teste de predicao bem-sucedida.
- Teste de usuario sem acesso.
- Teste de dataset insuficiente com `422`.
- Teste garantindo que endpoint nao aceita planilha como entrada.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Endpoint continuar predizendo conta antiga.
- Permitir predicao sem escopo de empresa.
