# Spec: ML de Contrapartida e Feedback Humano

## Objetivo

Adaptar o fluxo de ML para prever contrapartida contabil em movimentos de origem banco/caixa/aplicacao, mantendo confianca, marcacao de revisao e feedback humano como parte do ciclo de aprendizado.

Sucesso significa que o modelo usa o dataset normalizado, retorna predicoes explicaveis e permite correcao humana auditavel.

O fluxo novo de ML usa `LancamentoRazaoNormalizado` como origem canonica por
meio do dataset de contrapartida. `Transacao` permanece legado/compatibilidade
ate ser isolado, adaptado ou removido em issue propria; ver
`docs/razao-transacoes-dataset-decisao.md`.

## Tech Stack

- scikit-learn com pipeline de texto no estado inicial.
- Pandas para preparacao de treino.
- SQLAlchemy para consulta e persistencia.
- FastAPI para endpoints de predicao/classificacao/feedback.
- Pytest para comportamento do ML e feedback.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`

## Project Structure

- `core/ml_engine.py`: classificador e predicao.
- `core/`: builder de dataset e servicos auxiliares.
- `api/routes/classification.py`: endpoints de classificacao e predicao.
- `api/routes/feedback.py`: endpoint de correcao humana.
- `tests/test_ml_engine.py`: testes de ML.
- `tests/test_api.py`: testes de API.

## Code Style

O classificador deve receber dados ja normalizados e nao conhecer detalhes de parser de Excel.

Exemplo de resposta esperada:

```python
{
    "conta_contrapartida_predita": 50057,
    "confidence": 0.82,
    "needs_review": False,
}
```

## Testing Strategy

- Testar treino com dataset suficiente.
- Testar erro de dominio `422` com dataset insuficiente.
- Testar resposta de predicao com conta, confianca e revisao.
- Testar baixa confianca marcando revisao.
- Testar feedback corrigindo contrapartida.
- Testar feedback respeitando usuario e empresa.
- Testar que feedback altera dados usados em treino futuro.
- Testar que predicoes ficam limitadas a contas analiticas validas vinculadas a empresa.
- Evitar assertar classes exatas quando isso depender de comportamento fragil do algoritmo.

## Boundaries

- Sempre: escopo de treino por empresa.
- Sempre: registrar confianca e revisao.
- Sempre: feedback humano deve ser persistido.
- Sempre: usar limiar de confianca inicial `0.70`.
- Sempre: retornar `422` quando o dataset for insuficiente para treino.
- Sempre: limitar predicoes a contas analiticas validas vinculadas a empresa.
- Sempre: feedback corrige o lancamento existente e registra evento auditavel.
- Perguntar antes: trocar algoritmo principal.
- Perguntar antes: cachear modelos por empresa.
- Nunca: aceitar predicao sem empresa e usuario autorizados.
- Nunca: tratar previsao como decisao contabil final sem possibilidade de revisao.
- Nunca: criar exemplo duplicado de treino para feedback corrigido.

## Success Criteria

- Classificador preve contrapartida, nao conta generica solta.
- Predicoes incluem confianca e revisao.
- Feedback corrige predicoes e fica auditavel.
- Dataset insuficiente retorna `422`, nao erro generico `500`.
- Testes cobrem dataset insuficiente, resposta, revisao, escopo por empresa e feedback.
- Fluxo antigo de predicao e classificador e adaptado ou isolado sem quebrar cobertura existente.

## Decisoes Aprovadas

- O limiar de confianca inicial permanece `0.70`.
- O modelo sera treinado por request na primeira versao.
- A arquitetura deve permitir cache por empresa futuramente, mas cache nao sera implementado nesta fase.
- Feedback corrigido atualiza o lancamento/classificacao existente.
- Feedback nao cria exemplo duplicado de treino.
- Feedback gera evento auditavel.
- O proximo treino usa dados corrigidos.
- O classificador preve `conta_contrapartida`.
- Predicao respeita escopo de empresa.
- Predicao considera apenas contas analiticas validas vinculadas a empresa.
- Dataset insuficiente retorna erro de dominio `422`.
- Baixa confianca persiste previsao com `needs_review=True`.
- `/classification` classifica lancamentos normalizados pendentes de contrapartida.
- `/predict` prediz contrapartida para entrada externa/normalizada, sem depender de Excel.
- Schemas novos de contrapartida podem ser criados para evitar confusao com o fluxo antigo.
- O classificador nao conhece parser de Excel.
- O algoritmo principal nao sera trocado nesta fase.
- Metodos baseados em `Transacao` pertencem ao fluxo legado e nao devem ser
  usados como fonte do novo dataset de contrapartida.

## Open Questions

- Os endpoints antigos serao adaptados diretamente ou manterao compatibilidade por um periodo com novos schemas?
- Qual sera o nome final dos campos persistidos de contrapartida prevista e revisao?
- O evento auditavel de feedback sera implementado nesta spec ou dependera da spec de auditoria?
