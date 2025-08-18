import sys, json, argparse
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer


""" Script che definisce il comportamento del modello di Embeddding. Offre tutte le funzionalità per poter embeddizzare dei testi """



MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")     # Modello che stiamo utilizzando


def embed_text(text: str, normalize: bool = True) -> np.ndarray:
    """ Funzione che riceve un testo e lo embeddizza. Utile per embeddizzare la singola query """
    
    model = MODEL
    vec = model.encode([text], convert_to_numpy=True, normalize_embeddings=normalize)
    return vec[0].astype("float32")


def embed_many(texts: List[str], batch_size: int = 64, normalize: bool = True) -> np.ndarray:
    """ Funzione che riceve un elenco di testi e li embeddizza. Utile per embeddizzare i dati """
    
    model = MODEL
    vecs = model.encode(texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=normalize)
    return vecs.astype("float32")
