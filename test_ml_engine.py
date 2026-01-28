from core.database import SessionLocal, engine, Base
from core.models import Empresa, Transacao
from core.ml_engine import ClassificadorContabil
from datetime import date

# 1. Preparar o banco (limpar e criar)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # 2. Criar uma empresa de teste
    empresa = Empresa(nome_empresa="Teste Contábil LTDA", cnpj_cpf="12345678000199", api_key="chave_mestra", cod_dominio=1)
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    print(f"Empresa criada: {empresa.nome_empresa} (ID: {empresa.id})")

    # 3. Inserir dados de TREINO (Exemplos que o modelo vai aprender)
    # Precisamos de pelo menos 10 para o script não dar erro
    treino_dados = [
        ("PAGAMENTO SALARIO MES 10", 101), ("SALARIO FUNCIONARIOS", 101), ("FOLHA DE PAGAMENTO", 101),
        ("VENDA MERCADORIA NF 55", 301), ("RECEBIMENTO CLIENTE A", 301), ("VENDA DE PRODUTOS", 301),
        ("PAGTO IMPOSTO SIMPLES", 202), ("GUIA DAS IMPOSTO", 202), ("IMPOSTO SOBRE FATURAMENTO", 202),
        ("PAGAMENTO SALARIO", 101), ("VENDA NF 123", 301), ("GUIA IMPOSTO RETIDO", 202)
    ]

    for desc, conta in treino_dados:
        t = Transacao(
            empresa_id=empresa.id,
            historico=desc,
            cod_banco=1,
            conta_contabil=conta,
            data=date.today(),
            valor=100.0
        )
        db.add(t)

    # 4. Inserir dados para CLASSIFICAR (O que o modelo deve adivinhar)
    t1 = Transacao(empresa_id=empresa.id, historico="PAGTO SALARIO JOAO", cod_banco=1, data=date.today(), valor=1500.0)
    t2 = Transacao(empresa_id=empresa.id, historico="VENDA LOJA VIRTUAL", cod_banco=1, data=date.today(), valor=500.0)
    t3 = Transacao(empresa_id=empresa.id, historico="COMPRA CAFE ESCRITORIO", cod_banco=1, data=date.today(), valor=20.0) # Algo novo/incerto
    
    db.add_all([t1, t2, t3])
    db.commit()

    # 5. Instanciar a Engine e rodar o processo
    engine_ml = ClassificadorContabil(db)
    
    with open("test_result.log", "w", encoding="utf-8") as log:
        log.write(f"Empresa criada: {empresa.nome_empresa} (ID: {empresa.id})\n")
        
        log.write("\n--- Treinando o modelo para a empresa...\n")
        sucesso = engine_ml.train_for_company(empresa.id)
        log.write(f"Treino concluído: {sucesso}\n")

        if sucesso:
            log.write("--- Classificando novas transações...\n")
            # IDs das transações que acabamos de criar (sem conta)
            ids_para_classificar = [t1.id, t2.id, t3.id]
            resultados = engine_ml.classify_transactions(empresa.id, ids_para_classificar)

            for res in resultados:
                revisao = "⚠️ REVISAR" if res.needs_review else "✅ OK"
                log.write(f"Desc: {res.historico} -> Conta: {res.conta_contabil} | Confiança: {res.confidence:.2%} | Status: {revisao}\n")

finally:
    db.close()