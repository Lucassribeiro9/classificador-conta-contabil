# Metricas e limitacoes iniciais do ML de contrapartida

Este documento complementa a [spec 06](specs/06-ml-classificacao-feedback.md)
(`docs/specs/06-ml-classificacao-feedback.md`) e registra as expectativas da
primeira versao do classificador de contrapartida.

O objetivo aqui e explicar por que o modelo inicial e simples, quais limites
operacionais devem ser esperados e quais evolucoes ficam fora desta fase.

## Escolha inicial do modelo

A primeira versao usa um pipeline Scikit-learn com `TF-IDF + MultinomialNB`.

Essa escolha prioriza simplicidade, previsibilidade e baixo custo operacional:

- o treino e rapido em datasets pequenos;
- o resultado e deterministico para a mesma base de treino;
- a serializacao em `model_.joblib` e simples de operar;
- o pipeline e suficiente para validar o fluxo de dados, permissao, feedback e
  revisao humana antes de investir em modelos mais complexos.

O `MultinomialNB` assume independencia condicional entre features. Essa
hipotese nem sempre descreve bem textos contabeis reais, mas e aceitavel para a
primeira entrega porque o objetivo principal e estabilizar o ciclo completo:
dataset normalizado, treino, predicao, confianca, revisao e feedback humano.

## Dataset minimo e resposta 422

O criterio inicial recomendado para treino e:

- pelo menos 10 linhas validas no dataset da empresa;
- pelo menos 2 classes de contrapartida.

Quando o dataset nao atinge esse minimo, a API deve tratar o caso como erro de
dominio e retornar `422 Unprocessable Entity`, nao erro generico `500`.

Esse limite evita treinar um modelo que so memorizaria poucos exemplos ou uma
unica classe. Mesmo quando o treino e permitido com 10 linhas e 2 classes, esse
e apenas o minimo tecnico inicial. A qualidade esperada ainda pode ser baixa em
empresas com historico pequeno, historicos muito repetitivos ou targets
desbalanceados.

## Limite da predicao online

O endpoint de classificacao online aceita lote pequeno com limite inicial de
100 linhas por requisicao.

Esse limite existe para reduzir risco de timeout e evitar que uma chamada de
classificacao vire processamento em lote pesado. Arquivos maiores devem ser
tratados por fluxo de importacao, processamento controlado ou outra rotina
futura, nao pelo endpoint online.

## Confianca e revisao

A resposta da predicao informa a conta de contrapartida prevista e a
probabilidade de confianca calculada pelo modelo. O limiar inicial de revisao
permanece `0.70`.

Predicoes abaixo desse limiar devem ser marcadas como `needs_review=True`.
Mesmo acima do limiar, a previsao nao deve ser tratada como decisao contabil
final. O usuario continua responsavel por revisar e corrigir quando necessario.

## Feedback e novo treino

O feedback humano nao altera o modelo `joblib` imediatamente. Ele e persistido
como dado de correcao e passa a influenciar o proximo dataset de treino da
empresa.

Isso significa que nao existe online learning nesta fase. Depois de registrar
feedback, e necessario executar novo treino para que o arquivo `model_.joblib`
reflita as correcoes.

## Fora desta fase

Ficam fora da primeira versao:

- grid-search de hiperparametros;
- AutoML;
- comparacao automatica entre varios algoritmos;
- calibracao avancada de probabilidades;
- cache de modelo por empresa;
- aprendizado incremental em tempo real;
- predicao de lancamentos compostos ou multiplas partidas.

Esses pontos podem ser avaliados depois que o fluxo basico estiver estavel e
houver volume suficiente de dados reais por empresa.

## Como interpretar metricas nesta fase

As metricas iniciais devem ser usadas como diagnostico, nao como garantia de
qualidade contabil.

Sinais importantes para acompanhar:

- quantidade de linhas validas por empresa;
- quantidade de classes de contrapartida;
- distribuicao por target;
- volume de predicoes marcadas para revisao;
- volume de feedbacks por empresa;
- melhoria observada apos novo treino com feedback aplicado.

Com poucos exemplos, uma acuracia aparente alta pode ser ilusoria. O melhor uso
da primeira versao e medir se o pipeline completo esta funcionando e se o
feedback humano melhora o dataset usado no proximo treino.
