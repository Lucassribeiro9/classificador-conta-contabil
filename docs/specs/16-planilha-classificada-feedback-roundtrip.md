# Spec: Planilha Classificada e Feedback Round-trip

## Objetivo

Definir o contrato para baixar a planilha classificada de movimentos
operacionais e importar revisoes em lote pelo proprio arquivo, preservando o
fluxo individual do frontend e permitindo consumo por integracoes sem depender
do frontend.

Sucesso significa que o sistema consegue reconstruir o estado atual de um lote,
expor sugestoes e decisoes humanas de forma auditavel, receber correcoes em lote
com processamento parcial e impedir que arquivos desatualizados sobrescrevam
revisoes recentes.

## Contexto e Premissas

- Esta spec pertence ao Ciclo 2 da Release 1, rastreado pela issue #362.
- A issue #366 cria apenas esta spec; implementacao fica para issues futuras.
- O contrato dos movimentos operacionais e dos dois layouts oficiais esta na
  Spec 08.
- O download deve usar o mesmo layout/versionamento do lote importado.
- O arquivo deve ser reconstruido a partir dos templates oficiais e dos dados
  persistidos, sem depender do binario original enviado pelo usuario.
- A decisao de autenticacao de integracoes e n8n fica na issue #351. Esta spec
  apenas exige identidade de servico autorizada, sem expor segredo ao frontend.
- O endpoint individual de revisao permanece valido e deve compartilhar a mesma
  regra de dominio usada pelo round-trip.

## Fora de Escopo

- Implementar endpoints, geracao Excel, parser de feedback ou migrations.
- Armazenar o arquivo original enviado pelo usuario.
- Alterar sugestao, confianca ou status sugerido por reimportacao.
- Adaptar o workflow n8n nesta issue.
- Resolver a estrategia final de autenticacao da #351.
- PDF, OFX e layout Dominio.
- Autoaprovar classificacoes por confianca.
- Alterar o frontend nesta spec.

## Tech Stack Esperada

- `openpyxl` para geracao e leitura de `.xlsx` em issues futuras.
- FastAPI para endpoints de download e importacao de feedback.
- SQLAlchemy para consulta de lotes, movimentos, versoes e auditoria.
- Pytest para servicos, regras de dominio, API, concorrencia e idempotencia.

## Project Structure Esperada

- `core/`: servicos de exportacao, importacao de feedback e regra compartilhada
  de revisao.
- `api/routes/`: endpoints de download e round-trip de movimentos operacionais.
- `api/schemas.py`: contratos de resposta, resumo e resultado por linha.
- `tests/fixtures/`: templates oficiais e arquivos de feedback sanitizados.
- `tests/`: testes de Excel, API, autorizacao, idempotencia, concorrencia e
  auditoria.

## Contrato de Download

O download deve representar o estado atual do lote no momento da exportacao. Um
unico arquivo pode conter linhas preliminares e finais.

Regras:

- reconstruir a planilha a partir dos templates oficiais e dados persistidos;
- nao depender de armazenar nem reler o binario original;
- usar o mesmo `layout_version` do lote importado;
- preservar ordem das linhas e identificadores dos movimentos;
- preservar as colunas originais do layout do lote;
- adicionar colunas de sistema para classificacao, revisao, validacao e saldos;
- limitar o download a usuarios ou integracoes autorizadas para a empresa e o
  lote.

### Identificacao e Versao

Colunas de controle esperadas no arquivo exportado:

- `lote_id`
- `movimento_id`
- `linha_original`
- `layout_version`
- `export_revision`
- `row_version` ou `updated_at`

`export_revision` identifica a versao logica da exportacao. `row_version` ou
`updated_at` representa a versao esperada da linha no momento do download e deve
ser usado para concorrencia otimista na importacao de feedback.

### Colunas de Classificacao e Revisao

Colunas de entrada imutaveis:

- `contrapartida`

Colunas de sistema somente leitura:

- `contrapartida_sugerida`
- `confidence_sugerida`
- `status_atual`
- `mensagem_validacao`
- `saldo_observado_original`
- `saldo_observado_decimal`
- `saldo_calculado_decimal`
- `warnings_saldo`

Colunas editaveis pelo usuario ou integracao:

- `decisao_revisao`
- `contrapartida_final`
- `observacao_revisao`

Valores permitidos para `decisao_revisao`:

- vazio: sem alteracao;
- `aprovar`: aprova a classificacao aplicavel;
- `corrigir`: aplica `contrapartida_final` informada;
- `rejeitar`: rejeita o movimento.

`contrapartida_final` vazia significa sem alteracao, exceto quando
`decisao_revisao=rejeitar`. Para `corrigir`, `contrapartida_final` e obrigatoria
e deve ser validada contra o plano de contas e as regras de empresa.

`contrapartida_sugerida`, `confidence_sugerida`, `status_atual`, saldos e
mensagens de validacao nao podem ser aceitos como feedback humano nem
sobrescritos pelo arquivo.

## Contrato de Importacao do Round-trip

A importacao de revisoes deve ocorrer em endpoint separado do endpoint individual
de revisao. O endpoint individual permanece como contrato para o frontend e ambos
devem chamar a mesma regra de dominio item a item.

Regras:

- validar empresa, lote, permissao e identidade autenticada;
- validar que o arquivo pertence ao lote informado;
- processar linhas de forma parcial;
- aplicar apenas decisoes validas e autorizadas;
- retornar resultado por linha;
- registrar auditoria de importacao, aplicacoes, rejeicoes e conflitos;
- nao alterar sugestao, confianca ou campos somente leitura;
- nao sobrescrever revisao mais recente quando a linha estiver desatualizada.

### Resultado por Linha

A resposta da importacao deve permitir classificar cada linha como:

- `aplicada`: decisao aplicada com sucesso;
- `ignorada`: linha sem decisao nova ou reenvio idempotente;
- `invalida`: linha com erro de formato, conta invalida ou decisao incoerente;
- `conflitante`: linha desatualizada em relacao ao estado persistido;
- `nao_autorizada`: linha fora do escopo de empresa/lote permitido.

Resumo esperado:

- total de linhas lidas;
- total aplicado;
- total ignorado;
- total invalido;
- total conflitante;
- total nao autorizado;
- lista de resultados por linha com `linha_original`, `movimento_id`, status e
  mensagem segura.

## Concorrencia Otimista

A importacao deve comparar a versao esperada do arquivo com a versao persistida
do movimento.

Chaves esperadas:

- `lote_id`
- `movimento_id`
- `row_version` ou `updated_at`
- `export_revision`

Se o movimento tiver sido alterado apos a exportacao, a linha deve retornar
`conflitante` e nao deve sobrescrever a revisao mais recente.

A concorrencia e por linha. Conflitos em algumas linhas nao bloqueiam a
aplicacao de outras linhas validas do arquivo.

## Idempotencia

Reenvios do mesmo feedback nao devem duplicar eventos decisorios nem alterar
novamente o estado quando a decisao ja tiver sido aplicada.

A chave idempotente conceitual deve derivar de:

- `lote_id`
- `movimento_id`
- `decisao_revisao`
- `contrapartida_final`
- versao esperada da linha

Quando a mesma decisao for reenviada contra a mesma versao ja processada, a linha
deve retornar `ignorada` com mensagem segura de reenvio idempotente.

## Regra de Dominio Compartilhada

A decisao de revisao deve ser centralizada em uma regra de dominio reutilizada
por:

- endpoint individual do frontend;
- endpoint de importacao round-trip;
- integracoes autorizadas.

A regra compartilhada deve validar, no minimo:

- permissao por empresa;
- existencia do lote e movimento;
- status atual do movimento;
- decisao solicitada;
- obrigatoriedade de `contrapartida_final` em correcao;
- validade, analiticidade, atividade e vinculo da conta;
- elegibilidade para treino quando a decisao final permitir;
- auditoria da decisao humana.

## Autenticacao, Autorizacao e Auditoria

Usuarios devem usar JWT e permissoes por empresa. Integracoes devem usar
a estrategia definida pela #351, com identidade de servico e escopos explicitos.
Nenhuma API key, admin token ou segredo de integracao deve ser exposto ao
frontend ou versionado no repositorio.

Acoes auditaveis esperadas:

- geracao/download da planilha classificada;
- importacao de arquivo de feedback;
- decisao aplicada por linha;
- linha invalida, conflitante ou nao autorizada;
- tentativa cross-company ou lote inexistente.

Eventos de auditoria nao devem registrar historicos completos, documentos
sensiveis, segredos ou dados de outra empresa.

## Testing Strategy

### Download e Excel

- Gerar arquivo a partir do lote sem depender do binario original.
- Preservar ordem das linhas e `movimento_id`.
- Usar o mesmo `layout_version` do lote.
- Exportar layout A e layout B com colunas equivalentes de classificacao.
- Manter `contrapartida` imutavel.
- Expor `contrapartida_sugerida`, confianca, status, validacao e saldos como
  leitura.

### Round-trip e Processamento Parcial

- Aplicar linha valida de aprovacao.
- Aplicar linha valida de correcao com `contrapartida_final`.
- Aplicar rejeicao sem exigir `contrapartida_final`.
- Ignorar linha sem `decisao_revisao`.
- Retornar erro por linha com decisao invalida.
- Retornar erro por linha com conta inexistente, sintetica, inativa ou fora da
  empresa.
- Processar linhas validas mesmo quando outras linhas forem invalidas.

### Concorrencia e Idempotencia

- Rejeitar como `conflitante` linha com `row_version` ou `updated_at`
  desatualizado.
- Nao bloquear outras linhas quando houver conflito parcial.
- Reenviar a mesma decisao sem duplicar feedback nem auditoria decisoria.
- Reenviar decisao diferente contra versao antiga como conflito.

### Autorizacao e Auditoria

- Bloquear download sem acesso a empresa/lote.
- Bloquear importacao de feedback sem permissao operacional.
- Bloquear arquivo que tente referenciar movimento de outra empresa.
- Registrar auditoria de download, importacao e decisao aplicada.
- Nao retornar segredos nem dados de outra empresa.

### Consumo sem Frontend

- Permitir que cliente autorizado consuma download e round-trip sem depender de
  fluxo de tela.
- Manter o contrato compativel com integracao n8n futura apos decisao #351.

## Boundaries

- Sempre: reconstruir a planilha a partir de templates e dados persistidos.
- Sempre: usar o mesmo layout/versionamento do lote importado.
- Sempre: preservar ordem e identificadores das linhas.
- Sempre: manter `contrapartida` de entrada imutavel.
- Sempre: separar sugestao, confianca e decisao humana final.
- Sempre: tratar sugestao, confianca, saldos e validacoes como leitura no
  round-trip.
- Sempre: processar feedback em lote com resultado por linha.
- Sempre: usar concorrencia otimista para impedir sobrescrita de revisao recente.
- Sempre: tornar reenvio idempotente.
- Sempre: compartilhar regra de dominio com o endpoint individual.
- Sempre: validar isolamento por empresa e registrar auditoria segura.
- Perguntar antes: armazenar binario original.
- Perguntar antes: permitir edicao de campos do sistema pelo arquivo.
- Perguntar antes: bloquear o arquivo inteiro por uma linha invalida.
- Nunca: aceitar `contrapartida_sugerida` ou `confidence_sugerida` como feedback
  humano.
- Nunca: sobrescrever revisao mais recente com planilha antiga.
- Nunca: expor segredo, credencial, ID real sensivel ou dado de outra empresa.
- Nunca: autoaprovar por confianca.

## Success Criteria

- Spec criada e aprovada antes de implementacao.
- Download e round-trip possuem contratos separados e completos.
- Arquivo exportado nao depende do binario original.
- Ambos os layouts oficiais podem gerar saida equivalente.
- Campos editaveis e somente leitura estao definidos.
- `contrapartida` original permanece imutavel.
- Sugestao e confianca nao podem ser alteradas por reimportacao.
- Processamento parcial retorna resultado por linha.
- Concorrencia otimista e idempotencia estao definidas.
- Frontend, arquivo e integracao compartilham a mesma regra de dominio.
- Regras de acesso por empresa e auditoria estao definidas.
- A dependencia da #351 esta explicita sem decidir credenciais nesta spec.
- Tarefas futuras cabem em PRs pequenos.

## Tarefas e Issues Sugeridas

1. `feat(exportacao): gerar planilha classificada por layout do lote`
   - Reconstruir arquivo a partir dos templates e dados persistidos.
   - Preservar ordem, identificadores e `layout_version`.
   - Cobrir layout A, layout B e legado.

2. `feat(exportacao): expor endpoint autenticado de download`
   - Validar empresa, lote, usuario/integracao e permissao.
   - Retornar arquivo do estado atual com auditoria segura.

3. `feat(feedback): criar regra compartilhada de revisao operacional`
   - Reutilizar a mesma regra para endpoint individual e round-trip.
   - Validar decisao, contrapartida final, status e conta por empresa.

4. `feat(feedback): importar revisoes em lote por planilha`
   - Ler arquivo retornado pelo sistema.
   - Aplicar processamento parcial com resultado por linha.
   - Preservar campos somente leitura.

5. `feat(feedback): implementar concorrencia otimista no round-trip`
   - Validar `row_version` ou `updated_at` e `export_revision`.
   - Retornar conflitos por linha sem bloquear linhas validas.

6. `feat(feedback): implementar idempotencia de reenvio`
   - Detectar decisao ja aplicada contra a mesma versao.
   - Evitar duplicidade de feedback e auditoria decisoria.

7. `test(exportacao): cobrir consumo sem frontend`
   - Validar fluxo por API para integracao autorizada.
   - Manter #351 como dependencia para credencial final.

8. `docs(exportacao): documentar roteiro manual do round-trip`
   - Descrever download, edicao permitida, reenvio, conflitos e evidencias de
     homologacao.

## Open Questions

- A estrategia final de credencial de integracao depende da issue #351.
- O nome definitivo dos endpoints deve ser confirmado nas issues de implementacao
  para manter consistencia com as rotas existentes.
