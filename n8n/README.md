# Workflows n8n da esteira

Esta pasta guarda exports sanitizados e fixtures dos workflows n8n da esteira supervisionada.

## Agent Documental Pilot

Arquivo: `workflows/agent-documental-pilot.sanitized.json`

O workflow real deve permanecer inativo no final da #378. Valores privados ficam somente no n8n/configuracao privada e aparecem no export como placeholders:

- `__GITHUB_API_BASE_URL__`
- `__GITHUB_CREDENTIAL_PLACEHOLDER__`
- `__PRIVATE_RUNNER_URL__`
- `__RUNNER_HMAC_KEY_ID__`
- `__RUNNER_HMAC_SECRET__`
- `__N8N_DATA_TABLE_ID__`

Fallback manual: use `docs/prompts-fluxo-sdd-tdd.md` e as skills da esteira. Os prompts completos nao sao duplicados aqui para evitar drift.
