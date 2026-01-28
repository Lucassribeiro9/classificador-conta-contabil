from datetime import date
from pydantic import ValidationError
from api.schemas import TransacaoCreate, EmpresaCreate

# Teste básico de validação
def testar_validacao():
    try:
        transacao = TransacaoCreate(
            data=date(2025, 10, 15),
            descricao="Teste de transação",
            valor=100.50,
            empresa_id=1
        )
        print("✅ Validação passou!")
        print(f"Data: {transacao.data}")
        print(f"Descrição: {transacao.descricao}")
        print(f"Valor: {transacao.valor}")
    except ValidationError as e:
        print("❌ Erro de validação:")
        print(e)

    # Teste de empresa
    try:
        empresa = EmpresaCreate(
            nome="Teste de empresa2",
            cnpj="12.345.678/0001-90",
            cod_dominio=200
        )
        print("✅ Validação passou!")
        print(f"Nome: {empresa.nome}")
        print(f"CNPJ: {empresa.cnpj}")
        print(f"Cod Domínio: {empresa.cod_dominio}")
    except ValidationError as e:
        print("❌ Erro de validação:")
        print(e)

        # 2. Testar Empresa com campo faltando (cod_dominio é obrigatório)
        try:
            EmpresaCreate(nome="Erro", cnpj="000")
            print(
                "❌ Empresa (Inválida): Falhou (deveria ter bloqueado a falta de cod_dominio)."
            )
        except ValidationError:
            print("✅ Empresa (Inválida): Sucesso (bloqueou campo obrigatório ausente).")

        # 3. Testar Transação Válida (com campos opcionais ausentes)
        try:
            trans_ok = TransacaoCreate(
                data=date(2026, 1, 28),
                descricao="Compra de material",
                valor=150.50,
                empresa_id=1,
            )
            print("✅ Transação (Válida - Opcionais vazios): Sucesso.")
        except ValidationError as e:
            print(f"❌ Transacao (Válida): Falhou. Erro: {e}")

        # 4. Testar Transação com erro de tipo (valor como string não numérica)
        try:
            TransacaoCreate(data="hoje", descricao="Erro", valor="caro", empresa_id=1)
            print("❌ Transação (Inválida): Falhou (deveria ter bloqueado tipos errados).")
        except ValidationError:
            print("✅ Transação (Inválida): Sucesso (bloqueou tipos de dados incorretos).")

if __name__ == "__main__":
    testar_validacao()