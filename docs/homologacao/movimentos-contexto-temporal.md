# Homologação do contexto temporal de movimentos

Execute em ambiente de homologação com empresa, snapshots e planilhas
sintéticas. Registre o commit, ambiente/perfil, evidências sanitizadas,
divergências e resultado `APROVADO`, `REPROVADO` ou `BLOQUEADO`. Não registre
históricos, documentos, saldos reais, tokens ou credenciais.

## Roteiro

1. Prepare dois snapshots com vigências distintas e contas analíticas diferentes.
   Importe um lote sintético que atravesse a transição, com linhas datadas antes
   e depois dela. Classifique os pendentes e confirme que cada sugestão usa
   somente contas analíticas do snapshot aplicável à data da própria linha.
2. Confirme que a linha com data válida não é enviada à revisão só porque o lote
   atravessa uma transição. Confirme que conta financeira ausente/não analítica
   no snapshot aplicável resulta em abstinência, status `revisao`, mensagem
   explicativa e pendência na Central de Revisões.
3. Confirme que conflito ou ausência de snapshot não altera plano nem conta,
   produz abstinência e cria pendência rastreável. Abra **Abrir pendência** na
   tela do lote e confirme que chega ao `itemId` correto da Central.
4. Para a regra de fallback, use um lote sintético sem data por linha. Quando
   todo o período resolver para o mesmo snapshot, confirme o uso do início do
   lote e o evento `operational_movements.temporal_context_checked` com
   `context_source=batch_period_start_inferred`. Quando o lote atravessar uma
   vigência, confirme que a linha fica em revisão e que o evento registra a
   inferência sem escolher snapshot.
5. Confira que a auditoria contém somente IDs/contexto temporal e metadados
   seguros, sem histórico, documento, observação, valor ou saldos.
6. Exporte e reimporte a planilha classificada em ambos os layouts suportados.
   Confirme que colunas, saldos e round-trip permanecem compatíveis e que
   sugestões não são decisões finais nem entram automaticamente no dataset.

## Evidências

Registre snapshots sintéticos usados, IDs de lote/movimento/revisão, resultados
por linha, evento de auditoria sanitizado, captura da tela da Central, arquivos
exportados anonimizados e resultado final. Não considere testes automatizados
como homologação manual.

## Rollback

O fluxo usa colunas e tabelas existentes. Reverter o commit restaura o
comportamento anterior do classificador e remove os links da interface. As
pendências já criadas são dados auditáveis e devem ser tratadas explicitamente;
não as apague como parte do rollback.
