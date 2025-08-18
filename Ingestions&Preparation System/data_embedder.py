import os, json, hashlib
from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd
from tqdm import tqdm
import faiss         # import del VectorDB (FAISS nel nostro caso)
import sys
ROOT = Path(__file__).resolve().parents[1]   # Risolvo la root del progetto per far funzionare l'import dell'embedder
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from DIAMind import embedding_model  # Import dell'embedder


""" Script che prende i Chunk generati, li passa al modello di embedding, riceve i dati embeddizzati e li salva sul VectorDB """


# === VARIABILI DI CONFIGURAZIONE =========================================================================================================================
INPUT_JSONL = "Data/Chunks/chunks.jsonl"
OUT_DIR     = "Data/VectorDB"
NORMALIZE   = True         # La teniamo a TRUE perchè normalizza i vettori che vengono creati. Così facendo non ci sono vettori che vengono favoriti rispetto ad altri nel retrieval


# === SEZIONE PER IL CODICE ===============================================================================================================================


def sha1(s: str) -> str:
    """ Funzione che calcola l’hash SHA-1 di una stringa e lo restituisce in formato esadecimale."""

    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def load_chunks(path: str) -> List[Dict]:
    """ Funzione utile ad aprire il .jsonl ricevuto come input e caricare dallo storage alla memoria principale i chunk """

    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_input_text(row: Dict) -> str:
    """ Funzione che riceve il singolo chunk e costruisce il testo da embeddizzare """

    title = (row.get("section_title") or "").strip()       # Estraggo il titolo del chunk e ne rimuovo carratteri superflui
    body  = (row.get("text") or "").strip()                # Estraggo il testo del chunk  e ne rimuovo caratteri superflui
    txt = f"{title}\n\n{body}".strip() if title else body  # Costruisco il testo da embeddizzare per quel chunk
    
    # Dal testo creato, considero solamente i caratteri stampabili e restituisco il testo con solo quelli
    return "".join(ch for ch in txt if ch.isprintable() or ch in "\n\t\r")


def main():
    """ Funzione principale che orchestra l'embeddizzazione dei dati.
    Carica i chunk creati, li manda al modello di embedding, riceve i dati embeddizzati e li salva sul VectorDB """


    os.makedirs(OUT_DIR, exist_ok=True)      # Se non esiste la directory, la crea
    data = load_chunks(INPUT_JSONL)          # Carica dallo storage tutti i chunk    
    texts, metas = [], []                    # Inizializzo le variabili in cui memorizzare i record validi
    
    print("Estrazione del testo embeddizzabile dai chunk ed elaborazione dei metadati ...")
    for r in tqdm(data):
        t = build_input_text(r)                 # Dato un singolo chunk, estrapolo da questo solo il testo da embeddizzare
        if not t:
            continue
        texts.append(t)                         # Memorizzo il testo da embeddizzare in una lista di testi
        metas.append({                          # Per ciascun testo da embeddizzare, salvo anche le informazioni di contorno che non vanno embeddizzate ma serviranno a restituire il documento corrispondente a quell'embeddings nel momento in cui ci sarà un match
            "id": r.get("id"),
            "doc_id": r.get("doc_id"),
            "source_path": r.get("source_path"),
            "section_title": r.get("section_title"),
            "chunk_idx": r.get("chunk_idx"),
            "n_tokens": r.get("n_tokens"),
            "n_chars": r.get("n_chars"),
            "n_images": len(r.get("images", [])),
            "hash_text": sha1(t),               # Calcolo l'esadecimale dell' Hash SHA1 del testo originale (non ancora embeddizzato) 
            "text_len": len(t),
        })

    # Piccolo controllo per segnalare l'eventuale errore di assenza di testi da embeddizzare
    if not texts:
        print("‼️ ERRORE: Nessun testo valido da embeddizzare trovato. Ricontrollare i chunk!")
        return
    print("✅ Estrazione del testo embeddizzabile completata!")

    print("Inizio Embeddizzazione ...")
    Vb = embedding_model.embed_many(texts, batch_size=64, normalize=NORMALIZE)     # Passo i testi estratti all'Embedding Model che ne calcola gli embeddings. Batch_size ci dice quanti testi in parallelo andiamo ad embeddizzare (64 è il valore ottimale per la mia CPU). Diciamo anche al modello di normalizzare i vettori
    V = Vb.astype("float32", copy=False)                                           # Assicura che il dtype della matrice sia float32, che è quello atteso da FAISS. copy=False indica che non viene creata una copia della matrice se il dtype è già float32
    dim = V.shape[1]                            # La matrice è del tipo [N,384] cioè N righe (che sono gli N embeddings creati) e 384 colonne (la lunghezza del singolo embeddings). Questa riga prende il numero di colonne e lo salva in una variabile. Utile per costruire l'indice FAISS
    print("✅ Embeddizzazione completata!")

    print("Salvataggio degli embeddings ... ")
    # Costruisco il FAISS index
    if NORMALIZE:
        index = faiss.IndexFlatIP(dim)     # IP su vettori normalizzati = cosine
    else:
        index = faiss.IndexFlatL2(dim)

    # Mantengo ID interi allineati alle righe meta:
    # (IndexIDMap2 consente di mappare id interi -> vettori)
    id_index = faiss.IndexIDMap2(index)
    ids = np.arange(V.shape[0], dtype="int64")
    id_index.add_with_ids(V, ids)

    # Salva index e metadati
    faiss.write_index(id_index, str(Path(OUT_DIR) / "index.faiss"))
    meta_df = pd.DataFrame(metas)
    meta_df.to_parquet(Path(OUT_DIR) / "meta.parquet", index=False)

    # Info
    print("✅ Salvataggio completato!")
    print(f"✔ Indicizzati {len(meta_df)} chunk, dim={dim}, normalize={NORMALIZE}")
    print(f"- {OUT_DIR}/index.faiss")
    print(f"- {OUT_DIR}/meta.parquet")


# STARTER DELLO SCRIPT
if __name__ == "__main__":
    main()
