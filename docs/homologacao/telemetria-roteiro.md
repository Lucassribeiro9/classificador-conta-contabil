# Roteiro de homologação - telemetria operacional privada

Este roteiro valida a telemetria operacional privada da esteira de agentes.
Use somente ambiente controlado e uma base SQLite local fora do repositório
público.

## Objetivo

Confirmar que a esteira registra apenas metadados operacionais permitidos,
mantém detalhes por até 90 dias, gera agregados mensais e não altera o
resultado oficial da entrega quando a telemetria falha.

## Pré-requisitos

- Branch da issue #380 publicada em ambiente local ou HML controlado.
- Banco privado configurado por `AGENT_TELEMETRY_DB_PATH`.
- Caminho do banco fora do repositório.
- Evento de teste sem dados de cliente, prompts, respostas, diffs, logs brutos
  ou segredos.

## Cenários

### 1. Telemetria desabilitada

1. Remova `AGENT_TELEMETRY_DB_PATH` do ambiente do runner.
2. Execute uma solicitação válida da esteira.
3. Confirme que a entrega segue o fluxo normal.
4. Confirme que nenhum arquivo de telemetria foi criado no repositório.

Resultado esperado: telemetria fica desabilitada e não bloqueia a execução.

### 2. Registro permitido

1. Configure `AGENT_TELEMETRY_DB_PATH` apontando para um caminho privado.
2. Execute uma solicitação válida da esteira.
3. Abra o SQLite privado.
4. Verifique a tabela `telemetry_events`.

Resultado esperado: existem eventos de início e conclusão com campos
operacionais, como execução, repositório, issue, etapa, resultado, tentativas e
código. O registro não deve conter payload, prompt, resposta, diff, conteúdo de
arquivo, log bruto, segredo, URL privada nem dados contábeis.

### 3. Conteúdo proibido

1. Simule um evento de telemetria contendo um campo proibido, como `prompt`,
   `diff`, `raw_log` ou `accounting_data`.
2. Execute a gravação.
3. Consulte o SQLite privado.

Resultado esperado: o evento inteiro é rejeitado e nenhum dado desse evento é
persistido.

### 4. Agregação e limpeza

1. Use relógio controlado ou massa local de teste com eventos antigos e
   recentes.
2. Execute a rotina interna de agregação e limpeza.
3. Consulte `telemetry_events`.
4. Consulte `telemetry_monthly_aggregates`.

Resultado esperado: detalhes com mais de 90 dias são agregados por mês,
repositório, issue, etapa, resultado, código e categoria de comando. Eventos
recentes permanecem detalhados. Os agregados não permitem reconstruir prompts,
respostas, diffs, logs ou dados de cliente.

### 5. Falha de armazenamento

1. Configure um caminho privado indisponível ou simule falha de escrita.
2. Execute uma solicitação válida da esteira.
3. Verifique o resultado oficial retornado ao GitHub/n8n.

Resultado esperado: a falha da telemetria não altera estado oficial, checkpoint,
resultado da entrega ou notificações da esteira.

## Evidências esperadas

- Resultado dos testes automatizados focados de telemetria.
- Resultado da regressão proporcional do runner.
- Caminho privado usado na homologação descrito apenas de forma genérica.
- Captura ou consulta do SQLite sem dados sensíveis.
- Confirmação de que o diff público não contém métricas reais, caminhos
  privados, segredos ou dados de cliente.

## Critério de aprovação

A homologação é aprovada quando todos os cenários acima passam sem exposição de
conteúdo proibido e sem mudança indevida no estado oficial da esteira.
