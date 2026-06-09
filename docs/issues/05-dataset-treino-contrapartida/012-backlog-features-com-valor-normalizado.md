# Issue 012: backlog(dataset): avaliar features com valor normalizado

## Contexto

O PRD menciona valor como possivel contexto, mas a spec 05 decidiu excluir valor monetario bruto das features iniciais. No futuro, valor normalizado ou faixas podem ser avaliados com cuidado.

## Escopo

- Registrar possibilidade futura de usar valor normalizado, bins ou sinais derivados.
- Avaliar risco de overfitting e vazamento de padroes especificos.
- Nao implementar nesta fase.

## Criterios de Aceite

- Backlog registra que valor bruto segue fora da primeira versao.
- Possiveis abordagens futuras ficam descritas sem alterar o builder atual.

## Testes Esperados

- A definir quando implementada.

## TDD

Obrigatorio quando implementada.

## Riscos

- Introduzir feature que memoriza clientes ou valores recorrentes.
- Piorar generalizacao do modelo em vez de melhorar.
