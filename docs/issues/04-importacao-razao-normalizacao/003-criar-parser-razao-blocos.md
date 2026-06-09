# Issue 003: feat(razao): criar parser de blocos do Razao.xlsx

## Contexto

O livro-razao vem como relatorio `.xlsx` com cabecalhos, linhas vazias, saldos e blocos iniciados por `Conta:`. O parser deve detectar blocos e linhas uteis sem persistir dados.

## Escopo

- Criar parser para `.xlsx` do razao.
- Detectar blocos `Conta:`.
- Ignorar cabecalho, saldo anterior e linhas vazias.
- Retornar linhas em memoria com conta de origem, data, numero, historico, contrapartida, debito e credito.
- Nao normalizar debito/credito nesta issue, se isso for separado.
- Nao persistir dados.

## Criterios de Aceite

- Parser detecta conta de origem do bloco.
- Parser associa linhas ao bloco correto.
- Cabecalhos e saldos sao ignorados.
- Linhas uteis sao retornadas em estrutura normalizada de parse.
- Parser aceita apenas `.xlsx`.

## Testes Esperados

- Teste de deteccao de bloco `Conta:`.
- Teste de linha util dentro do bloco.
- Teste de cabecalho ignorado.
- Teste de saldo anterior ignorado.
- Teste de linha vazia ignorada.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Acoplar a parser a uma linha fixa em vez de marcadores do relatorio.
- Misturar parse com persistencia.
