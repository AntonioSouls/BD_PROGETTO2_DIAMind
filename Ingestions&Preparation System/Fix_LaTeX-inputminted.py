import os
import re


""" Script Python che analizza i file LaTeX e, se hanno degli inputminted collegati ad un codice esterno al file, sostituiscono quel riferimento 
con il codice scritto in Markdown. Serve come pulizia dei file LaTeX per facilitarne la conversione in Markdown """


# == VARIABILI DI CONFIGURAZIONE =============================================================================================================
base_dir = "Data/Raw"
INPUTMINTED_RE = re.compile(
    r"""
    \\inputminted                      # comando
    (?:\[(?P<opts>[^\]]*)\])?          # opzioni tra [] facoltative
    \{(?P<lang>[^}]+)\}                # linguaggio minted
    \{(?P<path>[^}]+)\}                # path del file
    """,
    re.VERBOSE | re.MULTILINE | re.DOTALL,
)


# == SEZIONE PER IL CODICE ===================================================================================================================


def _parse_opts(opts_str):
    """ FUNZIONE CHE PARSA LE POSSIBILI OPZIONI DI INPUTMINTED COME 'firstline=10,lastline=20,breaklines'.
    GRAZIE A QUESTA FUNZIONE ABBIAMO DELLE VARIABILI PER GESTIRE LE OPZIONI DI INPUTMINTED. """

    opts = {}
    if not opts_str:
        return opts
    for part in [p.strip() for p in opts_str.split(",") if p.strip()]:
        if "=" in part:
            k, v = part.split("=", 1)
            opts[k.strip().lower()] = v.strip()
        else:
            opts[part.strip().lower()] = True
    return opts


def _lang_from_ext(path, fallback_lang):
    """DETERMINA IL LINGUAGGIO DEL BLOCCO MARKDOWN DALL'ESTENSIONE O DAL LANG MINTED."""

    ext = os.path.splitext(path)[1].lower()
    by_ext = {
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".h": "c",
        ".hpp": "cpp",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".cs": "csharp",
        ".sh": "bash",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".kt": "kotlin",
        ".m": "matlab",
        ".tex": "tex",
        ".md": "markdown",
        ".txt": "",
    }
    return by_ext.get(ext, (fallback_lang or "")).strip()


def _read_text_any(path):
    """ FUNZIONE CHE LEGGE IL TESTO TENTANDO UTF-8 E POI LATIN-1. IN FALLBACK SOSTITUISCE I CARATTERI INVALIDI """

    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def fix_inputminted(file_path):
    """ FUNZIONE PER CORREGGERE GLI INPUTMINTED NEL FILE RICEVUTO """

    try:                                          # Prova a leggere il file con tutte le possibili codifiche
        original = _read_text_any(file_path)      
    except Exception as e:                        # Altrimenti, stampa errore
        print(f"[ERRORE] Impossibile leggere {file_path}: {e}")
        return

    replacements = 0

    def _replace(match):
        nonlocal replacements
        opts_str = match.group("opts") or ""
        minted_lang = (match.group("lang") or "").strip()
        code_rel_path = (match.group("path") or "").strip()
        print(f"Sto leggendo il file {code_rel_path}")

        opts = _parse_opts(opts_str)
        firstline = opts.get("firstline")
        lastline = opts.get("lastline")

        resolved = os.path.join(base_dir,code_rel_path)
        if not resolved:
            print(f"[ATTENZIONE] Sorgente non trovato: {code_rel_path} (nel file {file_path}). Lascio invariato.")
            return match.group(0)

        code_text = _read_text_any(resolved)

        # Applica firstline/lastline (1-based inclusivo) se presenti
        if firstline is not None or lastline is not None:
            try:
                lines = code_text.splitlines()
                start = int(firstline) if firstline is not None else 1
                end = int(lastline) if lastline is not None else len(lines)
                start = max(1, start)
                end = min(len(lines), end)
                code_text = "\n".join(lines[start - 1 : end]) if start <= end else ""
            except ValueError:
                # Opzioni mal formate: ignora slicing
                pass

        fence_lang = _lang_from_ext(resolved, minted_lang)

        # Commento informativo (facoltativo)
        header = f"<!-- from \\inputminted{{{minted_lang}}}{{{code_rel_path}}}"
        if firstline or lastline:
            header += f" (lines {firstline or 1}-{lastline or 'end'})"
        header += " -->\n"

        block = f"{header}```{fence_lang}\n{code_text}\n```\n"
        replacements += 1
        return block

    # Prende il testo originale, in questo trova tutte le righe che matchano con il pattern INPUTMINTED_RE e le sostituisce seguendo la logica della funzione _replace
    new_text = INPUTMINTED_RE.sub(_replace, original)

    # Se ho effettuato almeno una modifica al testo originale, sovrascrivo il file. Altrimenti lo lascio invariato e segnalo che non c'è stata alcuna modifica sul file
    if replacements > 0:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            print(f"[OK] Sostituiti {replacements} inputminted in: {file_path}")
        except Exception as e:
            print(f"[ERRORE] Impossibile scrivere {file_path}: {e}")
    else:
        print(f"[INFO] Nessun \\inputminted trovato/sostituito in: {file_path}")


def main():
    """ FUNZIONE PER GESTIRE L'INTERAZIONE CON L'UTENTE E FARGLI INSERIRE IL NOME DEL FILE DA CORREGGERE """

    file = input("Inserisci il nome del file su cui vanno corretti gli INPUTMINTED: ")
    if file in set(os.listdir(base_dir)):
        if file.endswith(".tex"):
            file_path = os.path.join(base_dir, file)
            fix_inputminted(file_path)
        else:
            print("Il file inserito non è un LaTeX file. Non ha INPUTMINTED da sistemare!")
    else:
        print("Il file cercato non esiste! Prova con un altro nome")
    return


if __name__ == '__main__':
    """ FUNZIONE STARTER DELLO SCRIPT """

    main()