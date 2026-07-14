# Deploy Interno Manual

Este runbook orquestra o deploy controlado de homologacao e producao no servidor
Ubuntu interno. Os detalhes de cada stack permanecem em `docs/devops-hml.md` e
`docs/devops-prod.md`.

Automacao completa de CD fica fora do MVP. Execute um ambiente por vez e nao
avance enquanto a validacao do ambiente atual estiver incompleta.

## Pre-deploy

- Confirme a branch e o commit aprovado para a liberacao.
- Confirme que o CI da versao esta verde.
- Registre o commit atualmente implantado para eventual rollback.
- Confirme que `.env.hml` e `.env.prod` existem apenas no servidor e nao contem
  placeholders `CHANGE_ME`.
- Confirme backup e procedimento de restauracao quando o deploy envolver
  migrations ou dados reais.

Atualize somente a branch aprovada, sem descartar alteracoes locais:

```bash
git fetch --prune
git switch <branch-aprovada>
git pull --ff-only
git rev-parse HEAD
```

## Deploy de Homologacao

Siga tambem `docs/devops-hml.md`.

```bash
docker compose --env-file .env.hml -f docker-compose.hml.yml config
docker compose --env-file .env.hml -f docker-compose.hml.yml up -d --build
docker compose --env-file .env.hml -f docker-compose.hml.yml ps
```

Conclua as validacoes de homologacao antes de continuar. Homologacao aprovada
antes de producao e um gate obrigatorio.

## Deploy de Producao

Siga tambem `docs/devops-prod.md`. Execute esta etapa somente depois da
aprovacao formal da homologacao.

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml config
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
```

## Validacao Pos-deploy

Confirme primeiro que `postgres`, `api` e `frontend` estao saudaveis no `ps` da
stack implantada. Em uma estacao autorizada e com a CA interna confiavel,
execute as verificacoes do ambiente correspondente:

```bash
curl --fail --show-error --silent https://classificador-hml.interno/api/health
curl --fail --show-error --silent https://classificador-hml.interno/login
curl --fail --show-error --silent https://classificador.interno/api/health
curl --fail --show-error --silent https://classificador.interno/login
```

Execute somente os dois comandos do ambiente implantado. Depois:

- confirme que o `/api/health` informa API e banco online;
- confirme que `/login` retorna a SPA;
- realize login com usuario de teste autorizado para o ambiente;
- confirme que o usuario visualiza apenas as empresas permitidas;
- revise logs curtos caso um healthcheck ou fluxo falhe.

Use o comando de logs do guia especifico do ambiente. Nao libere usuarios
enquanto houver validacao obrigatoria pendente ou falha sem justificativa.

## Evidencias

Registre ao final de cada deploy:

- data, ambiente e responsavel;
- branch e commit implantado;
- commit anterior registrado;
- resultado do CI e da validacao do Compose;
- estado resumido dos containers;
- resultado de `/api/health`, `/login` e do login operacional;
- decisao de liberar, bloquear ou executar rollback.

Nao registre senhas, tokens, segredos, chaves privadas, `.env` real, dados
contabeis reais ou respostas com informacoes sensiveis. Guarde as evidencias no
local controlado definido pela equipe.

## Rollback Manual

Se uma validacao obrigatoria falhar, bloqueie o acesso de usuarios ao ambiente
afetado e retorne ao commit anterior registrado:

```bash
git switch --detach <commit-anterior>
```

Reconstrua somente a stack afetada usando o mesmo arquivo `.env` e o mesmo
comando `up -d --build` documentado acima. Depois, repita toda a validacao
pos-deploy e registre o resultado do rollback.

Nunca remova volumes como tentativa de rollback. Migrations podem nao ser
reversiveis; restauracao do banco exige procedimento aprovado, backup validado
e autorizacao operacional. Depois de estabilizar o ambiente, o responsavel deve
regularizar o checkout para uma branch aprovada, sem reescrever o historico nem
descartar alteracoes locais.
