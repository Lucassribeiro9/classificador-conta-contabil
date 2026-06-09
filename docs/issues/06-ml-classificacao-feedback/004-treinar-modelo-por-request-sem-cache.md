# Issue 004: feat(ml): treinar modelo por request sem cache

## Contexto

A decisao aprovada e treinar por request na primeira versao, deixando cache por empresa para evolucao futura.

## Escopo

- Garantir que predicoes treinem usando dados atuais da empresa no momento da request.
- Nao implementar cache de modelo.
- Organizar codigo para permitir cache futuro sem grande refatoracao.
- Garantir que feedback corrigido afete o proximo treino.

## Criterios de Aceite

- Cada request de predicao usa dataset atual da empresa.
- Feedback anterior corrigido pode afetar a request seguinte.
- Nao ha cache persistente ou global de modelo nesta fase.
- Estrutura nao impede cache futuro por empresa.

## Testes Esperados

- Teste de request treinando com dataset atual.
- Teste em que correcao anterior aparece no proximo treino.
- Teste garantindo ausencia de reutilizacao indevida entre empresas.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar cache prematuro e servir modelo desatualizado.
- Treino por request ficar caro sem medicao real de volume.
