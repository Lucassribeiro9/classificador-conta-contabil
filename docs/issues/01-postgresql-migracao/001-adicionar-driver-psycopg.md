# Issue 001: chore(postgres): adicionar driver psycopg

## Contexto

A spec de PostgreSQL decidiu usar `psycopg` v3 com URLs no formato `postgresql+psycopg://...`. O projeto ainda precisa declarar essa dependencia para que SQLAlchemy consiga abrir conexoes PostgreSQL.

## Escopo

- Adicionar o driver PostgreSQL `psycopg` ao arquivo de dependencias do projeto.
- Manter as dependencias existentes intactas.
- Nao alterar ainda a configuracao de banco.

## Criterios de Aceite

- `psycopg` esta listado nas dependencias.
- A versao escolhida e compativel com Python 3.12 e SQLAlchemy 2.
- Nenhuma dependencia relacionada a SQLite e removida.

## Testes Esperados

- Rodar `.\venv\Scripts\python.exe -m pytest -q tests`.
- Esta issue nao exige teste novo obrigatorio, pois apenas declara dependencia.

## TDD

Nao obrigatorio.

## Riscos

- Escolher pacote errado, como `psycopg2`, pode divergir da decisao da spec.
- Atualizar dependencias em massa pode introduzir ruido no PR.
