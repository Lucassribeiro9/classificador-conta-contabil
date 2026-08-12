# Spec: Importacao do Razao e Normalizacao Debito/Credito

## Objetivo

Importar o livro-razao de uma empresa, interpretar blocos de conta e normalizar cada linha em conta de origem, contrapartida, conta de debito, conta de credito, historico, valor, data, numero, saldos observados e lote de importacao.

Sucesso significa que o sistema transforma relatorios de razao em dados estruturados e auditaveis, sem confundir debito/credito com regras globais incorretas e preservando saldos suficientes para derivar fechamentos mensais por conta.

## Tech Stack

- openpyxl para leitura de `.xlsx`.
- SQLAlchemy para persistencia.
- Alembic para schema.
- FastAPI para endpoint de upload/importacao.
- Pytest para parser, normalizacao e persistencia.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`
- Migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`

## Project Structure

- `core/`: parser do razao e servico de importacao.
- `core/models.py`: lote de importacao, lancamento normalizado e vinculo empresa-conta.
- `api/routes/`: endpoint de importacao do razao.
- `api/schemas.py`: resposta de importacao, erros e resumo.
- `tests/`: testes de parser, importacao e autorizacao.

## Code Style

O parser deve ser deterministico e explicito sobre a regra contabil:

```python
if debito is not None:
    conta_debito = conta_bloco
    conta_credito = conta_contrapartida
elif credito is not None:
    conta_debito = conta_contrapartida
    conta_credito = conta_bloco
```

## Contrato de Layout

O arquivo padrao de importacao do Razao deve ser `.xlsx` e pode seguir o
modelo higienizado `modelo-razao-importacao.xlsx`, documentado em
`docs/razao-planilha-modelo.md`. Arquivos `.xls` ficam fora desta fase.

Relatorios em formato de Razao por blocos devem usar linhas iniciadas por
`Conta:` para definir a conta de origem das linhas seguintes. A conta do bloco
permanece ativa ate que outro bloco `Conta:` seja encontrado.

Campos obrigatorios do cabecalho:

- `Empresa`: nome da empresa exibida no arquivo.
- `CNPJ`: documento da empresa. A importacao normaliza para digitos e usa o
  valor como validacao forte contra a empresa alvo da importacao.
- `Periodo inicio`: data inicial do Razao.
- `Periodo fim`: data final do Razao.

Campos obrigatorios dos lancamentos:

- `data`
- `conta_origem`
- `historico`
- `contrapartida`
- `debito` ou `credito`: exatamente um dos dois deve estar preenchido em cada
  linha valida.

Campos opcionais dos lancamentos:

- `numero`: numero externo do lancamento quando o relatorio de origem trouxer
  esta informacao.
- `conta_origem_classificacao`
- `conta_origem_nome`
- `saldo_anterior`
- `saldo`
- `saldo_exercicio`
- `saldo_exercicio_original`: alias legado de `saldo_exercicio`.

O campo persistido `numero_lancamento` representa o numero externo do
lancamento vindo da planilha. Ele pode ser nulo quando o layout de origem nao
fornecer numero de lancamento. O `id` interno do banco identifica o registro
persistido e nao substitui nem deve ser usado como numero externo do
lancamento.

## Semantica dos Saldos

O Razao anual pode trazer tres informacoes de saldo:

- `saldo_anterior`: saldo observado que abre a sequencia de um bloco de conta;
- `saldo`: saldo observado da sequencia exibida no bloco ou relatorio;
- `saldo_exercicio`: saldo acumulado do exercicio informado pelo relatorio.

`saldo_exercicio_original` permanece como alias legado de `saldo_exercicio`
quando o arquivo antigo ou a documentacao anterior usar esse nome.

`Saldo` e `Saldo-Exercicio` devem ser preservados separadamente como saldos
observados do Dominio. A importacao nao deve tentar inferir ou recalcular a
diferenca conceitual entre esses dois campos nesta fase.

Cada saldo preservado deve manter:

- `valor_original`, como apareceu no arquivo;
- `valor_decimal`, como numero normalizado com precisao decimal;
- `natureza`, com valor `D` ou `C`, quando informada.

A natureza `D` ou `C` pertence ao saldo e nao substitui a regra principal de
debito/credito do lancamento. Saldos nao definem `valor`, `direcao`,
`conta_debito` ou `conta_credito` do lancamento.

`saldo_exercicio` sera a referencia principal para conciliacao futura. `saldo`
fica preservado como diagnostico secundario e como apoio para entender a
sequencia exibida no relatorio.

Se o CNPJ informado no arquivo divergir da empresa alvo da importacao, a
importacao deve ser bloqueada antes de persistir lote ou lancamentos. Se o
CNPJ corresponder a uma empresa inativa, a importacao tambem deve ser
bloqueada antes de persistir dados.

Linhas invalidas nao devem ser persistidas como lancamento valido. A importacao
pode ser parcial: linhas validas entram, linhas invalidas geram warnings no
lote. Quando houver ao menos uma linha valida e warnings, o status aprovado e
`completed_with_warnings`.

## Sequencia de Saldos e Fechamentos Mensais

A sequencia de saldos deve ser avaliada por empresa, lote e bloco de conta.
Cada bloco possui sua propria sequencia independente.

Regras alvo:

- `saldo_anterior` abre a sequencia do bloco de conta;
- lancamentos validos atualizam o saldo calculado conforme debito/credito e
  natureza do saldo observado;
- `saldo` representa o saldo observado apos a linha ou ponto exibido pelo
  relatorio;
- divergencia recuperavel entre saldo calculado e saldo observado gera warning
  e nao bloqueia linhas validas;
- erro bloqueante de sequencia deve ficar restrito a casos em que a conta do
  bloco, a empresa ou a estrutura minima do Razao nao possam ser identificadas
  com seguranca;
- valor ou natureza de saldo em formato invalido deve gerar warning quando as
  demais informacoes do lancamento forem suficientes para continuar;
- ausencia de colunas de saldo em arquivo antigo mantem a importacao possivel,
  com aviso informativo de que conciliacao por saldo nao esta disponivel;
- lacunas de saldo nao interrompem o calculo das linhas seguintes quando houver
  dados suficientes para continuar.

Fechamentos mensais devem ser derivados do Razao anual por empresa, conta e
mes. O fechamento mensal deve usar o ultimo saldo observado do mes para a
conta, preservando tambem o saldo calculado para comparacao futura.

O fechamento mensal derivado e dado de conferencia. Ele nao faz pareamento de
conciliacao com movimentos operacionais nesta spec.

## Deduplicacao e ML

Saldos devem ficar fora da chave de deduplicacao do lancamento. A chave de
deduplicacao continua baseada no conteudo do lancamento contabil, nao no saldo
observado ao redor dele.

Saldos tambem nao podem ser usados como feature de treino ou predicao de ML.
Eles servem para conferencia, fechamento mensal e diagnostico de divergencias.

## Testing Strategy

- Testar deteccao de bloco `Conta:`.
- Testar cabecalho, linhas vazias e saldo anterior sem transformar saldo em
  lancamento.
- Testar linha com debito.
- Testar linha com credito.
- Testar linha sem contrapartida.
- Testar troca correta entre debito e credito.
- Testar captura de `saldo_anterior`, `saldo` e `saldo_exercicio`.
- Testar normalizacao de valor decimal, natureza `D`/`C` e valor original dos
  saldos.
- Testar troca de natureza entre saldos devedores e credores.
- Testar sequencia de saldo independente por bloco de conta.
- Testar divergencia recuperavel de saldo como warning.
- Testar erro bloqueante apenas para sequencia sem conta, empresa ou estrutura
  minima confiavel.
- Testar saldo com valor ou natureza invalida como warning recuperavel quando
  o lancamento puder continuar.
- Testar arquivo sem colunas de saldo importado com warning informativo.
- Testar derivacao de fechamento mensal por empresa, conta e mes.
- Testar resposta de API com warnings de saldo e resumos de fechamento quando
  estes contratos forem implementados.
- Testar que saldo fica fora da chave de deduplicacao.
- Testar que saldo fica fora das features de ML e do dataset de treino.
- Testar criacao de lote de importacao.
- Testar vinculo automatico das contas usadas pela empresa.
- Testar reimportacao sem duplicar lancamentos.
- Testar bloqueio para usuario sem acesso a empresa.
- Testar bloqueio de arquivo `.xlsx` ja importado com sucesso para a mesma empresa.
- Testar validacao de contas contra o catalogo do plano de contas.
- Testar importacao parcial com warnings para linhas invalidas.

## Boundaries

- Sempre: interpretar debito/credito em relacao a conta do bloco.
- Sempre: preservar conta de origem e contrapartida alem do par debito/credito.
- Sempre: associar importacao a empresa, usuario e lote.
- Sempre: aceitar apenas arquivos `.xlsx` nesta fase.
- Sempre: exigir que o plano de contas esteja importado antes do razao.
- Sempre: validar conta de origem e conta de contrapartida contra o catalogo.
- Sempre: registrar `original_filename` e `file_hash` no lote.
- Sempre: bloquear reimportacao do mesmo `file_hash` com sucesso para a mesma empresa.
- Sempre: usar chave composta de deduplicacao por conteudo do lancamento.
- Sempre: manter saldos fora da chave de deduplicacao.
- Sempre: manter saldos fora das features de ML.
- Sempre: preservar `valor_original`, `valor_decimal` e `natureza` `D`/`C` dos saldos.
- Sempre: tratar sequencia de saldo por bloco de conta.
- Sempre: permitir importacao parcial, persistindo linhas validas e registrando warnings para invalidas.
- Sempre: importar arquivos antigos sem saldo, registrando aviso de conciliacao por saldo indisponivel.
- Sempre: armazenar warnings de linhas invalidas e divergencias recuperaveis em metadata JSON do lote na primeira fase.
- Sempre: usar `completed_with_warnings` como status de lote quando a importacao persistir linhas validas e registrar warnings.
- Perguntar antes: aceitar layouts muito diferentes do razao lido.
- Perguntar antes: armazenar o arquivo original completo.
- Perguntar antes: persistir linhas sem contrapartida como lancamento incompleto.
- Perguntar antes: bloquear lote inteiro por divergencia recuperavel de saldo.
- Perguntar antes: transformar saldo com formato invalido em erro bloqueante.
- Nunca: assumir que debito sempre significa banco.
- Nunca: usar o arquivo `.xls` ignorado como base desta fase.
- Nunca: persistir como valido lancamento cuja conta de origem ou contrapartida nao exista no catalogo.
- Nunca: usar saldo para definir valor, direcao, debito ou credito do lancamento.
- Nunca: usar saldo como feature de ML.

## Success Criteria

- Razao `.xlsx` legivel e importado por empresa.
- Lancamentos sao normalizados corretamente.
- Lotes de importacao sao registrados.
- Contas usadas sao vinculadas automaticamente a empresa.
- Reimportacoes nao geram duplicidades indevidas.
- Mesmo arquivo ja importado com sucesso para a mesma empresa e bloqueado por `file_hash`.
- Linhas invalidas geram warnings e nao viram lancamentos validos.
- Contas inexistentes no catalogo impedem persistencia do lancamento como valido.
- Testes cobrem debito, credito, cabecalho, saldos, sequencia de saldo,
  fechamento mensal e autorizacao.
- `saldo_anterior`, `saldo` e `saldo_exercicio` possuem semantica documentada.
- Natureza `D`/`C`, `valor_original` e `valor_decimal` dos saldos sao preservados.
- Arquivos antigos sem saldo continuam importaveis com aviso informativo.
- Divergencias recuperaveis de saldo geram warnings sem bloquear linhas validas.
- Fechamentos mensais podem ser derivados por empresa, conta e mes.
- Saldo nao participa de deduplicacao nem de ML.

## Decisoes Aprovadas

- Apenas arquivos `.xlsx` serao aceitos nesta fase.
- O plano de contas deve estar importado antes da importacao do razao.
- A importacao de razao exige permissao `operacao` ou `admin_empresa` na empresa.
- Quando o arquivo trouxer metadados obrigatorios, o CNPJ do arquivo deve
  corresponder ao CNPJ da empresa alvo da importacao.
- O lote de importacao armazenara `original_filename`, `file_hash`, usuario, empresa, status, contadores e timestamps.
- Warnings de linhas invalidas serao armazenados em metadata JSON do lote na primeira fase.
- O status de lote para importacao parcial sera `completed_with_warnings`.
- O arquivo original completo nao sera armazenado nesta primeira fase.
- Se o mesmo `file_hash` ja foi importado com sucesso para a mesma empresa, a reimportacao sera bloqueada.
- Arquivos diferentes com lancamentos repetidos usarao deduplicacao por chave composta.
- A chave de deduplicacao sera `empresa_id`, `numero_lancamento`, `data`, `conta_origem`, `conta_contrapartida`, `valor`, `direcao` e `historico_normalizado`.
- Saldos ficam fora da chave de deduplicacao.
- Linhas sem contrapartida geram warning e nao sao persistidas como lancamento valido.
- Contas inexistentes no catalogo geram warning/erro e nao sao persistidas como lancamento valido.
- A importacao pode ser parcial: linhas validas entram, linhas invalidas ficam registradas em warnings.
- A decisao de metadata JSON para warnings nao exige armazenar o arquivo original completo.
- Cada lancamento normalizado preserva conta de origem, contrapartida, conta de debito, conta de credito, direcao, historico, valor, data, numero do lancamento e lote.
- O Razao anual deve preservar `saldo_anterior`, `saldo` e `saldo_exercicio`.
- `Saldo` e `Saldo-Exercicio` sao saldos observados do Dominio e nao devem ser
  fundidos em um unico campo.
- `saldo_anterior` abre a sequencia de cada bloco de conta.
- `saldo_exercicio` e a referencia principal para conciliacao futura; `saldo`
  permanece como diagnostico secundario.
- Cada saldo preserva `valor_original`, `valor_decimal` e `natureza` `D`/`C`,
  quando informada.
- Divergencia recuperavel de saldo gera warning e nao bloqueia a importacao das
  linhas validas.
- Arquivos antigos sem colunas de saldo continuam importaveis com aviso
  informativo de conciliacao por saldo indisponivel.
- Fechamentos mensais serao derivados por empresa, conta e mes usando o ultimo
  saldo observado do mes e preservando saldo calculado para comparacao futura.
- Saldos nao entram nas features de ML.
- Parser e persistencia permanecem separados.
- Contas validas encontradas no razao serao vinculadas automaticamente a empresa.
- `LancamentoRazaoNormalizado` e a fonte canonica do novo fluxo contabil e nao
  deve ser copiado automaticamente para `Transacao`; ver
  `docs/razao-transacoes-dataset-decisao.md`.

## Open Questions

- O endpoint de importacao sera sincrono nesta fase ou preparado desde ja para processamento em background?
