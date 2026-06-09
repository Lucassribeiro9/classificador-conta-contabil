# Issue 007: feat(dataset): retornar metadados do dataset

## Contexto

O builder precisa explicar o que produziu para que API e ML decidam se o dataset serve para treino.

## Escopo

- Retornar `empresa_id` nos metadados.
- Retornar total de linhas validas do dataset.
- Retornar total de descartes.
- Retornar contagem por target.
- Retornar indicador de treinabilidade ou campos suficientes para o ML decidir.
- Nao executar treino nesta issue.

## Criterios de Aceite

- Metadados acompanham todo retorno do builder.
- `total_linhas` corresponde ao numero de exemplos validos.
- `total_descartes` corresponde as linhas ignoradas por filtros e validacoes.
- `contagem_por_target` agrega por contrapartida.
- Metadados funcionam para dataset vazio.

## Testes Esperados

- Teste de totais com linhas validas.
- Teste de descartes por linha inelegivel.
- Teste de contagem por target.
- Teste de dataset vazio com metadados coerentes.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- O ML precisar reprocessar dados para descobrir se pode treinar.
- Metadados divergirem das linhas retornadas.
