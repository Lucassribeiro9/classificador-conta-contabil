import re
import logging
# - Bibliotecas para ML
import nltk
from nltk.corpus import stopwords

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session
from core.models import Transacao

logger = logging.getLogger(__name__)


class ClassificadorContabil:
    def __init__(self, db: Session):
        self.db = db

        self.pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
                ("clf", LogisticRegression(random_state=42)),
            ]
        )

    def clean_text(self, text):
        # transformar em minúsculas
        text = str(text).lower()
        # remover numeros
        text = re.sub(r"\d+", " ", text)
        # remover pontuação e caracteres especiais
        text = re.sub(r"[^\w\s]", " ", text)
        # remover espaços extras
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        # remover stopwords
        stopwords_pt = set(stopwords.words("portuguese"))
        # Opcional: adicionar stopwords condizentes ao contexto
        custom_stopwords = {"Lançamento", "pagto", "aplicações"}
        # update
        stopwords_pt.update(custom_stopwords)
        # Separar as palavras
        words = text.split()
        # Remover as stopwords
        words_filtered = [
            word for word in words if word not in stopwords_pt and len(word) > 2
        ]
        # Juntar as palavras novamente
        clean_text = " ".join(words_filtered)
        return clean_text

    def _build_feature_text(self, historico: str, cod_banco: int | None = None):
        clean_historico = self.clean_text(historico)
        if cod_banco is None:
            return clean_historico
        # O token de banco entra como feature categórica simples para o modelo.
        return f"{clean_historico} banco_cod_{cod_banco}"

    def _predict_features(self, feature_texts: list[str]):
        probabilities = self.pipeline.predict_proba(feature_texts)
        classes = self.pipeline.classes_
        predictions: list[dict] = []
        for i in range(len(feature_texts)):
            max_prob = float(probabilities[i].max())
            best_class = int(classes[probabilities[i].argmax()])
            predictions.append(
                {
                    "conta_contabil_predita": best_class,
                    "confidence": max_prob,
                    "needs_review": True if max_prob < 0.7 else False,
                }
            )
        return predictions

    def train_for_company(self, empresa_id: int):
        # Buscar as transações da empresa e verificar se não são nulas
        stmt = select(Transacao).where(
            Transacao.empresa_id == empresa_id, Transacao.conta_contabil.is_not(None)
        )
        results = self.db.execute(stmt).scalars().all()
        if not results:
            raise ValueError(
                f"Nenhuma transação encontrada para a empresa com ID {empresa_id}"
            )

        if len(results) < 10:
            logger.warning(
                "Poucas transacoes para treinamento",
                extra={"empresa_id": empresa_id, "quantidade_transacoes": len(results)},
            )
            return False
        # Transformar em DataFrame
        df = pd.DataFrame(
            [
                {
                    "features": self._build_feature_text(t.historico, t.cod_banco),
                    "conta_contabil": t.conta_contabil,
                }
                for t in results
            ]
        )
        # Treinando o modelo
        self.pipeline.fit(df["features"], df["conta_contabil"])
        return True

    def classify_transactions(self, empresa_id: int, transacao_id: list[int]):
        # Aplicando a regra dos 70% para classificar
        stmt = select(Transacao).where(Transacao.id.in_(transacao_id))
        transactions = self.db.execute(stmt).scalars().all()
        if not transactions:
            raise ValueError(f"Nenhuma transação encontrada para os IDs {transacao_id}")
        feature_texts = [
            self._build_feature_text(t.historico, t.cod_banco) for t in transactions
        ]
        predictions = self._predict_features(feature_texts)
        for i, t in enumerate(transactions):
            t.conta_contabil = predictions[i]["conta_contabil_predita"]
            t.confidence = predictions[i]["confidence"]
            t.needs_review = predictions[i]["needs_review"]
        self.db.commit()
        return transactions

    def predict_inputs(self, inputs: list[dict]):
        if not inputs:
            return []
        feature_texts = [
            self._build_feature_text(item["historico"], item.get("cod_banco"))
            for item in inputs
        ]
        predictions = self._predict_features(feature_texts)
        for idx, item in enumerate(inputs):
            predictions[idx]["historico"] = item["historico"]
            predictions[idx]["cod_banco"] = item.get("cod_banco")
        return predictions
