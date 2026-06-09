# Issue 009: feat(razao): vincular contas usadas a empresa

## Contexto

Contas validas encontradas no razao devem ser vinculadas automaticamente a empresa para registrar o uso real por cliente.

## Escopo

- Criar ou atualizar vinculo empresa-conta para contas validas do razao.
- Considerar conta de origem e contrapartida.
- Atualizar metadados simples como ultima utilizacao ou contagem, se ja definidos.
- Nao implementar tela de visualizacao nesta issue.

## Criterios de Aceite

- Conta de origem valida fica vinculada a empresa.
- Conta de contrapartida valida fica vinculada a empresa.
- Reimportacao nao duplica vinculos.
- Vinculo respeita empresa correta.

## Testes Esperados

- Teste de vinculo de origem.
- Teste de vinculo de contrapartida.
- Teste de idempotencia.
- Teste de isolamento por empresa.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Vincular conta a empresa errada.
- Criar duplicidade de vinculo.
