# Reimportacao do Plano de Contas

Este documento registra a regra operacional para contas ausentes em uma nova
importacao do plano de contas.

## Regra

Uma reimportacao do plano de contas nao substitui integralmente o catalogo.
Quando uma conta existente nao aparece em um novo arquivo importado, ela
permanece ativa.

O sistema nao deve excluir nem inativar automaticamente contas ausentes por
causa de uma reimportacao.

## Motivo

Arquivos de relatorio podem ser gerados com filtros, recortes por periodo,
opcoes de visualizacao ou falhas operacionais. Um arquivo incompleto nao e uma
evidencia segura de que uma conta deixou de existir no catalogo do escritorio.

Manter contas ausentes como ativas evita perda acidental de historico,
quebra de vinculos com empresas e impacto indevido em importadores, dataset e
classificacao.

## Comportamento esperado

Em uma reimportacao:

- contas novas sao criadas;
- contas existentes sao atualizadas quando dados oficiais mudam;
- contas existentes que nao aparecem no arquivo continuam ativas;
- nenhuma conta e excluida por ausencia;
- nenhuma conta e inativada por ausencia.

## Fora da primeira fase

Inativacao automatica de contas ausentes fica fora da primeira fase. Se esse
comportamento se tornar necessario, ele deve ser tratado em backlog proprio,
com revisao, criterio claro de seguranca e evidencia confiavel de que a
conta realmente saiu do plano.
