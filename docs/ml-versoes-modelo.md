# Versões do modelo de contrapartida

A API técnica mantém versões por empresa. `POST /api/v1/companies/{company_id}/ml/train`
compõe um manifesto do dataset, treina um **candidate**, avalia e grava o artefato
em `empresa_{company_id}/model_{version_id}.joblib`. O treino não ativa o
candidato. O endpoint exige permissão `operacao` ou superior e retorna
`version_id` com `status=candidate`.

Um admin global ou usuário com `admin_empresa` pode:

- consultar `GET /api/v1/companies/{company_id}/ml/models` para ver estado,
  manifesto, métricas, avaliação, threshold e classes críticas congeladas;
- definir a lista para avaliações futuras com
  `PUT /api/v1/companies/{company_id}/ml/critical-classes` e corpo
  `{"classes": [50057]}`; lista vazia aplica o guardrail a todas as classes
  avaliáveis;
- promover um candidato com
  `POST /api/v1/companies/{company_id}/ml/models/{version_id}/promote`;
- reativar uma versão aposentada, sem treino, com
  `POST /api/v1/companies/{company_id}/ml/models/{version_id}/rollback`.

A avaliação usa holdout estratificado de 20% com semente fixa quando cada classe
tem pelo menos cinco exemplos. Com duas a quatro amostras por classe, usa
validação cruzada estratificada. Se alguma classe tiver menos de duas amostras,
a avaliação fica inválida e a promoção é bloqueada. Métricas, método, hash do
manifesto, versão `ml-eval-v1` e lista de classes críticas são preservados na versão. O threshold
inicial da versão é `0.70`; ele controla revisão de sugestões, nunca aprova
uma classificação automaticamente.

A primeira promoção exige avaliação válida e ação humana. Nas seguintes, uma
queda de macro F1 ou de F1 de classe crítica frente ao ativo impede a promoção.
O desempenho do ativo é calculado nas mesmas amostras usadas na avaliação do
candidato e fica registrado com o ID do ativo comparado. Se o ativo mudar antes
da promoção, a avaliação do candidato fica desatualizada e a promoção é
bloqueada. Se o ativo já tiver visto essas amostras no treino anterior, a
comparação favorece o ativo; o admin deve interpretar as métricas como
diagnóstico conservador. Uma classe crítica ausente da avaliação também impede
a promoção. A promoção
aposenta o ativo anterior na mesma transação; o banco impõe unicidade de ativo
por empresa. Ações aceitas e recusadas geram eventos de auditoria. Arquivos de
modelo são conferidos por SHA-256 antes de promoção, rollback e inferência.

O leitor de inferência usa o ativo versionado quando existe. Durante a transição,
se a empresa ainda não tiver ativo versionado, continua lendo o artefato legado
`model_.joblib` se ele existir. O treino novo não sobrescreve esse arquivo.

## Migração e recuperação

A migration cria `model_versions`, a lista de classes críticas por empresa, um
índice parcial de unicidade do ativo e a proteção da evidência imutável no
PostgreSQL. Ela não copia nem remove arquivos legados. Falha entre a gravação do
arquivo e o commit pode deixar um artefato órfão; a conciliação deve comparar
IDs e hashes com `model_versions`, sem apagar um arquivo referenciado. Antes de um downgrade,
exporte as linhas de versões, eventos de auditoria e artefatos, confirme que
nenhum consumidor depende do ativo versionado e então execute o downgrade em
janela controlada. O downgrade elimina os registros de versões; os arquivos
não são removidos automaticamente. Em incidente de promoção, prefira rollback
pela API para reativar a versão anterior, preservando a trilha de auditoria.
