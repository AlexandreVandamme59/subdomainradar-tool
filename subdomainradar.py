import time
import requests
import sys
import os
from concurrent.futures import ThreadPoolExecutor

def get_all_enumerators(api_key, base_url):
    """
    Fetches the list of all available enumerators.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/enumerators"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return [enum["display_name"] for enum in response.json()]
    else:
        raise Exception(f"Error retrieving enumerators: {response.text}")

def launch_scan(domain, enumerators, api_key, base_url):
    """
    Launches a scan for a given domain using specified enumerators.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/enumerate"
    payload = {
        "domains": [domain],
        "enumerators": enumerators,
        "skip_processing": False,
    }
    response = requests.post(url, json=payload, headers=headers, timeout=600)
    if response.status_code == 200:
        return response.json()["tasks"][domain]
    else:
        raise Exception(f"Error launching scan: {response.text}")

def get_task_status(task_id, api_key, base_url):
    """
    Fetches the status of a given scan task.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{base_url}/tasks/{task_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error retrieving task status: {response.text}")

def save_subdomains_to_file(subdomains, filename):
    """
    Saves the list of subdomains to a file.
    """
    with open(filename, "w") as file:
        for subdomain in subdomains:
            file.write(f"{subdomain}\n")

def process_domain(api_key, domain, base_url, enumerators):
    """
    Processes a single domain by launching a scan and saving results.
    """
    domain_name = os.path.splitext(domain)[0]
    output_filename = f"{domain_name}.txt"

    try:
        # No need to fetch enumerators here since they are already retrieved
        print(f"Launching scan for {domain}...")
        task_id = launch_scan(domain, enumerators, api_key, base_url)
        print(f"Scan launched for {domain} with Task ID: {task_id}")

        # Wait for the scan to complete
        while True:
            task_status = get_task_status(task_id, api_key, base_url)
            status = task_status["status"]
            
            if status == "processing":
                subdomains = [sub["subdomain"] for sub in task_status.get("subdomains", [])]
                save_subdomains_to_file(subdomains, output_filename)
                print(f"Subdomains for {domain} saved to {output_filename}")
                break
            elif status == "failed":
                print(f"Scan for {domain} failed.")
                break
            
            time.sleep(5)

    except Exception as e:
        print(f"Error processing {domain}: {e}")

def process_batch(api_key, domains, base_url, enumerators):
    """
    Processes a batch of up to 5 domains concurrently.
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
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    # Fetch enumerators once
    try:
        print("Fetching enumerators...")
        enumerators = get_all_enumerators(api_key, base_url)
        print(f"Enumerators retrieved: {enumerators}")
    except Exception as e:
        print(f"Error retrieving enumerators: {e}")
        sys.exit(1)

    with open(input_file, "r") as file:
        domains = [line.strip() for line in file if line.strip()]

    batch_size = 5
    for i in range(0, len(domains), batch_size):
        batch = domains[i:i + batch_size]
        print(f"Processing batch: {batch}")
        process_batch(api_key, batch, base_url, enumerators)

if __name__ == "__main__":
    main()
