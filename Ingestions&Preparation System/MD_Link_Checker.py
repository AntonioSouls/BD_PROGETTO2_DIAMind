import os
import re

""" Script che controlla che tutti i riferimenti all'interno dei Raw file.md siano corretti. Se ce n'è qualcuno rotto, lo segnala in console e
manualmente lo si va a sistemare """

# === VARIABILI DI CONFIGURAZIONE ===========================================================================================================
base_dir = "Data/Raw"                           # Directory su cui lavorare
PATTERN = re.compile(r'\[[^\]]*\]\(([^)]+)\)')  # Prende esattamente il contenuto del tipo [ ... ]( ... )


# == SEZIONE PER IL CODICE ==================================================================================================================

def main():
    """ FUNZIONE PRINCIPALE """


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

            # Cerca tutti i pattern [...](...) nel file
            for m in PATTERN.finditer(text):
                target = m.group(1)                  # Per ogni pattern nel file, seleziona solamente la parte dentro (...)
                if target not in files_in_dir:
                    broken.append((filename, target))   # Se il link selezionato non è nell'elenco dei file in Raw, allora lo aggiungo all'elenco di quelli rotti
    
    # Stampo tutti i link rotti, se ce ne sono
    if not broken:
        print("✅ Nessun riferimento rotto trovato nei .md di Data/Raw.")
    else:
        print("❌ Riferimenti rotti trovati:")
        for md_file, bad in broken:
            print(f"- In '{md_file}': riferimento non trovato -> ({bad})")



if __name__ == "__main__":
    """ FUNZIONE STARTER DELLO SCRIPT """

    main()
