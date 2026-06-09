# Issue 011: docs(dataset): documentar contrato do dataset de contrapartida

## Contexto

O dataset sera consumido pelo ML e possivelmente por endpoints de diagnostico no futuro. O contrato precisa ficar claro para evitar que proximas specs mudem a semantica sem perceber.

## Escopo

- Documentar entrada do builder.
- Documentar estrutura das linhas de dataset.
- Documentar metadados retornados.
- Documentar criterio de origem financeira e target.
- Documentar que valor bruto nao entra como feature na primeira versao.

## Criterios de Aceite

- Documento explica quando uma linha entra no dataset.
- Documento explica quando uma linha e descartada.
- Documento referencia a spec 05.
- Documento diferencia dataset gerado de modelo treinado.

## Testes Esperados

- Revisao manual do documento.

## TDD

Nao obrigatorio.

## Riscos

- Documentacao ficar mais permissiva que a implementacao.
- Confundir dataset de contrapartida com classificacao final do ML.
