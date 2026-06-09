# Issue 013: docs(audit): documentar politica de auditoria e seguranca

## Contexto

As regras de auditoria precisam ficar claras para implementadores e revisores.

## Escopo

- Documentar campos da tabela `audit_events`.
- Documentar lista inicial de eventos.
- Documentar metadata permitida e proibida.
- Documentar retencao indefinida na primeira versao.
- Documentar diferenca entre logs tecnicos e auditoria.

## Criterios de Aceite

- Documento referencia a spec 07.
- Documento lista eventos por dominio.
- Documento explicita que senha, token, API key e payload sensivel nao podem ser gravados.
- Documento orienta revisao de PRs que adicionem eventos.

## Testes Esperados

- Revisao manual do documento.

## TDD

Nao obrigatorio.

## Riscos

- Times futuros adicionarem eventos sem sanitizacao.
- Confundir log tecnico com trilha auditavel.
