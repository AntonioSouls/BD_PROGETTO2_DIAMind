import os
import re
import argparse


""" Script creato per analizzare i file LaTeX e sostituire tutti i riferimenti a PDF contenenti una singola immagine con il riferimento al corrispettivo PNG """


# == VARIABILI DI CONFIGURAZIONE ===============================================================================================================================
base_dir = "Data/Raw"
INCLUDEGFX_RE = re.compile(
    r'(\\includegraphics\*?\s*(?:\[[^\]]*\]\s*)?\{)([^}]*)(\})',
    flags=re.IGNORECASE
)

# == SEZIONE PER IL CODICE ======================================================================================================================================


def replace_pdf_with_png_in_includegraphics(tex_content):
    """ FUNZIONE PER MODIFICARE IL FILE LATEX EFFETTUANDO LA CONVERSIONE """

    def _repl(m):
        prefix, inner, suffix = m.groups()

        # Conserva eventuali spazi finali dentro le graffe
        inner_raw = inner
        inner_no_trail = inner_raw.rstrip()
        trailing = inner_raw[len(inner_no_trail):]  # spazi finali (se presenti)

        if inner_no_trail.lower().endswith('.pdf'):
            # sostituisci solo l'estensione finale
            new_inner_no_trail = inner_no_trail[:-4] + '.png'
            return f"{prefix}{new_inner_no_trail}{trailing}{suffix}"
        else:
            return m.group(0)

    return INCLUDEGFX_RE.sub(_repl, tex_content)


def process_tex_file(path, dry_run=False, make_backup=True, encoding='utf-8'):
    """ FUNZIONE PER PROCESSARE IL SINGOLO FILE LATEX """
    
    # Apro il file in lettura
    with open(path, 'r', encoding=encoding) as f:
        original = f.read()

    print("  - Verifico se ci sono modifiche nel file")
    modified = replace_pdf_with_png_in_includegraphics(original)  # Creo una copia e modifico quello che ho letto

    # Se ci sono modifiche, le salva. Altrimenti, avvisa che non c'è stata nessuna sostituzione da fare
    if modified != original:
        print(f"  - Modifiche Trovate ✅")
        if dry_run:
            return  # non scrive su disco
        if make_backup:
            print("  - Salvataggio del Backup")
            bak = path + '.bak'
            with open(bak, 'w', encoding=encoding) as fb:
                fb.write(original)
            print("  - Backup Salvato Correttamente ✅")
        print("  - Salvataggio delle Modifiche")
        with open(path, 'w', encoding=encoding) as fw:
            fw.write(modified)
        print("  - Modifiche salvate Correttamente ✅")
    else:
        print(f"  - Nessuna sostituzione necessaria ✔️")


def main():
    """ FUNZIONE PER ITERARE SU TUTTI I FILE LATEX """

    for file in os.listdir(base_dir):
        if file.endswith(".tex"):
            print(f"➡️ Processamento del file {file}")
            process_tex_file(os.path.join(base_dir,file))


if __name__ == '__main__':
    """ FUNZIONE STARTER DELLO SCRIPT """

    main()
