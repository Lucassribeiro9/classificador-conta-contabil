# Issue 009: test(auth): garantir que API key nao substitui JWT em endpoints internos novos

## Contexto

API keys permanecem para compatibilidade e integracoes futuras, mas nao substituem usuario humano nos endpoints internos novos. Endpoints internos novos devem exigir JWT.

## Escopo

- Definir teste de endpoint interno novo ou dependencia representativa exigindo JWT.
- Garantir que chamada apenas com `X-API-Key` nao autentica usuario interno.
- Manter endpoints legados com API key sem mudanca fora do escopo.
- Documentar diferenca entre auth humana e API key.

## Criterios de Aceite

- Endpoint interno novo rejeita chamada sem JWT.
- Endpoint interno novo rejeita chamada apenas com API key.
- Endpoint interno novo aceita JWT valido.
- Teste nao quebra compatibilidade de endpoints legados sem decisao explicita.

## Testes Esperados

- Teste sem credencial.
- Teste apenas com `X-API-Key`.
- Teste com JWT valido.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Quebrar integracoes existentes por alterar endpoints legados.
- Permitir acao humana sem `usuario_id` auditavel.
