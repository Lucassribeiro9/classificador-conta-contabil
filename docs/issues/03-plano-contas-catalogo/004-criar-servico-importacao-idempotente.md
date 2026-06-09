# Issue 004: feat(contas): criar servico de importacao idempotente

## Contexto

A importacao do plano deve criar contas novas e atualizar existentes sem duplicar. Contas ausentes em nova importacao permanecem ativas.

## Escopo

- Criar servico que recebe contas normalizadas do parser.
- Criar contas novas.
- Atualizar nome, classificacao, tipo, grau e flag quando conta ja existir.
- Nao inativar contas ausentes.
- Retornar resumo da importacao.

## Criterios de Aceite

- Reimportacao nao duplica contas.
- Conta existente e atualizada quando dados mudam.
- Conta ausente em nova importacao permanece ativa.
- Resumo informa criadas, atualizadas e ignoradas/invalidas.

## Testes Esperados

- Teste de primeira importacao.
- Teste de reimportacao idempotente.
- Teste de atualizacao de conta existente.
- Teste de conta ausente permanecendo ativa.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Inativar ou excluir conta por ausencia acidental no arquivo.
- Criar duplicidade por tipo inconsistente de codigo.
