import streamlit as st
import pandas as pd
import numpy as np
import re
import nltk
from nltk.corpus import stopwords
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from io import BytesIO

# Configuração da página
st.set_page_config(page_title="Classificação Contábil 1.1", page_icon="🤖", layout="wide")

# Garantindo que os recursos do NLTK estejam disponíveis
try:
    stopwords.words('portuguese')
except LookupError:
    st.info("Baixando recursos do NLTK...")
    nltk.download('stopwords')

# Função de pré-processamento
@st.cache_data
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    stop_words = set(stopwords.words('portuguese'))
    text = ' '.join([word for word in text.split() if word not in stop_words])
    return text

# Interface do usuário
st.title("🤖 Ferramenta de Classificação Contábil")
st.write("Faça o upload da sua planilha e a ferramenta irá classificar automaticamente as contas contábeis assim que o modelo for treinado.")

# Layout padrão da planilha
st.divider()
st.subheader("📄 Layout padrão da planilha para download")
st.write("Baixe o modelo de planilha para garantir que sua planilha esteja no formato correto. Ela contém exemplos de lançamentos já classificados. Preencha com os seus dados seguindo o mesmo padrão."
         "OBS: Apague os exemplos antes de enviar sua planilha.")

# Criando DF na memória
df_template = pd.DataFrame({
    'CONTA': [10829, 103900, ''],
    'DATA': ['2023-01-05', '2023-01-10', '2023-01-15'],
    'BANCO': ['Banco do Brasil', 'Banco do Brasil', 'Banco do Brasil'],
    'DESCRIÇÃO DO LANÇAMENTO': ['Pagamento fornecedor X', 'Recebimento cliente Y', 'Transferência entre contas'],
    'VALOR': [1000, 2000, 3000]
})
# Convertendo para Excel na memória
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Lançamentos')
    processed_data = output.getvalue()
    return processed_data
excel_data = to_excel(df_template)
st.download_button(
    label="📥 Baixar modelo de planilha",
    data=excel_data,
    file_name='modelo_planilha_classificacao.xlsx',
    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
st.divider()
# Upload e processamento da planilha
st.subheader("📂 Envio da planilha para classificação")
st.info(
    "**Instruções:**\n"
    "Sua planilha deve estar no formato Excel (.xlsx) e conter o mesmo layout da planilha fornecida\n"
    "A ferramenta usará as linhas preenchidas para aprender e treinar o modelo e depois preencherá as linhas vazias.\n"
)
# Upload do arquivo
uploaded_file = st.file_uploader("Escolha uma planilha Excel", type=["xlsx"])
if uploaded_file is not None:
    if st.button("Processar e classificar planilha"):
        with st.spinner("Lendo a planilha e realizando os testes. Por favor, aguarde..."):
            try:
                if uploaded_file.name.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file)
                else:
                    st.error("Por favor, envie um arquivo no formato .xlsx")
                    st.stop()
                COL_HIS = 'DESCRIÇÃO DO LANÇAMENTO'
                COL_ACC = 'CONTA'
                
                # Separando dados para treinamento e classificação
                cond_for_class = df[COL_ACC].isna() | (df[COL_ACC].astype(str).str.strip() == '')
                df_for_class = df[cond_for_class].copy()
                df_training = df[~cond_for_class].copy()
                
                # Filtrando classes com poucas amostras
                acc_counts = df_training[COL_ACC].value_counts()
                CUTOFF = 5
                valid_accs = acc_counts[acc_counts >= CUTOFF].index
                df_filtered_training = df_training[df_training[COL_ACC].isin(valid_accs)].copy()
                df_filtered_training[COL_ACC] = df_filtered_training[COL_ACC].astype(int)
                
                # Treinamento do modelo
                df_filtered_training['DESCRIÇÃO LIMPA'] = df_filtered_training[COL_HIS].apply(clean_text)
                X = df_filtered_training['DESCRIÇÃO LIMPA']
                y = df_filtered_training[COL_ACC]
                text_clf_pipeline = Pipeline([
                    ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
                    ('clf', LogisticRegression(random_state=42))
                ])
                text_clf_pipeline.fit(X, y)
                
                # Aplicando o modelo para classificação
                if not df_for_class.empty:
                    text_for_class = df_for_class[COL_HIS].apply(clean_text)
                    arr_proba = text_clf_pipeline.predict_proba(text_for_class)
                    
                    filled_accs = []
                    final_proba = []
                    CONFIDENCE_LIMIT = 0.70 # % de confiança
                    
                    for i in range(len(arr_proba)): # para cada lançamento
                        lanc_proba = arr_proba[i]
                        best_acc_index = lanc_proba.argmax()
                        max_proba = lanc_proba[best_acc_index]
                        predicted_acc = text_clf_pipeline.classes_[best_acc_index]
                        if max_proba >= CONFIDENCE_LIMIT:
                            filled_accs.append(predicted_acc)
                            final_proba.append(f"{max_proba:.2%}") # convertendo para porcentagem
                        else:
                            filled_accs.append(predicted_acc) 
                            final_proba.append(f"Revisar: {predicted_acc} ({max_proba:.2%})") # convertendo para porcentagem
                    df_for_class['CONTA'] = filled_accs
                    df_for_class['PROBABILIDADE'] = final_proba
                # Preenchendo NaNs restantes com 'Conta já veio preenchida'
                df_training['PROBABILIDADE'] = 'Conta já veio preenchida'
                # Gerando planilha final com os resultados
                df_final = pd.concat([df_training, df_for_class], ignore_index=True)
                # Garantindo que a coluna 'CONTA' seja do tipo string
                df_final['CONTA'] = df_final['CONTA'].astype(str)
                # Regex para remover '.0' de números inteiros representados como string
                df_final['CONTA'] = df_final['CONTA'].str.replace(r'\.0$', '', regex=True)
                st.success("Classificação concluída!")
                st.write(f"Total de lançamentos processados: {len(df_final)}")
                st.dataframe(df_final.tail(len(df_for_class)+5)) # Mostra os classificados + 5 anteriores
                # Preparando arquivo para download
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='Classificação')
                processed_data = output.getvalue()
                st.download_button(
                    label="📥 Baixar planilha classificada",
                    data=processed_data,
                    file_name='classificacao_contas_resultado.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f"Erro ao processar a planilha: {e}")
                st.error("Verifique se a planilha está no formato correto e tente novamente.")