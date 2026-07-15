# Spec: Homologacao e Massa Sanitizada

## Objetivo

Definir a primeira homologacao da interface grafica interna com foco em operador/contador e dados sanitizados.

A homologacao deve validar o fluxo operacional real sem expor dados sensiveis de clientes.

## Escopo

Incluido:

- massa ficticia/sanitizada de plano de contas;
- massa ficticia/sanitizada de razao;
- massa ficticia/sanitizada de movimentos operacionais;
- usuario admin para preparacao;
- usuario operador/contador para teste;
- empresas de teste com permissoes vinculadas;
- checklist de aceite da interface.

Fora de escopo:

- uso de dados reais na primeira rodada;
- carga completa historica;
- homologacao de CRUD admin;
- OFX;
- PDF/OCR;
- exportacao TXT/OFX para Dominio.

## Dados Necessarios

### Plano de Contas

Deve conter:

- codigos validos;
- nomes sanitizados;
- contas analiticas e sinteticas;
- contas financeiras de banco, caixa ou aplicacao;
- contas de contrapartida suficientes para testar classificacao.

### Razao

Deve conter:

- CNPJ/CPF sanitizado coerente com empresa de teste;
- periodo controlado;
- blocos de conta;
- debitos e creditos;
- contrapartidas existentes no plano;
- volume suficiente para treinar/classificar exemplos simples;
- casos com warnings nao bloqueantes quando util.

### Movimentos Operacionais

Deve conter:

- CNPJ/CPF coerente com empresa de teste;
- data;
- codigo dominio quando aplicavel;
- conta financeira/origem;
- historico;
- valor;
- exemplos que gerem sugestoes confiaveis;
- exemplos que exijam revisao;
- exemplos com warning recuperavel.

## Estrutura Recomendada

```text
tests/fixtures/homologacao/
  plano_contas_hml.xlsx
  razao_hml.xlsx
  movimentos_operacionais_hml.xlsx

scripts/
  seed_homologacao.py
```

O script de seed deve ser criado em issue propria. Esta spec apenas define o contrato.

## Checklist de Homologacao

1. Admin prepara ambiente, usuarios, empresas e permissoes.
2. Operador faz login.
3. Operador visualiza empresas permitidas.
4. Operador acessa empresa de teste.
5. Operador consulta contexto de razao e contas vinculadas.
6. Operador importa movimentos `.xlsx`.
7. Sistema exibe resumo de importacao.
8. Operador abre lote.
9. Operador classifica pendentes da empresa.
10. Operador revisa sugestoes em lista.
11. Operador aprova selecionados elegiveis.
12. Operador rejeita movimento com ou sem motivo.
13. Operador revisa movimento individual e troca conta.
14. Sistema preserva isolamento por empresa.
15. Evidencias sao registradas.

## Evidencias Esperadas

- Versao/branch testada.
- Data da homologacao.
- Usuario de teste.
- Empresa de teste.
- Arquivos sanitizados usados.
- Resultado dos comandos de validacao.
- Prints ou logs curtos quando ajudarem.
- Lista de falhas bloqueantes.
- Lista de melhorias futuras.

## Validacoes Tecnicas Minimas

- Backend tests relevantes verdes.
- Falhas conhecidas tratadas ou justificadas.
- Frontend build verde.
- Frontend typecheck verde.
- Frontend lint verde.
- API `/health` respondendo.
- Tela de login carregando.
- Banco de homologacao separado de producao.

## Boundaries

- Sempre: usar dados sanitizados na primeira homologacao.
- Sempre: manter homologacao separada de producao.
- Sempre: registrar evidencias.
- Sempre: separar falhas bloqueantes de melhorias.
- Perguntar antes: usar dados reais.
- Perguntar antes: abrir ambiente fora da rede interna.
- Nunca: versionar dados sensiveis.
- Nunca: homologar producao diretamente.
- Nunca: tratar melhoria cosmetica como bloqueio sem impacto operacional.

## Success Criteria

- Massa de homologacao esta definida em termos de plano, razao e movimentos.
- Fluxo operador/contador possui checklist objetivo.
- Riscos de dados sensiveis estao mitigados.
- Criterios minimos para liberar teste com usuarios estao documentados.

## Proximas Issues Recomendadas

1. `test(homologacao): criar fixtures sanitizadas de plano razao e movimentos`
2. `chore(homologacao): criar seed de dados sanitizados`
3. `docs(homologacao): criar roteiro de teste operador contador`
4. `chore(homologacao): configurar ambiente hml separado`
5. `test(homologacao): validar smoke test da aplicacao completa`

## Open Questions

- O seed de homologacao deve usar apenas API publica ou pode usar servicos internos controlados?

## Decisoes Aprovadas Apos Issue #304

- A empresa ficticia padrao e `EMPRESA MODELO HOMOLOGACAO LTDA`.
- O CNPJ sanitizado e deliberadamente invalido e `22.333.444/0001-55`.
- O codigo Dominio da massa e `7701`.
