# Roteiro de Homologacao do Round-trip da Planilha Classificada

Use este roteiro para validar, sem depender da SPA, o fluxo de download,
edicao permitida e reenvio da planilha classificada de movimentos
operacionais.

Contexto canonico:

- Spec: `docs/specs/16-planilha-classificada-feedback-roundtrip.md`
- Issue-pai: #362
- Versionamento e rotas: #417
- Validacao integrada sem frontend: #429
- Estrategia de autenticacao de integracoes: #351

## Regra de seguranca

Execute somente em ambiente controlado de dev ou homologacao. Nao use dados
reais de cliente. Nao registre senhas, tokens, segredos, chaves, documentos
reais, conteudo contabil real ou planilhas integrais nas evidencias.

Nao anexe a planilha inteira como evidencia. Registre apenas identificadores
ficticios, totais, estados, trechos de resposta e prints tratados quando
necessario.

## Pre-condicoes

Antes de iniciar, confirme:

- API e banco apontam para ambiente descartavel ou homologacao controlada;
- existe uma empresa de teste ativa;
- existe usuario com JWT e permissao `operacao` na empresa;
- opcionalmente, existe identidade de servico autorizada para a empresa com
  escopos `movimentos:download` e `movimentos:feedback`;
- existe ao menos um lote operacional importado e classificado;
- quando possivel, ha um lote do layout A e um lote do layout B;
- as contas usadas em `contrapartida_final` existem, sao analiticas, ativas e
  validas para a empresa;
- as evidencias serao tratadas antes de anexar em issue ou PR.

O roteiro vale para os layouts A/B. Quando os dois estiverem disponiveis,
execute o fluxo principal em pelo menos um lote de cada layout.

## Autenticacao

Usuarios humanos usam `JWT` no header `Authorization`.

```bash
curl -X GET "$API_URL/api/v1/companies/$COMPANY_ID/movimentos-operacionais/lotes/$LOTE_ID/planilha-classificada" \
  -H "Authorization: Bearer $JWT_TRATADO"
```

Integracoes autorizadas usam `X-Service-Credential`.

```bash
curl -X GET "$API_URL/api/v1/companies/$COMPANY_ID/movimentos-operacionais/lotes/$LOTE_ID/planilha-classificada" \
  -H "X-Service-Credential: $SERVICE_CREDENTIAL_TRATADA"
```

Nao use `X-API-Key` nem `X-Admin-Token` neste round-trip. Esses mecanismos sao
legados ou administrativos e nao devem validar este fluxo.

## Campos da planilha

### Edicao permitida

Edite somente:

- `decisao_revisao`
- `contrapartida_final`
- `observacao_revisao`

Valores aceitos em `decisao_revisao`:

- vazio: sem alteracao;
- `aprovar`: aprova a sugestao aplicavel;
- `corrigir`: aplica a conta em `contrapartida_final`;
- `rejeitar`: rejeita o movimento sem exigir `contrapartida_final`.

Use `observacao_revisao` para registrar comentario curto e tratado quando
necessario. Nao inclua dados de cliente ou informacoes sensiveis.

### Campos que nao devem ser editados

Nao altere:

- `contrapartida`
- `contrapartida_sugerida`
- `confidence_sugerida`
- `status_atual`
- `mensagem_validacao`
- `saldo_observado_original`
- `saldo_observado_decimal`
- `saldo_calculado_decimal`
- `warnings_saldo`
- `lote_id`
- `movimento_id`
- `linha_original`
- `layout_version`
- `export_revision`
- `row_version`

Atencao: no comportamento atual implementado, alterar campo somente leitura
marca a linha como `invalida`. Para homologacao, considere isso um bloqueio da
linha alterada, mas nao do arquivo inteiro.

## Download

Rota:

GET `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada`

Exemplo sanitizado:

```bash
curl -L "$API_URL/api/v1/companies/$COMPANY_ID/movimentos-operacionais/lotes/$LOTE_ID/planilha-classificada" \
  -H "Authorization: Bearer $JWT_TRATADO" \
  --output planilha-classificada.xlsx
```

Resultado esperado:

- HTTP 200;
- arquivo `.xlsx` baixado;
- aba `Movimentos` presente;
- colunas de controle presentes, incluindo `row_version` e `export_revision`;
- colunas editaveis visiveis;
- campos de entrada, sugestao, validacao e saldo preservados.

## Edicao permitida

Abra a planilha baixada e preencha linhas de teste:

| Cenario | decisao_revisao | contrapartida_final | Resultado esperado |
| --- | --- | --- | --- |
| Aprovacao | `aprovar` | conta sugerida ou final valida | linha `aplicada` |
| Correcao | `corrigir` | conta final valida | linha `aplicada` |
| Rejeicao | `rejeitar` | vazio | linha `aplicada` |
| Sem decisao | vazio | vazio | linha `ignorada` |
| Decisao invalida | valor fora da lista | opcional | linha `invalida` |

Salve o arquivo editado com nome tratado, por exemplo
`roundtrip-hml-feedback.xlsx`.

## Reenvio

Rota:

POST `/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/planilha-classificada/feedback`

Exemplo sanitizado:

```bash
curl -X POST "$API_URL/api/v1/companies/$COMPANY_ID/movimentos-operacionais/lotes/$LOTE_ID/planilha-classificada/feedback" \
  -H "Authorization: Bearer $JWT_TRATADO" \
  -F "file=@roundtrip-hml-feedback.xlsx"
```

Resposta resumida esperada:

```json
{
  "total_linhas": 5,
  "total_aplicado": 3,
  "total_ignorado": 1,
  "total_invalido": 1,
  "total_conflitante": 0,
  "total_nao_autorizado": 0,
  "resultados": [
    {
      "linha_original": 2,
      "movimento_id": 1001,
      "status": "aplicada",
      "mensagem": "Decisao aplicada"
    }
  ]
}
```

Os identificadores acima sao exemplos ficticios. Em evidencias reais, trate os
IDs quando houver risco de exposicao.

## Resultados por linha

- `aplicada`: decisao valida aplicada com sucesso;
- `ignorada`: linha sem nova decisao ou reenvio idempotente;
- `invalida`: decisao, conta, controle ou campo somente leitura invalido;
- `conflitante`: `row_version` da planilha esta desatualizado;
- `nao_autorizada`: linha referencia empresa, lote ou movimento fora do escopo.

O processamento e parcial: linhas invalidas, conflitantes ou nao autorizadas
nao devem impedir a aplicacao das linhas validas do mesmo arquivo.

## Processamento parcial

Para validar processamento parcial:

1. Baixe uma planilha classificada.
2. Preencha uma linha valida de aprovacao.
3. Preencha outra linha com `decisao_revisao` invalida.
4. Reenvie o arquivo.

Resultado esperado:

- HTTP 200;
- a linha valida retorna `aplicada`;
- a linha invalida retorna `invalida`;
- os totais refletem as duas condicoes;
- apenas a linha valida altera o movimento persistido.

## Reenvio idempotente

Para validar reenvio idempotente:

1. Reenvie novamente o mesmo arquivo ja processado.
2. Confira o resumo da resposta.

Resultado esperado:

- HTTP 200;
- decisoes ja aplicadas retornam como `ignorada`;
- eventos decisorios nao sao duplicados;
- o estado final dos movimentos permanece igual.

## Conflito com planilha antiga

Para validar concorrencia por `row_version`:

1. Baixe a planilha classificada.
2. Revise um movimento por outro caminho, como o endpoint individual de review
   ou a tela de revisao quando disponivel.
3. Edite a planilha antiga tentando aplicar decisao diferente para o mesmo
   movimento.
4. Reenvie a planilha antiga.

Resultado esperado:

- a linha alterada retorna `conflitante`;
- a revisao mais recente nao e sobrescrita;
- outras linhas validas do arquivo ainda podem ser processadas.

`export_revision` identifica o download da planilha. `row_version` e o controle
por linha usado para impedir sobrescrita de revisoes recentes.

## Validacao com identidade de servico

Quando houver identidade de servico disponivel:

1. Repita o download com `X-Service-Credential`.
2. Edite somente as colunas permitidas.
3. Reenvie com `X-Service-Credential`.

Resultado esperado:

- download e feedback funcionam sem frontend;
- auditoria identifica ator de servico sem expor a credencial;
- tentativas cross-company ou com escopo insuficiente sao bloqueadas.

## Casos de erro recomendados

Valide ao menos:

| Cenario | Acao | Resultado esperado |
| --- | --- | --- |
| Credencial legada | usar `X-API-Key` ou `X-Admin-Token` | HTTP 401 ou 403 |
| Campo somente leitura alterado | editar `status_atual` ou saldos | linha `invalida` |
| Conta final inexistente | `corrigir` com conta invalida | linha `invalida` |
| Movimento de outro lote | alterar `lote_id` ou `movimento_id` | linha `nao_autorizada` ou `invalida` |
| Planilha antiga | reenviar versao desatualizada | linha `conflitante` |

## Evidencias esperadas

Registre evidencias curtas:

- commit e ambiente usados;
- perfil: usuario JWT ou integracao;
- empresa e lote tratados;
- layout testado: layout A, layout B ou legado;
- rotas chamadas;
- totais da resposta;
- status por linha;
- decisao final da homologacao.

Nao registre:

- planilha inteira;
- senhas, tokens, segredos ou credenciais;
- documentos reais;
- historicos contabeis reais;
- prints com dados de cliente.

## Validacao automatizada relacionada

A issue #429 cobre o consumo sem frontend com teste de integracao
PostgreSQL/API/XLSX. Esse teste automatizado serve como evidencia tecnica
relacionada, mas nao substitui esta homologacao manual.

O homologador nao precisa executar `make test-postgres` para preencher este
roteiro, salvo quando a revisao tecnica do PR exigir.

## Checklist preenchivel

Responsavel pela execucao:

Commit testado:

Ambiente:

Data/hora:

Empresa/lote tratados:

Layout testado:

Perfil usado: JWT / identidade de servico

| Etapa | Status | Evidencia tratada | Observacoes |
| --- | --- | --- | --- |
| Pre-condicoes conferidas |  |  |  |
| Download executado |  |  |  |
| Edicao permitida validada |  |  |  |
| Reenvio executado |  |  |  |
| Aprovacao validada |  |  |  |
| Correcao validada |  |  |  |
| Rejeicao validada |  |  |  |
| Processamento parcial validado |  |  |  |
| Reenvio idempotente validado |  |  |  |
| Planilha antiga/conflito validado |  |  |  |
| Evidencias tratadas |  |  |  |
| Limpeza executada |  |  |  |

Falhas bloqueantes:

- ID:
- Cenario:
- Resultado esperado:
- Resultado observado:
- Evidencia tratada:
- Encaminhamento:

Melhorias futuras:

- ID:
- Impacto:
- Sugestao:

Resultado final: APROVADO / REPROVADO / BLOQUEADO

Responsavel pela decisao:

## Limpeza

Apos a rodada:

1. remova arquivos locais de planilha usados no teste;
2. descarte ou limpe dados ficticios do ambiente, quando aplicavel;
3. remova evidencias brutas que contenham conteudo sensivel;
4. mantenha somente o resumo tratado da homologacao no PR ou issue.
