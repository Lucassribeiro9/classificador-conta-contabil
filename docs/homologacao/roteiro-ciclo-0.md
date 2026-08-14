# Roteiro de Homologacao Formal do Ciclo 0

Use este roteiro para registrar a homologacao formal da
`Fase 3 / Release 1 / Ciclo 0`. O objetivo e consolidar, em um artefato unico e
reproduzivel, o ambiente testado, o commit, os responsaveis, os cenarios
executados, as evidencias tratadas, as divergencias e a decisao final.

Este roteiro nao substitui os checklists existentes. Use-os como entradas da
rodada e registre aqui somente o resultado consolidado:

- Spec canonica: `docs/specs/15-harness-qualidade-documentacao.md`;
- checklist tecnico: `docs/homologacao-checklist-tecnico.md`;
- roteiro operador/contador: `docs/homologacao-roteiro-operador-contador.md`;
- criterios de UX por tela: `docs/frontend-homologacao-mvp-ux.md`;
- smoke da aplicacao em HML: `docs/homologacao-smoke-aplicacao.md`.

## Regras de seguranca das evidencias

Nao versione evidencias reais neste repositorio. Registre apenas referencias
sanitizadas para o local controlado da equipe, como comentario de PR, Notion,
pasta interna ou registro de homologacao.

Nao registre senhas, tokens, segredos, chaves privadas, documentos reais,
planilhas completas, prints com dados sensiveis ou dados contabeis reais.
Quando uma evidencia for necessaria, use resumo curto, identificadores
ficticios e a sanitizacao aplicada.

## Identificacao da rodada

| Campo | Valor |
| --- | --- |
| Release/ciclo | Fase 3 / Release 1 / Ciclo 0 |
| Ambiente |  |
| URL ou host interno |  |
| Banco de dados |  |
| Commit testado |  |
| Branch testada |  |
| Data/hora de inicio |  |
| Data/hora de termino |  |
| Responsavel pela execucao |  |
| Responsavel tecnico |  |
| Responsavel pela decisao |  |
| Perfil utilizado |  |
| Empresa sanitizada |  |
| Massa/fixtures sanitizadas |  |

## Servicos necessarios

Liste somente os servicos usados na rodada e o estado observado.

| Servico | Obrigatorio? | Estado | Evidencia |
| --- | --- | --- | --- |
| API | Sim |  |  |
| PostgreSQL HML | Sim |  |  |
| Frontend interno | Sim |  |  |
| Proxy/edge | Quando aplicavel |  |  |
| n8n/workflow | Quando aplicavel |  |  |

## Roteiro executado

Marque cada cenario com `APROVADO`, `REPROVADO`, `BLOQUEADO` ou
`NAO APLICAVEL`. Todo cenario deve ter resultado esperado, resultado observado
e evidencia sanitizada ou justificativa de `NAO APLICAVEL`.

| ID | Cenario | Referencia | Resultado esperado | Resultado observado | Status | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| C0-01 | Gates tecnicos obrigatorios | `docs/homologacao-checklist-tecnico.md` | Testes, build, ambiente e massa atendem aos gates aplicaveis. |  |  |  |
| C0-02 | Smoke da aplicacao em HML | `docs/homologacao-smoke-aplicacao.md` | API `/health` e tela `/login` respondem no ambiente correto. |  |  |  |
| C0-03 | Login e empresas permitidas | `docs/homologacao-roteiro-operador-contador.md` | Usuario operador/contador acessa apenas empresas autorizadas. |  |  |  |
| C0-04 | Operacao da empresa | `docs/frontend-homologacao-mvp-ux.md` | Hub preserva empresa selecionada e exibe contexto operacional. |  |  |  |
| C0-05 | Importacao de movimentos | `docs/homologacao-roteiro-operador-contador.md` | `.xlsx` sanitizado gera resumo de lote sem dados reais em evidencia. |  |  |  |
| C0-06 | Classificacao e lote de movimentos | `docs/homologacao-roteiro-operador-contador.md` | Classificacao atualiza somente movimentos pendentes da empresa. |  |  |  |
| C0-07 | Revisao em lista e individual | `docs/homologacao-roteiro-operador-contador.md` | Decisoes humanas sao persistidas no movimento correto. |  |  |  |
| C0-08 | Razao e contas vinculadas | `docs/frontend-homologacao-mvp-ux.md` | Consulta usa dados sanitizados e respeita paginacao/permissao. |  |  |  |
| C0-09 | Seguranca das evidencias | Este roteiro | Evidencias nao contem segredo, dado real ou payload bruto. |  |  |  |

## Evidencias tratadas

Registre referencias sanitizadas. Nao cole logs brutos, tokens, screenshots com
dado sensivel, planilhas completas ou conteudo contabil real.

| Tipo | Referencia | Conteudo resumido | Sanitizacao aplicada | Responsavel |
| --- | --- | --- | --- | --- |
| Comando |  |  |  |  |
| Print |  |  |  |  |
| Arquivo sanitizado |  |  |  |  |
| Comentario de PR |  |  |  |  |
| Registro interno |  |  |  |  |

## Divergencias

Toda divergencia deve ter responsavel e encaminhamento. Divergencia bloqueante
deve gerar issue ou apontar para issue existente. Melhorias sem impacto
bloqueante podem ser encaminhadas para backlog.

| ID | Cenario | Severidade | Responsavel | Encaminhamento | Link ou issue |
| --- | --- | --- | --- | --- | --- |
|  |  | BLOQUEANTE / RESSALVA / MELHORIA |  |  |  |

## Decisao final

Use uma das opcoes:

- `APROVADO`;
- `APROVADO COM RESSALVAS`;
- `REPROVADO`;
- `BLOQUEADO`.

| Campo | Valor |
| --- | --- |
| Decisao final |  |
| Justificativa |  |
| Ressalvas aceitas |  |
| Bloqueantes abertos |  |
| Issues geradas ou vinculadas |  |
| Responsavel pela decisao |  |
| Data/hora da decisao |  |

## Exemplo de preenchimento sanitizado

Este exemplo e ficticio. Use-o apenas como referencia de formato.

### Identificacao

| Campo | Valor |
| --- | --- |
| Release/ciclo | Fase 3 / Release 1 / Ciclo 0 |
| Ambiente | HML interno |
| URL ou host interno | `https://classificador-hml.interno` |
| Banco de dados | PostgreSQL HML separado de producao |
| Commit testado | `abc1234` |
| Branch testada | `release-1-ciclo-0-candidato` |
| Responsavel pela execucao | Analista HML |
| Responsavel tecnico | Lucas Ribeiro |
| Responsavel pela decisao | Lucas Ribeiro |
| Perfil utilizado | Operador/contador |
| Empresa sanitizada | EMPRESA MODELO HOMOLOGACAO LTDA |
| Massa/fixtures sanitizadas | `plano_contas_hml.xlsx`, `razao_hml.xlsx`, `movimentos_operacionais_hml.xlsx` |

### Resultado por cenario

| ID | Cenario | Referencia | Resultado esperado | Resultado observado | Status | Evidencia |
| --- | --- | --- | --- | --- | --- | --- |
| C0-01 | Gates tecnicos obrigatorios | `docs/homologacao-checklist-tecnico.md` | Gates aplicaveis aprovados. | Backend e frontend validados com ressalva documentada. | APROVADO COM RESSALVAS | Comentario PR #000 |
| C0-03 | Login e empresas permitidas | `docs/homologacao-roteiro-operador-contador.md` | Usuario acessa apenas empresa autorizada. | `usuario.operador.hml` acessou apenas EMPRESA MODELO HOMOLOGACAO LTDA. | APROVADO | Registro interno HML-000 |
| C0-09 | Seguranca das evidencias | Este roteiro | Evidencias sem dados reais. | Prints revisados e nomes/documentos ficticios mantidos. | APROVADO | Checklist interno HML-000 |

### Evidencias tratadas

| Tipo | Referencia | Conteudo resumido | Sanitizacao aplicada | Responsavel |
| --- | --- | --- | --- | --- |
| Comentario de PR | PR #000, comentario de homologacao | Resultado resumido dos comandos e decisoes. | Sem tokens, senhas, documentos reais ou dados contabeis reais. | Analista HML |
| Print | Registro interno HML-000 | Tela de empresas com empresa ficticia. | Dados ficticios e sem credenciais visiveis. | Analista HML |

### Divergencias

| ID | Cenario | Severidade | Responsavel | Encaminhamento | Link ou issue |
| --- | --- | --- | --- | --- | --- |
| DIV-001 | C0-01 | RESSALVA | Lucas Ribeiro | Corrigir falha documental nao bloqueante em issue futura. | #000 |

### Decisao

| Campo | Valor |
| --- | --- |
| Decisao final | APROVADO COM RESSALVAS |
| Justificativa | Fluxo principal validado com massa sanitizada; ressalva nao bloqueia uso interno. |
| Ressalvas aceitas | DIV-001 |
| Bloqueantes abertos | Nenhum |
| Issues geradas ou vinculadas | #000 |
| Responsavel pela decisao | Lucas Ribeiro |
| Data/hora da decisao | 2026-08-14 10:00 BRT |
