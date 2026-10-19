
import pandas as pd

def create_google_maps_link_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        return "Le fichier spécifié n'a pas été trouvé."

    # Assurez-vous que les colonnes d'adresse existent
    if 'Adresse destinataire' not in df.columns or 'Gouvernorat' not in df.columns:
        return "Les colonnes d'adresse requises ('Adresse destinataire', 'Gouvernorat') sont introuvables dans le fichier CSV."

    # Construire l'URL Google Maps
    base_url = "https://www.google.com/maps/dir/"
    addresses = []
    for index, row in df.iterrows():
        # Créer une adresse complète et l'ajouter à la liste
        full_address = f"{row['Adresse destinataire']}, {row['Gouvernorat']}"
        addresses.append(full_address)

    # Joindre les adresses pour l'URL
    url = base_url + "/".join(addresses)

    # Générer un fichier HTML avec le lien
    html_content = f"""
    <html>
    <head>
        <title>Lien Google Maps pour les livraisons</title>
    </head>
    <body>
        <h1>Lien Google Maps pour les livraisons</h1>
        <p>Cliquez sur le lien ci-dessous pour voir l'itinéraire sur Google Maps :</p>
        <a href="{url}" target="_blank">Voir l'itinéraire des livraisons</a>
    </body>
    </html>
    """

    try:
        with open("C:/Users/User/OneDrive/Documents/GitHub/V-2-V--logistics/central agent/outputs/google_maps_links.html", "w") as f:
            f.write(html_content)
        return "Le fichier HTML avec le lien Google Maps a été créé avec succès dans le dossier 'outputs'."
    except Exception as e:
        return f"Une erreur est survenue lors de la création du fichier HTML : {e}"

# Exécuter la fonction
file_path = "C:/Users/User/OneDrive/Documents/GitHub/V-2-V--logistics/central agent/data/Copie de client_data.csv"
print(create_google_maps_link_from_csv(file_path))
