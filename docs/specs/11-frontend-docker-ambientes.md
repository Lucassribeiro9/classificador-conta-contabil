# Spec: Docker, Ambientes e Deploy Interno do Frontend

## Objetivo

Definir como a aplicacao completa sera executada em ambiente interno com frontend, API e PostgreSQL, separando homologacao e producao desde a primeira rodada de testes com usuarios.

## Ambientes

### Desenvolvimento

- Roda localmente na maquina do desenvolvedor.
- Frontend usa servidor Vite.
- API roda via Uvicorn ou Docker.
- Banco pode usar container local.

### Homologacao

- Ambiente interno separado de producao.
- Banco proprio.
- Variaveis de ambiente proprias.
- Dados ficticios/sanitizados.
- Usado por operador/contador para validar o fluxo real.

### Producao

- Ambiente interno do escritorio.
- Banco proprio.
- Dados reais apenas apos homologacao aprovada.
- Acesso restrito a rede do escritorio ou mecanismo aprovado.

## Componentes Docker Esperados

- `api`: FastAPI.
- `frontend`: build estatico da SPA.
- `postgres`: banco privado.
- `proxy`: Nginx de borda compartilhado para servir a SPA, terminar TLS e
  encaminhar a API.

O frontend nunca deve acessar o banco diretamente.

## Topologia Interna Aprovada

Homologacao e producao rodam no mesmo servidor Ubuntu e usam os seguintes
enderecos internos:

- homologacao: `https://classificador-hml.interno`;
- producao: `https://classificador.interno`.

Um Nginx de borda compartilhado e a unica entrada para os dois ambientes. Ele
roteia por hostname TLS/SNI, serve cada SPA em `/` e encaminha `/api` para a
FastAPI do ambiente correspondente. Ao encaminhar a requisicao, o proxy remove
o prefixo `/api`, preservando os endpoints atuais da API. O fallback da SPA nao
deve capturar chamadas iniciadas por `/api` nem substituir erros da API ou do
proxy.

HTTPS e obrigatorio mesmo na rede interna. Homologacao e producao usam
certificados proprios emitidos por uma autoridade certificadora interna, cuja
raiz deve ser confiavel nas estacoes autorizadas. Chaves privadas e certificados
reais nao devem ser versionados.

O Nginx publica somente as portas `80` e `443` no host. A porta `80` apenas
redireciona para HTTPS. API e PostgreSQL nao publicam portas no host e ficam
acessiveis somente pelas redes Docker necessarias. O firewall do servidor deve
permitir `80` e `443` apenas para sub-redes internas autorizadas. DNS interno
nao substitui essa restricao, nem a autenticacao JWT e a autorizacao por empresa.

Cada ambiente usa projetos Compose, redes, volumes, bancos, certificados e
variaveis separados. O Nginx e o unico componente compartilhado e deve acessar
somente a API de cada rede, sem criar comunicacao direta entre as demais partes
das stacks.

## Variaveis de Ambiente

Variaveis esperadas:

- URL publica/interna do frontend.
- URL base da API para o frontend: `VITE_API_BASE_URL=/api` em homologacao e
  producao.
- `DATABASE_URL` da API.
- segredo JWT da API.
- configuracoes de CORS.
- identificacao do ambiente (`dev`, `hml`, `prod`).

Como frontend e API compartilham a mesma origem em cada ambiente, HML e
producao nao dependem de CORS entre a SPA e a API. CORS fica restrito ao
desenvolvimento local e deve aceitar apenas as origens explicitamente
necessarias.

Arquivos `.env` reais nao devem ser versionados. Exemplos devem ficar em arquivos `.env.example` ou documentacao sanitizada.

## CI/CD Inicial

CI esperado:

- testes backend;
- lint/typecheck/build frontend;
- validacao de Docker Compose quando aplicavel.

Na Release 1, a matriz completa de comandos `dev`, `hml`, `prod` e `all`, os
contratos de `make check` e `make check-full`, o uso de PostgreSQL real e
Playwright relevante em PRs e os limites de producao sao definidos em
`docs/specs/15-harness-qualidade-documentacao.md`.

CD inicial pode ser manual e controlado:

1. atualizar branch aprovada no servidor;
2. revisar variaveis de ambiente;
3. executar build;
4. subir containers;
5. validar `/health` da API;
6. validar tela de login;
7. registrar evidencias.

Automacao completa de deploy fica fora do MVP.

## Criterios para Liberar Homologacao

- Backend tests relevantes verdes.
- Falhas conhecidas da suite backend tratadas ou explicitamente justificadas.
- Frontend com build, typecheck e lint verdes.
- Banco de homologacao separado.
- Massa sanitizada carregada.
- API `/health` respondendo.
- Tela de login acessivel.
- Usuario operador/contador de teste criado.
- Empresas e permissoes de teste configuradas.

## Boundaries

- Sempre: separar homologacao e producao.
- Sempre: usar dados sanitizados em homologacao inicial.
- Sempre: manter banco privado.
- Sempre: exigir HTTPS e restringir o acesso no firewall a rede interna.
- Sempre: documentar comandos de subida e validacao.
- Sempre: alinhar comandos de ambiente e validacao com
  `docs/specs/15-harness-qualidade-documentacao.md`.
- Perguntar antes: expor ambiente fora da rede do escritorio.
- Perguntar antes: automatizar deploy em producao.
- Nunca: versionar `.env` real.
- Nunca: versionar certificados, chaves privadas ou segredos reais.
- Nunca: compartilhar banco entre homologacao e producao.
- Nunca: publicar diretamente as portas da API ou do PostgreSQL.
- Nunca: liberar producao sem validacao minima da homologacao.

## Success Criteria

- Ambientes dev, homologacao e producao estao diferenciados.
- Criterios minimos de homologacao estao definidos.
- Componentes Docker esperados estao documentados.
- Hosts internos, roteamento do proxy, TLS, CORS e portas publicadas estao
  definidos.
- Stacks de homologacao e producao permanecem isoladas apesar do proxy
  compartilhado.
- Riscos de dados sensiveis e exposicao externa estao mitigados.

## Proximas Issues Recomendadas

1. `chore(devops): definir compose de homologacao`
2. `chore(devops): documentar variaveis de ambiente do frontend`
3. `chore(devops): configurar build do frontend em Docker`
4. `chore(ci): adicionar validacoes do frontend`
5. `docs(devops): documentar deploy interno manual`

## Decisoes Aprovadas Apos Task Review #292

- Frontend e API usam a mesma origem em cada ambiente.
- Um Nginx compartilhado roteia os dois hosts internos e é a unica entrada
  publicada.
- A SPA usa `/`, a API usa `/api` e o proxy remove esse prefixo antes de
  encaminhar para a FastAPI.
- HTTPS, certificados da autoridade interna e restricao por firewall sao
  obrigatorios.
- Homologacao e producao compartilham apenas o proxy e mantem suas stacks e
  dados separados.
