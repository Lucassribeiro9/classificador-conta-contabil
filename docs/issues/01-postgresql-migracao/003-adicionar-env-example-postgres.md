# Issue 003: docs(env): criar .env.example com variaveis de PostgreSQL

## Contexto

A spec exige documentar variaveis de ambiente e credenciais locais ficticias para desenvolvimento. O projeto precisa de um `.env.example` para orientar execucao local e Docker sem versionar segredos reais.

## Escopo

- Criar `.env.example`.
- Documentar `DATABASE_URL`.
- Documentar `POSTGRES_DB`, `POSTGRES_USER` e `POSTGRES_PASSWORD` com valores locais/ficticios.
- Documentar variaveis ja usadas pelo compose quando forem relevantes, sem incluir segredos reais.

## Criterios de Aceite

- `.env.example` existe no repositorio.
- Nenhum segredo real e versionado.
- Variaveis permitem entender como conectar API ao PostgreSQL local.
- Valores sao claramente de desenvolvimento.

## Testes Esperados

- Nao exige teste automatizado novo.
- Revisao manual do arquivo para garantir ausencia de credenciais reais.

## TDD

Nao obrigatorio.

## Riscos

- Versionar acidentalmente token real de ngrok ou senha real.
- Misturar variaveis de n8n com variaveis da API sem clareza.
