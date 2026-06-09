# Issue 012: test(security): cobrir bloqueios de seguranca operacional

## Contexto

Mesmo em rede interna, o sistema deve bloquear usuario inativo, acesso entre empresas e acoes sem permissao.

## Escopo

- Criar testes para usuario inativo sem acesso.
- Criar testes para usuario tentando operar empresa nao vinculada.
- Criar testes para importacao sem permissao.
- Criar testes para classificacao/feedback sem permissao.
- Garantir que bloqueios relevantes gerem auditoria quando aplicavel.

## Criterios de Aceite

- Usuario inativo nao acessa endpoints protegidos.
- Usuario sem empresa nao importa, classifica ou corrige dados dela.
- Bloqueios retornam status HTTP adequado.
- Eventos de acesso negado sao registrados quando aplicavel.

## Testes Esperados

- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.
- Cobertura de auth, importacao, classificacao e feedback.

## TDD

Obrigatorio.

## Riscos

- Confiar apenas na rede interna e deixar autorizacao frouxa.
- Falhar silenciosamente sem evento auditavel.
