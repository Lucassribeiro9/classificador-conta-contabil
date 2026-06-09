# Issue 003: chore(auth): criar script interno de bootstrap do primeiro admin

## Contexto

O primeiro usuario admin nao deve ser criado por endpoint publico sem autenticacao. A spec determina script interno de bootstrap.

## Escopo

- Criar script/CLI para criar o primeiro admin.
- Receber nome, login/email e senha de forma segura.
- Gerar senha hash.
- Nao recriar admin se login/email ja existir.
- Documentar uso basico do script.

## Criterios de Aceite

- Script cria usuario com papel `admin`.
- Script nao armazena senha em texto puro.
- Reexecutar com mesmo login/email nao duplica usuario.
- Script falha de forma clara quando parametros obrigatorios faltam.

## Testes Esperados

- Teste do fluxo de criacao de admin.
- Teste de reexecucao sem duplicidade.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Recomendado.

## Riscos

- Expor senha em logs ou historico de shell.
- Criar usuario admin duplicado.
