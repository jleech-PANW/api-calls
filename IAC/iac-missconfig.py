import requests, json
from collections import defaultdict
from auth import auth_func, base_url
url = f'{base_url}/code/api/v2/code-issues/code_review_scan'
def main():
    auth_str = auth_func()
    payload = json.dumps({
        "limit": 10,
        "filters": {
            "runId": 0,
            "checkStatus": "Error",
            "codeCategories": [
                "IacMisconfiguration"
            ],
            "severities": [
                "CRITICAL",
                "HIGH"
            ]
        }        
    })
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'authorization': auth_str
    }
    iac_response = requests.request("POST", url, headers=headers, data=payload)
    #print(iac_response.text)
    response_parse = json.loads(iac_response.text)

    grouped_data = defaultdict(list)
    for item in response_parse['data']:
        grouped_data[item['repository']].append({
            'policy': item['policy'],
            'severity': item['severity'],
            'resourceName': item['resourceName'],
            'labels': item['labels'],
            'firstDetected': item['firstDetected']
        })
    sorted_data = {repository: sorted(policies, key=lambda x: x['policy']) for repository, policies in sorted(grouped_data.items())}
    print(json.dumps(sorted_data, indent=2))
main()
