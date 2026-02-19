"""
Testes da API de Classificação de Contas Contábeis.
Testa endpoints de empresas, transações, classificação e feedback.
"""

import pytest


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

    def test_create_company(self, client, empresa_data):
        """Testa criação de empresa."""
        response = client.post("/api/v1/companies", json=empresa_data)
        assert response.status_code == 200
        data = response.json()
        assert data["nome_empresa"] == empresa_data["nome_empresa"]
        assert data["cnpj_cpf"] == empresa_data["cnpj_cpf"]
        assert "api_key" in data
        assert data["api_key"].startswith("sk_")

    def test_create_company_duplicate_cnpj(self, client, empresa_data):
        """Testa que não é possível criar empresa com CNPJ duplicado."""
        client.post("/api/v1/companies", json=empresa_data)
        response = client.post("/api/v1/companies", json=empresa_data)
        assert response.status_code == 400
        assert "CNPJ já cadastrado" in response.json()["detail"]

    def test_list_companies(self, client, empresa_criada):
        """Testa listagem de empresas."""
        response = client.get("/api/v1/companies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["nome_empresa"] == empresa_criada["nome_empresa"]

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
        assert response.status_code == 400
        assert "Empresa já está desativada" in response.json()["detail"]

    def test_activate_company_already_active(self, client, empresa_criada):
        """Testa erro ao ativar empresa já ativa."""
        company_id = empresa_criada["id"]
        response = client.patch(f"/api/v1/companies/{company_id}/activate")
        assert response.status_code == 400
        assert "Empresa já está ativa" in response.json()["detail"]
class TestTransactionsAuth:
    """Testes de autenticação nos endpoints de transações."""

    def test_create_transactions_without_api_key(self, client, empresa_criada, transacao_data):
        """Testa que criar transações sem API key retorna erro."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/transactions",
            json=transacao_data,
        )
        assert response.status_code == 422  # Validation error - header obrigatório

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
        assert "Invalid API Key" in response.json()["detail"]

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
        assert response.status_code == 422

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


class TestFeedbackAuth:
    """Testes de autenticação no endpoint de feedback."""

    def test_feedback_without_api_key(self, client):
        """Testa que feedback sem API key retorna erro."""
        response = client.patch(
            "/api/v1/transactions/1/feedback",
            json={"conta_contabil": 1234},
        )
        assert response.status_code == 422

    def test_feedback_with_invalid_api_key(self, client):
        """Testa que feedback com API key inválida retorna erro 403."""
        response = client.patch(
            "/api/v1/transactions/1/feedback",
            json={"conta_contabil": 1234},
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403


class TestClassificationAuth:
    """Testes de autenticação no endpoint de classificação."""

    def test_classification_without_api_key(self, client, empresa_criada):
        """Testa que classificação sem API key retorna erro."""
        company_id = empresa_criada["id"]
        response = client.post(f"/api/v1/companies/{company_id}/classification")
        assert response.status_code == 422

    def test_classification_with_invalid_api_key(self, client, empresa_criada):
        """Testa que classificação com API key inválida retorna erro 403."""
        company_id = empresa_criada["id"]
        response = client.post(
            f"/api/v1/companies/{company_id}/classification",
            headers={"X-API-Key": "invalid_key"},
        )
        assert response.status_code == 403
