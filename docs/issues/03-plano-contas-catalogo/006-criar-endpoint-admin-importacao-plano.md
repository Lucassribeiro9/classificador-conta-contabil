# Issue 006: feat(contas): criar endpoint admin de importacao do plano

## Contexto

O plano de contas e catalogo unico do escritorio. A importacao deve ser restrita a usuarios `admin`.

## Escopo

- Criar endpoint de upload/importacao do plano de contas.
- Exigir JWT de usuario admin.
- Aceitar apenas `.xlsx`.
- Usar parser e servico de importacao.
- Retornar resumo da importacao.
- Bloquear contador/operador.

## Criterios de Aceite

- Admin importa plano com sucesso.
- Usuario nao admin recebe bloqueio.
- Arquivo nao `.xlsx` e rejeitado.
- Resposta informa criadas, atualizadas e invalidas/ignoradas.
- Importacao nao duplica contas em reexecucao.

## Testes Esperados

- Teste admin importando.
- Teste contador/operador bloqueado.
- Teste sem JWT bloqueado.
- Teste arquivo invalido.
- Teste resumo da importacao.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Permitir alteracao do catalogo por usuario nao autorizado.
- Misturar responsabilidade de parser, servico e rota.
