# Spec: Movimentos Operacionais para Classificacao Contabil

## Objetivo

Criar um fluxo separado para importar movimentos operacionais em `.xlsx`,
classificar contrapartidas com apoio do modelo treinado a partir do Razao
canonico e permitir revisao humana antes de qualquer uso como dado confiavel.

Sucesso significa que planilhas operacionais, OFX ou PDFs futuros possam
convergir para um contrato intermediario sem serem confundidos com o
`LancamentoRazaoNormalizado`, que permanece a fonte canonica contabil.

## Contexto e Premissas

- O Razao importado permanece canonico e usa `LancamentoRazaoNormalizado`.
- O plano de contas ja esta persistido como catalogo do escritorio.
- A importacao do Razao valida CNPJ/CPF contra a empresa selecionada.
- O dataset atual de ML usa o Razao canonico como fonte inicial de treino.
- A primeira fase deste fluxo aceita apenas planilha operacional `.xlsx`.
- OFX, PDF/OCR e exportacao para Dominio ficam fora dessa fase.
- A planilha anexada ao brainstorming e o modelo candidato do layout.
- Apos validacao, o modelo deve ser versionado primeiro em
  `tests/fixtures/modelo_movimentos_operacionais_classificacao.xlsx`.

## Escopo do MVP

- Definir contrato de layout da planilha operacional `.xlsx`.
- Definir lote proprio de importacao operacional.
- Definir entidade intermediaria `MovimentoOperacionalImportado`.
- Validar empresa por CNPJ/CPF da planilha contra empresa selecionada.
- Validar periodo do lote.
- Validar `conta_financeira` e `contrapartida` contra plano de contas.
- Persistir movimentos validos ou recuperaveis para revisao.
- Permitir importacao parcial com warnings por linha.
- Separar pre-classificacao humana, sugestao da ML e decisao final.
- Definir fluxo de classificacao, revisao, aprovacao, correcao e rejeicao.
- Definir regras iniciais de debito/credito a partir do sinal do valor.
- Definir testes esperados e issues derivadas.

## Fora de Escopo

- Importar OFX.
- Interpretar PDF ou OCR.
- Exportar TXT, OFX ou layout para Dominio.
- Criar `LancamentoRazaoNormalizado` a partir de movimento operacional.
- Copiar movimento operacional para `Transacao` legada.
- Gerar treino automaticamente no momento da importacao operacional.
- Auto-aprovar sugestoes da ML.
- Predizer `conta_financeira`.
- Aprovar em lote movimentos que criem vinculos novos de conta por empresa.

## Tech Stack

- `openpyxl` para leitura de `.xlsx`.
- SQLAlchemy para persistencia.
- Alembic para schema.
- FastAPI para endpoints de importacao, consulta, classificacao e revisao.
- Pytest para parser, importador, regras de dominio e API.

## Comandos

- Testes: `./venv/bin/python -m pytest -q tests`
- API local: `./venv/bin/python -m uvicorn api.main:app --reload`
- Migrations: `./venv/bin/python -m alembic upgrade head`

## Project Structure

- `core/`: parser e servicos de importacao/classificacao operacional.
- `core/models.py`: lote operacional e movimento operacional importado.
- `api/routes/`: endpoints de movimentos operacionais.
- `api/schemas.py`: contratos de resposta e payloads.
- `tests/fixtures/`: modelo e fixtures sanitizadas do layout `.xlsx`.
- `tests/`: testes de parser, importacao, validacao, API e ML.

## Contrato do Layout `.xlsx`

O arquivo deve conter uma aba obrigatoria chamada `Movimentos`.

As abas `Instrucoes` e `Exemplos` podem existir como apoio ao usuario, mas nao
sao obrigatorias para a importacao.

O parser deve detectar metadados do lote por rotulo, nao por posicao fixa.

Metadados obrigatorios:

- `CNPJ/CPF`
- `Periodo inicio`
- `Periodo fim`

Metadados auxiliares:

- `Empresa`
- `Codigo dominio`

Regras de metadados:

- `CNPJ/CPF` e normalizado para digitos e comparado com a empresa selecionada.
- CNPJ/CPF divergente bloqueia o lote antes de persistir movimentos.
- `Periodo inicio` e `Periodo fim` sao obrigatorios e devem ser datas validas.
- `Codigo dominio` divergente gera warning de lote, nao bloqueio.
- `Empresa` e informativo e nao deve ser usado como chave forte.

O parser deve detectar a linha de cabecalho pelos nomes das colunas, nao pela
linha fixa do modelo.

Colunas obrigatorias:

- `data`
- `conta_financeira`
- `historico`
- `valor`

Colunas opcionais:

- `contrapartida`
- `tipo_movimento`
- `documento`
- `observacao`

Colunas preenchidas pelo sistema e ignoradas como entrada decisoria:

- `status_sugerido`
- `confidence_sugerida`
- `mensagem_validacao`

## Entidades

### LoteImportacaoMovimentoOperacional

Representa uma importacao operacional de planilha.

Campos conceituais:

- `id`
- `empresa_id`
- `usuario_id`
- `original_filename`
- `file_hash`
- `status`
- `total_linhas`
- `total_importadas`
- `total_invalidas`
- `warnings_metadata`
- `periodo_inicio`
- `periodo_fim`
- `cnpj_cpf_arquivo`
- `codigo_dominio_arquivo`
- `created_at`
- `updated_at`

Status de lote:

- `processing`
- `completed`
- `completed_with_warnings`
- `failed`

Reimportacao:

- mesmo `file_hash` para a mesma empresa com status `completed` ou
  `completed_with_warnings` deve ser bloqueado;
- lote `failed` permite nova tentativa;
- mesmo arquivo para outra empresa so passa se o CNPJ/CPF da planilha
  corresponder a essa empresa.

### MovimentoOperacionalImportado

Representa uma linha operacional importada para classificacao/revisao.

Campos de origem:

- `id`
- `lote_id`
- `empresa_id`
- `data`
- `conta_financeira`
- `historico`
- `historico_normalizado`
- `valor_original`
- `valor_absoluto`
- `direcao` (`debito` ou `credito`)
- `tipo_movimento`
- `documento`
- `observacao`

Campos de classificacao:

- `contrapartida_informada`
- `contrapartida_sugerida`
- `contrapartida_final`
- `confidence_sugerida`
- `status`
- `elegivel_treino`

Campos de validacao:

- `mensagens_validacao`

Campos contabeis finais:

- `conta_debito`
- `conta_credito`

`conta_debito` e `conta_credito` finais so devem ser persistidos quando houver
`contrapartida_final` aprovada ou corrigida por usuario.

## Status do Movimento

- `pendente`: sem contrapartida e ainda sem sugestao.
- `pre_classificado`: veio com contrapartida preenchida na planilha.
- `sugerido`: ML sugeriu contrapartida.
- `revisao`: exige decisao humana antes de seguir.
- `aprovado`: usuario aprovou a classificacao.
- `corrigido`: usuario alterou a classificacao antes de aprovar.
- `rejeitado`: usuario decidiu que a linha nao deve seguir.
- `convertido`: reservado para exportacao/conversao futura.

Somente `aprovado` e `corrigido` podem ser elegiveis para treino futuro.

## Validacoes

### Validacoes de Lote

Bloqueiam o lote antes de persistir movimentos:

- arquivo nao `.xlsx`;
- aba `Movimentos` ausente;
- `CNPJ/CPF` ausente ou divergente da empresa selecionada;
- `Periodo inicio` ausente ou invalido;
- `Periodo fim` ausente ou invalido;
- cabecalho de movimentos sem colunas obrigatorias;
- mesmo `file_hash` ja importado com sucesso total ou parcial para a empresa.

Geram warning de lote:

- `Codigo dominio` preenchido e divergente do cadastro da empresa.

### Validacoes de Linha

Linha invalida, nao persistida como movimento valido:

- `data` ausente ou invalida;
- `conta_financeira` ausente;
- `historico` ausente;
- `valor` ausente, invalido ou igual a zero;
- `conta_financeira` inexistente no plano;
- `conta_financeira` sintetica ou inativa;
- `contrapartida` preenchida, mas inexistente no plano;
- `contrapartida` preenchida, mas sintetica ou inativa.

Linha persistida em `revisao` com warning:

- `data` fora de `periodo_inicio` e `periodo_fim`;
- `conta_financeira` valida no plano, mas nao vinculada a empresa;
- `contrapartida` valida no plano, mas nao vinculada a empresa;
- `tipo_movimento` incoerente com o sinal do valor;
- `tipo_movimento` em `transferencia`, `aplicacao` ou `resgate` sem
  `contrapartida`;
- sugestao da ML com `confidence_sugerida < 0.70`.

Linha persistida como `pre_classificado`:

- `contrapartida` preenchida;
- contas validas no plano;
- sem erro bloqueante;
- aguardando validacao humana.

Linha persistida como `pendente`:

- `contrapartida` vazia;
- campos obrigatorios validos;
- sem regra especial que exija revisao imediata.

## Regras de Valor, Direcao e Debito/Credito

`valor` da planilha usa sinal operacional:

- `valor > 0`: entrada na conta financeira;
- `valor < 0`: saida da conta financeira;
- `valor = 0`: linha invalida.

Campos derivados na importacao:

- `valor_absoluto = abs(valor)`;
- `direcao = debito` quando `valor > 0`;
- `direcao = credito` quando `valor < 0`.

A semantica operacional de entrada ou saida continua derivavel pelo sinal de
`valor_original` quando necessario, mas nao deve ser persistida no campo
`direcao`.

Regra conceitual para par final:

```python
if valor > 0:
    conta_debito = conta_financeira
    conta_credito = contrapartida_final
elif valor < 0:
    conta_debito = contrapartida_final
    conta_credito = conta_financeira
```

O par final so e persistido quando `contrapartida_final` existir por aprovacao
ou correcao humana.

`tipo_movimento` nao altera a regra de debito/credito. Ele serve para revisao,
diagnostico, filtros e feature futura.

Para `transferencia`, `aplicacao` e `resgate`, a `contrapartida` e obrigatoria
para seguir como pre-classificada/aprovavel. Se estiver ausente, o movimento
fica em `revisao` e nao entra no fluxo comum de sugestao da ML no MVP.

## Fluxo de Importacao

1. Usuario seleciona empresa.
2. Usuario envia planilha `.xlsx`.
3. Sistema calcula `file_hash`.
4. Sistema valida metadados do lote.
5. Sistema valida reimportacao.
6. Sistema detecta cabecalho de movimentos.
7. Sistema valida cada linha.
8. Linhas invalidas entram em warnings do lote.
9. Linhas recuperaveis sao persistidas em `revisao`.
10. Linhas com contrapartida valida sao persistidas como `pre_classificado`.
11. Linhas sem contrapartida sao persistidas como `pendente`.
12. Lote recebe `completed`, `completed_with_warnings` ou `failed`.
13. Auditoria registra sucesso, falha ou bloqueio.

Importacao parcial e permitida. Divergencia de CNPJ/CPF e duplicidade de arquivo
continuam bloqueios do lote inteiro.

## Fluxo de Classificacao

Classificacao e acao separada da importacao no MVP.

1. Usuario consulta movimentos pendentes.
2. Usuario dispara classificacao para movimentos `pendente`.
3. Sistema treina/usa modelo baseado no dataset canonico do Razao da empresa.
4. Features iniciais do movimento:
   - `historico_normalizado`;
   - `conta_financeira`;
   - `direcao` (`debito` ou `credito`);
   - `tipo_movimento`, se preenchido.
5. Sistema preenche `contrapartida_sugerida` e `confidence_sugerida`.
6. Se `confidence_sugerida >= 0.70`, status vira `sugerido`.
7. Se `confidence_sugerida < 0.70`, status vira `revisao`.

Fora das features iniciais:

- `valor`;
- `documento`;
- `observacao`;
- `empresa`;
- `codigo_dominio`;
- `cnpj_cpf`.

O modelo nao prediz `conta_financeira` no MVP. A `conta_financeira` e
obrigatoria na planilha.

## Fluxo de Revisao e Aprovacao

Contrapartida preenchida na planilha e pre-classificacao, nao aprovacao.

O usuario pode:

- aprovar movimento individual;
- corrigir contrapartida e aprovar;
- rejeitar movimento;
- aprovar em lote movimentos elegiveis.

Aprovacao individual pode criar vinculo `EmpresaContaContabil` quando a conta
for valida no plano mas ainda nao estiver vinculada a empresa. Essa acao deve
gerar auditoria.

Aprovacao em lote e permitida, mas conservadora.

Pode aprovar em lote:

- `pre_classificado` com contas validas e ja vinculadas;
- `sugerido` com `confidence_sugerida >= 0.70`;
- sem warnings criticos;
- com lista explicita de IDs ou filtro revisavel.

Nao pode aprovar em lote:

- movimentos em `revisao`;
- baixa confianca;
- conta financeira nao vinculada;
- contrapartida nao vinculada;
- movimentos que exigiriam criar vinculo novo;
- linhas com validacao bloqueante.

Aprovacao em lote deve retornar aprovados, ignorados e erros por item.

## Relacao com Treino

Nem toda entrada operacional vira treino.

Regras:

- movimento importado sem contrapartida nao e treino;
- movimento sugerido pela ML nao e treino por si so;
- contrapartida preenchida na planilha nao e treino ate aprovacao;
- movimento `aprovado` ou `corrigido` com `elegivel_treino=True`,
  `contrapartida_final`, `conta_debito` e `conta_credito` preenchidos pode ser
  fonte complementar do dataset de contrapartida;
- movimento pendente, sugerido, em revisao, pre-classificado, rejeitado ou sem
  contas finais nao entra no dataset.

O Razao canonico da empresa permanece a fonte principal do dataset de treino.
Movimentos operacionais aprovados ou corrigidos entram apenas como complemento
controlado apos decisao humana final.

## Auditoria

Eventos sensiveis esperados:

- importacao operacional concluida;
- importacao operacional falhou;
- importacao operacional bloqueada por permissao ou validacao de lote;
- classificacao operacional executada;
- aprovacao individual;
- correcao individual;
- rejeicao;
- aprovacao em lote;
- criacao de vinculo empresa-conta por revisao humana.

Eventos nao devem registrar historicos completos ou documentos sensiveis quando
isso nao for necessario para auditoria.

## Testing Strategy

### Parser/Layout

- Aceita `.xlsx` com aba `Movimentos`.
- Rejeita arquivo sem aba `Movimentos`.
- Detecta metadados por rotulo.
- Rejeita lote sem CNPJ/CPF.
- Rejeita lote sem periodo valido.
- Detecta cabecalho de movimentos pelos nomes das colunas.
- Rejeita layout sem colunas obrigatorias.

### Importador

- Bloqueia CNPJ/CPF divergente.
- Gera warning para `codigo_dominio` divergente.
- Bloqueia reimportacao por `file_hash`.
- Permite importacao parcial.
- Persiste lote com contadores corretos.
- Persiste `pendente`, `pre_classificado` e `revisao` conforme regras.
- Nao persiste linhas com valor zero, conta inexistente, sintetica ou inativa.

### Validacoes de Conta

- `conta_financeira` valida e vinculada segue fluxo normal.
- `conta_financeira` valida nao vinculada vira `revisao`.
- `contrapartida` valida nao vinculada vira `revisao`.
- `contrapartida` sintetica/inativa/inexistente invalida a linha.

### Debito/Credito

- Valor positivo deriva `direcao=debito`.
- Valor negativo deriva `direcao=credito`.
- Features de classificacao usam `direcao_debito` ou `direcao_credito`,
  alinhadas ao dataset canonico do Razao.
- Par debito/credito final so existe apos aprovacao/correcao.

### Classificacao e Revisao

- Classificacao nao roda automaticamente apos importacao.
- Classificacao usa dataset canonico do Razao.
- `confidence < 0.70` gera `revisao`.
- `confidence >= 0.70` gera `sugerido`.
- Aprovacao individual define `contrapartida_final`.
- Correcao define `contrapartida_final` diferente da sugestao/pre-classificacao.
- Aprovacao em lote ignora movimentos nao elegiveis.
- Movimentos aprovados/corrigidos com `elegivel_treino=True` e contas finais
  ficam elegiveis como fonte complementar de treino.

### API e Seguranca

- Usuario sem acesso a empresa nao importa.
- Usuario sem permissao operacional nao aprova/corrige.
- Empresas diferentes nao compartilham movimentos.
- Auditoria e registrada nos eventos sensiveis.

## Boundaries

- Sempre: Razao canonico continua sendo `LancamentoRazaoNormalizado`.
- Sempre: movimento operacional fica em entidade separada.
- Sempre: CNPJ/CPF e validacao forte de empresa.
- Sempre: importacao operacional aceita apenas `.xlsx` no MVP.
- Sempre: `conta_financeira` e obrigatoria.
- Sempre: ML prediz apenas contrapartida no MVP.
- Sempre: `confidence < 0.70` exige revisao.
- Sempre: aprovacao humana define quando um movimento vira confiavel.
- Sempre: somente movimento `aprovado` ou `corrigido`, com
  `elegivel_treino=True`, pode virar fonte complementar do dataset.
- Perguntar antes: criar exportacao para Dominio.
- Perguntar antes: importar OFX/PDF.
- Nunca: transformar movimento operacional automaticamente em Razao canonico.
- Nunca: copiar movimento operacional automaticamente para `Transacao`.
- Nunca: persistir conta sintetica/inativa como classificacao valida.
- Nunca: auto-aprovar sugestao da ML no MVP.

## Success Criteria

- Spec aprovada antes de implementacao.
- Layout `.xlsx` candidato e validado e versionado como fixture antes do parser.
- Entidades de lote e movimento ficam claramente separadas do Razao.
- Regras de validacao distinguem erro bloqueante, warning e revisao.
- Regras de debito/credito dependem do sinal do valor e da contrapartida final.
- Fluxo de ML sugere contrapartida sem auto-aprovar.
- Revisao humana controla aprovacao, correcao, rejeicao e elegibilidade futura
  para treino.
- Tarefas derivadas cabem em PRs pequenos.

## Tarefas e Issues Sugeridas

1. `spec(movimentos): versionar fixture do layout operacional`
   - Copiar modelo validado para `tests/fixtures`.
   - Validar que nao contem dados sensiveis.

2. `feat(movimentos): criar modelos de lote e movimento operacional`
   - Criar `LoteImportacaoMovimentoOperacional`.
   - Criar `MovimentoOperacionalImportado`.
   - Criar migration Alembic.

3. `feat(movimentos): criar parser do layout xlsx operacional`
   - Ler aba `Movimentos`.
   - Extrair metadados e linhas.
   - Cobrir erros de layout.

4. `feat(movimentos): criar servico de importacao operacional`
   - Validar empresa, periodo, contas e file hash.
   - Persistir lote e movimentos.
   - Permitir importacao parcial.

5. `feat(movimentos): criar endpoint de importacao e consulta`
   - Upload `.xlsx`.
   - Consulta de lotes e movimentos por empresa.
   - Permissoes por empresa.

6. `feat(movimentos): classificar movimentos pendentes`
   - Acao separada da importacao.
   - Usar modelo treinado com dataset do Razao.
   - Persistir sugestao, confianca e status.

7. `feat(movimentos): revisar, aprovar, corrigir e rejeitar`
   - Fluxo individual.
   - Criacao de vinculo empresa-conta por decisao humana.
   - Auditoria.

8. `feat(movimentos): aprovacao em lote conservadora`
   - Aprovar apenas movimentos elegiveis.
   - Retornar aprovados, ignorados e erros por item.

9. `backlog(movimentos): incluir aprovados no dataset futuro`
   - Decidir e implementar quando movimentos aprovados entram no treino.

10. `backlog(movimentos): adaptar OFX para contrato operacional`
    - Mapear campos OFX para `MovimentoOperacionalImportado`.

11. `backlog(movimentos): avaliar PDF/OCR`
    - Definir estrategia por banco/layout.

12. `backlog(movimentos): exportar movimentos aprovados para Dominio`
    - Definir formato, validacoes e auditoria.

## Open Questions

- O nome final das rotas deve ser `/movimentos-operacionais` ou outro padrao?
- A permissao para aprovar/corrigir sera `operacao`, `admin_empresa` ou uma
  permissao mais especifica?
- A exclusao de lote operacional deve existir no MVP ou seguir como backlog?
