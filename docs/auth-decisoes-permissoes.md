# Decisoes de Autenticacao e Permissoes

Este documento resume as decisoes aprovadas na spec
`docs/specs/02-auth-usuarios-permissoes.md` para orientar implementacao e
review das issues de autenticacao. Ele nao substitui a spec; apenas torna as
decisoes operacionais mais faceis de consultar.

## Fluxo de autenticacao humana

Usuarios internos autenticam na API com JWT bearer. A primeira versao usa
apenas access token, com expiracao de 12 horas.

O fluxo esperado e:

1. O usuario informa suas credenciais no endpoint de login.
2. A API valida o usuario ativo e a senha armazenada com hash seguro.
3. A API emite um access token JWT assinado com `HS256`.
4. O cliente envia o token nas proximas chamadas como bearer token.
5. A API valida assinatura, tipo, expiracao e usuario ativo a cada request.

As claims minimas do access token sao:

- `sub`: identificador do usuario.
- `role`: papel global do usuario.
- `type`: valor `access`.
- `iat`: data/hora de emissao.
- `exp`: data/hora de expiracao.

Permissoes por empresa nao ficam embutidas no token. Elas devem ser consultadas
no banco em cada fluxo sensivel para evitar autorizacao desatualizada.

## Papeis globais

Os papeis globais iniciais sao:

- `admin`: gerencia usuarios e permissoes na primeira versao.
- `contador`: opera fluxos contabeis das empresas vinculadas.
- `operador`: executa operacoes permitidas nas empresas vinculadas.

Somente `admin` gerencia usuarios e permissoes nesta fase.

## Permissoes por empresa

O acesso operacional e limitado pelas empresas vinculadas a cada usuario. As
permissoes iniciais por empresa sao:

- `leitura`: permite consultar dados da empresa quando o endpoint exigir acesso
  de leitura.
- `operacao`: permite executar acoes operacionais da empresa, como importacoes
  e classificacoes quando esses fluxos estiverem disponiveis.
- `admin_empresa`: reserva acoes administrativas por empresa quando esse nivel
  for necessario.

Endpoints sensiveis devem validar primeiro o usuario autenticado e depois a
permissao exigida para a empresa alvo. Tentativas cross-company devem ser
bloqueadas.

## JWT de usuario

JWT de usuario representa uma pessoa interna autenticada. Ele deve ser exigido
nos endpoints internos novos que dependem de responsabilidade individual,
permissao por empresa ou registro de `usuario_id`.

Depois do login, usuario nao deve usar `X-API-Key` nem `X-Admin-Token`.
Admin tambem usa JWT, com papel global e permissoes adequadas.

O frontend usa exclusivamente JWT e nunca deve receber API key, admin token ou
credencial de servico.

## Integracoes e n8n

Integracoes como n8n nao devem reutilizar login, senha ou JWT de usuario humano.
O modelo alvo e uma identidade de servico futura, separada de `Usuario` humano e
de `Empresa.api_key`.

A identidade de servico deve ter:

- empresas permitidas;
- escopos explicitos;
- status ativo ou revogado;
- fingerprint/hash da credencial;
- auditoria de emissao, uso, rotacao e revogacao.

Escopos conceituais iniciais para n8n:

- `empresas:read`;
- `ml:classificar`;
- `movimentos:download`;
- `movimentos:feedback`.

Credenciais de servico devem ser armazenadas apenas como hash/fingerprint. O
segredo nao deve ser persistido em texto puro nem em formato reversivel.

## API key e admin token legados

`X-API-Key` permanece temporariamente para endpoints legados existentes e
integracoes atuais ate que existam endpoints equivalentes com identidade de
servico, testes de autorizacao e workflow n8n migrado.

`X-API-Key` nao substitui JWT humano e nao deve ser aceita em endpoints internos
novos como atalho de autenticacao humana.

`X-Admin-Token` permanece como mecanismo administrativo legado temporario. Rotas
administrativas novas devem usar JWT admin. Rotas legadas devem migrar em issue
futura para JWT admin, credencial de servico admin ou descontinuacao.

## Matriz de credenciais

Issues futuras devem manter matriz por grupo de rota com:

- mecanismo atual;
- mecanismo alvo;
- ator permitido;
- empresas e escopos exigidos;
- compatibilidade temporaria;
- criterio de remocao do legado;
- testes esperados.

Grupos iniciais:

- auth e usuarios humanos: JWT;
- frontend interno e empresas autorizadas: JWT + permissao por empresa;
- movimentos operacionais novos: JWT humano ou identidade de servico futura;
- planilha classificada e feedback round-trip: JWT humano ou identidade de
  servico futura;
- ML/classificacao nova: JWT humano ou identidade de servico futura;
- transacoes legadas: `X-API-Key` temporaria;
- administracao legada global: `X-Admin-Token` temporario.

## Fora da primeira fase

Refresh token fica fora da primeira versao. A autenticacao inicial permanece
simples, usando apenas access token com expiracao de 12 horas. A necessidade de
refresh token deve ser avaliada em backlog proprio com armazenamento seguro,
revogacao e expiracao definidos antes da implementacao.

Reset de senha tambem fica fora da primeira fase. Qualquer fluxo futuro deve
ser aprovado em issue propria e considerar requisitos de seguranca antes de ser
implementado.

A implementacao de identidade de servico, rotacao e revogacao tambem fica para
issues futuras. Esta decisao documental define o contrato alvo.

## Cuidados de seguranca

- Nunca documentar tokens reais, senhas reais, hashes reais ou segredos de
  ambiente.
- Nunca registrar senha, token completo, API key ou segredo em log ou auditoria.
- Nunca usar senha compartilhada para usuarios internos.
- Nunca confiar apenas na rede interna como autenticacao.
- Nunca entregar API key, admin token ou credencial de servico ao navegador.
- Nunca usar JWT de usuario para automacao n8n.
- Sempre armazenar senhas apenas com hash seguro.
- Sempre validar se o usuario continua ativo em requests autenticadas.
- Sempre auditar uso, rotacao e revogacao de credenciais de integracao sem
  expor segredo.
