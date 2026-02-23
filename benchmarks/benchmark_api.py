import json
import time
import requests
from statistics import mean


# URL base para a API
BASE_URL = "http://localhost:8000"

# Quantidade de runs para o benchmark
RUNS = 30

# Quantidade de requests para o warmup
WARMUP = 5

# ID da empresa para a qual vamos fazer as requisições
company_id = "id da empresa"

# Chave da API para fazer as requisiões
api_key = "chave api"

# Payload para a requisição de predição
predict_payload = {"historico": "Pagamento fornecedor", "cod_banco": 341}



# Função que calcula o percentual de uma lista de valores
def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    k = int((len(values) - 1) * p)
    return values[k]


# Função que implementa o que faz o benchmark da API
def bench_predict():
    times = []
    ok = 0
    err = 0

    # Faz o warmup (executa RUNS requisições sem contar o tempo)
    for _ in range(WARMUP):
        requests.post(
            f"{BASE_URL}/api/v1/companies/{company_id}/predict",
            json=predict_payload,
            headers={"X-API-Key": api_key},
            timeout=30,
        )

    # Faz o benchmark (executa RUNS requisições e conta o tempo)
    for _ in range(RUNS):
        t0 = time.perf_counter()
        r = requests.post(
            f"{BASE_URL}/api/v1/companies/{company_id}/predict",
            json=predict_payload,
            headers={"X-API-Key": api_key},
            timeout=30,
        )
        dt = (time.perf_counter() - t0) * 1000
        if r.status_code >= 400:
            print("status:", r.status_code, "body:", r.text[:300])

        if 200 <= r.status_code < 300:
            ok += 1
            times.append(dt)
        else:
            err += 1

    # Calcula as estatísticas do benchmark
    return {
        "endpoint": "/predict",
        "runs": RUNS,
        "success": ok,
        "errors": err,
        "mean_ms": round(mean(times), 2) if times else 0.0,
        "p50_ms": round(percentile(times, 0.50), 2) if times else 0.0,
        "p95_ms": round(percentile(times, 0.95), 2) if times else 0.0,
        "max_ms": round(max(times), 2) if times else 0.0,
    }

# Função que implementa o que faz o benchmark da API
def bench_classification():
    times = []
    ok = 0
    err = 0

    # Faz o warmup (executa RUNS requisições sem contar o tempo)
    for _ in range(WARMUP):
        requests.post(
            f"{BASE_URL}/api/v1/companies/{company_id}/classification",
            json=predict_payload,
            headers={"X-API-Key": api_key},
            timeout=30,
        )

    # Faz o benchmark (executa RUNS requisições e conta o tempo)
    for _ in range(RUNS):
        t0 = time.perf_counter()
        r = requests.post(
            f"{BASE_URL}/api/v1/companies/{company_id}/classification",
            json=predict_payload,
            headers={"X-API-Key": api_key},
            timeout=30,
        )
        dt = (time.perf_counter() - t0) * 1000
        if r.status_code >= 400:
            print("status:", r.status_code, "body:", r.text[:300])
        if 200 <= r.status_code < 300:
            ok += 1
            times.append(dt)
        else:
            err += 1

    # Calcula as estatísticas do benchmark
    return {
        "endpoint": "/classification",
        "runs": RUNS,
        "success": ok,
        "errors": err,
        "mean_ms": round(mean(times), 2) if times else 0.0,
        "p50_ms": round(percentile(times, 0.50), 2) if times else 0.0,
        "p95_ms": round(percentile(times, 0.95), 2) if times else 0.0,
        "max_ms": round(max(times), 2) if times else 0.0,
    }



if __name__ == "__main__":
    result = bench_predict(), bench_classification()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    with open("bench_results_before.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
