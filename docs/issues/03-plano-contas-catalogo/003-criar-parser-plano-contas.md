# Issue 003: feat(contas): criar parser do Plano de Contas.xlsx

## Contexto

O arquivo de plano de contas e um relatorio `.xlsx` com cabecalho e linhas uteis a partir da area de titulos. O parser deve retornar dados normalizados antes de qualquer persistencia.

## Escopo

- Criar parser para `.xlsx` do plano de contas.
- Ignorar cabecalho do relatorio.
- Extrair codigo, tipo, classificacao, nome e grau.
- Identificar contas sinteticas e analiticas pelo campo `tipo`.
- Rejeitar ou reportar linhas incompletas de forma clara.
- Nao persistir dados nesta issue.

## Criterios de Aceite

- Parser retorna lista de contas normalizadas.
- Cabecalho e linhas vazias sao ignorados.
- Campos essenciais sao extraidos corretamente.
- Linhas invalidas geram erro ou warning claro.
- Parser nao depende do banco.

## Testes Esperados

- Teste com amostra de planilha contendo cabecalho.
- Teste de conta sintetica.
- Teste de conta analitica.
- Teste de linha incompleta.
- Teste de linha vazia ignorada.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Acoplar parser ao layout por numero fixo de linha sem validacao.
- Persistir dados diretamente no parser.
