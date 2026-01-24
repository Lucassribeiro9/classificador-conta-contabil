# Plano de Implementação - Migração para Arquitetura API-First

## 📋 Visão Geral

Migração da ferramenta de classificação contábil baseada em Streamlit para uma arquitetura robusta **API-first** utilizando **FastAPI** e **SQLAlchemy**, permitindo integração com automações (n8n), suporte a multi-tenancy e preparação para análises de BI.

---

## 🎯 Objetivos

1. **API-First**: Criar endpoints RESTful para todas as operações
2. **Multi-Tenancy**: Suportar múltiplas empresas (companies) isoladas
3. **Persistência**: Armazenar histórico de transações e classificações no banco de dados
4. **Integração**: Permitir integração com n8n e outras ferramentas de automação
5. **Compatibilidade**: Manter a aplicação Streamlit funcional (opcional, para suporte legado)

---

## 🏗️ Arquitetura Proposta

```
classificador-conta-contabil/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app principal
│   ├── dependencies.py      # Dependency injection (get_db, auth)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── companies.py     # CRUD de empresas
│   │   ├── transactions.py  # CRUD de transações
│   │   ├── classification.py # Endpoint de classificação
│   │   └── feedback.py      # Endpoint de feedback/correção
│   └── schemas.py           # Pydantic models
├── core/
│   ├── __init__.py
│   ├── database.py          # Configuração SQLAlchemy
│   ├── models.py            # Models SQLAlchemy
│   ├── ml_engine.py         # Lógica de ML refatorada
│   └── config.py            # Configurações da aplicação
├── tests/
│   ├── __init__.py
│   ├── test_api.py          # Testes da API
│   └── test_ml_engine.py    # Testes do ML
├── n8n_workflows/           # Workflows do n8n (JSON)
├── app.py                   # Streamlit (legado, opcional)
├── requirements.txt
└── README.md
```

---

## 📦 Dependências Adicionais

### Novas Dependências Necessárias

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pydantic==2.9.2
pydantic-settings==2.5.2
python-multipart==0.0.12  # Para upload de arquivos
```

### Dependências Existentes (já presentes)
- pandas, numpy, scikit-learn, nltk, openpyxl, xlsxwriter

---

## 🔄 Fluxo de Dados

### 1. Ingestão de Dados Históricos (Treinamento)
```
n8n/Cliente → POST /api/v1/transactions (batch)
  → Salva no DB (company_id, description, account_code, date, value)
  → Dados ficam disponíveis para treinamento
```

### 2. Classificação de Nova Transação
```
n8n/Cliente → POST /api/v1/classify
  → Busca histórico da company_id
  → Treina modelo (ou usa cache)
  → Classifica transação
  → Retorna: {account_code, confidence, needs_review}
  → Salva transação no DB
```

### 3. Feedback/Correção
```
n8n/Cliente → POST /api/v1/feedback
  → Atualiza transação com account_code correto
  → Marca como "corrigido"
  → Dados podem ser usados para retreinar
```

---

## 🗄️ Modelo de Dados

### Tabela: `companies`
```python
- id: Integer (PK)
- name: String (único)
- api_key: String (único, para autenticação)
- created_at: DateTime
- updated_at: DateTime
```

### Tabela: `transactions`
```python
- id: Integer (PK)
- company_id: Integer (FK → companies.id)
- date: Date
- bank: String (nullable)
- description: String
- value: Decimal
- account_code: Integer (nullable - preenchido pela classificação)
- confidence: Float (nullable - probabilidade da classificação)
- needs_review: Boolean (default: False)
- is_corrected: Boolean (default: False)
- created_at: DateTime
- updated_at: DateTime
```

### Tabela: `account_codes` (opcional - catálogo de contas)
```python
- id: Integer (PK)
- code: Integer (único)
- name: String
- description: String (nullable)
```

---

## 🔐 Autenticação

### Estratégia Inicial: API Key
- Cada `company` possui um `api_key` único
- Header: `X-API-Key: <api_key>`
- Middleware FastAPI valida a chave antes de processar requests

### Futuro: OAuth2 (se necessário para acesso multiusuário direto)

---

## 📡 Endpoints da API

### Companies
- `POST /api/v1/companies` - Criar empresa
- `GET /api/v1/companies/{company_id}` - Obter empresa
- `GET /api/v1/companies` - Listar empresas (admin)

### Transactions
- `POST /api/v1/transactions` - Criar transação (batch suportado)
- `GET /api/v1/transactions` - Listar transações (filtrado por company_id)
- `GET /api/v1/transactions/{transaction_id}` - Obter transação
- `PATCH /api/v1/transactions/{transaction_id}` - Atualizar transação

### Classification
- `POST /api/v1/classify` - Classificar transação(s)
  - Body: `{company_id, transactions: [{description, date, value, bank?}]}`
  - Response: `{results: [{transaction_id, account_code, confidence, needs_review}]}`

### Feedback
- `POST /api/v1/feedback` - Enviar feedback de correção
  - Body: `{transaction_id, correct_account_code}`
  - Atualiza a transação e marca como corrigida

### Health & Docs
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

---

## 🧪 Estratégia de Testes

### Testes Unitários
- `test_ml_engine.py`: Testar `clean_text`, pipeline de ML, classificação
- `test_models.py`: Testar models SQLAlchemy

### Testes de Integração
- `test_api.py`: Testar todos os endpoints com `TestClient`
  - Criação de companies
  - Ingestão de transações
  - Classificação
  - Feedback
  - Tratamento de erros

### Testes Manuais
- Teste de integração com n8n (HTTP POST local)
- Verificar persistência no SQLite
- Validar resultados de classificação

---

## 🔄 Refatoração da Lógica de ML

### `core/ml_engine.py`

```python
class ClassificationEngine:
    def __init__(self, db_session):
        self.db = db_session
        self.pipeline = None
        self.cache = {}  # Cache de modelos por company_id
    
    def clean_text(self, text: str) -> str:
        # Move função clean_text do app.py
    
    def train_model(self, company_id: int, min_samples: int = 5):
        # Busca transações do DB
        # Filtra por min_samples
        # Treina pipeline
        # Salva no cache
    
    def classify(self, company_id: int, descriptions: List[str]) -> List[Dict]:
        # Treina modelo se necessário
        # Classifica
        # Retorna resultados com confidence
```

---

## 📊 Notebooks & BI

### Atualização dos Notebooks
- Refatorar `analise-contabil-real.ipynb` para usar `core.ml_engine` e `core.database`
- Criar queries SQL para visualizações no Power BI

### Views SQL (opcional)
```sql
CREATE VIEW vw_classification_stats AS
SELECT 
    company_id,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN account_code IS NOT NULL THEN 1 ELSE 0 END) as classified,
    AVG(confidence) as avg_confidence
FROM transactions
GROUP BY company_id;
```

---

## 🚀 Fases de Implementação

### Fase 1: Infrastructure Setup
- Atualizar `requirements.txt`
- Criar estrutura de diretórios
- Configurar SQLAlchemy e banco de dados

### Fase 2: Database & Models
- Criar models SQLAlchemy
- Script de inicialização do banco
- Migrations (Alembic - opcional)

### Fase 3: Core Logic
- Refatorar lógica de ML para `core/ml_engine.py`
- Adaptar para trabalhar com DB ao invés de DataFrame

### Fase 4: API Development
- Criar schemas Pydantic
- Implementar endpoints
- Autenticação via API Key

### Fase 5: Testing & Integration
- Testes automatizados
- Integração com n8n
- Documentação da API

### Fase 6: Documentation & Deployment
- Atualizar README
- Guia de integração n8n
- Deploy (se necessário)

---

## ⚠️ Considerações Importantes

### SQLite vs PostgreSQL
- **Inicial**: SQLite (`conta.db`) para simplicidade
- **Produção**: Migrar para PostgreSQL se houver alta concorrência

### Autenticação
- **Inicial**: API Key simples
- **Futuro**: OAuth2 se necessário acesso multiusuário direto

### Cache de Modelos
- Modelos podem ser treinados por company_id e cacheados em memória
- Considerar persistência de modelos treinados (joblib) para evitar retreinar sempre

### Compatibilidade Streamlit
- A aplicação Streamlit pode continuar funcionando conectando direto ao DB
- Ou pode ser atualizada para consumir a API (opcional)

---

## 📝 Checklist de Verificação

- [ ] API responde corretamente a todos os endpoints
- [ ] Multi-tenancy funcionando (isolamento por company_id)
- [ ] Classificação ML retorna resultados corretos
- [ ] Feedback atualiza transações corretamente
- [ ] Testes automatizados passando
- [ ] Integração n8n testada e funcionando
- [ ] Documentação da API completa (Swagger)
- [ ] README atualizado com instruções de uso da API

---

## 🔗 Referências

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
