import os
import re
import json
import csv
import argparse
from pathlib import Path
from typing import List, Dict, Tuple


""" Script per creare dei chunk dei file .md arricchiti con i metadati. Questi chunk ed i relativi metadati servono per poter fare gli embeddings. """


# == VARIABILI DI CONFIGURAZIONE ======================================================================================================================
base_dir = "Data/Cleaned"
out_dir = "Data/Chunks"

MAX_TOKENS = 300
OVERLAP_TOKENS = 60
MIN_TOKENS = 80

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)\s*$', re.MULTILINE)
CODE_FENCE_RE = re.compile(r'^(```|~~~).*?^\1\s*$', re.DOTALL | re.MULTILINE)
IMG_MD_RE = re.compile(r'!\[[^\]]*\]\(([^)]+)\)', re.IGNORECASE)
IMG_HTML_RE = re.compile(r'<img\s+[^>]*src=["\']([^"\']+\.(?:png|jpg|jpeg|gif|webp|svg))["\'][^>]*>', re.IGNORECASE)


# == SEZIONE PER IL CODICE ============================================================================================================================

def token_len(text: str) -> int:
    """Stima rapida: ~1 token ogni 4 caratteri (spazi inclusi)."""

    return max(0, len(text) // 4)


def normalize(text: str) -> str:
    """ Funzione di Normalizzazione minima per stabilizzare il chunking."""

    text = text.replace("\r\n", "\n").replace("\r", "\n")    # Converto tutti i ritorni a capo in un formato uniforme
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)  # Rimuovo gli spazi ed i tab invisibili a fine riga
    text = re.sub(r"\n{3,}", "\n\n", text)                   # Rimuovo le spaziature eccessive
    return text


def looks_like_list(seg: str) -> bool:
    return bool(re.match(r'^(\s*([-*+]\s+|\d+\.\s+).*\n?)+$', seg, flags=re.MULTILINE))


def looks_like_table(seg: str) -> bool:
    # euristica semplice per tabelle markdown in pipe
    if '|' not in seg:
        return False
    return re.search(r'^\s*\|', seg, flags=re.MULTILINE) is not None


def split_sections(text: str) -> List[Dict]:
    """Funzione che prende in ingresso il testo di un file.md e ritorna una lista delle sue sezioni: {level, title, body}."""

    matches = list(HEADING_RE.finditer(text))                  # Trova nel testo tutte le sezioni
    sections = []

    # Se non ci sono sezioni, ritorna tutto il testo come unica sezione
    if not matches:
        sections.append({"level": 1, "title": "(no heading)", "body": text.strip()})
        return sections

    # Se ci sono sezioni, restituisce la lista di sezioni ciascuna con il proprio testo e taggata con il proprio livello
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        sections.append({
            "level": len(m.group(1)),
            "title": m.group(2).strip(),
            "body": text[start:end].strip()
        })
    return sections


def split_blocks(body: str) -> List[Dict]:
    """
    Estrae una sequenza di blocchi 'atomici' preservando l'ordine:
    - code: fence ``` o ~~~
    - table: blocchi pipe-based
    - list: liste contigue
    - para: paragrafi
    """
    blocks = []

    # 1) Estrai code-fence come atomi
    parts = []
    last = 0
    for m in CODE_FENCE_RE.finditer(body):
        before = body[last:m.start()]
        if before.strip():
            parts.append(("text", before))
        parts.append(("code", m.group(0)))
        last = m.end()
    tail = body[last:]
    if tail.strip():
        parts.append(("text", tail))

    # 2) Dai pezzi 'text' ricava liste/tabelle/paragrafi
    for kind, chunk in parts:
        if kind == "code":
            blocks.append({"type": "code", "text": chunk.strip()})
        else:
            # separa per righe vuote
            for seg in re.split(r'\n\s*\n', chunk):
                seg = seg.strip()
                if not seg:
                    continue
                if looks_like_table(seg):
                    blocks.append({"type": "table", "text": seg})
                elif looks_like_list(seg):
                    blocks.append({"type": "list", "text": seg})
                else:
                    blocks.append({"type": "para", "text": seg})
    return blocks


def tail_overlap(text: str, overlap_tokens: int) -> str:
    """Prende ~overlap_tokens dalla coda, cercando un confine frase/parola sensato."""

    if overlap_tokens <= 0:
        return ""
    approx_chars = overlap_tokens * 4
    tail = text[-approx_chars:]
    # prova a tagliare da un segno di fine frase
    m = re.search(r'[\.\!\?\n]\s+\S[^\n]*$', tail)
    if m:
        return tail[m.start():].lstrip()
    # altrimenti da confine di parola
    m2 = re.search(r'\s+\S[^\s]*$', tail)
    return (tail[m2.start():].lstrip() if m2 else tail)


def pack_chunks(blocks: List[Dict], max_tokens=300, overlap_tokens=60, min_tokens=80) -> List[str]:
    """Impacchetta i blocchi in chunk rispettando budget e overlap."""

    chunks: List[str] = []
    buf: List[str] = []
    buf_tok = 0

    def flush():
        nonlocal buf, buf_tok
        if buf:
            chunks.append("\n\n".join(buf).strip())
            buf = []
            buf_tok = 0

    for b in blocks:
        btxt = b["text"]
        btok = token_len(btxt)

        if btok > max_tokens:
            # blocco atomico troppo lungo → chunk dedicato
            flush()
            chunks.append(btxt.strip())
            continue

        # se ci sta
        if buf_tok + btok <= max_tokens:
            buf.append(btxt)
            buf_tok += btok
        else:
            # chiudi il corrente
            prev = "\n\n".join(buf).strip()
            flush()
            # prepara overlap dalla coda del chunk precedente
            if prev:
                ov = tail_overlap(prev, overlap_tokens)
                if ov:
                    buf.append(ov)
                    buf_tok = token_len(ov)
            # aggiungi il blocco corrente (se non entra per via dell'overlap, flush e metti da solo)
            if buf_tok + btok <= max_tokens:
                buf.append(btxt)
                buf_tok += btok
            else:
                flush()
                buf.append(btxt)
                buf_tok = btok

    flush()

    # evita micro-chunk finali (se possibile)
    if len(chunks) >= 2 and token_len(chunks[-1]) < min_tokens:
        last = chunks.pop()
        merged = chunks[-1] + "\n\n" + last
        if token_len(merged) <= max_tokens + overlap_tokens:  # tolleranza
            chunks[-1] = merged
        else:
            chunks.append(last)

    # filtra eventuali vuoti
    chunks = [c for c in chunks if c.strip()]
    return chunks


def harvest_images(text: str) -> List[str]:
    """Estrae i path immagine citati sia in Markdown che in HTML <img>."""

    paths = []

    # Markdown: ![alt](path)
    for m in IMG_MD_RE.finditer(text):
        p = m.group(1)

        # rimuovi anchor/query se presenti
        p = p.split("#")[0].split("?")[0]
        paths.append(p)

    # HTML: <img src="path" ...>
    for m in IMG_HTML_RE.finditer(text):
        p = m.group(1)

        # rimuovi anchor/query se presenti
        p = p.split("#")[0].split("?")[0]
        paths.append(p)

    # dedup preservando l'ordine
    out, seen = [], set()
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out



def build_record(doc_id: str, source_path: str, section_title: str, chunk_text: str, sec_idx: int, c_idx: int) -> Dict:
    return {
        "id": f"{doc_id}__s{sec_idx}__c{c_idx}",
        "doc_id": doc_id,
        "source_path": source_path,
        "section_title": section_title,
        "chunk_idx": c_idx,
        "n_tokens": token_len(chunk_text),
        "n_chars": len(chunk_text),
        "images": harvest_images(chunk_text),
        "text": chunk_text
    }


def process_md_file(md_path: Path, out_jsonl_handle, csv_writer, base_root: Path):
    """ Funzione che riceve in ingresso un file.md, lo analizza e ne estrae i chunk """

    text = md_path.read_text(encoding="utf-8", errors="ignore")       # Leggo il testo del file
    text = normalize(text)                                            # Chiamo la funzione per normalizzare il testo
    doc_id = md_path.stem                                             # Calcolo l'ID del file che sto analizzando semplicemente considerando il nome del file senza estensione
    rel_src = f"BD_PROGETTO2_DIAMind/{md_path}"                     # Calcolo il path assoluto del file 

    sections = split_sections(text)                                   # Divido il testo del file in sezioni
    n_chunks_file = 0

    # Per ogni sezione, divido il suo testo in blocchi e poio formulo i chunk
    for s_idx, sec in enumerate(sections):
        blocks = split_blocks(sec["body"])
        if not blocks:
            continue
        chunk_texts = pack_chunks(blocks, MAX_TOKENS, OVERLAP_TOKENS, MIN_TOKENS)        # Creazione dei chunk e scrittura sull'output
        for c_idx, chunk in enumerate(chunk_texts):
            rec = build_record(doc_id, rel_src, sec["title"], chunk, s_idx, c_idx)
            out_jsonl_handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
            csv_writer.writerow([
                rec["id"], rec["doc_id"], rec["source_path"], rec["section_title"],
                rec["chunk_idx"], rec["n_tokens"], rec["n_chars"], len(rec["images"])
            ])
            n_chunks_file += 1
    return n_chunks_file


def open_outputs(out_dir):
    """ Funzione che crea i file di output su cui scrivere i chunk ed il sommario dei chunks. Se esistono già dei file, li elimina e li ricrea."""

    # Vedo se i file di output esistono già nella output directory. Se si, li elimino
    existent_files = set(os.listdir(out_dir))
    if "chunks.jsonl" in existent_files:
        jsonl_path = os.path.join(out_dir, "chunks.jsonl")
        os.remove(jsonl_path)
    if "chunks_summary.csv" in existent_files:
        csv_path = os.path.join(out_dir, "chunks_summary.csv")
        os.remove(csv_path)
    
    # Creo ed apro i file di output
    jsonl_path = os.path.join(out_dir, "chunks.jsonl")
    csv_path = os.path.join(out_dir, "chunks_summary.csv")
    jsonl = open(jsonl_path, "w", encoding="utf-8")
    csvf = open(csv_path, "w", newline="", encoding="utf-8")
    w = csv.writer(csvf)
    w.writerow(["id","doc_id","source_path","section_title","chunk_idx","n_tokens","n_chars","n_images"])
    return jsonl, csvf, w


def main():
    """ Funzione principale che itera sui file.md e per ognuno invoca la funzione che ne crea i chunk """


    total_chunks = 0           # Inizializzo la variabile per contare il numero di chunks creati

    jsonl, csvf, writer = open_outputs(out_dir)    # Creo ed apro i file di output dove vado ad inserire i chunks ed il riepilogo dei chunks

    # Itero su tutti gli .md e ne creo i chunk
    for filename in sorted(os.listdir(base_dir)):
        if filename.endswith(".md"):
            print(f"▶️​ Creazione dei chunk per il file {filename}")
            md_path = Path(base_dir) / filename
            n = process_md_file(md_path, jsonl, writer, Path(base_dir))
            total_chunks += n

    # Chiudo i file di output
    jsonl.close()
    csvf.close()

    print(f"✅ Processati tutti i file.md")
    print(f"Chunks totali creati: {total_chunks}")


# STARTER DELLO SCRIPT
if __name__ == "__main__":
    main()
