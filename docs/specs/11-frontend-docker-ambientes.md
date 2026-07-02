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
- `frontend`: build estatico da SPA servido por Nginx ou servico equivalente.
- `postgres`: banco privado.
- `proxy` opcional: roteamento interno entre frontend e API quando necessario.

O frontend nunca deve acessar o banco diretamente.

## Variaveis de Ambiente

Variaveis esperadas:

- URL publica/interna do frontend.
- URL base da API para o frontend.
- `DATABASE_URL` da API.
- segredo JWT da API.
- configuracoes de CORS.
- identificacao do ambiente (`dev`, `hml`, `prod`).

Arquivos `.env` reais nao devem ser versionados. Exemplos devem ficar em arquivos `.env.example` ou documentacao sanitizada.

## CI/CD Inicial

CI esperado:

- testes backend;
- lint/typecheck/build frontend;
- validacao de Docker Compose quando aplicavel.

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
- Sempre: documentar comandos de subida e validacao.
- Perguntar antes: expor ambiente fora da rede do escritorio.
- Perguntar antes: automatizar deploy em producao.
- Nunca: versionar `.env` real.
- Nunca: compartilhar banco entre homologacao e producao.
- Nunca: liberar producao sem validacao minima da homologacao.

## Success Criteria

- Ambientes dev, homologacao e producao estao diferenciados.
- Criterios minimos de homologacao estao definidos.
- Componentes Docker esperados estao documentados.
- Riscos de dados sensiveis e exposicao externa estao mitigados.

## Proximas Issues Recomendadas

1. `chore(devops): definir compose de homologacao`
2. `chore(devops): documentar variaveis de ambiente do frontend`
3. `chore(devops): configurar build do frontend em Docker`
4. `chore(ci): adicionar validacoes do frontend`
5. `docs(devops): documentar deploy interno manual`

## Open Questions

- O frontend sera servido pelo mesmo dominio interno da API ou por host separado?
- Havera proxy reverso unico para `/api` e SPA?
