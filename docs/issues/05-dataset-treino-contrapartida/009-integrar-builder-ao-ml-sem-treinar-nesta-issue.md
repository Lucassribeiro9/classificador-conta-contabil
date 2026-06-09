# Issue 009: refactor(ml): preparar consumo do builder pelo classificador

## Contexto

O `core/ml_engine.py` deve passar a depender do contrato de dataset, mas a mudanca completa de predicao pertence a spec de ML.

## Escopo

- Ajustar pontos de integracao para que o classificador consiga consumir linhas e metadados do builder.
- Manter compatibilidade com testes existentes quando possivel.
- Nao implementar novo endpoint de predicao nesta issue.
- Nao alterar regra de resposta 422 da spec de ML nesta issue.
- Nao treinar automaticamente fora do fluxo ja existente.

## Criterios de Aceite

- Existe caminho claro para o ML receber dataset por empresa.
- O classificador nao consulta lancamentos brutos diretamente quando o builder deve ser usado.
- Mudancas ficam pequenas e revisaveis.
- Comportamento externo so muda se coberto por spec aprovada.

## Testes Esperados

- Teste de integracao leve entre builder e camada de ML, se houver contrato ja disponivel.
- Testes existentes de ML continuam passando ou sao ajustados conforme a spec.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Misturar entrega de dataset com mudanca completa de predicao.
- Quebrar endpoints atuais antes da spec de ML ser implementada.
