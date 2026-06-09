# Spec: Usuarios Internos e Permissoes por Empresa

## Objetivo

Criar autenticacao para usuarios internos e autorizacao por empresa. O sistema sera usado apenas no escritorio, mas cada usuario deve ter identidade propria e acesso restrito as empresas sob sua responsabilidade.

Sucesso significa que usuarios autenticados conseguem operar apenas empresas permitidas, enquanto usuarios sem permissao sao bloqueados em endpoints sensiveis.

## Tech Stack

- FastAPI dependencies para autenticacao e autorizacao.
- SQLAlchemy para usuarios, papeis e vinculos com empresas.
- Pydantic para schemas.
- Hash seguro de senha.
- JWT bearer com access token para autenticacao inicial da API.
- Pytest e FastAPI TestClient para cenarios de API.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`
- Migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`

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
- Testar admin vinculando usuario a empresa.
- Testar usuario sem acesso recebendo bloqueio.
- Testar usuario com acesso importando ou consultando empresa permitida.
- Testar que API keys atuais nao substituem usuario humano nos endpoints internos novos.

## Boundaries

- Sempre: registrar `usuario_id` em acoes sensiveis.
- Sempre: validar permissao por empresa antes de importar, classificar ou alterar feedback.
- Sempre: manter passwords com hash, nunca texto puro.
- Sempre: usar JWT bearer com access token como mecanismo inicial.
- Sempre: validar se usuario continua ativo a cada request autenticada.
- Sempre: criar o primeiro admin por script interno de bootstrap.
- Perguntar antes: adicionar refresh token.
- Perguntar antes: permitir reset de senha ou fluxo de convite.
- Perguntar antes: permitir que contador gerencie permissoes de empresas.
- Nunca: usar senha compartilhada para todos os usuarios.
- Nunca: confiar apenas em rede interna como autenticacao.
- Nunca: permitir que API key substitua usuario humano em endpoints internos novos.

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
- Os papeis globais iniciais serao `admin`, `contador` e `operador`.
- As permissoes por empresa serao `leitura`, `operacao` e `admin_empresa`.
- Apenas `admin` gerencia usuarios e permissoes na primeira versao.
- O primeiro usuario admin sera criado por script interno de bootstrap.
- Senhas devem ser armazenadas apenas com hash seguro.
- Endpoints internos novos exigem JWT.
- API keys permanecem para compatibilidade e integracoes futuras, mas nao substituem usuario humano.
- `usuario_id` deve ser registrado em importacoes, feedbacks e acoes sensiveis.

## Open Questions

- Qual biblioteca JWT/hash sera usada na implementacao?
- Reset de senha sera manual por admin ou tera fluxo proprio em backlog?
- Eventos de login devem entrar ja nesta spec ou ficar na spec de auditoria?
