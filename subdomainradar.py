import time
import requests
import sys
import os
from concurrent.futures import ThreadPoolExecutor

def get_all_enumerators(api_key, base_url):
    """
    Récupère la liste de tous les énumérateurs disponibles.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/enumerators"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [enum["display_name"] for enum in response.json()]
    else:
        raise Exception(f"Erreur lors de la récupération des énumérateurs : {response.text}")

def launch_scan(domain, enumerators, api_key, base_url):
    """
    Lance un scan pour un domaine donné en utilisant les énumérateurs spécifiés.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/enumerate"
    payload = {
        "domains": [domain],
        "enumerators": enumerators,
        "skip_processing": True,
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["tasks"][domain]
    else:
        raise Exception(f"Erreur lors du lancement du scan : {response.text}")

def get_task_status(task_id, api_key, base_url):
    """
    Récupère le statut d'une tâche de scan donnée.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/tasks/{task_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Erreur lors de la récupération du statut de la tâche : {response.text}")

def save_subdomains_to_file(subdomains, filename):
    """
    Enregistre la liste des sous-domaines dans un fichier.
    """
    with open(filename, "w") as file:
        for subdomain in subdomains:
            file.write(f"{subdomain}\n")

def process_domain(api_key, domain, base_url, enumerators):
    """
    Traite un domaine en lançant un scan et en enregistrant les résultats.
    """
    domain_name = os.path.splitext(domain)[0]
    output_filename = f"{domain_name}.txt"

    try:
        # Les énumérateurs sont déjà récupérés, pas besoin de les récupérer à nouveau
        print(f"Lancement du scan pour {domain}...")
        task_id = launch_scan(domain, enumerators, api_key, base_url)
        print(f"Scan lancé pour {domain} avec l'ID de tâche : {task_id}")

        # Attendre la fin du scan
        while True:
            task_status = get_task_status(task_id, api_key, base_url)
            status = task_status["status"]
            
            if status == "processing":
                subdomains = [sub["subdomain"] for sub in task_status.get("subdomains", [])]
                save_subdomains_to_file(subdomains, output_filename)
                print(f"Sous-domaines pour {domain} enregistrés dans {output_filename}")
                break
            elif status == "failed":
                print(f"Le scan pour {domain} a échoué.")
                break
            
            time.sleep(5)

    except Exception as e:
        print(f"Erreur lors du traitement de {domain} : {e}")

def process_batch(api_key, domains, base_url, enumerators):
    """
    Traite un lot de jusqu'à 5 domaines en parallèle.
    """
    with ThreadPoolExecutor(max_workers=5) as executor:
        for domain in domains:
            executor.submit(process_domain, api_key, domain, base_url, enumerators)

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <api_key> <input_file>")
        sys.exit(1)

    api_key = sys.argv[1]
    input_file = sys.argv[2]
    base_url = "https://api.subdomainradar.io"

    if not os.path.exists(input_file):
        print(f"Erreur : Le fichier '{input_file}' est introuvable.")
        sys.exit(1)

    # Récupération des énumérateurs une seule fois
    try:
        print("Récupération des énumérateurs...")
        enumerators = get_all_enumerators(api_key, base_url)
        print(f"Énumérateurs récupérés : {enumerators}")
    except Exception as e:
        print(f"Erreur lors de la récupération des énumérateurs : {e}")
        sys.exit(1)

    with open(input_file, "r") as file:
        domains = [line.strip() for line in file if line.strip()]

    batch_size = 5
    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        print(f"Traitement du lot : {batch}")
        process_batch(api_key, batch, base_url, enumerators)

if __name__ == "__main__":
    main()
