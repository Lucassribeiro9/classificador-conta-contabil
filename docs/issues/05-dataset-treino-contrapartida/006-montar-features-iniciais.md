# Issue 006: feat(dataset): montar features iniciais do exemplo de treino

## Contexto

As features iniciais devem ser simples e explicaveis: historico normalizado, conta de origem e direcao. O valor monetario bruto nao entra nesta fase.

## Escopo

- Montar texto de features a partir de `historico_normalizado`.
- Incluir codigo da `conta_origem` como token textual.
- Incluir `direcao` como token textual.
- Garantir ordem e formato deterministico.
- Excluir valor monetario bruto das features.
- Nao criar engenharia de features avancada nesta issue.

## Criterios de Aceite

- Cada linha valida gera campo `features`.
- Features incluem historico normalizado.
- Features incluem origem financeira como token.
- Features incluem direcao como token.
- Valor bruto nao aparece no texto de features.

## Testes Esperados

- Teste de features com historico, origem e direcao.
- Teste de formato deterministico.
- Teste garantindo ausencia de valor monetario bruto.
- Teste de historico vazio ou minimo, se permitido pelo dominio.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar feature fragil com dados monetarios brutos.
- Misturar feature engineering com treinamento do modelo.
