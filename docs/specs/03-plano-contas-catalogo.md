# Spec: Catalogo Unico do Plano de Contas

## Objetivo

Importar e manter o plano de contas do escritorio como catalogo unico. O catalogo deve conter codigo, classificacao, nome, tipo e grau, preservando a diferenca entre contas sinteticas e analiticas.

Sucesso significa que o sistema consegue importar o arquivo de plano de contas, atualizar registros existentes sem duplicidade e expor contas para uso por importadores, dataset e ML.

## Tech Stack

- openpyxl para leitura de `.xlsx`.
- SQLAlchemy para persistencia.
- Alembic para schema.
- FastAPI para endpoint futuro de importacao.
- Pytest para parser e idempotencia.

## Comandos

- Testes: `.\venv\Scripts\python.exe -m pytest -q tests`
- Migrations: `.\venv\Scripts\python.exe -m alembic upgrade head`
- API local: `.\venv\Scripts\python.exe -m uvicorn api.main:app --reload`

## Project Structure

- `core/models.py`: modelo de conta contabil.
- `core/`: servico/parser de plano de contas.
- `api/routes/`: endpoint de importacao e consulta.
- `api/schemas.py`: schemas de conta e resultado de importacao.
- `tests/`: testes de parser, API e persistencia.

## Code Style

Parser deve retornar objetos normalizados antes de persistir. Persistencia deve ser separada da leitura do arquivo.

Exemplo de shape esperado:

```python
{
    "codigo": 10046,
    "classificacao": "1.1.01.01.02.10046",
    "nome": "BCO. SANTANDER ( BRASIL ) S.A.",
    "tipo": "A",
    "grau": 6,
    "is_financial_origin": True,
}
```

## Testing Strategy

- Testar parser ignorando cabecalho do relatorio.
- Testar leitura de codigo, tipo, classificacao, nome e grau.
- Testar identificacao de contas sinteticas e analiticas.
- Testar importacao idempotente.
- Testar atualizacao de nome/classificacao quando a conta ja existe.
- Testar rejeicao de linhas incompletas ou invalidas com mensagem clara.
- Testar que contas ausentes em nova importacao permanecem ativas.
- Testar inferencia inicial de contas candidatas a origem financeira.
- Testar bloqueio de importacao por usuario que nao seja admin.

## Boundaries

- Sempre: tratar `codigo` como identificador unico do catalogo.
- Sempre: manter contas sinteticas para hierarquia, mas nao usa-las como alvo classificavel.
- Sempre: separar parse de persistencia.
- Sempre: manter contas ausentes em uma nova importacao como ativas por padrao.
- Sempre: restringir importacao do plano de contas a usuarios `admin`.
- Sempre: identificar contas de banco/caixa/aplicacao por heuristica inicial e flag persistida.
- Sempre: permitir que a flag financeira seja revisada futuramente sem alterar os campos oficiais do plano.
- Perguntar antes: excluir ou inativar contas que sumiram de uma nova importacao.
- Perguntar antes: permitir edicao manual de conta no catalogo.
- Nunca: criar catalogo separado por cliente nesta fase.
- Nunca: permitir que conta sintetica seja alvo de classificacao ou contrapartida prevista.
- Nunca: editar manualmente `codigo`, `classificacao`, `nome`, `tipo` ou `grau` na primeira fase.

## Success Criteria

- Plano de contas e importado como catalogo unico.
- Reimportacao nao duplica contas.
- Contas analiticas e sinteticas sao distinguiveis.
- Contas podem ser usadas por vinculos de empresa e dataset.
- Contas ausentes em nova importacao nao sao inativadas automaticamente.
- Contas candidatas a origem financeira possuem flag persistida.
- Importacao do plano exige usuario admin.
- Testes cobrem parser e idempotencia.

## Decisoes Aprovadas

- O catalogo sera unico para o escritorio.
- `codigo` sera o identificador unico do catalogo.
- Contas sinteticas e analiticas serao importadas.
- Apenas contas analiticas (`tipo = A`) serao lancaveis/classificaveis.
- Reimportacao sera idempotente: cria contas novas e atualiza existentes.
- Contas ausentes em nova importacao permanecem ativas.
- Contas ausentes nao serao excluidas nem inativadas automaticamente.
- A importacao do plano sera restrita a usuarios `admin`.
- Contas de banco/caixa/aplicacao serao identificadas por heuristica inicial e flag persistida.
- Campos oficiais do plano (`codigo`, `classificacao`, `nome`, `tipo`, `grau`) nao terao edicao manual na primeira fase.
- Parser e persistencia permanecem separados.

## Open Questions

- Qual sera o nome final da flag financeira: `is_financial_origin`, `is_conta_financeira` ou outro?
- A heuristica financeira usara apenas `nome` e `classificacao`, ou tambem `grau`?
- A revisao manual da flag financeira entra nesta fase ou apenas em backlog?
