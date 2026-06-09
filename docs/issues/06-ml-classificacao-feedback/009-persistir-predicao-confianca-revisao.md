# Issue 009: feat(ml): persistir predicao, confianca e revisao

## Contexto

Predicoes de baixa confianca devem ficar marcadas para revisao. A confianca inicial usa limiar `0.70`.

## Escopo

- Persistir conta de contrapartida prevista no lancamento ou entidade relacionada.
- Persistir confianca da predicao.
- Persistir `needs_review`.
- Usar limiar inicial `0.70`.
- Marcar baixa confianca como `needs_review=True`.
- Nao transformar predicao em decisao final sem feedback.

## Criterios de Aceite

- Predicao com confianca >= 0.70 fica com `needs_review=False`.
- Predicao com confianca < 0.70 fica com `needs_review=True`.
- Campos persistidos podem ser consultados depois.
- Predicao nao sobrescreve correcao humana sem regra explicita.

## Testes Esperados

- Teste de alta confianca.
- Teste de baixa confianca.
- Teste de persistencia dos campos.
- Teste de nao sobrescrever feedback corrigido.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Aceitar previsao incerta silenciosamente.
- Sobrescrever revisao humana por nova predicao automatica.
