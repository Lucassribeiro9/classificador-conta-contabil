# Issue 008: feat(razao): bloquear reimportacao do mesmo file_hash

## Contexto

Se o mesmo arquivo ja foi importado com sucesso para a mesma empresa, a reimportacao deve ser bloqueada por `file_hash`.

## Escopo

- Calcular hash do arquivo enviado.
- Armazenar `file_hash` no lote.
- Bloquear novo lote com mesmo `file_hash` e empresa quando ja houver importacao bem-sucedida.
- Permitir que arquivos diferentes ainda usem deduplicacao por chave de lancamento.

## Criterios de Aceite

- Primeiro upload de arquivo e aceito.
- Segundo upload do mesmo arquivo para mesma empresa e bloqueado.
- Mesmo arquivo para outra empresa segue regra separada.
- Arquivo diferente nao e bloqueado por hash, mas pode deduplicar linhas.

## Testes Esperados

- Teste de primeiro upload.
- Teste de reupload mesma empresa.
- Teste de mesmo hash em outra empresa.
- Teste de arquivo diferente.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Bloquear reprocessamento necessario sem caminho de recuperacao.
- Calcular hash de forma inconsistente.
