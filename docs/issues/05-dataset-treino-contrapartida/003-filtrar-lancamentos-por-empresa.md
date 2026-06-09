# Issue 003: feat(dataset): filtrar lancamentos por empresa

## Contexto

O dataset inicial deve ser gerado por empresa e nunca misturar exemplos de clientes diferentes.

## Escopo

- Consultar apenas lancamentos normalizados da empresa informada.
- Garantir que joins com contas e vinculos nao tragam dados de outra empresa.
- Descartar ou ignorar lancamentos sem `empresa_id` valido.
- Nao implementar filtros financeiros nesta issue, se estiverem separados.

## Criterios de Aceite

- Dataset de uma empresa contem apenas lancamentos dessa empresa.
- Empresas sem lancamentos elegiveis retornam dataset vazio com metadados.
- O builder nao permite chamada sem escopo de empresa.

## Testes Esperados

- Teste com duas empresas e lancamentos semelhantes.
- Teste garantindo que empresa A nao recebe exemplos da empresa B.
- Teste de empresa sem dados.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Vazamento de dados entre empresas.
- Criar dataset global por acidente para facilitar o treino.
