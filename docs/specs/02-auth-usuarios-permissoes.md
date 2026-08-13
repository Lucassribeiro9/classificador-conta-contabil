# Spec: Usuarios Internos e Permissoes por Empresa

## Objetivo

Criar autenticacao para usuarios internos e autorizacao por empresa. O sistema sera usado apenas no escritorio, mas cada usuario deve ter identidade propria e acesso restrito as empresas sob sua responsabilidade.

Sucesso significa que usuarios autenticados conseguem operar apenas empresas permitidas, enquanto usuarios sem permissao sao bloqueados em endpoints sensiveis.

## Tech Stack

- FastAPI dependencies para autenticacao e autorizacao.
- SQLAlchemy para usuarios, papeis e vinculos com empresas.
- Pydantic para schemas.
- Hash seguro de senha com `pwdlib[argon2]`.
- JWT bearer com access token criado e validado com `PyJWT`.
- Pytest e FastAPI TestClient para cenarios de API.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`
- Migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`
- Bootstrap do primeiro admin: `.\venv\Scripts\python.exe -m scripts.bootstrap_admin --nome "Admin" --login admin --email admin@example.com`

## Project Structure

- `core/models.py`: modelos de usuario e permissao por empresa.
- `api/dependencies.py`: usuario atual e validacao de acesso por empresa.
- `api/schemas.py`: schemas de login, usuario e permissoes.
- `api/routes/`: rotas de auth e administracao de usuarios.
- `tests/`: testes de login, usuario inativo e cross-company.

## Code Style

Dependencias devem deixar a regra de acesso visivel nas rotas.

Exemplo de uso esperado:

```python
@router.post("/companies/{company_id}/imports/ledger")
def import_ledger(
    company: Empresa = Depends(require_company_import_access),
):
    ...
```

## Testing Strategy

- Testar login valido e invalido.
- Testar usuario inativo.
- Testar access token JWT valido, expirado e invalido.
- Testar admin criando usuario.
- Testar admin redefinindo senha manualmente.
- Testar admin vinculando usuario a empresa.
- Testar usuario sem acesso recebendo bloqueio.
- Testar usuario com acesso importando ou consultando empresa permitida.
- Testar que API keys atuais nao substituem usuario humano nos endpoints internos novos.
- Testar matriz endpoint versus credencial nas issues futuras de migracao:
  JWT humano, `X-API-Key`, `X-Admin-Token` e identidade de servico.
- Testar que endpoints novos da Release 1 rejeitam `X-API-Key` como substituto
  de usuario humano.
- Testar que credenciais de integracao futuras respeitam empresas permitidas,
  escopos, revogacao e auditoria.

## Boundaries

- Sempre: registrar `usuario_id` em acoes sensiveis.
- Sempre: validar permissao por empresa antes de importar, classificar ou alterar feedback.
- Sempre: manter passwords com hash, nunca texto puro.
- Sempre: usar JWT bearer com access token como mecanismo inicial.
- Sempre: validar se usuario continua ativo a cada request autenticada.
- Sempre: criar o primeiro admin por script interno de bootstrap.
- Perguntar antes: adicionar refresh token.
- Perguntar antes: adicionar fluxo de reset por token temporario, e-mail ou convite.
- Perguntar antes: permitir que contador gerencie permissoes de empresas.
- Nunca: usar senha compartilhada para todos os usuarios.
- Nunca: confiar apenas em rede interna como autenticacao.
- Nunca: permitir que API key substitua usuario humano em endpoints internos novos.
- Nunca: entregar `X-API-Key`, `X-Admin-Token` ou credencial de servico ao
  navegador.
- Nunca: usar JWT de usuario humano como credencial de integracao n8n.
- Nunca: armazenar segredo de integracao em texto puro ou formato reversivel.
- Sempre: tratar `X-API-Key` e `X-Admin-Token` como mecanismos legados
  temporarios ate migracao explicita.
- Sempre: exigir identidade de servico com empresas e escopos explicitos para
  integracoes novas, como n8n.

## Estrategia para JWT, API Keys, Admin Token e n8n

### Modelo alvo por ator

Usuarios humanos usam login e senha para obter JWT bearer. Depois do login, a
API identifica a pessoa pelo JWT e consulta permissoes por empresa no banco.
Usuario humano logado nao deve usar `X-API-Key` nem `X-Admin-Token`.

Frontend humano:

- usa exclusivamente JWT bearer;
- nunca recebe `X-API-Key`, `X-Admin-Token` ou credencial de servico;
- depende das permissoes por empresa persistidas no banco.

Admin humano:

- usa JWT bearer com papel global `admin` e permissoes aplicaveis;
- nao usa `X-Admin-Token` pelo navegador;
- operacoes administrativas novas devem migrar para dependencias JWT/admin.

Integracoes e n8n:

- nao reutilizam login, senha ou JWT de usuario humano;
- usam identidade de servico futura com empresas permitidas e escopos
  explicitos;
- nao recebem privilegio global por padrao;
- devem ser auditaveis, revogaveis e rotacionaveis.

### Identidade de servico futura

A identidade de servico sera uma entidade propria de integracao, separada de
`Usuario` humano e de `Empresa.api_key`. A implementacao fica para issue futura.

Campos conceituais esperados:

- identificador da integracao;
- nome seguro da integracao;
- empresas permitidas;
- escopos concedidos;
- status ativo/revogado;
- fingerprint ou hash da credencial;
- datas de emissao, rotacao, expiracao opcional e revogacao;
- usuario/admin responsavel pela emissao, rotacao ou revogacao.

A credencial deve ser apresentada ao operador apenas no momento da emissao ou
rotacao. O sistema deve persistir apenas hash/fingerprint, nunca segredo em texto
puro nem valor reversivel.

Escopos conceituais iniciais para n8n:

- `empresas:read`: consultar empresas permitidas e metadados seguros;
- `ml:classificar`: executar classificacao autorizada;
- `movimentos:download`: baixar planilha classificada de lote autorizado;
- `movimentos:feedback`: enviar revisoes em lote ou feedback operacional
  autorizado.

### Compatibilidade temporaria

`X-API-Key` permanece temporariamente para endpoints legados existentes e
integracoes atuais ate que existam endpoints equivalentes com identidade de
servico, testes de autorizacao e workflow n8n migrado.

`X-API-Key` nao deve ser aceito em endpoints internos novos como substituto de
JWT humano. Quando um endpoint novo precisar atender integracao, o contrato alvo
deve prever identidade de servico.

`X-Admin-Token` permanece como mecanismo legado administrativo temporario. Rotas
administrativas novas devem usar JWT admin. Rotas legadas protegidas por
`X-Admin-Token` devem receber decisao futura de migracao para JWT admin,
credencial de servico admin ou descontinuacao.

### Inventario por grupo de rota

Issues futuras devem manter uma matriz por grupo de rota com:

- rota ou grupo de rotas;
- mecanismo atual;
- mecanismo alvo;
- ator permitido;
- empresas/escopos exigidos;
- compatibilidade temporaria;
- criterio de remocao do legado;
- testes esperados.

Grupos iniciais esperados:

- auth e usuario humano: JWT;
- empresas autorizadas e frontend interno: JWT + permissoes por empresa;
- movimentos operacionais novos: JWT humano ou identidade de servico futura;
- download/round-trip da Spec 16: JWT humano ou identidade de servico futura;
- ML/classificacao nova: JWT humano ou identidade de servico futura;
- transacoes legadas: `X-API-Key` temporaria ate migracao;
- administracao legada global: `X-Admin-Token` temporario ate migracao.

### Auditoria, rotacao e revogacao

Acoes de credencial de servico devem gerar auditoria segura:

- emissao;
- uso autorizado;
- tentativa negada;
- rotacao;
- revogacao;
- alteracao de empresas ou escopos.

Auditoria deve registrar integracao, empresa, escopo e acao, sem registrar
segredo, token completo, senha, historico sensivel ou payload bruto.

Rotacao deve permitir janela planejada quando necessario para nao interromper o
workflow n8n. Revogacao deve impedir novos usos da credencial revogada.

### Estrategia incremental de migracao

1. Documentar inventario e matriz de credenciais.
2. Criar modelo e armazenamento seguro para identidade de servico.
3. Criar dependencias de autenticacao/autorizacao para integracoes.
4. Proteger endpoints novos da Release 1 com JWT humano ou identidade de
   servico, conforme ator.
5. Migrar workflow n8n para identidade de servico.
6. Descontinuar `X-API-Key` dos fluxos substituidos.
7. Migrar ou remover rotas administrativas baseadas em `X-Admin-Token`.

## Success Criteria

- Existem usuarios internos individuais.
- Existem papeis basicos como admin, contador e operador.
- Empresas podem ser vinculadas a usuarios.
- Permissoes por empresa suportam leitura, operacao e admin_empresa.
- Endpoints sensiveis validam usuario e empresa.
- Tentativas cross-company sao bloqueadas.
- Testes cobrem usuario inativo, sem permissao e com permissao.

## Decisoes Aprovadas

- A autenticacao inicial sera JWT bearer.
- A primeira versao usara apenas access token, sem refresh token.
- O access token tera expiracao de 12 horas.
- `PyJWT` e `pwdlib[argon2]` sao compativeis com Python 3.12 e FastAPI para esta fase.
- Tokens JWT serao assinados com `PyJWT` usando `HS256` e segredo vindo de variavel de ambiente.
- O access token tera formato bearer e claims minimos: `sub` com o identificador do usuario, `role` com o papel global, `type` com valor `access`, `iat` com emissao e `exp` com expiracao.
- Permissoes por empresa nao serao embutidas no token; devem ser consultadas no banco para evitar autorizacao desatualizada.
- Hash de senha usara `pwdlib[argon2]` com `PasswordHash.recommended()`, armazenando hashes Argon2id.
- Refresh token permanece fora desta fase e deve ser tratado em backlog proprio se necessario.
- Os papeis globais iniciais serao `admin`, `contador` e `operador`.
- As permissoes por empresa serao `leitura`, `operacao` e `admin_empresa`.
- Apenas `admin` gerencia usuarios e permissoes na primeira versao.
- O primeiro usuario admin sera criado por script interno de bootstrap.
- O reset inicial de senha sera manual por usuario `admin` autenticado.
- Reset por token temporario, envio de e-mail ou convite permanece fora desta
  fase e deve ser tratado em backlog proprio se necessario.
- Senhas devem ser armazenadas apenas com hash seguro.
- Endpoints internos novos exigem JWT.
- API keys permanecem para compatibilidade temporaria de endpoints legados e
  integracoes atuais, mas nao substituem usuario humano.
- Usuarios humanos autenticados usam JWT e permissoes por empresa; nao usam
  `X-API-Key` nem `X-Admin-Token`.
- Frontend nunca recebe `X-API-Key`, `X-Admin-Token` ou credencial de servico.
- Integracoes como n8n terao identidade de servico futura, separada de usuario
  humano e de `Empresa.api_key`.
- Identidade de servico futura deve ter empresas permitidas, escopos explicitos,
  auditoria, rotacao e revogacao.
- Escopos iniciais para n8n serao `empresas:read`, `ml:classificar`,
  `movimentos:download` e `movimentos:feedback`.
- `X-Admin-Token` e mecanismo legado administrativo temporario e deve migrar
  para JWT admin, credencial de servico admin ou descontinuacao em issue futura.
- Credenciais de integracao futuras devem ser armazenadas apenas como
  hash/fingerprint, nunca em texto puro ou formato reversivel.
- `usuario_id` deve ser registrado em importacoes, feedbacks e acoes sensiveis
  executadas por usuario humano.
- Acoes de integracao devem registrar identificador da integracao, empresa,
  escopo e acao auditavel sem expor segredo.

## Tarefas e Issues Sugeridas

1. `test(auth): inventariar matriz endpoint versus credencial`
   - Mapear grupos de rota, mecanismo atual, mecanismo alvo e testes esperados.
   - Cobrir JWT, `X-API-Key`, `X-Admin-Token` e identidade de servico futura.

2. `feat(auth): criar modelo de identidade de servico`
   - Persistir integracao, empresas, escopos e fingerprint/hash da credencial.
   - Nao armazenar segredo em texto puro.

3. `feat(auth): emitir, rotacionar e revogar credenciais de servico`
   - Criar fluxo administrativo seguro.
   - Auditar emissao, rotacao e revogacao.

4. `feat(auth): criar dependencias de integracao por escopo e empresa`
   - Validar credencial ativa, empresa permitida e escopo exigido.
   - Retornar erro seguro para credencial invalida ou revogada.

5. `feat(auth): proteger endpoints da Release 1 para usuarios e integracoes`
   - Permitir JWT humano ou identidade de servico conforme contrato.
   - Bloquear `X-API-Key` como substituto humano.

6. `docs(auth): planejar descontinuacao de X-API-Key e X-Admin-Token`
   - Definir endpoints substituidos, condicao de remocao e rollback.
   - Relacionar migracao do workflow n8n.

## Open Questions

- Eventos de login devem entrar ja nesta spec ou ficar na spec de auditoria?
- Os nomes definitivos dos endpoints administrativos de credencial de servico
  serao definidos nas issues de implementacao.
