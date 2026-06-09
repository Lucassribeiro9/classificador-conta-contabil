# Issue 008: feat(dataset): sinalizar dataset insuficiente para treino

## Contexto

O builder pode gerar dataset com pelo menos uma linha valida, mas isso nao significa que o modelo deve treinar. A spec define minimo recomendado de treino como 10 linhas e 2 classes.

## Escopo

- Sinalizar em metadados se o dataset atende ao minimo recomendado para treino.
- Usar criterio inicial de pelo menos 10 linhas totais e pelo menos 2 classes de contrapartida.
- Manter a decisao final de resposta HTTP para a spec de ML.
- Nao retornar erro HTTP nesta issue.

## Criterios de Aceite

- Dataset com 1 linha pode ser gerado, mas fica marcado como nao treinavel.
- Dataset com menos de 10 linhas fica marcado como nao treinavel.
- Dataset com apenas 1 target fica marcado como nao treinavel.
- Dataset com 10 ou mais linhas e 2 ou mais targets fica marcado como treinavel.

## Testes Esperados

- Teste de 1 linha valida.
- Teste de 9 linhas.
- Teste de 10 linhas com 1 classe.
- Teste de 10 linhas com 2 classes.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Bloquear geracao de dataset quando ele ainda e util para diagnostico.
- Confundir insuficiencia de dataset com erro de importacao.
