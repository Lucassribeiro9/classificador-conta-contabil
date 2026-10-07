# Homologação do envio manual de movimentos à central

Use uma empresa e um lote com movimentos sintéticos, em ambiente descartável ou
de homologação. Registre o commit testado, ambiente, perfil, evidências,
divergências e resultado `APROVADO`, `REPROVADO` ou `BLOQUEADO`. Não inclua tokens
nem dados contábeis reais nas evidências.

## Roteiro

1. Entre como usuário com permissão `operacao` na empresa e abra **Lote de
   Movimentos**. Selecione um movimento `pendente` e outro `revisao` e acione
   **Enviar para revisao**.
2. Confirme o resultado por movimento e abra cada link **Abrir pendência**.
   Verifique que a central mostra o item correto, inclusive se ele estiver fora
   da primeira página da fila.
3. Repita o envio dos mesmos IDs. Confirme `existing` e os mesmos
   `review_item_id`, sem duplicatas. Confira o evento
   `operational_movements.review_submitted` apenas para cada criação.
4. Selecione um movimento `aprovado` junto com um elegível. Confirme sucesso do
   elegível e motivo `ineligible` para o aprovado, sem alterar o status ou a
   classificação de nenhum deles.
5. Tente enviar com usuário `leitura` e com usuário sem acesso à empresa.
   Confirme `403` e ausência de nova pendência. Tente um ID de outro lote ou
   empresa e confirme `not_found`, sem expor o registro.
6. Resolva uma pendência no ambiente de teste e repita o envio. Confirme
   `closed`, sem reabertura automática.

## API de apoio

Com JWT de usuário de teste, envie `POST
/api/v1/companies/{company_id}/movimentos-operacionais/lotes/{lote_id}/enviar-revisao`
com `{"movimento_ids":[<id_sintetico>]}`. A resposta informa resultado e
`review_item_id` por ID. Use a central em
`/empresas/{company_id}/revisoes?itemId={review_item_id}` para conferir o item.

## Rollback

O contrato adiciona código e não altera schema. Reverter o commit da entrega
restaura a tela e remove o endpoint; pendências de teste já criadas precisam ser
identificadas por `source_type=movimento_operacional_manual` e tratadas
separadamente no ambiente descartável. Não remova dados de produção como parte
da reversão do código.
