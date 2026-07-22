# Mapa de Telas e Contratos da API

Documento auxiliar da issue #271 para validar as sete telas do MVP da interface
contra a spec 09, o PRD e os contratos atuais da API antes de implementar
frontend.

Referencias:

- PRD: `docs/prd/evolucao-plano-contas-importacao-ml.md`
- Spec UX: `docs/specs/09-frontend-ux-fluxos.md`
- Spec tecnica frontend: `docs/specs/10-frontend-arquitetura-tecnica.md`
- Figma: https://www.figma.com/design/fgyl1um1G1kxyRvts6Midj/Classificador-cont%C3%A1bil?m=auto&t=6JsEmHJyBD23Ij1y-6

## Decisoes Da Task Review

- O entregavel principal e este documento auxiliar.
- A spec 09 so deve ser atualizada quando uma decisao normativa mudar.
- O mapa lista contratos reais ja existentes e contratos esperados ainda
  ausentes.
- Gaps devem ser registrados sem workaround visual.
- `Razao e Contas Vinculadas` deve considerar paginacao obrigatoria no MVP.
- Novas issues so devem ser abertas quando o gap bloquear uma feature futura ou
  exigir mudanca de API separada.
- A validacao direta do Figma depende de acesso ao arquivo/frame; este documento
  preserva o link e a direcao visual declarada no PRD/spec.

## Estados Obrigatorios

Todas as telas do MVP devem prever, quando aplicavel:

- `carregando`: dados ou acao em andamento.
- `vazio`: nao ha dados para operar.
- `erro de rede`: API indisponivel, timeout ou falha inesperada.
- `acesso negado`: usuario autenticado sem permissao para empresa/recurso.
- `sessao expirada`: token invalido ou expirado, com retorno ao login.

Mensagens devem ser curtas, operacionais e orientadas a proxima acao.

## 1. Login

Responsabilidade: autenticar usuario interno e iniciar sessao da SPA.

Contratos reais:

- `POST /api/v1/auth/login`
  - payload: `login`, `senha`
  - resposta: `access_token`, `token_type`, `expires_in`

Contratos esperados:

- Nenhum contrato adicional para o MVP.
- Nao ha fluxo de "esqueci minha senha" no MVP.

Estados obrigatorios:

- carregando ao enviar credenciais;
- erro de rede;
- sessao expirada quando usuario volta de rota protegida;
- vazio nao se aplica como estado principal;
- acesso negado deve aparecer como credencial invalida ou usuario inativo,
  conforme resposta da API.

Permissoes:

- Qualquer usuario interno ativo pode tentar login.

Gaps:

- A politica final de armazenamento do token pertence a spec tecnica frontend,
  nao a esta issue.

## 2. Empresas

Responsabilidade: exibir empresas operaveis pelo usuario e exigir escolha
consciente do cliente antes da operacao.

Contratos reais:

- `GET /api/v1/companies/authorized`
  - exige JWT bearer;
  - admin global recebe todas as empresas;
  - demais usuarios recebem somente empresas vinculadas, com a permissao efetiva;
  - nao expoe API key.
- `GET /api/v1/companies`
  - contrato administrativo legado com `X-Admin-Token`.
- `GET /api/v1/companies/{company_id}`
  - consulta empresa especifica.

Contratos esperados:

- Nenhum contrato adicional para a listagem inicial de empresas.

Estados obrigatorios:

- carregando lista;
- vazio com orientacao para contato com administrador;
- erro de rede;
- acesso negado;
- sessao expirada.

Permissoes:

- Usuario comum visualiza apenas empresas vinculadas.
- Admin visualiza todas as empresas autorizadas pelo backend.
- UI nao deve inferir permissoes localmente nem exibir empresas fora do retorno
  autorizado.

Gaps:

- O frontend deve adotar o contrato JWT de empresas autorizadas na issue #355.

## 3. Operacao da Empresa

Responsabilidade: funcionar como hub operacional da empresa selecionada.

Dados obrigatorios no MVP:

- identificacao da empresa;
- permissoes do usuario naquela empresa;
- status do dataset/modelo;
- status/resumo do Razao;
- quantidade ou resumo de contas vinculadas;
- resumo de movimentos operacionais por estado quando a API expuser;
- atalhos operacionais para importar movimentos, abrir lotes, revisar
  movimentos, consultar Razao/contas, treinar modelo e classificar quando
  aplicavel.

Dados desejaveis, mas melhoria futura:

- ultimo lote de Razao;
- data da ultima importacao;
- total de lancamentos normalizados;
- total de contas financeiras;
- ultimo lote de movimentos;
- warnings recentes;
- metricas simples de confianca/classificacao.

Contratos reais:

- `GET /api/v1/companies/{company_id}`
- `GET /api/v1/companies/{company_id}/ml/status`
- `GET /api/v1/companies/{company_id}/razao/lotes`
- `GET /api/v1/companies/{company_id}/movimentos-operacionais/lotes`
- `GET /api/v1/plano-contas`

Contratos esperados:

- Endpoint ou composicao de endpoints para resumo operacional da empresa.
- Se nao houver endpoint agregado, a UI pode compor dados reais de endpoints
  existentes, desde que o custo de rede seja aceitavel e o contrato fique
  documentado.

Estados obrigatorios:

- carregando dados do hub;
- vazio quando nao houver Razao, movimentos ou contas vinculadas;
- erro de rede;
- acesso negado;
- sessao expirada.

Permissoes:

- Leitura deve bastar para consultar resumo.
- Acoes como importar, treinar, classificar, aprovar ou rejeitar dependem de
  permissao operacional retornada/validada pela API.

Gaps:

- Falta confirmar endpoint JWT de empresas permitidas.
- Falta confirmar se o hub usara endpoint agregado ou composicao de chamadas.
- Movimentos operacionais por estado podem exigir agregacao especifica se a
  listagem paginada nao for suficiente.

## 4. Importar Movimentos

Responsabilidade: enviar planilha operacional `.xlsx` e mostrar resumo do lote.

Contratos reais:

- `POST /api/v1/companies/{company_id}/movimentos-operacionais/import`
  - upload `.xlsx`
  - resposta: `lote_id`, `status`, `total_linhas`, `total_importadas`,
    `total_invalidas`, `warnings`

Contratos esperados:

- Nenhum contrato adicional para o MVP.

Estados obrigatorios:

- carregando upload/processamento;
- vazio quando nenhum arquivo foi selecionado;
- erro de rede;
- acesso negado;
- sessao expirada;
- importacao concluida;
- importacao com warnings;
- importacao bloqueada.

Permissoes:

- Requer acesso operacional a empresa.

Gaps:

- Confirmar mensagens finais para warnings recuperaveis versus bloqueios.

## 5. Lote de Movimentos

Responsabilidade: listar movimentos de um lote, filtrar e acionar revisao,
aprovacao, rejeicao ou classificacao.

Contratos reais:

- `GET /api/v1/companies/{company_id}/movimentos-operacionais/lotes`
- `GET /api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/movimentos`
- `POST /api/v1/companies/{company_id}/movimentos-operacionais/classificar`
- `POST /api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{movimento_id}/review`

Contratos esperados:

- Acoes em lote devem usar contrato existente ou futuro para aprovacao/rejeicao
  multipla; se o backend aceitar apenas item individual, registrar custo antes
  da tela.
- Filtros por status devem ser suportados pela API ou pela resposta paginada.

Estados obrigatorios:

- carregando lote/movimentos;
- vazio quando lote nao tiver movimentos no filtro;
- erro de rede;
- acesso negado;
- sessao expirada.

Permissoes:

- Leitura para visualizar.
- Operacao para classificar, aprovar, rejeitar ou enviar para revisao.

Gaps:

- Confirmar contrato final de acao em lote.
- Confirmar paginacao e filtros de movimentos quando o volume crescer.

## 6. Revisar Movimento

Responsabilidade: revisar um movimento individual, corrigir conta final,
aprovar ou rejeitar.

Contratos reais:

- `GET /api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/movimentos`
  - hoje serve como fonte para localizar o item dentro do lote.
- `POST /api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/movimentos/{movimento_id}/review`
- `GET /api/v1/plano-contas`

Contratos esperados:

- Endpoint de detalhe individual pode ser desejavel, mas nao e obrigatorio se a
  tela vier da lista do lote com dados suficientes.
- Busca deve priorizar contas vinculadas da empresa e permitir busca no plano
  completo.

Estados obrigatorios:

- carregando movimento/contas;
- vazio quando movimento nao for encontrado ou conta nao tiver resultados;
- erro de rede;
- acesso negado;
- sessao expirada.

Permissoes:

- Operacao para aprovar, corrigir ou rejeitar.
- Leitura pode permitir visualizacao sem acoes finais, se o frontend precisar
  desse modo no futuro.

Gaps:

- Falta endpoint claro para buscar apenas contas vinculadas por empresa.
- Confirmar se selecionar conta ainda nao vinculada exige mensagem especifica
  ou se o backend cria vinculo automaticamente no fluxo.

## 7. Razao e Contas Vinculadas

Responsabilidade: consultar base do Razao e contas usadas pela empresa.

Contratos reais:

- `GET /api/v1/companies/{company_id}/razao/lotes`
- `GET /api/v1/companies/{company_id}/razao/lotes/{lote_id}/lancamentos`
- `GET /api/v1/plano-contas`
- `GET /api/v1/plano-contas/{codigo}`
- `GET /api/v1/plano-contas/id/{conta_id}`

Contratos esperados:

- Listagem de contas vinculadas a empresa, com quantidade de lancamentos e
  ultima utilizacao.
- Busca por codigo ou nome nas contas vinculadas.
- Busca no plano completo quando necessario.
- paginacao obrigatoria para lancamentos do Razao e contas vinculadas.

Estados obrigatorios:

- carregando lotes/lancamentos/contas;
- vazio para empresa sem Razao, lote sem lancamentos ou busca sem resultados;
- erro de rede;
- acesso negado;
- sessao expirada.

Permissoes:

- Leitura deve bastar para consultar Razao e contas vinculadas.

Gaps:

- Falta confirmar endpoint de contas vinculadas por empresa.
- Falta confirmar filtros e paginacao da consulta de contas vinculadas.
- Se a API de plano completo nao representar "contas usadas pela empresa",
  abrir issue de API antes da tela.

## Gaps Consolidados

Gaps que provavelmente bloqueiam features futuras:

1. Contrato de contas vinculadas por empresa com busca e paginacao.
2. Decisao de hub operacional: endpoint agregado ou composicao de endpoints.

Gaps que podem ser registrados como melhoria futura:

1. Endpoint de detalhe individual de movimento operacional.
2. Agregados de ultimo lote, warnings recentes e metricas de confianca.
3. Contrato otimizado para acoes em lote se o backend atual ficar custoso.

## Checklist Para As Proximas Issues De UI

- Confirmar contratos reais antes da implementacao da tela.
- Registrar contratos esperados quando houver gap.
- Nao criar workaround visual para dado que a API nao expoe.
- Cobrir os estados obrigatorios da tela.
- Preservar a direcao visual do Figma e as cores definidas no PRD/spec.
- Nao implementar CRUD administrativo no MVP.
- Nao auto-aprovar sugestoes de ML.
