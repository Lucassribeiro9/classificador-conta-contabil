# Homologação da Central de Revisões

Este roteiro cobre a central genérica da issue #500. Execute em ambiente
descartável ou homologação, com usuários de teste e uma empresa autorizada.
Não use dados contábeis reais. Antes de iniciar, registre commit testado,
ambiente, perfil, evidências, divergências e resultado `APROVADO`,
`REPROVADO` ou `BLOQUEADO`.

## Pré-condições

- Migration `b8c4d2e6f910` aplicada.
- Dois usuários ativos com permissão `operacao` na empresa e um usuário ativo
  com `admin_empresa` (ou admin global).
- Acesso ao frontend e à API do mesmo ambiente.
- Token obtido por login e fornecido ao `curl` sem gravá-lo em arquivos,
  histórico de shell ou evidências compartilhadas.

## Criar pendência sintética

Use o Python e a configuração de banco do ambiente para criar uma pendência
sem conteúdo contábil real. Guarde o ID impresso para a execução e limpeza.

```bash
./venv/bin/python - <<'PY'
from uuid import uuid4

from core.database import SessionLocal
from core.review_items import create_review_item

company_id = int(input("ID da empresa de teste: "))
key = f"homologacao-central:{uuid4()}"
with SessionLocal() as session:
    item = create_review_item(
        session,
        empresa_id=company_id,
        source_type="homologacao",
        grouping_key=key,
        summary="Pendência sintética para homologação",
        criticality="high",
        evidence=[{
            "source_type": "roteiro",
            "source_id": key,
            "summary": "Evidência sintética sem dados contábeis",
        }],
    )
    session.commit()
    print(f"review_item_id={item.id}")
PY
```

## Cenários

1. Faça login como operador autorizado e abra `/empresas/{empresa_id}/revisoes`.
   Confirme que a pendência sintética aparece com criticidade, origem, resumo e
   referência da evidência.
2. Faça login como segundo operador. Dispare, quase ao mesmo tempo, `POST
   /api/v1/companies/{company_id}/review-items/{item_id}/claim` com os dois
   tokens. Confirme um `200` e um `409`; apenas um usuário deve ficar como
   responsável.
3. Como responsável, use **Liberar** e confirme o retorno a `pending`. Assuma
   novamente e use **Resolver**; confirme que sai da fila aberta e aparece no
   filtro Resolvidas.
4. Crie outra pendência sintética, assuma e descarte com justificativa. Como
   usuário `admin_empresa`, abra o filtro Descartadas, reabra com justificativa
   e confirme status `pending`, sem responsável.
5. Crie outra pendência, assuma como operador e reatribua como `admin_empresa`
   a outro usuário com acesso operacional. Confirme o novo responsável e que o
   primeiro operador não consegue liberar ou resolver o claim novo.
6. Verifique eventos `review_item.claimed`, `released`, `resolved`, `dismissed`,
   `reassigned` e `reopened` na auditoria. Metadados devem conter apenas ID da
   transição e estados anterior/novo; justificativas ficam no histórico
   específico da pendência.
7. Repita a listagem com usuário sem permissão para a empresa e confirme `403`.
   Tente consultar um item de outra empresa e confirme que ele não é retornado.

Para as chamadas diretas de API, use tokens de usuários distintos e o mesmo
endpoint de claim mostrado no cenário 2. Registre somente status HTTP e IDs
sintéticos nas evidências, nunca o token.

## Limpeza e rollback

- Após a homologação, remova cada item sintético e seus registros de evidência e
  transição usando uma sessão autenticada no mesmo banco. Os `audit_events`
  permanecem como trilha da homologação.
- A migration é aditiva. Em ambiente sem dados da central, rollback é
  `./venv/bin/alembic downgrade 517a8d4c2e11`.
- Downgrade remove pendências, evidências e justificativas da central. Se já
  houver dados reais, preserve/exporte essas tabelas e faça backup do banco
  antes de qualquer downgrade; não execute rollback destrutivo como rotina de
  recuperação.
