# Issue 004: feat(audit): sanitizar metadata antes de persistir

## Contexto

Auditoria deve ser util sem gravar senha, token, API key, conteudo completo de planilhas ou payload sensivel.

## Escopo

- Criar rotina central de sanitizacao de metadata.
- Remover ou mascarar chaves sensiveis como `password`, `senha`, `token`, `api_key`, `authorization`.
- Bloquear conteudo completo de planilhas e payloads grandes.
- Definir limite razoavel de tamanho de metadata.
- Aplicar sanitizacao no servico de auditoria.

## Criterios de Aceite

- Segredos conhecidos nao sao persistidos.
- Payloads sensiveis ou grandes sao removidos, resumidos ou rejeitados conforme regra.
- Metadata operacional segura continua disponivel.
- Sanitizacao e testada de forma independente.

## Testes Esperados

- Teste removendo senha.
- Teste removendo token/API key.
- Teste com payload grande.
- Teste preservando metadata segura, como contadores.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Auditoria virar vazamento de dados.
- Sanitizacao agressiva demais remover informacao operacional util.
