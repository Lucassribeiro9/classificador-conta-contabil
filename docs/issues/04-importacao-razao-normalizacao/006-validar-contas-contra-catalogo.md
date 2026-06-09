# Issue 006: feat(razao): validar contas do razao contra catalogo

## Contexto

O plano de contas e catalogo canonico. Lancamentos cuja conta de origem ou contrapartida nao exista no catalogo nao devem ser persistidos como validos.

## Escopo

- Validar conta de origem contra catalogo.
- Validar conta de contrapartida contra catalogo.
- Gerar warning/erro para conta ausente.
- Impedir persistencia como lancamento valido quando conta estiver ausente.
- Nao criar contas automaticamente a partir do razao.

## Criterios de Aceite

- Lancamento com contas existentes e aceito.
- Conta origem inexistente gera warning/erro.
- Contrapartida inexistente gera warning/erro.
- Lancamento invalido nao e persistido como valido.

## Testes Esperados

- Teste com contas existentes.
- Teste com origem inexistente.
- Teste com contrapartida inexistente.
- Teste que conta ausente nao cria conta nova.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Criar conta automaticamente e contaminar catalogo unico.
- Persistir lancamento invalido como dado de treino.
