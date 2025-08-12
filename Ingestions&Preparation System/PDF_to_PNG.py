import os
import subprocess


""" Script python che converte dei PDF contenenti un'immagine singola in formato PNG usando ImageMagick """


base_dir = "Data/Raw"   # Directory di partenza

# == CONVERTITORE DA PDF A PNG ==
def convert_pdfs_to_pngs():
    for file in os.listdir(base_dir):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(base_dir, file)
            png_path = os.path.splitext(pdf_path)[0] + ".png"

            print(f"🔄 Converto: {pdf_path} -> {png_path}")

            try:
                subprocess.run(
                    ["convert", "-density", "300", pdf_path, png_path],
                    check=True
                )
                print(f"✅ Creato: {png_path}")
            except subprocess.CalledProcessError as e:
                print(f"❌ Errore nella conversione di {pdf_path}: {e}")


# == FUNZIONE STARTER DELLO SCRIPT ==
if __name__ == "__main__":
    convert_pdfs_to_pngs()
    print("CONVERSIONE DEI PDF IN PNG COMPLETATA!")
