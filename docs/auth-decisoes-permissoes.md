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

## JWT de usuario e API key de integracao

JWT de usuario representa uma pessoa interna autenticada. Ele deve ser exigido
nos endpoints internos novos que dependem de responsabilidade individual,
permissao por empresa ou registro de `usuario_id`.

API keys permanecem apenas para compatibilidade e integracoes futuras. Elas nao
substituem o JWT de usuario em endpoints internos novos e nao devem conceder
acesso humano a fluxos sensiveis.

## Fora da primeira fase

Refresh token fica fora da primeira versao. A autenticacao inicial permanece
simples, usando apenas access token com expiracao de 12 horas. A necessidade de
refresh token deve ser avaliada em backlog proprio com armazenamento seguro,
revogacao e expiracao definidos antes da implementacao.

Reset de senha tambem fica fora da primeira fase. Qualquer fluxo futuro deve
ser aprovado em issue propria e considerar requisitos de seguranca antes de ser
implementado.

## Cuidados de seguranca

- Nunca documentar tokens reais, senhas reais, hashes reais ou segredos de
  ambiente.
- Nunca registrar senha, token ou API key em log ou auditoria.
- Nunca usar senha compartilhada para usuarios internos.
- Nunca confiar apenas na rede interna como autenticacao.
- Sempre armazenar senhas apenas com hash seguro.
- Sempre validar se o usuario continua ativo em requests autenticadas.
