# Issues: 07 Auditoria e Seguranca Operacional

Issues derivadas da spec `docs/specs/07-auditoria-seguranca-operacional.md`.

## Ordem Recomendada

1. `001-confirmar-contratos-auditoria.md`
2. `002-criar-modelo-audit-events.md`
3. `003-criar-servico-auditoria.md`
4. `004-sanitizar-metadata-auditoria.md`
5. `005-capturar-contexto-request.md`
6. `006-auditar-auth-login-acesso-negado.md`
7. `007-auditar-importacao-plano-contas.md`
8. `008-auditar-importacao-razao.md`
9. `009-auditar-classificacao-ml.md`
10. `010-auditar-feedback.md`
11. `011-auditar-gestao-usuarios-permissoes.md`
12. `012-testar-bloqueios-seguranca-operacional.md`
13. `013-documentar-politica-auditoria-seguranca.md`
14. `014-documentar-operacao-rede-interna.md`
15. `015-backlog-consulta-auditoria-admin.md`
16. `016-backlog-retencao-limpeza-auditoria.md`

## TDD Obrigatorio

- `002-criar-modelo-audit-events.md`
- `003-criar-servico-auditoria.md`
- `004-sanitizar-metadata-auditoria.md`
- `005-capturar-contexto-request.md`
- `006-auditar-auth-login-acesso-negado.md`
- `007-auditar-importacao-plano-contas.md`
- `008-auditar-importacao-razao.md`
- `009-auditar-classificacao-ml.md`
- `010-auditar-feedback.md`
- `011-auditar-gestao-usuarios-permissoes.md`
- `012-testar-bloqueios-seguranca-operacional.md`

## Observacao

Estas issues assumem que autenticacao, permissoes por empresa, importacoes e ML serao implementados pelas specs anteriores. A auditoria deve ser integrada aos fluxos sensiveis sem gravar segredos e sem adicionar ferramenta externa de observabilidade nesta fase.
