# Homologação da validação temporal do Razão (#502)

Execute este roteiro em ambiente de homologação com dados fictícios. Registre o
commit testado, ambiente, perfil, evidências, divergências e resultado
`APROVADO`, `REPROVADO` ou `BLOQUEADO`. Testes automatizados não substituem esta
execução manual.

## Pré-condições

- Migration `502a6e1c9d40` aplicada após `501a7c4e2d90`.
- Empresa de teste com usuário de permissão `operacao` e acesso à Central de
  Revisões. Use um segundo usuário sem acesso à empresa para o teste negativo.
- Snapshot da empresa vigente em 2026-01-01 com conta fictícia `10046` e
  descrição `Banco Teste`. Prepare um Razão sanitizado de 2026 com a conta
  observada `20001`, descrita no bloco como `Banco Teste`, e uma contrapartida
  válida `10046`. Prepare outra cópia com código de bloco `10046` e descrição
  divergente `Caixa Teste`.

## Cenários

1. Envie o Razão pelo fluxo assíncrono e aguarde estado terminal. Confira que a
   linha com `20001` foi persistida, sem invalidar o lançamento por estar fora
   do snapshot. Consulte a Central de Revisões e confirme uma pendência de
   conta desconhecida com referência ao lote e à linha. Uma correspondência
   única de descrição pode aparecer como **possível alias**; ela não confirma o
   vínculo automaticamente. Os warnings técnicos permanecem na consulta de
   warnings do lote.
2. Assuma a pendência. Na Central, use **Confirmar alias**, informe o código
   `10046` e uma justificativa. Confira status `resolved` e o evento auditável.
   A chamada equivalente é `POST
   /api/v1/companies/{company_id}/review-items/{item_id}/confirm-razao-alias`
   com JSON `{"target_codigo": 10046, "reason": "Equivalência conferida"}`.
   Um destino ausente do snapshot deve receber `409`; sem claim ou sem acesso à
   empresa, a ação deve falhar.
3. Importe um segundo arquivo sanitizado, de conteúdo diferente, com `20001`
   na mesma vigência. Confira que o alias confirmado é reutilizado e que não
   surge nova pendência para o mesmo código. Verifique que o lote anterior
   preservou seu estado terminal, contadores e warnings.
4. Crie um segundo snapshot com vigência posterior e importe uma linha com
   `20001` nessa nova vigência. Confirme que o alias antigo não foi aplicado e
   que surgiu nova pendência. Repita com outra empresa: nenhuma confirmação da
   primeira empresa deve ser reutilizada.
5. Importe a cópia cuja descrição do bloco diverge da descrição da conta no
   snapshot. Confirme a pendência de divergência semântica com suas evidências,
   mantendo as linhas do Razão e o estado do lote.
6. Se a data da linha cair em conflito de vigência, confira que a linha fica
   persistida e a ambiguidade gera pendência. Resolver a pendência do Razão
   exige antes uma decisão válida do snapshot; a resolução não altera o lote.

## Evidência e recuperação

Registre apenas IDs sintéticos, estados, contadores, códigos HTTP e capturas
sanitizadas. Não anexe token, planilha real, conteúdo contábil privado ou log
bruto. Para recuperação, não atualize lotes históricos nem edite aliases
diretamente no banco; reverta o código pelo fluxo de PR e trate os registros
confirmados por procedimento auditável. O downgrade da migration é bloqueado
quando existem aliases confirmados, para evitar perda silenciosa de decisões.
