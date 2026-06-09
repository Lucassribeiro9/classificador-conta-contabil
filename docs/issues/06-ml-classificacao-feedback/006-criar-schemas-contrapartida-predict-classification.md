# Issue 006: feat(api): criar schemas de contrapartida para predict e classification

## Contexto

Schemas novos ajudam a diferenciar o fluxo de contrapartida do fluxo antigo de classificacao de conta generica.

## Escopo

- Criar schemas de request/response para predicao de contrapartida.
- Incluir `conta_contrapartida_predita`, `confidence` e `needs_review` na resposta.
- Incluir campos minimos de entrada normalizada para `/predict`.
- Manter compatibilidade com autorizacao por empresa.
- Nao implementar logica de ML nesta issue, se ja separada.

## Criterios de Aceite

- Schemas deixam explicita a semantica de contrapartida.
- Resposta tem conta prevista, confianca e revisao.
- Entrada nao depende de arquivo Excel.
- Nomes nao entram em conflito com schemas antigos.

## Testes Esperados

- Testes de validacao de payload valido.
- Testes de payload invalido.
- Testes de serializacao da resposta.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Continuar usando nomes antigos e confundir consumidores da API.
- Exigir campos de Excel em endpoint que deve receber entrada normalizada.
