import os
import requests
import ipaddress

def get_ip_list(url):
    response = requests.get(url)
    response.raise_for_status()
    lines = response.text.strip().split('\n')
    valid_ips = []
    for ip in lines:
        ip = ip.strip()
        try:
            ipaddress.IPv4Address(ip)
            valid_ips.append(ip)
        except ValueError:
            # 非法IP，跳过
            pass
    return valid_ips

def get_cloudflare_zone(api_token):
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
    }
    response = requests.get('https://api.cloudflare.com/client/v4/zones', headers=headers)
    response.raise_for_status()
    zones = response.json().get('result', [])
    if not zones:
        raise Exception("No zones found")
    return zones[0]['id'], zones[0]['name']

def delete_existing_dns_records(api_token, zone_id, subdomain, domain):
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
    }
    record_name = domain if subdomain == '@' else f'{subdomain}.{domain}'
    while True:
        response = requests.get(
            f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={record_name}',
            headers=headers
        )
        response.raise_for_status()
        records = response.json().get('result', [])
        if not records:
            break
        for record in records:
            delete_response = requests.delete(
                f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record["id"]}',
                headers=headers
            )
            delete_response.raise_for_status()
            print(f"Deleted DNS record {record['id']} for {record_name}")

def update_cloudflare_dns(ip_list, api_token, zone_id, subdomain, domain):
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
    }
    record_name = domain if subdomain == '@' else f'{subdomain}.{domain}'
    for ip in ip_list:
        data = {
            "type": "A",
            "name": record_name,
            "content": ip,
            "ttl": 1,
            "proxied": False
        }
        response = requests.post(
            f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records',
            json=data,
            headers=headers
        )
        if response.status_code == 200:
            print(f"Added A record {ip} to {record_name}")
        else:
            print(f"Failed to add A record for IP {ip} to {record_name}: {response.status_code} {response.text}")

if __name__ == "__main__":
    api_token = os.getenv('CF_API_TOKEN')
    if not api_token:
        print("Error: Environment variable CF_API_TOKEN not set.")
        exit(1)

    subdomain_ip_mapping = {
        'bestcf': 'https://raw.githubusercontent.com/ymyuuu/IPDB/refs/heads/main/BestCF/bestcfv4.txt',
        'api': 'https://raw.githubusercontent.com/464681925/youxuanyuming/refs/heads/main/ip.txt',
    }

    try:
        zone_id, domain = get_cloudflare_zone(api_token)

        for subdomain, url in subdomain_ip_mapping.items():
            ip_list = get_ip_list(url)
            if subdomain == 'bestcf':
                ip_list = ip_list[:5]
            elif subdomain == 'api':
                ip_list = ip_list[:40]
            else:
                ip_list = ip_list[:5]

            print(f"Processing {subdomain} ({len(ip_list)} valid IPs)...")
            delete_existing_dns_records(api_token, zone_id, subdomain, domain)
            update_cloudflare_dns(ip_list, api_token, zone_id, subdomain, domain)

    except Exception as e:
        print(f"Error: {e}")
