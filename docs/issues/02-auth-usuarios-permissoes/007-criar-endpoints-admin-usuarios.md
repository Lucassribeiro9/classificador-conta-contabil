# Issue 007: feat(auth): criar endpoints admin de usuarios

## Contexto

Apenas usuarios `admin` podem gerenciar usuarios na primeira versao. O sistema precisa de endpoints para criar, listar e ativar/desativar usuarios internos.

## Escopo

- Criar endpoint admin para criar usuario.
- Criar endpoint admin para listar usuarios.
- Criar endpoint admin para ativar/desativar usuario.
- Garantir que senha seja armazenada com hash.
- Bloquear acesso de nao admin.
- Nao implementar reset de senha nesta issue.

## Criterios de Aceite

- Admin cria usuario com papel permitido.
- Admin lista usuarios.
- Admin desativa e reativa usuario.
- Nao admin nao acessa endpoints administrativos.
- Senha nunca aparece em resposta.

## Testes Esperados

- Teste admin criando usuario.
- Teste nao admin bloqueado.
- Teste listar usuarios sem senha hash exposta.
- Teste desativar usuario.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Expor senha hash em resposta.
- Permitir criacao de admin por usuario nao autorizado.
