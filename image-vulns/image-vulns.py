import requests, json
url = 'https://yourconsole/api/v33.00/images?limit=3'
def main():
    headers = {
        'Content-Type': 'application/json',
        'authorization': 'Bearer TOKEN'
    }
    payload = {}
    response = requests.request("GET", url, headers=headers, data=payload) 
    data = json.loads(response.text)
    filtered_data = [{k: v for k, v in entry.items() if k in ["repoTag", "instances", "vulnerabilities"]} for entry in data]
    print(json.dumps(filtered_data, indent=2))

main()
