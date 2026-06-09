# Issue 007: feat(audit): auditar importacao do plano de contas

## Contexto

Importacao do plano altera o catalogo unico do escritorio e deve ser rastreavel.

## Escopo

- Registrar `chart_import.started`.
- Registrar `chart_import.completed`.
- Registrar `chart_import.failed`.
- Incluir usuario executor.
- Incluir metadados seguros, como contadores de criadas, atualizadas e ignoradas.
- Nao armazenar arquivo completo nem conteudo de planilha.

## Criterios de Aceite

- Inicio da importacao gera evento.
- Sucesso gera evento com contadores.
- Falha gera evento com erro resumido e seguro.
- Metadata nao inclui conteudo completo do arquivo.

## Testes Esperados

- Teste de importacao iniciada.
- Teste de importacao concluida.
- Teste de importacao com falha.
- Teste de sanitizacao de metadata.
- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.

## TDD

Obrigatorio.

## Riscos

- Registrar dados demais do plano.
- Evento de sucesso ficar fora de sincronia com transacao real.
