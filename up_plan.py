import requests
import pathlib
import pandas as pd

# Arquivo de teste para subir para o banco de dados

API_URL = "http://localhost:8000/api/v1/companies/{company_id}/transactions"
API_KEY = "sk_1f3a274ef693f603c70fd08c537fc820"
COMPANY_ID = 3

path = pathlib.Path("C:/Users/administrador/Desktop/transacoes_ficticias_2024.xlsx")

df = pd.read_excel(path)

# Fazendo o POST para a API

payload = []
for _, row in df.iterrows():
    # Converte Timestamp para string no formato ISO (YYYY-MM-DD)
    data_str = pd.Timestamp(row['DATA']).strftime('%Y-%m-%d') if pd.notna(row['DATA']) else None
    
    # Trata conta_contabil - pode ser NaN (vazia na planilha)
    conta = int(row['CONTA']) if pd.notna(row['CONTA']) else None
    
    # Trata cod_banco - pode ser NaN
    banco = int(row['BANCO']) if pd.notna(row['BANCO']) else None
    
    payload.append({
        "data": data_str,
        "cod_banco": banco,
        "historico": str(row['DESCRIÇÃO DO LANÇAMENTO']),
        "valor": float(row['VALOR']),
        "conta_contabil": conta,
        "empresa_id": COMPANY_ID,
    })

# Enviando para a API
headers = {"X-API-KEY": API_KEY}

# URL corrigida (API_URL já contém o path completo)
response = requests.post(API_URL.format(company_id=COMPANY_ID), json=payload, headers=headers)

print(response.status_code)
print(response.json())