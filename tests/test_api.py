"""
Testes da API de Classificação de Contas Contábeis.
Testa endpoints de empresas, transações, classificação e feedback.
"""


class TestHealth:
    """Testes do endpoint de health check."""

    def test_health_check(self, client):
        """Verifica se a API está online."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["database"] == "online"
        assert "api_version" in data

    def test_root_endpoint(self, client):
        """Verifica endpoint raiz."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()


class TestCompanies:
    """Testes dos endpoints de empresas."""

    def test_create_company(self, client, empresa_data, admin_headers):
        """Testa criação de empresa."""
        response = client.post("/api/v1/companies", json=empresa_data, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["nome_empresa"] == empresa_data["nome_empresa"]
        assert data["cnpj_cpf"] == empresa_data["cnpj_cpf"]
        assert "api_key" in data
        assert data["api_key"].startswith("sk_")

    def test_create_company_with_mask_normalizes_document(self, client, admin_headers):
        """Testa criação com máscara e persistência normalizada."""
        payload = {
            "nome_empresa": "Empresa Máscara LTDA",
            "cnpj_cpf": "12.345.678/0001-90",
            "cod_dominio": 1010,
        }
        response = client.post("/api/v1/companies", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["cnpj_cpf"] == "12345678000190"

    def test_create_company_duplicate_cnpj(self, client, empresa_data, admin_headers):
        """Testa que não é possível criar empresa com CNPJ duplicado."""
        client.post("/api/v1/companies", json=empresa_data, headers=admin_headers)
        response = client.post("/api/v1/companies", json=empresa_data, headers=admin_headers)
        assert response.status_code == 409
        assert "Documento já cadastrado" in response.json()["detail"]

    def test_create_company_duplicate_document_masked_unmasked(self, client, admin_headers):
        """Testa duplicidade de documento com e sem máscara."""
        payload_masked = {
            "nome_empresa": "Empresa A LTDA",
            "cnpj_cpf": "12.345.678/0001-90",
            "cod_dominio": 1011,
        }
        payload_unmasked = {
            "nome_empresa": "Empresa B LTDA",
            "cnpj_cpf": "12345678000190",
            "cod_dominio": 1012,
        }
        first_response = client.post("/api/v1/companies", json=payload_masked, headers=admin_headers)
        assert first_response.status_code == 200

        second_response = client.post("/api/v1/companies", json=payload_unmasked, headers=admin_headers)
        assert second_response.status_code == 409
        assert "Documento já cadastrado" in second_response.json()["detail"]

    def test_create_company_invalid_document_size(self, client, admin_headers):
        """Testa erro de validação para cnpj_cpf com tamanho inválido."""
        payload = {
            "nome_empresa": "Empresa Inválida LTDA",
            "cnpj_cpf": "12.345.678/0001",
            "cod_dominio": 1013,
        }
        response = client.post("/api/v1/companies", json=payload, headers=admin_headers)
        assert response.status_code == 422   
    
    def test_create_company_batch_success(self, client, admin_headers):
        payload = [
        {
            "nome_empresa": "Empresa Batch A",
            "cnpj_cpf": "12.345.678/0001-90",
            "cod_dominio": 3101,
        },
        {
            "nome_empresa": "Empresa Batch B",
            "cnpj_cpf": "98765432100",
            "cod_dominio": 3102,
        },
    ]

        response = client.post("/api/v1/companies/batch", json=payload, headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["cnpj_cpf"] == "12345678000190"
        assert data[1]["cnpj_cpf"] == "98765432100"


    def test_create_company_batch_duplicate_inside_batch(self, client, admin_headers):
        payload = [
        {
            "nome_empresa": "Empresa Batch Dup 1",
            "cnpj_cpf": "12.345.678/0001-90",
            "cod_dominio": 3201,
        },
        {
            "nome_empresa": "Empresa Batch Dup 2",
            "cnpj_cpf": "12345678000190",
            "cod_dominio": 3202,
        },
        ]

        response = client.post("/api/v1/companies/batch", json=payload, headers=admin_headers)
        assert response.status_code == 409
        assert "Documento já cadastrado" in response.json()["detail"]


    def test_create_company_batch_duplicate_against_db(self, client, admin_headers):
        existing = {
        "nome_empresa": "Empresa Existente",
        "cnpj_cpf": "12.345.678/0001-90",
        "cod_dominio": 3301,
        }
        create_response = client.post("/api/v1/companies", json=existing, headers=admin_headers)
        assert create_response.status_code == 200

        payload = [
            {
            "nome_empresa": "Empresa Batch C",
            "cnpj_cpf": "12345678000190",
            "cod_dominio": 3302,
            }
        ]

        response = client.post("/api/v1/companies/batch", json=payload, headers=admin_headers)
        assert response.status_code == 409
        assert "Documento já cadastrado" in response.json()["detail"]


    def test_create_company_batch_invalid_document_returns_422(self, client, admin_headers):
        payload = [
        {
            "nome_empresa": "Empresa Batch Inválida",
            "cnpj_cpf": "12.345.678/0001",
            "cod_dominio": 3401,
        }
        ]

        response = client.post("/api/v1/companies/batch", json=payload, headers=admin_headers)
        assert response.status_code == 422
    def test_create_company_without_admin_token(self, client, empresa_data):
        """Testa que criar empresa sem token de admin retorna erro."""
        response = client.post("/api/v1/companies", json=empresa_data)
        assert response.status_code == 401
        assert "Admin token ausente" in response.json()["detail"]
    def test_create_company_with_invalid_admin_token(self, client, empresa_data):
        """Testa que criar empresa com token de admin inválido retorna erro."""
        response = client.post(
            "/api/v1/companies",
            json=empresa_data,
            headers={"X-Admin-Token": "invalid token"},
        )
        assert response.status_code == 403

    def test_list_companies(self, client, empresa_criada, admin_headers):
        """Testa listagem de empresas."""
        response = client.get("/api/v1/companies", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["nome_empresa"] == empresa_criada["nome_empresa"]

    def test_list_companies_without_admin_token(self, client):
        """Testa que listar empresas sem token de admin retorna erro."""
        response = client.get("/api/v1/companies")
        assert response.status_code == 401
    
    def test_list_companies_with_invalid_admin_token(self, client):
        """Testa que listar empresas com token de admin inválido retorna erro."""
        response = client.get(
            "/api/v1/companies",
            headers={"X-Admin-Token": "invalid_token"},
        )
        assert response.status_code == 403    

    
    def test_get_company_by_id(self, client, empresa_criada):
        """Testa busca de empresa por ID."""
        company_id = empresa_criada["id"]
        response = client.get(f"/api/v1/companies/{company_id}")
        assert response.status_code == 200
        assert response.json()["id"] == company_id

    def test_get_company_not_found(self, client):
        """Testa busca de empresa inexistente."""
        response = client.get("/api/v1/companies/9999")
        assert response.status_code == 404

    def test_deactivate_company(self, client, empresa_criada):
        """Testa desativação de empresa."""
        company_id = empresa_criada["id"]
        response = client.patch(f"/api/v1/companies/{company_id}/deactivate")
        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_activate_company(self, client, empresa_criada):
        """Testa ativação de empresa."""
        company_id = empresa_criada["id"]
        client.patch(f"/api/v1/companies/{company_id}/deactivate")
        response = client.patch(f"/api/v1/companies/{company_id}/activate")
        assert response.status_code == 200
        assert response.json()["is_active"] is True

    def test_deactivate_company_already_inactive(self, client, empresa_criada):
        """Testa erro ao desativar empresa já desativada."""
        company_id = empresa_criada["id"]
        client.patch(f"/api/v1/companies/{company_id}/deactivate")
        response = client.patch(f"/api/v1/companies/{company_id}/deactivate")
        assert response.status_code == 403
        assert "Empresa já está desativada" in response.json()["detail"]

    def test_activate_company_already_active(self, client, empresa_criada):
        """Testa erro ao ativar empresa já ativa."""
        company_id = empresa_criada["id"]
        response = client.patch(f"/api/v1/companies/{company_id}/activate")
        assert response.status_code == 403
        assert "Empresa já está ativa" in response.json()["detail"]

    def test_delete_company_without_admin_token(self, client, empresa_criada):
        """Testa que deletar empresa sem token de admin retorna erro."""
        company_id = empresa_criada["id"]
        response = client.delete(f"/api/v1/companies/{company_id}")
        assert response.status_code == 401
        assert "Admin token ausente" in response.json()["detail"]


    def test_delete_company_with_invalid_admin_token(self, client, empresa_criada):
        """Testa que deletar empresa com token de admin inválido retorna erro."""
        company_id = empresa_criada["id"]
        response = client.delete(
            f"/api/v1/companies/{company_id}",
            headers={"X-Admin-Token": "invalid_token"},
        )
        assert response.status_code == 403
        assert "Admin token inválido" in response.json()["detail"]


    def test_delete_company_with_valid_admin_token(self, client, empresa_criada, admin_headers):
        """Testa deleção de empresa com token admin válido."""
        company_id = empresa_criada["id"]
        response = client.delete(
            f"/api/v1/companies/{company_id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

        # confirma que a empresa foi removida
        get_response = client.get(f"/api/v1/companies/{company_id}")
        assert get_response.status_code == 404


class TestPredict:
    """Testes do endpoint de predição."""

    @staticmethod
    def _patch_ml(monkeypatch): # helper para mockar ML nos testes de predição
        from core.ml_engine import ClassificadorContabil
        monkeypatch.setattr(
            ClassificadorContabil,
            "train_for_company",
            TestPredict._mock_train_for_company,
        )
        monkeypatch.setattr(
            ClassificadorContabil, "predict_inputs", TestPredict._mock_predict_inputs
        )

    @staticmethod
    def _mock_train_for_company(self, company_id):
        return True

    @staticmethod
    def _mock_predict_inputs(self, inputs):
        results = []
        for item in inputs:
            confidence = 0.5 if "incerto" in item["historico"].lower() else 0.9
            results.append(
                {
                    "conta_contabil_predita": 1234,
                    "confidence": confidence,
                    "needs_review": confidence < 0.7,
                    "historico": item["historico"],
                    "cod_banco": item.get("cod_banco"),
                }
            )
        return results

    def test_predict_single_success(self, client, empresa_criada, monkeypatch):
        """Testa predição unitária com sucesso."""
        self._patch_ml(monkeypatch)

        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        payload = {"historico": "Pagamento fornecedor", "cod_banco": 341}

        response = client.post(
            f"/api/v1/companies/{company_id}/predict",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["empresa_id"] == company_id
        assert data["quantidade_processada"] == 1
        assert data["persisted"] is False
        assert len(data["results"]) == 1
        assert data["results"][0]["conta_contabil_predita"] == 1234
        assert data["results"][0]["needs_review"] is False

    def test_predict_batch_success(self, client, empresa_criada, monkeypatch):
        """Testa predição em lote com sucesso."""

        self._patch_ml(monkeypatch)

        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        payload = [
            {"historico": "Recebimento cliente", "cod_banco": 341},
            {"historico": "Pagamento incerto taxa", "cod_banco": 33},
        ]

        response = client.post(
            f"/api/v1/companies/{company_id}/predict",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantidade_processada"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["needs_review"] is False
        assert data["results"][1]["needs_review"] is True

    def test_predict_company_not_found(self, client, empresa_criada, monkeypatch):
        """Testa erro de empresa inexistente."""

        self._patch_ml(monkeypatch)

        api_key = empresa_criada["api_key"]
        response = client.post(
            "/api/v1/companies/9999/predict",
            json={"historico": "Pagamento fornecedor", "cod_banco": 341},
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 404
        assert "Empresa não encontrada" in response.json()["detail"]

    def test_predict_invalid_api_key(self, client, empresa_criada):
        """Testa erro para API key inválida."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/predict",
            json={"historico": "Pagamento fornecedor", "cod_banco": 341},
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403

    def test_predict_company_inactive(self, client, empresa_criada, monkeypatch):
        """Testa erro para empresa desativada."""

        self._patch_ml(monkeypatch)

        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        client.patch(f"/api/v1/companies/{company_id}/deactivate")

        response = client.post(
            f"/api/v1/companies/{company_id}/predict",
            json={"historico": "Pagamento fornecedor", "cod_banco": 341},
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 400
        assert "Empresa está desativada" in response.json()["detail"]

    def test_predict_persist_false_does_not_create_transaction(
        self, client, empresa_criada, monkeypatch
    ):
        """Testa que persist=false não cria transação."""

        self._patch_ml(monkeypatch)

        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        predict_response = client.post(
            f"/api/v1/companies/{company_id}/predict",
            json={"historico": "Pagamento fornecedor", "cod_banco": 341},
            headers={"X-API-Key": api_key},
        )
        assert predict_response.status_code == 200
        assert predict_response.json()["persisted"] is False

        list_response = client.get(
            f"/api/v1/companies/{company_id}/transactions",
            headers={"X-API-Key": api_key},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 0

    def test_predict_persist_true_creates_transaction(
        self, client, empresa_criada, monkeypatch
    ):
        """Testa que persist=true cria transação classificada."""

        self._patch_ml(monkeypatch)

        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        predict_response = client.post(
            f"/api/v1/companies/{company_id}/predict?persist=true",
            json={"historico": "Pagamento fornecedor", "cod_banco": 341},
            headers={"X-API-Key": api_key},
        )
        assert predict_response.status_code == 200
        assert predict_response.json()["persisted"] is True

        list_response = client.get(
            f"/api/v1/companies/{company_id}/transactions",
            headers={"X-API-Key": api_key},
        )
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        assert list_response.json()[0]["conta_contabil"] == 1234
        assert list_response.json()[0]["is_classified"] is True


class TestTransactionsAuth:
    """Testes de autenticação nos endpoints de transações."""

    def test_create_transactions_without_api_key(
        self, client, empresa_criada, transacao_data
    ):
        """Testa que criar transações sem API key retorna erro."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
        )
        assert response.status_code == 401  # Validation error - header obrigatório

    def test_create_transactions_with_invalid_api_key(
        self, client, empresa_criada, transacao_data
    ):
        """Testa que criar transações com API key inválida retorna erro 403."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403
        assert "API Key inválida" in response.json()["detail"]

    def test_create_transactions_with_valid_api_key(
        self, client, empresa_criada, transacao_data
    ):
        """Testa criação de transações com API key válida."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        # Ajusta empresa_id nas transações
        for transacao in transacao_data:
            transacao["empresa_id"] = company_id

        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["historico"] == transacao_data[0]["historico"]

    def test_list_transactions_without_api_key(self, client, empresa_criada):
        """Testa que listar transações sem API key retorna erro."""
        company_id = empresa_criada["id"]
        response = client.get(f"/api/v1/companies/{company_id}/transactions")
        assert response.status_code == 401

    def test_list_transactions_with_valid_api_key(self, client, empresa_criada):
        """Testa listagem de transações com API key válida."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        response = client.get(
            f"/api/v1/companies/{company_id}/transactions",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_transactions_duplicate_against_db_returns_409(
        self, client, empresa_criada, transacao_data
    ):
        """Testa que transação duplicada no banco retorna conflito."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        first_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert first_response.status_code == 200

        second_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert second_response.status_code == 409
        assert (
            "Transação duplicada para os mesmos dados de empresa, data, histórico, valor, conta e banco"
            in second_response.json()["detail"]
        )

    def test_create_transactions_duplicate_inside_payload_returns_409(
        self, client, empresa_criada, transacao_data
    ):
        """Testa que duplicidade no mesmo payload é bloqueada."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        duplicated_payload = [transacao_data[0], transacao_data[0]]

        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=duplicated_payload,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 409
        assert (
            "Transação duplicada para os mesmos dados de empresa, data, histórico, valor, conta e banco"
            in response.json()["detail"]
        )

    def test_create_transactions_with_different_conta_contabil_returns_200(
        self, client, empresa_criada, transacao_data
    ):
        """Permite transações com mesma base, mas conta contábil diferente."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        payload = [dict(transacao_data[0]), dict(transacao_data[0])]
        payload[0]["conta_contabil"] = None
        payload[1]["conta_contabil"] = 1234

        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_create_transactions_with_different_cod_banco_returns_200(
        self, client, empresa_criada, transacao_data
    ):
        """Permite transações com mesma base, mas banco diferente."""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        payload = [dict(transacao_data[0]), dict(transacao_data[0])]
        payload[0]["cod_banco"] = None
        payload[1]["cod_banco"] = 341

        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=payload,
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 200
        assert len(response.json()) == 2


class TestTransactionsDeleteBatch:
    """Testes de exclusão em lote de transações."""

    def test_delete_batch_requires_admin_token(
        self, client, empresa_criada, transacao_data
    ):
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200

        response = client.delete(
            f"/api/v1/companies/{company_id}/transactions",
            headers={"X-API-Key": api_key},
        )
        assert response.status_code == 401
        assert "Admin token ausente" in response.json()["detail"]

    def test_delete_batch_requires_api_key(
        self, client, empresa_criada, transacao_data, admin_headers
    ):
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200

        response = client.delete(
            f"/api/v1/companies/{company_id}/transactions",
            headers=admin_headers,
        )
        assert response.status_code == 401
        assert "API Key ausente" in response.json()["detail"]

    def test_delete_batch_forbidden_with_api_key_from_another_company(
        self, client, empresa_criada, transacao_data, admin_headers
    ):
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200

        empresa_y_payload = {
            "nome_empresa": "EMPRESA Y DELETE LTDA",
            "cnpj_cpf": "08455780000299",
            "cod_dominio": 8011,
        }
        empresa_y_response = client.post(
            "/api/v1/companies", json=empresa_y_payload, headers=admin_headers
        )
        assert empresa_y_response.status_code == 200
        api_key_outra_empresa = empresa_y_response.json()["api_key"]

        response = client.delete(
            f"/api/v1/companies/{company_id}/transactions",
            headers={
                "X-Admin-Token": admin_headers["X-Admin-Token"],
                "X-API-Key": api_key_outra_empresa,
            },
        )
        assert response.status_code == 403
        assert "Acesso negado" in response.json()["detail"]

    def test_delete_batch_success_returns_deleted_items(
        self, client, empresa_criada, transacao_data, admin_headers
    ):
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]

        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200
        created_transactions = create_response.json()

        response = client.delete(
            f"/api/v1/companies/{company_id}/transactions",
            headers={
                "X-Admin-Token": admin_headers["X-Admin-Token"],
                "X-API-Key": api_key,
            },
        )
        assert response.status_code == 200
        deleted_transactions = response.json()
        assert len(deleted_transactions) == len(created_transactions)
        assert {item["id"] for item in deleted_transactions} == {
            item["id"] for item in created_transactions
        }

        list_response = client.get(
            f"/api/v1/companies/{company_id}/transactions",
            headers={"X-API-Key": api_key},
        )
        assert list_response.status_code == 200
        assert list_response.json() == []


class TestFeedbackAuth:
    """Testes de autenticação no endpoint de feedback."""

    def test_feedback_without_api_key(self, client):
        """Testa que feedback sem API key retorna erro."""
        response = client.patch(
            "/api/v1/transactions/1/feedback",
            json={"conta_contabil": 1234},
        )
        assert response.status_code == 401

    def test_feedback_with_invalid_api_key(self, client):
        """Testa que feedback com API key inválida retorna erro 403."""
        response = client.patch(
            "/api/v1/transactions/1/feedback",
            json={"conta_contabil": 1234},
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403


class TestFeedbackScope:
    """Testes por empresa no endpoint de feedback."""

    def test_feedback_same_company(self, client, empresa_criada):
        """Empresa da transação consegue aplicar feedback"""
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        # payload de transação
        transaction_payload = [
            {
                "data": "2022-01-01",
                "cod_banco": 341,
                "historico": "Pagamento fornecedor",
                "empresa_id": company_id,
                "valor": 100.0,
                "conta_contabil": None,
            }
        ]
        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transaction_payload,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200
        transaction_id = create_response.json()[0]["id"]
        # Tenta atualizar feedback
        feedback_response = client.patch(
            f"/api/v1/transactions/{transaction_id}/feedback",
            json={"conta_contabil": 1234},
            headers={"X-API-Key": api_key},
        )
        assert feedback_response.status_code == 200
        assert feedback_response.json()["id"] == transaction_id
        assert feedback_response.json()["conta_contabil"] == 1234

    def test_feedback_cross_company(self, client, empresa_criada, admin_headers):
        """Empresa x não pode atualizar transação de empresa y"""
        empresa_criada_x = empresa_criada

        # Empresa y
        empresa_y_payload = {
            "nome_empresa": "EMPRESA Y LTDA",
            "cnpj_cpf": "08455780000199",
            "cod_dominio": 8001,
        }
        empresa_y_response = client.post(
            "/api/v1/companies",
            json=empresa_y_payload, headers=admin_headers
        )
        assert empresa_y_response.status_code == 200
        empresa_y = empresa_y_response.json()

        # Cria transação de empresa y
        transaction_payload = [
            {
                "data": "2022-01-01",
                "cod_banco": 341,
                "historico": "Pagamento fornecedor",
                "empresa_id": empresa_y["id"],
                "valor": 100.0,
                "conta_contabil": None,
            }
        ]
        create_response = client.post(
            f"/api/v1/companies/{empresa_y['id']}/transactions",
            json=transaction_payload,
            headers={"X-API-Key": empresa_y["api_key"]}
        )
        assert create_response.status_code == 200
        transaction_id = create_response.json()[0]["id"]
        # Tenta atualizar feedback
        feedback_response = client.patch(
            f"/api/v1/transactions/{transaction_id}/feedback",
            json={"conta_contabil": 8555},
            headers={"X-API-Key": empresa_criada_x["api_key"]},
        )
        assert feedback_response.status_code == 403
        assert "outra empresa" in feedback_response.json()["detail"].lower()

    def test_feedback_company_inactive(self, client, empresa_criada):
        company_id = empresa_criada["id"]
        api_key = empresa_criada["api_key"]
        transaction_payload = [
            {
                "data": "2022-01-01",
                "cod_banco": 341,
                "historico": "Pagamento fornecedor",
                "empresa_id": company_id,
                "valor": 100.0,
                "conta_contabil": None,
            }
        ]
        create_response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transaction_payload,
            headers={"X-API-Key": api_key},
        )
        assert create_response.status_code == 200
        transaction_id = create_response.json()[0]["id"]
        
        deactivate_response = client.patch(
            f"/api/v1/companies/{company_id}/deactivate",
        )
        assert deactivate_response.status_code == 200

        feedback_response = client.patch(
            f"/api/v1/transactions/{transaction_id}/feedback",
            json={"conta_contabil": 1234},
            headers={"X-API-Key": api_key},
        )
        assert feedback_response.status_code == 400
        assert "Empresa está desativada" in feedback_response.json()["detail"]
class TestClassificationAuth:
    """Testes de autenticação no endpoint de classificação."""

    def test_classification_without_api_key(self, client, empresa_criada):
        """Testa que classificação sem API key retorna erro."""
        company_id = empresa_criada["id"]
        response = client.post(f"/api/v1/companies/{company_id}/classification")
        assert response.status_code == 401

    def test_classification_with_invalid_api_key(self, client, empresa_criada):
        """Testa que classificação com API key inválida retorna erro 403."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/classification",
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403

    def test_classification_with_insufficient_data(self, client, empresa_criada):
        """Testa que classificação com dados insuficientes retorna erro 422."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/classification",
            headers={"X-API-Key": empresa_criada["api_key"]},
        )
        assert response.status_code == 422

class TestMultiTenantScope:
    # Teste com função de helper
    @staticmethod
    def _create_company(client, suffix: str, cod_dominio: int, admin_headers):
        payload = {
            "nome_empresa": f"EMPRESA {suffix} LTDA",
            "cnpj_cpf": f"08455780001{suffix}",
            "cod_dominio": cod_dominio,
        }
        response = client.post("/api/v1/companies", json=payload, headers=admin_headers)
        assert response.status_code == 200
        return response.json()

    def test_transactions_cross_company_forbidden(
        self, client, empresa_criada, transacao_data, admin_headers
    ):
        empresa_a = empresa_criada
        empresa_b = self._create_company(client, "B", 1000, admin_headers)
        response = client.post(
            f"/api/v1/companies/{empresa_b['id']}/transactions",
            json=[transacao_data],
            headers={"X-API-Key": empresa_a["api_key"]},
        )
        assert response.status_code == 403
