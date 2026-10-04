# Operacao em Rede Interna

Este documento registra as premissas operacionais da aplicacao contabil em rede
interna, conforme o PRD
`docs/prd/evolucao-plano-contas-importacao-ml.md` e a spec
`docs/specs/07-auditoria-seguranca-operacional.md`.

A primeira entrega deve rodar no servidor Ubuntu do escritorio, com Docker, sem
exposicao publica permanente da aplicacao contabil ou do banco PostgreSQL.

## Modelo de acesso interno

A aplicacao e destinada a usuarios internos do escritorio. O acesso deve partir
da rede do escritorio ou de um caminho operacional controlado pela equipe
responsavel pela infraestrutura.

Rede interna nao substitui autenticacao. Endpoints internos novos devem exigir
usuario autenticado, validar usuario ativo e respeitar permissoes por empresa.
Credenciais compartilhadas nao devem ser usadas para acesso humano.

## Acesso da aplicacao

A API pode ser publicada no host Docker para consumo dentro da rede interna do
escritorio. Qualquer publicacao de porta deve considerar o escopo da rede onde o
servidor esta conectado.

Na primeira fase:

- nao exponha a aplicacao contabil diretamente para a internet;
- nao use Streamlit Community Cloud para dados contabeis internos;
- nao mantenha tunel publico permanente via ngrok para a aplicacao contabil;
- nao trate um tunel temporario de teste como solucao operacional;
- mantenha login individual mesmo quando o acesso vier da rede interna.

Se for necessario usar tunel temporario para diagnostico, ele deve ser pontual,
acompanhado por responsavel tecnico e removido ao fim do teste. Essa excecao
nao muda a decisao de produto de manter a aplicacao restrita ao escritorio.

## Acesso ao banco PostgreSQL

O PostgreSQL e o banco operacional alvo e deve permanecer privado ao ambiente
da aplicacao. O banco nao deve ter porta publicada para acesso externo.

No Docker Compose atual, o servico `postgres` participa da rede Docker e nao
declara `ports`. Essa e a postura esperada: a API acessa o banco pelo
`DATABASE_URL` interno, e usuarios finais nao acessam o PostgreSQL diretamente.

Regras operacionais:

- nao publique a porta `5432` para a internet;
- nao libere acesso direto ao banco para estacoes de trabalho sem necessidade
  operacional clara;
- nao use credenciais do banco em ferramentas de usuario final;
- rode migrations, importacoes e backups a partir de ambiente controlado;
- mantenha dumps fora do repositorio.

## n8n e ngrok

O n8n fica fora do caminho critico da primeira entrega da aplicacao contabil.
Configuracoes de n8n ou ngrok usadas para testes nao devem ser interpretadas
como autorizacao para expor a API contabil publicamente.

Quando houver ngrok no ambiente local ou de teste:

- use apenas para fluxos temporarios e controlados;
- nao aponte webhooks publicos permanentes para a aplicacao contabil;
- nao publique tokens de ngrok no repositorio;
- revise variaveis como `WEBHOOK_URL` antes de reutilizar `.env` entre
  ambientes.

## Variaveis de ambiente

Use `.env.example` apenas como referencia de nomes e valores ficticios. O
arquivo `.env` real deve permanecer fora do versionamento.

Cuidados minimos:

- defina `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD`
  por ambiente;
- use `JWT_SECRET_KEY`, `ADMIN_TOKEN` e `NGROK_AUTH_TOKEN` reais apenas em
  ambiente protegido;
- nao reutilize segredos de desenvolvimento em ambiente com dados reais;
- nao registre segredos em logs, auditoria, prints ou documentos de PR;
- troque segredos se houver suspeita de exposicao.

## Backups

Antes de migrations, importacoes relevantes ou operacoes com dados reais, gere
backup do PostgreSQL conforme `docs/postgresql-operacao.md`.

Backups podem conter dados contabeis, chaves de API e outras informacoes
sensiveis. Por isso:

- nao committe arquivos de backup;
- nao armazene dumps em diretorios sincronizados sem controle;
- copie dumps para local seguro fora do container;
- valide restauracao apenas em ambiente controlado;
- trate automacao, criptografia, retencao e teste recorrente de restore em
  issue propria antes de uso operacional recorrente.

## Logs tecnicos

API e `razao-worker` gravam diagnósticos em JSONL em volumes separados por
serviço, no diretório configurado por `TECHNICAL_LOG_DIR`. O arquivo da API é
`api.jsonl` e o do worker é `razao-worker.jsonl`. A rotação ocorre diariamente,
em UTC, com retenção inicial de 30 arquivos rotacionados (30 dias).

Os campos técnicos permitidos são timestamp, nível, logger, evento, mensagem
sanitizada, `request_id`, método, rota, status HTTP, duração, tipo de erro e
serviço. Senhas, tokens, API keys, credenciais, headers, query strings, corpos,
respostas completas, planilhas e dados contábeis não devem ser registrados.
`audit_events` continua sendo a trilha persistente de auditoria e não é
redirecionado para esses arquivos.

Falha de escrita ou rotação do log técnico é best-effort: não deve invalidar a
operação de negócio. O acesso aos arquivos deve permanecer restrito ao
ambiente operacional; não copie logs brutos para issues, PRs ou documentos.

Para diagnóstico, consulte apenas trechos sanitizados no container do serviço
correspondente e preserve os arquivos nos volumes dedicados. A limpeza e a
retenção da auditoria não fazem parte desta configuração.

## Checklist operacional minimo

Antes de operar com dados reais, confirme:

- a aplicacao contabil esta acessivel apenas pelo caminho interno aprovado;
- o PostgreSQL nao possui porta publica exposta;
- `.env` real nao foi versionado;
- segredos de desenvolvimento foram substituidos;
- backups recentes existem e nao estao no repositorio;
- usuarios acessam com identidade propria;
- permissoes por empresa foram configuradas;
- ngrok, se usado, e temporario e nao aponta para exposicao permanente da API.
