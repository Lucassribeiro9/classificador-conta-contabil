# Spec: UX e Fluxos da Interface Grafica Interna

## Objetivo

Definir os fluxos e telas do MVP da interface grafica interna do classificador contabil.

A interface deve permitir que operadores e contadores usem os fluxos ja existentes da API sem depender de chamadas manuais. O foco da primeira homologacao e validar a operacao real: login, escolha de empresa, importacao de movimentos, classificacao, revisao, aprovacao, rejeicao e consulta de razao/contas vinculadas.

## Tech Stack

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- API FastAPI existente

## Telas do MVP

1. Login.
2. Empresas.
3. Operacao da Empresa.
4. Importar Movimentos.
5. Lote de Movimentos.
6. Revisar Movimento.
7. Razao e Contas Vinculadas.

## Fluxos Principais

### Login

1. Usuario informa credenciais.
2. Interface chama a API de autenticacao.
3. Token JWT e armazenado no estado seguro definido pela spec tecnica.
4. Usuario e redirecionado para Empresas.

Nao ha fluxo de "esqueci minha senha" no MVP. Problemas de acesso devem orientar contato com o administrador.

### Empresas

1. Usuario autenticado acessa a lista de empresas.
2. Usuario comum ve apenas empresas vinculadas.
3. Admin ve todas as empresas.
4. Se nao houver empresas disponiveis, a tela exibe estado vazio orientando contato com o administrador.
5. Ao escolher uma empresa, usuario entra em Operacao da Empresa.

### Operacao da Empresa

A tela funciona como hub operacional da empresa selecionada.

Deve mostrar:

- identificacao da empresa;
- resumo de razao importado;
- quantidade de contas vinculadas;
- resumo de movimentos operacionais;
- status basico do modelo/classificacao;
- atalhos para importar movimentos, abrir lotes, classificar pendentes e consultar razao/contas.

Deve alertar quando nao houver razao importado ou quando nao houver base suficiente para classificacao.

### Importar Movimentos

1. Usuario seleciona arquivo `.xlsx`.
2. Interface envia arquivo para API.
3. Ao concluir, tela mostra resumo do lote.
4. Usuario decide se abre o lote ou permanece na tela.

O resumo deve exibir status, linhas lidas, movimentos importados, warnings e bloqueios.

### Lote de Movimentos

A visualizacao principal deve ser uma lista/tabela operacional.

Deve permitir:

- filtrar por status;
- selecionar movimentos;
- abrir revisao individual;
- aprovar selecionados;
- rejeitar selecionados;
- enviar selecionados para revisao;
- disparar classificacao dos pendentes da empresa.

A acao "Classificar pendentes" deve deixar claro que atua sobre todos os pendentes da empresa, nao apenas sobre o lote aberto.

### Revisar Movimento

Deve mostrar os dados do movimento, sugestao de conta, confianca, warnings e historico relevante.

A busca de conta deve priorizar contas vinculadas a empresa e permitir busca no plano completo. Quando o usuario escolher conta ainda nao vinculada, a interface deve avisar que o vinculo sera criado conforme regra do backend.

O motivo de rejeicao e opcional.

### Razao e Contas Vinculadas

Tela de apoio para consulta.

Deve permitir:

- listar lotes de razao importados;
- consultar lancamentos normalizados;
- listar contas vinculadas a empresa;
- buscar por codigo ou nome;
- exibir quantidade de lancamentos e ultima utilizacao quando a API fornecer esses dados.

## Estados e Mensagens

- Carregando.
- Vazio.
- Erro de rede.
- Acesso negado.
- Sessao expirada.
- Sem empresas vinculadas.
- Importacao concluida.
- Importacao com warnings.
- Importacao bloqueada.

Mensagens devem ser curtas, operacionais e orientadas a proxima acao.

## Boundaries

- Sempre: manter empresa selecionada visivel no contexto da operacao.
- Sempre: respeitar permissoes retornadas pela API.
- Sempre: exigir revisao humana antes de decisoes finais em movimentos.
- Sempre: preservar a direcao visual aprovada no Figma.
- Perguntar antes: alterar telas do MVP aprovado.
- Perguntar antes: adicionar fluxo administrativo ao MVP.
- Nunca: exibir empresas sem permissao para usuario comum.
- Nunca: auto-aprovar sugestoes da ML no MVP.
- Nunca: transformar movimento operacional em razao canonico pela interface.

## Success Criteria

- As sete telas do MVP estao descritas com responsabilidades claras.
- Fluxos de login, empresa, importacao, classificacao, revisao e consulta estao definidos.
- Estados vazios, erros e acesso negado estao previstos.
- Acoes em lote seguem as regras aprovadas.
- A spec pode gerar issues pequenas de frontend.

## Proximas Issues Recomendadas

1. `spec(frontend): validar UX do MVP contra Figma`
2. `feat(frontend): criar shell autenticado e rotas base`
3. `feat(frontend): implementar login simples`
4. `feat(frontend): implementar tela de empresas`
5. `feat(frontend): implementar hub operacional da empresa`
6. `feat(frontend): implementar importacao de movimentos`
7. `feat(frontend): implementar lista e acoes do lote`
8. `feat(frontend): implementar revisao individual`
9. `feat(frontend): implementar consulta de razao e contas vinculadas`

## Open Questions

- O backend ja expoe todos os metadados necessarios para os resumos da tela Operacao da Empresa?
- A consulta de razao/contas vinculadas deve ter paginacao obrigatoria no MVP?
