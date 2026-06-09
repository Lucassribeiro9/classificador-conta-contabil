# Issue 005: feat(razao): calcular historico normalizado e chave de deduplicacao

## Contexto

Arquivos diferentes podem conter lancamentos repetidos. A deduplicacao por conteudo usa `empresa_id`, `numero_lancamento`, `data`, `conta_origem`, `conta_contrapartida`, `valor`, `direcao` e `historico_normalizado`.

## Escopo

- Criar normalizacao de historico para deduplicacao.
- Criar funcao/servico para gerar chave composta do lancamento.
- Garantir estabilidade da chave para espacos e variacoes simples de caixa.
- Nao bloquear ainda reimportacao por `file_hash`.

## Criterios de Aceite

- Historico com espacos/capitalizacao diferentes gera chave consistente quando o conteudo for equivalente.
- Chave inclui todos os campos aprovados.
- Chave diferencia lancamentos com valores, direcoes ou contas diferentes.

## Testes Esperados

- Teste de historico com espacos extras.
- Teste de historico com caixa diferente.
- Teste de chave igual para linha equivalente.
- Teste de chave diferente para valor/direcao/conta diferente.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Normalizar demais e colapsar lancamentos diferentes.
- Normalizar de menos e permitir duplicidade.
