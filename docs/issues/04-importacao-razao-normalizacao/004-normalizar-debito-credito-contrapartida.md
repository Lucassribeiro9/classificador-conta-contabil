# Issue 004: feat(razao): normalizar debito credito e contrapartida

## Contexto

Debito e credito devem ser interpretados em relacao a conta do bloco do razao. A conta de contrapartida vai para o lado oposto.

## Escopo

- Implementar normalizacao de uma linha parseada.
- Se houver debito: conta debito = conta origem; conta credito = contrapartida.
- Se houver credito: conta debito = contrapartida; conta credito = conta origem.
- Preservar conta origem e conta contrapartida.
- Marcar direcao como `debito` ou `credito`.

## Criterios de Aceite

- Linha com debito normaliza corretamente.
- Linha com credito normaliza corretamente.
- Conta origem e contrapartida sao preservadas.
- Linha sem debito/credito valido gera warning ou erro de normalizacao.
- Nunca assume que debito sempre significa banco.

## Testes Esperados

- Teste de debito no bloco.
- Teste de credito no bloco.
- Teste de linha sem valor.
- Teste de preservacao de origem e contrapartida.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Inverter debito/credito.
- Perder a conta de origem ao manter apenas par final.
