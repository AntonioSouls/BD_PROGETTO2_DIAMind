#================================================================================================
# Script per convertire tutti i file LaTeX in file di tipo Markdown tramite la libreria Pandoc ||
#================================================================================================


set -euo pipefail

# 0) Trova la root del progetto (una cartella sopra la cartella di questo script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RAW_DIR="${PROJECT_ROOT}/Data/Raw"

if [[ ! -d "$RAW_DIR" ]]; then
  echo "[ERR] Non trovo Data/Raw in: $RAW_DIR"
  echo "     Sposta lo script dentro il progetto o passa un path personalizzato."
  echo "     (Se vuoi: ./TEX_to_MD.sh /path/assoluto/alla/tuacartella/Data/Raw)"
  exit 1
fi

# Supporto opzionale: se passi un argomento, usalo come Data/Raw personalizzato
if [[ $# -ge 1 ]]; then
  RAW_DIR="$1"
  if [[ ! -d "$RAW_DIR" ]]; then
    echo "[ERR] Argomento passato non è una directory: $RAW_DIR"
    exit 1
  fi
fi

echo "[INFO] Uso RAW_DIR = $RAW_DIR"

# 1) Converte tutti i .tex in .md con estrazione immagini
shopt -s nullglob
tex_files=("$RAW_DIR"/*.tex)
if (( ${#tex_files[@]} )); then
  for f in "${tex_files[@]}"; do
    out="${f%.tex}.md"
    echo "[PANDOC] $(basename "$f") -> $(basename "$out")"
    pandoc "$f" \
      --from=latex+raw_tex \
      --to=gfm \
      --resource-path="$RAW_DIR" \
      --extract-media="$RAW_DIR" \
      --wrap=none \
      -o "$out"
  done
else
  echo "[PANDOC] Nessun .tex trovato in $RAW_DIR (ok se li hai già convertiti)"
fi

# 2) Converte immagini .pdf in media/ in .png (se esiste media/)
MEDIA_DIR="${RAW_DIR}/media"
if [[ -d "$MEDIA_DIR" ]]; then
  echo "[CONVERT] PDF -> PNG nelle cartelle media/"
  # usa -print0 per gestire spazi nei nomi
  while IFS= read -r -d '' pdf; do
    png="${pdf%.pdf}.png"
    echo "   $(basename "$pdf") -> $(basename "$png")"
    convert -density 300 "$pdf" "$png"
  done < <(find "$MEDIA_DIR" -type f -name "*.pdf" -print0)
else
  echo "[CONVERT] Nessuna cartella media/ (Pandoc potrebbe non aver estratto immagini)"
fi

# 3) Aggiorna riferimenti nei .md: (...media/qualcosa.pdf) -> (...media/qualcosa.png)
echo "[SEDR] Aggiorno riferimenti nei .md (.pdf -> .png in percorsi media/)"
# sed su tutti i .md nella root Raw (non ricorsivo)
md_count=0
while IFS= read -r -d '' md; do
  sed -i 's#(\([^)]*media[^)]*\)\.pdf)#(\1.png)#g' "$md"
  ((md_count++))
done < <(find "$RAW_DIR" -maxdepth 1 -type f -name "*.md" -print0)

echo "[DONE] Aggiornati $md_count file .md"