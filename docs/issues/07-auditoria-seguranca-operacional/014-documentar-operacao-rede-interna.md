# Issue 014: docs(ops): documentar operacao em rede interna

## Contexto

O sistema sera usado apenas no escritorio, no servidor Ubuntu com Docker, sem exposicao permanente via ngrok.

## Escopo

- Documentar premissas de rede interna.
- Documentar que banco PostgreSQL nao deve ficar exposto publicamente.
- Documentar que aplicacao nao deve usar ngrok permanente nesta fase.
- Documentar cuidados basicos de variaveis de ambiente e backups.
- Nao implementar configuracao de infraestrutura nesta issue.

## Criterios de Aceite

- Documento deixa claro o modelo de acesso interno.
- Documento separa acesso da aplicacao e acesso ao banco.
- Documento registra restricao contra exposicao publica.
- Documento aponta cuidados operacionais minimos.

## Testes Esperados

- Revisao manual do documento.

## TDD

Nao obrigatorio.

## Riscos

- Expor app ou banco por conveniencia durante testes.
- Misturar acesso interno com tunel publico permanente.
