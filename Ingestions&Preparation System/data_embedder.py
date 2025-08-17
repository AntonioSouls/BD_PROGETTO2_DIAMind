import os, json, hashlib
from pathlib import Path
from typing import Dict, List
import numpy as np
import pandas as pd
from tqdm import tqdm
import faiss         # import del VectorDB (FAISS nel nostro caso)
from DIAMind  import embedding_model  # Import dell'embedder


""" Script che prende i Chunk generati, li passa al modello di embedding, riceve i dati embeddizzati e li salva sul VectorDB """


# === VARIABILI DI CONFIGURAZIONE =========================================================================================================================
INPUT_JSONL = "Data/Chunks/chunks.jsonl"
OUT_DIR     = "Data/VectorDB"
#BATCH_EMB   = 128         # batch di embedding
#NORMALIZE   = True        # True => usa IndexFlatIP come cosine
MIN_TOKENS  = 0           # OPZIONALE: Se posta a 0 accetta tutti i chunk. Se aumentata di valore rifiuta tutti i chunk con un numero di token sotto la soglia definita


# === SEZIONE PER IL CODICE ===============================================================================================================================


def sha1(s: str) -> str:
    """ Funzione che calcola l’hash SHA-1 di una stringa e lo restituisce in formato esadecimale."""

    import hashlib
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
    
    for r in data:
        # Istruzione inserita se volessimo embeddizzare solo i chunk con un numero di token sopra una certa soglia.
        # Cambiando il valore alla variabile MIN_TOKENS, si entra nel corpo di questa istruzione che rifiuta tutti i chunk sotto la soglia stabilita
        # da quella variabile
        if MIN_TOKENS and (r.get("n_tokens") or 0) < MIN_TOKENS:
            continue
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
        print("Nessun testo valido da indicizzare.")
        return

    # Embedding a batch usando lo script riusabile
    vec_parts = []
    for i in tqdm(range(0, len(texts), BATCH_EMB), desc="Embedding"):
        batch = texts[i:i+BATCH_EMB]
        Vb = embed_many(batch, batch_size=min(64, BATCH_EMB), normalize=True if NORMALIZE else False)
        vec_parts.append(Vb.astype("float32"))
    V = np.vstack(vec_parts)  # [N, 384]
    dim = V.shape[1]

    # FAISS index
    if NORMALIZE:
        index = faiss.IndexFlatIP(dim)     # IP su vettori normalizzati = cosine
    else:
        index = faiss.IndexFlatL2(dim)

    # Se vuoi mantenere ID interi allineati alle righe meta:
    # (IndexIDMap2 consente di mappare id interi -> vettori)
    id_index = faiss.IndexIDMap2(index)
    ids = np.arange(V.shape[0], dtype="int64")
    id_index.add_with_ids(V, ids)

    # Salva index e metadati
    faiss.write_index(id_index, str(Path(OUT_DIR) / "index.faiss"))
    meta_df = pd.DataFrame(metas)
    meta_df.to_parquet(Path(OUT_DIR) / "meta.parquet", index=False)

    # Info
    print(f"✔ Indicizzati {len(meta_df)} chunk, dim={dim}, normalize={NORMALIZE}")
    print(f"- {OUT_DIR}/index.faiss")
    print(f"- {OUT_DIR}/meta.parquet")


# STARTER DELLO SCRIPT
if __name__ == "__main__":
    main()
