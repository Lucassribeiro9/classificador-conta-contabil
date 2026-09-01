# Paridade das instrucoes dos modelos de movimentos operacionais

## Objetivo

Atualizar os dois modelos oficiais de movimentos operacionais para oferecer a
mesma riqueza semantica de instrucoes e exemplos do modelo legado, adaptada ao
contrato de cada layout. A mudanca deve facilitar o preenchimento correto das
planilhas sem alterar o comportamento do importador.

## Escopo

Arquivos de produto a atualizar:

- `tests/fixtures/modelo_movimentos_operacionais_valor_saldo.xlsx`;
- `tests/fixtures/modelo_movimentos_operacionais_debito_credito_saldo.xlsx`.

Testes de contrato a ajustar:

- `tests/test_movimentos_operacionais_fixture.py`.

A aba `Movimentos` deve permanecer sem lancamentos demonstrativos. Ela conserva
somente titulo, metadados, cabecalhos e eventuais orientacoes estruturais.

## Conteudo das instrucoes

A aba `Instrucoes` dos dois modelos deve explicar, com redacao apropriada ao
layout:

- objetivo do modelo;
- identificacao da conta financeira;
- interpretacao de `valor` assinado ou de `debito` e `credito`;
- uso do `saldo` para conferencia por conta financeira;
- preenchimento opcional da contrapartida;
- derivacao contabil de debito e credito;
- validacao contra o plano de contas e contas permitidas para a empresa;
- encaminhamento para revisao quando faltar contrapartida ou houver baixa
  confianca;
- responsabilidade do sistema pelas colunas `status_sugerido`,
  `confidence_sugerida` e `mensagem_validacao`.

No layout `valor_saldo`, valor positivo representa entrada e valor negativo
representa saida. No layout `debito_credito_saldo`, credito representa entrada,
debito representa saida e exatamente um dos dois deve ser preenchido por linha.

## Exemplos

A aba `Exemplos` deve conter dados exclusivamente ficticios e cobrir os mesmos
cinco cenarios nos dois layouts:

1. recebimento;
2. pagamento;
3. aplicacao;
4. resgate;
5. movimento sem contrapartida para classificacao pelo sistema.

Os cenarios devem demonstrar saldo e derivacao contabil. Seus saldos precisam
ser aritmeticamente coerentes, e `valor`, `debito` e `credito` devem representar
a mesma movimentacao economica nos dois modelos.

## Contrato dos testes

Os testes devem validar requisitos semanticos e estruturais, evitando comparar
frases completas. Cada falha deve permitir identificar a planilha, a aba e o
requisito ausente.

A cobertura deve assegurar que:

- `Movimentos` nao contenha lancamentos de exemplo;
- `Instrucoes` cubra conta financeira, contrapartida, saldo, validacao, revisao
  e colunas preenchidas pelo sistema;
- cada layout documente sua propria regra de direcao;
- `Exemplos` contenha os cinco cenarios;
- os exemplos demonstrem saldo e derivacao contabil;
- as fixtures nao contenham identificacao real de cliente ou empresa.

## Fora de escopo

- alterar o modelo legado
  `modelo_movimentos_operacionais_classificacao.xlsx`;
- modificar parser, API, persistencia ou regras de importacao;
- criar um gerador de planilhas;
- realizar reformulacao visual ampla;
- alterar a documentacao existente, salvo se a implementacao revelar uma
  contradicao de contrato.

## Criterios de aceite

- Os dois modelos oficiais possuem instrucoes semanticamente equivalentes as do
  modelo legado e adaptadas aos respectivos layouts.
- A aba `Movimentos` permanece sem lancamentos demonstrativos.
- A aba `Exemplos` cobre os cinco cenarios aprovados com dados ficticios.
- Os saldos dos exemplos sao aritmeticamente coerentes.
- A derivacao contabil esta correta para entradas e saidas.
- Os testes automatizados protegem os requisitos acordados e passam.
- Nenhum dado real ou identificacao de cliente e introduzido.
- Nao ha alteracao comportamental na aplicacao.

## Riscos e mitigacoes

O risco principal e tornar os testes frageis por acoplamento a redacao das
celulas. A mitigacao e validar topicos, cenarios e estrutura por marcadores
semanticos, sem exigir textos literais. Outro risco e um exemplo incoerente
ensinar preenchimento incorreto; os testes devem conferir direcao contabil e
continuidade aritmetica do saldo.

## Corpo proposto da issue

Titulo: `chore(fixtures): alinhar instrucoes dos modelos de movimentos`

### Contexto

Os modelos oficiais `valor_saldo` e `debito_credito_saldo` possuem abas
`Instrucoes` e `Exemplos`, mas o conteudo atual e mais resumido que o modelo
legado. Faltam orientacoes sobre conta financeira, contrapartida, derivacao
contabil, validacao e revisao, alem de cenarios equivalentes de aplicacao,
resgate e classificacao. Isso reduz a capacidade dos modelos de orientar o
preenchimento correto e a interpretacao dos layouts.

### Escopo da tarefa

- Area: fixtures e testes de contrato.
- Itens que serao alterados:
  - enriquecer `Instrucoes` nos dois modelos oficiais com paridade funcional
    adaptada a cada layout;
  - enriquecer `Exemplos` com recebimento, pagamento, aplicacao, resgate e
    movimento sem contrapartida;
  - manter a aba `Movimentos` sem lancamentos demonstrativos;
  - ajustar testes para validar conteudo semantico, coerencia de saldo,
    derivacao contabil e sanitizacao.
- Dependencias tecnicas: `openpyxl` e os contratos da Spec 08.

### Definicao de pronto

- [ ] Mudanca implementada conforme escopo
- [ ] Os dois modelos possuem instrucoes semanticamente equivalentes as do
      modelo legado, adaptadas ao respectivo layout
- [ ] A aba `Movimentos` permanece sem lancamentos de exemplo
- [ ] A aba `Exemplos` cobre os cinco cenarios aprovados com dados ficticios
- [ ] Saldos, valores e derivacoes contabeis dos exemplos sao coerentes
- [ ] Testes automatizados validam os requisitos sem depender de frases exatas
- [ ] Documentacao atualizada somente se surgir contradicao com o contrato atual
- [ ] Sem impacto funcional inesperado na API, importadores ou ML
- [ ] Sem segredos, credenciais ou dados sensiveis versionados
- [ ] PR vinculado com `Closes #<numero>`

### Criticidade e risco

- Criticidade: baixa.
- Risco principal: testes frageis por acoplamento ao texto ou exemplos que
  ensinem uma direcao contabil incorreta.
- Mitigacao: assercoes semanticas e estruturais, incluindo coerencia aritmetica
  do saldo e equivalencia entre os layouts.

### Observacoes para review

- Confirmar que o modelo legado nao foi alterado.
- Confirmar que `Movimentos` continua sem dados demonstrativos.
- Comparar os mesmos cenarios nos dois layouts e verificar que representam as
  mesmas entradas e saidas.
- Confirmar que todo conteudo permanece ficticio e sanitizado.

### Fora de escopo

- Alterar parser, API, persistencia ou regras de importacao.
- Criar gerador de planilhas.
- Reformular amplamente o visual das fixtures.
- Modificar o modelo legado.
