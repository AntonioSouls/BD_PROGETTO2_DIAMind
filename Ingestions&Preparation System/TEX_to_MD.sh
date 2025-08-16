
#================================================================================================
# Converte tutti i .tex in Data/Raw in Markdown (GFM) lasciando i .md nella stessa cartella.
# Mantiene i riferimenti alle immagini .png già presenti in Data/Raw (niente estrazione media).
#================================================================================================

set -euo pipefail

# Imposta locale UTF-8 (evita problemi con caratteri accentati)
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"

# 0) Rileva le cartelle in modo robusto (gestione spazi e & nel path)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RAW_DIR="${PROJECT_ROOT}/Data/Raw"

# Verifica esistenza Data/Raw
if [[ ! -d "$RAW_DIR" ]]; then
  echo "[ERR] Non trovo Data/Raw in: $RAW_DIR"
  echo "     Assicurati che la struttura sia BD_PROGETTO2_DIAMind/Data/Raw"
  exit 1
fi

echo "[INFO] Uso RAW_DIR = $RAW_DIR"

# 1) Crea un header temporaneo per stubbare macro non supportate da Pandoc
#    - \labelText{T}{L} -> stampa solo T (ignoriamo la label, inutile in Markdown)
#    - Aggiungi qui altre macro se necessario (in forma innocua)
PANDOC_HEADER="$(mktemp)"
cat >"$PANDOC_HEADER" <<'EOF'
\providecommand{\labelText}[2]{#1}
EOF

# 2) Converte tutti i .tex in .md nella stessa cartella, senza estrarre media
shopt -s nullglob
tex_files=("$RAW_DIR"/*.tex)

if (( ${#tex_files[@]} == 0 )); then
  echo "[PANDOC] Nessun .tex trovato in $RAW_DIR (ok se li hai già convertiti)"
else
  for f in "${tex_files[@]}"; do
    out="${f%.tex}.md"
    echo "[PANDOC] $(basename "$f") -> $(basename "$out")"

    # Nota importanti:
    # - --resource-path="$RAW_DIR" fa sì che eventuali \includegraphics senza path
    #   vengano risolti rispetto a Data/Raw, ma NON estrae/riscrive i file.
    # - NON usiamo --extract-media: le immagini restano dov’erano.
    # - --wrap=none evita rewrapping scomodo in Markdown.
    # - --from=latex+raw_tex permette a Pandoc di non buttare via parti TeX.
    pandoc "$f" \
      --from=latex+raw_tex \
      --to=gfm \
      --resource-path="$RAW_DIR" \
      --include-in-header="$PANDOC_HEADER" \
      --wrap=none \
      -o "$out"
  done
fi

# 3) Pulizia file temporaneo
rm -f "$PANDOC_HEADER"

echo "[DONE] Conversione completata. I .md sono in: $RAW_DIR"
