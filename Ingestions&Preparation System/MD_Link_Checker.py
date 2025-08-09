import os
import re

""" Script che controlla che tutti i riferimenti all'interno dei file.md siano corretti. Se ce n'è qualcuno rotto, lo segnala in console e
manualmente lo si va a sistemare """


base_dir = "Data/Raw"    # Directory su cui lavorare
PATTERN = re.compile(r'!\[[^\]]*\]\(([^)]+)\)')  # prende esattamente il contenuto del tipo ![ ... ]( ... )

def main():
    entries = os.listdir(base_dir)           # Lista di tutti i file contenuti nella directory (ci serve per selezionare i file da analizzare)
    files_in_dir = set(entries)              # Insieme di tutti i file contenuti nella directory (ci serve per fare un confronto più veloce quando troviamo i riferimenti)
    broken = []                              # Lista di tutti i link rotti

    for filename in entries:
        if filename.endswith(".md"):
            md_path = os.path.join(base_dir, filename)
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                print(f"⚠️ Impossibile leggere {filename}: {e}")
                continue

            # Cerca tutti i pattern ![...](...)
            for m in PATTERN.finditer(text):
                target = m.group(1)
                if target not in files_in_dir:
                    broken.append((filename, target))
    
    if not broken:
        print("✅ Nessun riferimento rotto trovato nei .md di Data/Raw.")
    else:
        print("❌ Riferimenti rotti trovati:")
        for md_file, bad in broken:
            print(f"- In '{md_file}': riferimento non trovato -> ({bad})")


# Funzione starter dello script
if __name__ == "__main__":
    main()
