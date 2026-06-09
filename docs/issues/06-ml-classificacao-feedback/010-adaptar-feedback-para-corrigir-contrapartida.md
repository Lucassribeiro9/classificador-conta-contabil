# Issue 010: feat(feedback): corrigir contrapartida no lancamento existente

## Contexto

Feedback humano deve corrigir o lancamento/classificacao existente e nao criar exemplo duplicado de treino.

## Escopo

- Adaptar endpoint ou servico de feedback para contrapartida.
- Exigir usuario autenticado e permissao na empresa.
- Validar que a conta corrigida existe, e analitica e vinculada a empresa.
- Atualizar o lancamento existente com a contrapartida corrigida.
- Marcar revisao como resolvida quando aplicavel.
- Nao criar linha duplicada de treino.

## Criterios de Aceite

- Feedback altera o registro existente.
- Feedback respeita empresa e usuario.
- Conta corrigida precisa ser candidata valida.
- Proximo treino usa dado corrigido.
- Nao ha duplicidade de exemplo por feedback.

## Testes Esperados

- Teste de feedback bem-sucedido.
- Teste de usuario sem acesso.
- Teste de conta sintetica rejeitada.
- Teste de conta nao vinculada rejeitada.
- Teste de proximo treino usando correcao.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Feedback virar dado duplicado e enviesar treino.
- Permitir correcao para conta invalida.
