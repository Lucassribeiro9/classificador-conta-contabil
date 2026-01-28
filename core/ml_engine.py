# - Bibliotecas para manipulação e análise de dados
import pandas as pd
import re
import joblib

# - Bibliotecas para visualização de dados
import plotly.express as px
import seaborn as sns
import matplotlib.pyplot as plt
from IPython.display import display, Markdown, Image

# - Bibliotecas para ML
import nltk
try:
    from nltk.corpus import stopwords
except:
    nltk.download('stopwords')
    from nltk.corpus import stopwords

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.models import Transacao

class ClassificadorContabil:
    def __init__(self, db: Session):
        self.db = db

        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
            ('clf', LogisticRegression(random_state=42))
        ])

    def clean_text(self, text):
        # transformar em minúsculas
        text = str(text).lower()
        # remover numeros
        text = re.sub(r'\d+', ' ', text)
        # remover pontuação e caracteres especiais
        text = re.sub(r'[^\w\s]', ' ', text)
        # remover espaços extras
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        # remover stopwords
        stopwords_pt = set(stopwords.words('portuguese'))
        # Opcional: adicionar stopwords condizentes ao contexto
        custom_stopwords = {'Lançamento', 'pagto', 'aplicações'}
        # update
        stopwords_pt.update(custom_stopwords)
        # Separar as palavras
        words = text.split()
        # Remover as stopwords
        words_filtered = [word for word in words if word not in stopwords_pt and len(word) > 2]
        # Juntar as palavras novamente
        clean_text = ' '.join(words_filtered)
        return clean_text

    def train_for_company(self, empresa_id: int):
        # Buscar as transações da empresa e verificar se não são nulas
        stmt = select(Transacao).where(Transacao.empresa_id == empresa_id, Transacao.conta_contabil.is_not(None))
        results = self.db.execute(stmt).scalars().all()
        if not results:
            raise ValueError(f"Nenhuma transação encontrada para a empresa com ID {empresa_id}")
        
        if len(results) < 10:
            print("Foram encontradas poucas transações para o treinamento")
            return False
        # Transformar em DataFrame
        df = pd.DataFrame([{
            'historico': self.clean_text(t.historico),
            'conta_contabil': t.conta_contabil
        } for t in results])
        # Treinando o modelo
        self.pipeline.fit(df['historico'], df['conta_contabil'])
        return True
    
    def classify_transactions(self, empresa_id: int, transacao_id: list[int]):
        # Aplicando a regra dos 70% para classificar
        stmt = select(Transacao).where(Transacao.id.in_(transacao_id))
        transactions = self.db.execute(stmt).scalars().all()
        if not transactions:
            raise ValueError(f"Nenhuma transação encontrada para os IDs {transacao_id}")
        clean_historico = [self.clean_text(t.historico) for t in transactions]
        # Pega as probabilidades de cada classe
        probabilities = self.pipeline.predict_proba(clean_historico)
        # Pega a classe com maior probabilidade
        classes = self.pipeline.classes_
        for i, t in enumerate(transactions):
           max_prob = probabilities[i].max()
           best_class = classes[probabilities[i].argmax()]
           t.conta_contabil = int(best_class)
           t.confidence = float(max_prob)
           t.needs_review = True if max_prob < 0.7 else False
        self.db.commit()
        return transactions