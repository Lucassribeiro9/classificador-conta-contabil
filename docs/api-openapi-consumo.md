# API, OpenAPI e exemplos de consumo

OpenAPI e a fonte canonica para consumo dos endpoints da API. Esta documentacao
explica fluxos, autenticacao e exemplos sanitizados, mas nao substitui o schema
exposto pela aplicacao FastAPI.

## Fonte canonica

Em ambiente local, com a API em execucao, consulte:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Schema OpenAPI: `http://localhost:8000/openapi.json`

Para validar o schema sem subir servidor HTTP, use o app FastAPI diretamente:

```bash
./venv/bin/python - <<'PY'
from api.main import app
schema = app.openapi()
print(schema["openapi"])
print(schema["info"]["title"])
print(len(schema["paths"]))
PY
```

O teste documental focado e:

```bash
./venv/bin/pytest tests/test_openapi_contract.py
```

## Autenticacao e credenciais

A estrategia vigente esta documentada em `docs/specs/02-auth-usuarios-permissoes.md`
e `docs/auth-decisoes-permissoes.md`.

Resumo operacional:

- usuarios humanos usam login/senha e JWT bearer;
- permissoes por empresa sao consultadas no banco;
- frontend nunca recebe `X-API-Key`, `X-Admin-Token` ou credencial de servico;
- `X-API-Key` permanece apenas para endpoints legados enquanto houver
  compatibilidade;
- `X-Admin-Token` permanece apenas para rotas administrativas legadas;
- n8n e integracoes futuras devem usar identidade de servico com empresas e
  escopos explicitos, conforme #351.

Exemplo de login:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login":"operador.demo","senha":"senha-ficticia"}'
```

Resposta esperada, com token ficticio:

```json
{
  "access_token": "<JWT_DE_USUARIO>",
  "token_type": "bearer"
}
```

Exemplo de chamada autenticada com JWT:

```bash
curl -sS "http://localhost:8000/api/v1/companies/authorized" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

## Fluxos principais existentes

### Health

```bash
curl -sS "http://localhost:8000/health"
```

Resposta típica:

```json
{
  "status": "online",
  "database": "online",
  "api_version": "v1",
  "env": "desenvolvimento"
}
```

### Empresas autorizadas

Use JWT humano. Este fluxo e a base do frontend interno para listar empresas
permitidas ao usuario autenticado.

```bash
curl -sS "http://localhost:8000/api/v1/companies/authorized" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

### Plano de contas

Consulta de catalogo:

```bash
curl -sS "http://localhost:8000/api/v1/plano-contas?limit=20&offset=0" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

Importacao administrativa do plano de contas:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/admin/plano-contas/import" \
  -H "Authorization: Bearer <JWT_ADMIN>" \
  -F "file=@plano-contas-sanitizado.xlsx"
```

### Razao

Importacao de razao por empresa:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/razao/import" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -F "file=@razao-sanitizado.xlsx"
```

Consulta de lotes de razao:

```bash
curl -sS "http://localhost:8000/api/v1/companies/123/razao/lotes?limit=20&offset=0" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

### Movimentos operacionais

Importacao de movimentos operacionais:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/movimentos-operacionais/import" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -F "file=@movimentos-operacionais-sanitizado.xlsx"
```

Classificacao de pendencias do lote:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/movimentos-operacionais/classificar?lote_id=456" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

Revisao individual de movimento:

```bash
curl -sS -X PATCH \
  "http://localhost:8000/api/v1/companies/123/movimentos-operacionais/lotes/456/movimentos/789/review" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve"}'
```

Consulte o OpenAPI para o schema exato de payloads e respostas. Este documento
mantem exemplos curtos para orientar consumo, sem duplicar o contrato inteiro.

### ML e classificacao de contrapartida

Status do dataset/modelo:

```bash
curl -sS "http://localhost:8000/api/v1/companies/123/ml/status" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

Treino explicito:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/ml/train" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>"
```

Classificacao de contrapartida:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/ml/classification" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -H "Content-Type: application/json" \
  -d '{"historico":"PAGAMENTO FORNECEDOR FICTICIO","conta_origem":10036,"direcao":"credito"}'
```

### Feedback

Feedback novo de ML sobre lancamento normalizado:

```bash
curl -sS -X POST "http://localhost:8000/api/v1/companies/123/ml/feedback" \
  -H "Authorization: Bearer <JWT_DE_USUARIO>" \
  -H "Content-Type: application/json" \
  -d '{"lancamento_id":456,"conta_sugerida":40010,"conta_final":50057}'
```

Endpoint legado de feedback de transacao:

```bash
curl -sS -X PATCH "http://localhost:8000/api/v1/transactions/789/feedback" \
  -H "X-API-Key: <API_KEY_LEGADA>" \
  -H "Content-Type: application/json" \
  -d '{"conta_contabil":50057}'
```

### Transacoes legadas

Endpoints de transacoes permanecem como compatibilidade e usam `X-API-Key`
enquanto nao forem migrados.

```bash
curl -sS "http://localhost:8000/api/v1/companies/123/transactions" \
  -H "X-API-Key: <API_KEY_LEGADA>"
```

Nao use `X-API-Key` como substituto de JWT em endpoints internos novos.

## Erros publicos e correlacao

Erros publicos da API usam o envelope canonico:

```json
{
  "code": "validation_error",
  "message": "Dados invalidos enviados para a API.",
  "details": {},
  "request_id": "<REQUEST_ID>"
}
```

Toda resposta HTTP deve incluir o header `X-Request-ID`. Quando o cliente envia
um valor seguro nesse header, a API o preserva; quando o valor esta ausente ou
fora do formato aceito, a API gera um UUID4. Use esse identificador ao reportar
falhas, sem copiar tokens, planilhas, payloads brutos ou dados contabeis.

## Lacunas conhecidas e encaminhamento

- Identidade de servico para n8n e integracoes pertence a #351 e issues futuras
  derivadas.
- Download da planilha classificada e feedback round-trip pertencem a Spec 16 e
  issues futuras; ainda nao devem ser documentados como endpoints executaveis.
- Logs JSON, retencao e correlacao operacional pertencem a #404.
- README geral e consolidacao ampla de operacao pertencem a #396.

## Cuidados com exemplos

- Use apenas dados ficticios ou sanitizados.
- Nunca versionar tokens, API keys, admin tokens, senhas, hashes reais ou dados
  de clientes.
- Prefira placeholders como `<JWT_DE_USUARIO>`, `<JWT_ADMIN>` e
  `<API_KEY_LEGADA>`.
- Se um exemplo divergir do OpenAPI, corrija o exemplo ou registre a lacuna; nao
  trate esta documentacao como contrato paralelo.
