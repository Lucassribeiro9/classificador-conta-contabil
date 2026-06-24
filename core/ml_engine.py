import re
import logging
from time import perf_counter
from pathlib import Path

# - Bibliotecas para ML
import joblib
import nltk
from nltk.corpus import stopwords

try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sqlalchemy import select
from sqlalchemy.orm import Session
from core.audit import record_audit_event
from core.config import settings
from core.dataset_builder import DatasetTreinoContrapartida
from core.models import Transacao
from core.razao_parser import normalize_razao_historico

logger = logging.getLogger(__name__)


def legacy_transacao_flow(method):
    """Marca metodos mantidos apenas para compatibilidade com Transacao."""
    method.legacy_flow = "transacao"
    return method


class ClassificadorContabil:
    def __init__(self, db: Session, model_dir: str | Path | None = None):
        self.db = db
        self.model_dir = Path(model_dir or settings.MODEL_DIR)

        self.pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
                ("clf", MultinomialNB()),
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
                    "conta_contrapartida_predita": best_class,
                    "confidence": max_prob,
                    "needs_review": True if max_prob < 0.7 else False,
                }
            )
        return predictions

    def train_from_dataset(self, dataset: DatasetTreinoContrapartida) -> bool:
        started_at = perf_counter()
        empresa_id = int(dataset.metadata["empresa_id"])
        dataset_examples = int(dataset.metadata.get("total_linhas", len(dataset.linhas)))
        if not dataset.metadata.get("treinavel", False):
            logger.warning(
                "Dataset insuficiente para treinamento",
                extra={
                    "empresa_id": dataset.metadata.get("empresa_id"),
                    "total_linhas": dataset.metadata.get("total_linhas"),
                    "contagem_por_target": dataset.metadata.get("contagem_por_target"),
                },
            )
            record_audit_event(
                self.db,
                event_type="model.train_failed",
                empresa_id=empresa_id,
                metadata={
                    "dataset_examples": dataset_examples,
                    "training_time_ms": _elapsed_ms(started_at),
                    "reason": "insufficient_dataset",
                },
            )
            self.db.flush()
            return False

        df = pd.DataFrame(dataset.linhas)
        self.pipeline.fit(df["features"], df["target_conta_contrapartida"])
        self._persist_model(empresa_id)
        record_audit_event(
            self.db,
            event_type="model.trained",
            empresa_id=empresa_id,
            resource_id=f"empresa_{empresa_id}/model_.joblib",
            metadata={
                "dataset_examples": dataset_examples,
                "training_time_ms": _elapsed_ms(started_at),
            },
        )
        self.db.flush()
        return True

    def _model_path_for_company(self, empresa_id: int) -> Path:
        return self.model_dir / f"empresa_{empresa_id}" / "model_.joblib"

    def _persist_model(self, empresa_id: int) -> None:
        model_path = self._model_path_for_company(empresa_id)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = model_path.with_suffix(".joblib.tmp")
        joblib.dump(self.pipeline, tmp_path)
        tmp_path.replace(model_path)

    def model_exists_for_company(self, empresa_id: int) -> bool:
        return self._model_path_for_company(empresa_id).exists()

    def classify_lancamentos_from_saved_model(
        self,
        empresa_id: int,
        lancamentos: list[dict],
    ) -> list[dict]:
        model = joblib.load(self._model_path_for_company(empresa_id))
        feature_texts = [
            self._build_dataset_feature_text(
                historico=item["historico"],
                conta_origem=item["conta_origem"],
                direcao=item["direcao"],
            )
            for item in lancamentos
        ]
        probabilities = model.predict_proba(feature_texts)
        classes = model.classes_
        predictions: list[dict] = []
        for index in range(len(feature_texts)):
            row_probabilities = probabilities[index]
            max_prob = float(max(row_probabilities))
            best_class = int(classes[list(row_probabilities).index(max_prob)])
            predictions.append(
                {
                    "conta_contrapartida": best_class,
                    "confianca": max_prob,
                    "needs_review": max_prob < 0.7,
                }
            )
        return predictions

    def classify_operational_movements_from_saved_model(
        self,
        empresa_id: int,
        movimentos: list[dict],
    ) -> list[dict]:
        """Classifica movimentos operacionais usando modelo salvo do dataset canonico."""
        model = joblib.load(self._model_path_for_company(empresa_id))
        feature_texts = [
            self.build_operational_movement_feature_text(
                historico_normalizado=item["historico_normalizado"],
                conta_financeira=item["conta_financeira"],
                direcao=item["direcao"],
                tipo_movimento=item.get("tipo_movimento"),
            )
            for item in movimentos
        ]
        probabilities = model.predict_proba(feature_texts)
        classes = model.classes_
        predictions: list[dict] = []
        for index in range(len(feature_texts)):
            row_probabilities = probabilities[index]
            max_prob = float(max(row_probabilities))
            best_class = int(classes[list(row_probabilities).index(max_prob)])
            predictions.append(
                {
                    "contrapartida_sugerida": best_class,
                    "confidence_sugerida": max_prob,
                    "status": "revisao" if max_prob < 0.70 else "sugerido",
                }
            )
        return predictions

    def build_operational_movement_feature_text(
        self,
        *,
        historico_normalizado: str,
        conta_financeira: int,
        direcao: str,
        tipo_movimento: str | None = None,
    ) -> str:
        """Monta features do movimento operacional sem usar valor ou documento."""
        feature_tokens = [
            normalize_razao_historico(historico_normalizado),
            f"origem_{conta_financeira}",
            f"direcao_{direcao}",
            f"tipo_{normalize_razao_historico(tipo_movimento)}"
            if tipo_movimento
            else "",
        ]
        return " ".join(token for token in feature_tokens if token)

    def _build_dataset_feature_text(
        self,
        *,
        historico: str,
        conta_origem: int,
        direcao: str,
    ) -> str:
        historico_normalizado = normalize_razao_historico(historico)
        feature_tokens = [
            historico_normalizado,
            f"origem_{conta_origem}",
            f"direcao_{direcao}",
        ]
        return " ".join(token for token in feature_tokens if token)

    @legacy_transacao_flow
    def train_for_company(self, empresa_id: int):
        """Fluxo legado: treina a partir de Transacao para endpoints antigos."""
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

    @legacy_transacao_flow
    def classify_transactions(self, empresa_id: int, transacao_id: list[int]):
        """Fluxo legado: classifica registros Transacao ja existentes."""
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

    @legacy_transacao_flow
    def predict_inputs(self, inputs: list[dict]):
        """Fluxo legado: prediz payloads no formato historico/cod_banco."""
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


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((perf_counter() - started_at) * 1000))
