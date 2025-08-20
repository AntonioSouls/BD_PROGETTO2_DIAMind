import streamlit as st
import numpy as np
from DIAMind.embedding_model import embed_text

st.set_page_config(page_title="DIAMind RAG Frontend", layout="centered")
st.title("DIAMind RAG System")
st.write("Inserisci una query per ottenere l'embedding:")

user_query = st.text_input("Query:", "")

if st.button("Genera embedding"):
    if user_query.strip():
        embedding = embed_text(user_query)
        st.write("**Embedding generato:**")
        st.write(embedding)
    else:
        st.warning("Inserisci una query valida.")
