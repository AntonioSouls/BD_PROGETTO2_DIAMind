import os
import re
import sys
import shutil
import fitz
import subprocess
from typing import Optional


""" Script per convertire i PDF puri (no scansioni) in formato .md che è più gestibile per l'embeddizzazione """


# === CONFIG ===
base_dir = "Data/Raw"    # Directory su cui lavorare
OVERWRITE = False        # Se False, non sovrascrive .md esistenti



# === FUNZIONE CHE OPERA UNA PULIZIA BASILARE DEL TESTO ESTRATTO DAL PDF ===
def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\u00ad", "")            # soft hyphen
    s = re.sub(r"[ \t]+", " ", s)          # spazi multipli
    s = re.sub(r"\n{3,}", "\n\n", s)       # troppe righe vuote
    return s.strip()

# === FUNZIONE CHE SALVA UN PIXMAP GESTENDO CMYK/ALPHA -> RGB ===
def save_pixmap(pix: fitz.Pixmap, out_path: str):
    try:
        if pix.n > 4:  # CMYK o con alpha
            pix = fitz.Pixmap(fitz.csRGB, pix)
        pix.save(out_path)
    finally:
        try:
            pix = None
        except Exception:
            pass

# === FUNZIONE CHE CONVERTE UN SINGOLO PDF PURO IN .md + CARTELLA IMMAGINI ===
def convert_pdf_to_md(pdf_path: str):
    pdf_dir = os.path.dirname(pdf_path)
    pdf_name = os.path.basename(pdf_path)
    stem, _ = os.path.splitext(pdf_name)

    md_path = os.path.join(pdf_dir, stem + ".md")
    img_dir = os.path.join(pdf_dir, f"{stem}_imgs")
    os.makedirs(img_dir, exist_ok=True)

    if os.path.exists(md_path) and not OVERWRITE:
        print(f"[SKIP] {pdf_name} -> {os.path.basename(md_path)} già presente (OVERWRITE=False)")
        return

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"[ERR] Impossibile aprire {pdf_name}: {e}")
        return

    md_lines = [f"# {stem}\n"]
    img_counter = 0

    for pnum in range(len(doc)):
        page = doc[pnum]
        md_lines.append(f"\n\n<!-- Page {pnum+1} -->\n")

        # Testo pagina
        text = page.get_text("text") or ""
        text = clean_text(text)
        if text:
            md_lines.append(text + "\n")

        # Immagini pagina
        images = page.get_images(full=True)
        for img_idx, img_info in enumerate(images, start=1):
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
            except Exception:
                # alcuni xref richiedono un passaggio extra
                try:
                    pix = fitz.Pixmap(fitz.Pixmap(doc, xref), 0)
                except Exception:
                    print(f"[WARN] Impossibile estrarre immagine xref={xref} (p.{pnum+1}) in {pdf_name}")
                    continue

            img_counter += 1
            img_filename = f"{stem}_p{pnum+1}_{img_counter}.png"
            img_path = os.path.join(img_dir, img_filename)
            save_pixmap(pix, img_path)

            # Percorso relativo rispetto al .md (stessa cartella del PDF)
            md_lines.append(f"\n![img p.{pnum+1}]({os.path.basename(img_dir)}/{img_filename})\n")

    doc.close()

    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        print(f"[OK] {pdf_name} → {os.path.basename(md_path)}  (immagini: {img_counter} in {os.path.basename(img_dir)}/)")
    except Exception as e:
        print(f"[ERR] Scrittura {md_path} fallita: {e}")

# === FUNZIONE CHE ORCHESTRA TUTTE LE OPERAZIONI UTILI PER LA CONVERSIONE ===
def main():
    counter_pdf = 0
    for filename in os.listdir(base_dir):
        if filename.endswith(".pdf"):
            counter_pdf += 1
            pdf_path = os.path.join(base_dir, filename)
            convert_pdf_to_md(pdf_path)

    if counter_pdf == 0:
        print("Non ci sono PDF da convertire")
    else:
        print(f"Convertiti tutti i {counter_pdf} PDF trovati!")





# === FUNZIONE STARTER DELLO SCRIPT ===
if __name__ == "__main__":
    main()
