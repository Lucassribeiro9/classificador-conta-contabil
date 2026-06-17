# Spec: Importacao do Razao e Normalizacao Debito/Credito

## Objetivo

Importar o livro-razao de uma empresa, interpretar blocos de conta e normalizar cada linha em conta de origem, contrapartida, conta de debito, conta de credito, historico, valor, data, numero e lote de importacao.

Sucesso significa que o sistema transforma relatorios de razao em dados estruturados e auditaveis, sem confundir debito/credito com regras globais incorretas.

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
  valor para validar a situacao da empresa quando informado no arquivo.
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
- `saldo_exercicio_original`

O campo persistido `numero_lancamento` representa o numero externo do
lancamento vindo da planilha. Ele pode ser nulo quando o layout de origem nao
fornecer numero de lancamento. O `id` interno do banco identifica o registro
persistido e nao substitui nem deve ser usado como numero externo do
lancamento.

`saldo_exercicio_original` e dado auxiliar de conferencia visual. Ele nao
participa da regra principal de debito/credito, nao define `valor`, nao define
`direcao` e nao entra na chave de deduplicacao aprovada.

Se o CNPJ informado no arquivo pertencer a uma empresa inativa, a importacao
deve ser bloqueada antes de persistir lote ou lancamentos.

Linhas invalidas nao devem ser persistidas como lancamento valido. A importacao
pode ser parcial: linhas validas entram, linhas invalidas geram warnings no
lote. Quando houver ao menos uma linha valida e warnings, o status aprovado e
`completed_with_warnings`.

## Testing Strategy

- Testar deteccao de bloco `Conta:`.
- Testar ignorar cabecalho, saldo anterior e linhas vazias.
- Testar linha com debito.
- Testar linha com credito.
- Testar linha sem contrapartida.
- Testar troca correta entre debito e credito.
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
- Sempre: permitir importacao parcial, persistindo linhas validas e registrando warnings para invalidas.
- Sempre: armazenar warnings de linhas invalidas em metadata JSON do lote na primeira fase.
- Sempre: usar `completed_with_warnings` como status de lote quando a importacao persistir linhas validas e registrar warnings.
- Perguntar antes: aceitar layouts muito diferentes do razao lido.
- Perguntar antes: armazenar o arquivo original completo.
- Perguntar antes: persistir linhas sem contrapartida como lancamento incompleto.
- Nunca: assumir que debito sempre significa banco.
- Nunca: usar o arquivo `.xls` ignorado como base desta fase.
- Nunca: persistir como valido lancamento cuja conta de origem ou contrapartida nao exista no catalogo.

## Success Criteria

- Razao `.xlsx` legivel e importado por empresa.
- Lancamentos sao normalizados corretamente.
- Lotes de importacao sao registrados.
- Contas usadas sao vinculadas automaticamente a empresa.
- Reimportacoes nao geram duplicidades indevidas.
- Mesmo arquivo ja importado com sucesso para a mesma empresa e bloqueado por `file_hash`.
- Linhas invalidas geram warnings e nao viram lancamentos validos.
- Contas inexistentes no catalogo impedem persistencia do lancamento como valido.
- Testes cobrem debito, credito, cabecalho, saldo e autorizacao.

## Decisoes Aprovadas

- Apenas arquivos `.xlsx` serao aceitos nesta fase.
- O plano de contas deve estar importado antes da importacao do razao.
- A importacao de razao exige permissao `operacao` ou `admin_empresa` na empresa.
- O lote de importacao armazenara `original_filename`, `file_hash`, usuario, empresa, status, contadores e timestamps.
- Warnings de linhas invalidas serao armazenados em metadata JSON do lote na primeira fase.
- O status de lote para importacao parcial sera `completed_with_warnings`.
- O arquivo original completo nao sera armazenado nesta primeira fase.
- Se o mesmo `file_hash` ja foi importado com sucesso para a mesma empresa, a reimportacao sera bloqueada.
- Arquivos diferentes com lancamentos repetidos usarao deduplicacao por chave composta.
- A chave de deduplicacao sera `empresa_id`, `numero_lancamento`, `data`, `conta_origem`, `conta_contrapartida`, `valor`, `direcao` e `historico_normalizado`.
- Linhas sem contrapartida geram warning e nao sao persistidas como lancamento valido.
- Contas inexistentes no catalogo geram warning/erro e nao sao persistidas como lancamento valido.
- A importacao pode ser parcial: linhas validas entram, linhas invalidas ficam registradas em warnings.
- A decisao de metadata JSON para warnings nao exige armazenar o arquivo original completo.
- Cada lancamento normalizado preserva conta de origem, contrapartida, conta de debito, conta de credito, direcao, historico, valor, data, numero do lancamento e lote.
- Parser e persistencia permanecem separados.
- Contas validas encontradas no razao serao vinculadas automaticamente a empresa.

## Open Questions

- O endpoint de importacao sera sincrono nesta fase ou preparado desde ja para processamento em background?
