# Homologação: snapshots temporais do plano de contas (#501)

## Preparação

- Aplicar `alembic upgrade head` em PostgreSQL de homologação isolado.
- Usar duas empresas sintéticas e um usuário `contador` com `operacao` em apenas uma delas.
- Montar duas planilhas `.xlsx` válidas com as colunas `Codigo`, `Tipo`, `Classificacao`, `Nome` e `Grau`. Exemplo sanitizado: código `100`, tipo `A`, classificação `1.1`, grau `2`; na primeira, nome `Banco`, na segunda, nome `Despesa`.
- Registrar o commit testado, o ambiente, a versão da migration e os IDs criados. Não incluir planilhas reais ou dados contábeis no registro.

## Roteiro manual

1. Enviar a primeira planilha para `POST /api/v1/empresas/{company_id}/plano-contas/snapshots/import` com formulário `file`, `origem=exemplo-a` e `vigencia=2026-02-01`. Registrar `snapshot_id` e `import_event_id`.
2. Repetir com conteúdo equivalente e `origem=exemplo-b`. Confirmar o mesmo `snapshot_id`, outro `import_event_id` e ausência de nova pendência.
3. Enviar a segunda planilha com a mesma vigência. Confirmar novo `snapshot_id`, novo `import_event_id` e `review_item_id`.
4. Consultar `GET /api/v1/empresas/{company_id}/plano-contas/snapshots/at/2026-03-01`: deve retornar `409`. Consultar os dois snapshots por `GET /api/v1/empresas/{company_id}/plano-contas/snapshots/{snapshot_id}` para comparar conteúdo, origem e vigência.
5. Assumir a pendência na central, tentar a resolução genérica e confirmar `409`. Resolver por `POST /api/v1/empresas/{company_id}/plano-contas/snapshots/conflicts/{item_id}/resolve` com `snapshot_id` escolhido e `reason` justificada. Consultar `GET /api/v1/empresas/{company_id}/plano-contas/snapshots/conflicts/{item_id}/decision` e confirmar responsável, justificativa e candidatos. Confirmar evento de revisão e evento de auditoria sem conteúdo contábil. Repetir a consulta temporal e confirmar o snapshot escolhido.
6. Importar um plano histórico com `vigencia=2025-01-01`. Confirmar seleção histórica sem alteração dos snapshots e eventos anteriores. Importar sem `vigencia` e confirmar `vigencia_inferida=true`.
7. Repetir leitura e escrita com usuário sem acesso à empresa: deve retornar `403`. Confirmar que a importação global legada mantém seu comportamento.

## Rollback e recuperação

O downgrade da migration recusa execução se houver qualquer snapshot, evento de importação, entrada ou decisão. Antes de considerar reversão estrutural, exportar e verificar esses dados, preservar os eventos de auditoria e obter decisão operacional explícita. A aplicação anterior pode ignorar as novas tabelas, mantendo os dados para recuperação. Não apagar histórico para forçar `alembic downgrade`.

Uma importação incorreta não modifica snapshots já existentes. Tratar a vigência conflitante pela central e registrar a decisão; uma correção do conteúdo entra como novo snapshot e novo evento. Registrar divergências e resultado `APROVADO`, `REPROVADO` ou `BLOQUEADO` com evidências do ambiente testado.
