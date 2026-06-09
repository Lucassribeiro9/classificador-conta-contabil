# Issue 008: docs(postgres): documentar decisao sobre transacoes legadas

## Contexto

A spec decidiu que a migracao obrigatoria cobre apenas empresas. Transacoes e classificacoes antigas ficam fora da migracao inicial e podem virar backlog.

## Escopo

- Documentar que a migracao inicial preserva empresas obrigatoriamente.
- Documentar que transacoes/classificacoes antigas nao serao migradas nesta fase.
- Explicar o motivo: novo dominio de razao, contrapartida e dataset normalizado.
- Registrar que uma migracao futura pode ser criada se houver necessidade operacional.

## Criterios de Aceite

- Decisao esta documentada em local apropriado.
- A documentacao nao deixa duvida de que transacoes ficam fora do escopo inicial.
- O texto referencia o PRD/spec quando fizer sentido.

## Testes Esperados

- Nao exige teste automatizado.

## TDD

Nao obrigatorio.

## Riscos

- Equipe assumir que todos os dados antigos foram migrados.
- Perder contexto da decisao quando a implementacao comecar.
