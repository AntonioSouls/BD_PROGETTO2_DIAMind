import os

"""" Script che sostituisce gli spazi con un _ nei nomi dei file Raw """

base_dir = "Data/Raw"       # Percorso della cartella da elaborare

for filename in os.listdir(base_dir):             # Per ogni file nella cartella
    if " " in filename:                           # Se contiene uno spazio nel nome, allora lo sostituisce con un _
        old_path = os.path.join(base_dir, filename)
        new_filename = filename.replace(" ", "_")
        new_path = os.path.join(base_dir, new_filename)

        os.rename(old_path, new_path)
        print(f"Rinominato: {filename} → {new_filename}")

print("Rinomina dei file completata")
