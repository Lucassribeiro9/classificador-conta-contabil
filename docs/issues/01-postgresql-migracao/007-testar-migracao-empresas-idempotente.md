# Issue 007: test(migracao): cobrir migracao idempotente de empresas

## Contexto

A migracao de empresas precisa ser confiavel porque preserva o cadastro existente no banco atual. A idempotencia deve ser demonstrada por testes claros.

## Escopo

- Fortalecer testes da migracao de empresas.
- Cobrir reexecucao sem duplicidade.
- Cobrir atualizacao segura de empresa existente quando a chave corresponder.
- Cobrir conflitos reais que devem bloquear a migracao.
- Esta issue pode ser combinada com a issue 006 se o PR continuar pequeno.

## Criterios de Aceite

- Ha teste especifico para reexecutar a migracao duas vezes.
- Ha teste para impedir duplicidade.
- Ha teste para conflito de chaves unicas.
- Testes documentam o comportamento esperado para empresas existentes.

## Testes Esperados

- `.\venv\Scripts\python.exe -m pytest -q tests`

## TDD

Obrigatorio. Esta issue e de teste.

## Riscos

- Testar apenas caminho feliz e deixar conflito sem cobertura.
- Criar testes muito acoplados a detalhes de implementacao do script.
