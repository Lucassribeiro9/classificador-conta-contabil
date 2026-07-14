# Checklist Tecnico de Liberacao da Homologacao

Use este checklist antes de liberar o ambiente de homologacao para uma rodada
com operador/contador. Ele complementa o roteiro funcional em
`docs/frontend-homologacao-mvp-ux.md` e segue as specs 11 e 13.

Preencha cada item com `Aprovado`, `Bloqueado` ou `Nao aplicavel`. Um item
obrigatorio diferente de `Aprovado` impede a liberacao.

## Identificacao da Rodada

- Data:
- Branch/commit:
- Responsavel tecnico:
- Responsavel pela homologacao:
- Ambiente/host:

## Gates Tecnicos Obrigatorios

| Item | Status | Evidencia | Responsavel |
| --- | --- | --- | --- |
| Backend tests relevantes estao verdes; falhas conhecidas foram tratadas ou justificadas. |  |  |  |
| Frontend lint esta verde. |  |  |  |
| Frontend typecheck esta verde. |  |  |  |
| Frontend build esta verde. |  |  |  |
| Docker Compose de homologacao foi validado com variaveis sanitizadas. |  |  |  |
| Banco de homologacao separado de producao foi confirmado. |  |  |  |
| API `/health` responde no ambiente de homologacao. |  |  |  |
| Tela de login carrega por HTTPS no host interno de homologacao. |  |  |  |
| Usuario operador/contador de teste esta ativo. |  |  |  |
| Empresas e permissoes de teste estao vinculadas corretamente. |  |  |  |
| Massa sanitizada de plano de contas, razao e movimentos esta carregada. |  |  |  |

## Criterios de Bloqueio

A liberacao deve ser marcada como `Bloqueado` quando ocorrer qualquer um dos
seguintes casos:

- uso de dados reais ou sensiveis;
- ambiente ou banco compartilhado com producao;
- falha em teste, lint, typecheck ou build obrigatorio sem justificativa aceita;
- API `/health` indisponivel ou tela de login inacessivel;
- falha de autenticacao ou permissao por empresa;
- usuario, empresa, permissao ou massa sanitizada obrigatoria ausente;
- segredo, certificado real ou porta privada exposta indevidamente.

Melhoria cosmetica nao bloqueia a liberacao quando nao prejudica seguranca,
integridade dos dados ou conclusao do fluxo operacional. O status
`Nao aplicavel` exige justificativa obrigatoria e aprovacao do responsavel
tecnico.

## Evidencias Minimas

Registre evidencias curtas e reproduziveis:

- comando executado e resultado resumido para cada validacao automatizada;
- branch ou commit e data da verificacao;
- URL interna e resposta esperada do `/health`, sem cabecalhos sensiveis;
- identificador sanitizado do usuario e da empresa de teste;
- nomes dos arquivos sanitizados utilizados;
- resultado do login e das permissoes, sem credenciais;
- justificativa e responsavel por qualquer excecao aceita.

Nao registre senhas, tokens, segredos, chaves privadas, documentos reais,
conteudo contabil real ou prints com informacoes sensiveis. Evidencias devem
ficar no local controlado definido pela equipe, e nao necessariamente no
repositorio.

## Decisao

- Resultado: Liberado / Bloqueado
- Responsavel pela decisao:
- Data/hora:
- Observacoes:
