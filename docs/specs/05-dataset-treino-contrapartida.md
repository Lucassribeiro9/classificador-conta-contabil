# Spec: Dataset de Treino para Contrapartida Financeira

## Objetivo

Gerar dataset de treino a partir de lancamentos normalizados cujo bloco de origem seja banco, caixa ou aplicacao financeira. O alvo inicial do modelo sera a conta de contrapartida.

Sucesso significa que o dataset evita ambiguidade do razao completo e fornece exemplos consistentes para o ML prever o outro lado de movimentos financeiros.

## Tech Stack

- SQLAlchemy para consulta dos lancamentos normalizados.
- Pandas para transformacao tabular quando necessario.
- scikit-learn para consumo posterior pelo classificador.
- Pytest para regras de filtro e target.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`

## Project Structure

- `core/`: builder de dataset de treino.
- `core/models.py`: campos necessarios em contas e lancamentos normalizados.
- `core/ml_engine.py`: uso futuro do dataset no classificador.
- `tests/`: testes de filtro, target e features.

## Contratos de Campos Base

O builder deve usar os nomes finais ja persistidos pelos dominios de plano de
contas e Razao. Estes nomes sao contrato para as issues funcionais desta spec.

Catalogo de contas (`ContaContabil`):

- `codigo`: identificador unico da conta contabil no catalogo.
- `tipo`: indica conta analitica (`A`) ou sintetica (`S`).
- `is_active`: indica se a conta esta ativa.
- `is_financial_origin`: flag persistida que identifica contas de banco, caixa
  ou aplicacao financeira. O builder deve consultar esta flag, sem recalcular a
  heuristica financeira.
- `is_classificavel`: helper de dominio para validar se a conta pode ser alvo
  de classificacao; hoje exige conta ativa e `tipo = A`.

Lancamento normalizado do Razao (`LancamentoRazaoNormalizado`):

- fonte canonica do novo fluxo de dataset; a decisao completa esta em
  `docs/razao-transacoes-dataset-decisao.md`.
- `empresa_id`: escopo obrigatorio do dataset.
- `conta_origem`: conta do bloco do Razao, usada para filtrar origem financeira.
- `conta_contrapartida`: alvo inicial do dataset.
- `direcao`: `debito` ou `credito`, usada como contexto da feature.
- `historico_normalizado`: historico ja persistido pela importacao do Razao,
  gerado por `normalize_razao_historico`.

Campos minimos do dataset:

- Filtros: `empresa_id`, `conta_origem`, `conta_contrapartida`.
- Features iniciais: `historico_normalizado`, `conta_origem`, `direcao`.
- Target: `conta_contrapartida`.

O builder nao deve depender de `valor` bruto na primeira versao e nao deve usar
conta sintetica, inativa ou inexistente como target.

## Code Style

Builder de dataset deve ser separado do treino do modelo. Ele deve retornar estrutura explicita de features e target.

Exemplo de linha esperada:

```python
{
    "features": "pagto boleto sul america saude origem_10046 direcao_credito",
    "target_conta_contrapartida": 50057,
}
```

Exemplo de metadados esperados:

```python
{
    "empresa_id": 1,
    "total_linhas": 120,
    "total_descartes": 3,
    "contagem_por_target": {50057: 14, 10722: 40},
    "treinavel": True,
}
```

## Testing Strategy

- Testar que apenas origens banco/caixa/aplicacao entram no dataset.
- Testar que contas nao financeiras ficam fora como origem.
- Testar que a contrapartida e o target.
- Testar que historico, origem e direcao compoem as features iniciais.
- Testar que linhas sem contrapartida valida ficam fora ou marcadas conforme decisao da spec de razao.
- Testar dataset vazio ou insuficiente.
- Testar que origem financeira vem da flag persistida `is_financial_origin` no catalogo.
- Testar que target precisa ser conta analitica existente.
- Testar que valor bruto nao entra nas features da primeira versao.
- Testar que metadados retornam total, descartes e contagem por target.

## Boundaries

- Sempre: usar contrapartida como target inicial.
- Sempre: preservar empresa como escopo do dataset.
- Sempre: evitar misturar lancamentos de empresas diferentes.
- Sempre: usar a flag persistida `is_financial_origin` do catalogo para identificar origem financeira.
- Sempre: usar apenas lancamentos normalizados validos.
- Sempre: usar apenas contas analiticas existentes como target.
- Sempre: retornar metadados do dataset.
- Perguntar antes: usar qualquer bloco do razao como treino.
- Perguntar antes: incluir contas sinteticas como target.
- Perguntar antes: usar valor monetario bruto como feature.
- Nunca: treinar com conta de origem como alvo quando a origem e banco/caixa.
- Nunca: recalcular heuristica financeira no builder ignorando a flag persistida `is_financial_origin`.
- Nunca: misturar empresas no dataset inicial.

## Success Criteria

- Dataset e gerado por empresa.
- Apenas origens financeiras entram no dataset inicial.
- Target e contrapartida contabil.
- Features refletem historico e contexto minimo.
- Features iniciais nao usam valor monetario bruto.
- Builder retorna metadados de linhas, descartes e contagem por target.
- Testes cobrem filtros, target e isolamento por empresa.

## Decisoes Aprovadas

- O dataset sera gerado por empresa.
- O dataset de contrapartida consome diretamente `LancamentoRazaoNormalizado`;
  `Transacao` permanece como legado/compatibilidade e nao e fonte do novo
  dataset.
- Origem financeira sera definida pela flag persistida `is_financial_origin` no catalogo.
- A heuristica de banco/caixa/aplicacao pertence a spec de plano de contas, nao ao builder.
- O dataset usara apenas lancamentos normalizados validos.
- O dataset usara apenas origem financeira.
- O alvo sera `conta_contrapartida`.
- O alvo deve existir no catalogo e ser conta classificavel
  (`ContaContabil.is_classificavel`), o que exige conta ativa e analitica
  (`tipo = A`).
- Contas sinteticas nao podem ser target.
- Features iniciais serao `historico_normalizado`, `conta_origem` e `direcao`.
- Codigo da conta de origem pode entrar como token textual.
- Valor monetario bruto nao entra como feature na primeira versao.
- O builder pode retornar dataset insuficiente; o ML decide se treina.
- Minimo para gerar dataset: pelo menos 1 linha valida.
- Minimo recomendado para treinar modelo: pelo menos 10 linhas totais e pelo menos 2 classes de contrapartida.
- O builder retornara metadados: total de linhas, descartes, contagem por target e empresa.
- Empresas nao serao misturadas no dataset inicial.

## Open Questions

- O criterio de treinabilidade ficara no builder como metadado ou apenas no ML?
