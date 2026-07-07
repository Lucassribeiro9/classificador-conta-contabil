# Decisoes de Auth e Formularios do Frontend

Documento auxiliar da Issue #283 para fechar as perguntas abertas da spec
`docs/specs/10-frontend-arquitetura-tecnica.md`, em alinhamento com o PRD
`docs/prd/evolucao-plano-contas-importacao-ml.md`.

## Contexto

O frontend e uma SPA interna que consome a API FastAPI. O login humano usa JWT
bearer emitido pela API, com access token de 12 horas conforme decisoes de
autenticacao ja registradas no backend.

A spec tecnica do frontend deixou duas decisoes abertas:

- onde manter o token JWT no MVP;
- se os formularios iniciais usarao biblioteca ou controle simples em React.

## Decisao

No MVP, o frontend deve persistir o access token JWT em `sessionStorage`.

O token tambem pode ficar refletido no estado React da aplicacao enquanto a SPA
esta aberta. Ao abrir ou recarregar a aba, o estado pode ser reidratado a partir
do `sessionStorage`. Ao sair, ao receber `401` da API ou ao detectar sessao
expirada, o frontend deve limpar estado e `sessionStorage` e voltar para login.

O frontend nao deve usar `localStorage` como persistencia inicial do JWT.

Os formularios iniciais devem usar formularios controlados simples em React,
sem biblioteca de formularios. Bibliotecas como gerenciadores de form ou
validacao externa so devem entrar em issue propria se o MVP revelar formularios
grandes, validacoes compostas ou duplicacao relevante.

## Trade-offs

### Seguranca

Guardar o JWT apenas em memoria reduz persistencia apos um ataque XSS, mas
derruba a sessao em qualquer refresh de pagina. Para a operacao interna, isso
prejudica o fluxo do usuario.

`sessionStorage` equilibra seguranca e UX: o token permanece apenas na aba atual
e e removido ao fechar a aba. Ele ainda pode ser lido por JavaScript em caso de
XSS, portanto o frontend deve continuar evitando HTML inseguro, dados sensiveis
em fixtures e logs com token.

`localStorage` persiste alem da sessao da aba e aumenta a janela de exposicao.
Por isso fica fora do MVP.

### UX

Com `sessionStorage`, refresh da pagina nao exige novo login imediatamente. O
timeout real continua sendo controlado pelo `exp` do JWT emitido pela API. Na
primeira versao, o backend emite access token de 12 horas e nao ha refresh
token.

Quando a API retornar `401`, a UI deve tratar como sessao expirada, limpar o
token e orientar novo login.

### Complexidade

Formularios controlados simples evitam dependencia grande cedo demais. Eles
cobrem o login e os formularios operacionais pequenos do MVP com menos codigo
de infraestrutura e menos superficie de manutencao.

Se houver muitos formularios, validacao condicional complexa ou repeticao
relevante, uma biblioteca pode ser avaliada em issue propria.

## Impactos em Implementacao

- `AuthProvider` deve ser a fronteira de leitura/escrita da sessao no frontend.
- Login bem-sucedido deve gravar sessao em estado React e `sessionStorage`.
- Logout, `401` e sessao expirada devem limpar estado React e `sessionStorage`.
- Rotas protegidas podem reidratar sessao a partir do `sessionStorage`.
- Testes de auth devem cobrir login, refresh com sessao persistida, `401` e
  limpeza de sessao.
- Formularios devem permanecer controlados por estado local enquanto forem
  pequenos e legiveis.

## Fora de Escopo

- Implementar refresh token.
- Persistir JWT em `localStorage`.
- Adicionar biblioteca de formularios.
- Alterar contrato de login da API.
- Mudar expiracao do access token no backend.

## Revisao Futura

Abrir issue propria antes de:

- introduzir refresh token;
- trocar `sessionStorage` por outra estrategia;
- adicionar biblioteca de formularios;
- persistir dados sensiveis alem do token de sessao;
- mudar a duracao do access token.
