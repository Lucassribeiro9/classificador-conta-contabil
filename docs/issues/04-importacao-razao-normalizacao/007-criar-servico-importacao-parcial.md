# Issue 007: feat(razao): criar servico de importacao parcial

## Contexto

A importacao pode ser parcial: linhas validas entram, linhas invalidas ficam registradas como warnings. Linhas sem contrapartida nao viram lancamento valido.

## Escopo

- Criar servico que orquestra parse, normalizacao, validacao e persistencia.
- Persistir linhas validas.
- Registrar warnings de linhas invalidas.
- Atualizar contadores do lote.
- Definir status final conforme decisao da issue 001.

## Criterios de Aceite

- Lote com todas as linhas validas conclui com sucesso.
- Lote com algumas linhas invalidas persiste validas e registra warnings.
- Lote sem linhas validas falha ou fica em status apropriado.
- Contadores refletem processadas, importadas e invalidas.

## Testes Esperados

- Teste de importacao totalmente valida.
- Teste de importacao parcial com warning.
- Teste de linha sem contrapartida.
- Teste de lote sem validas.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Persistir parcialmente sem deixar claro ao usuario.
- Tratar warning como sucesso silencioso.
