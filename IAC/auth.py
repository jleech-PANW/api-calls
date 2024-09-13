import requests, json
base_url = "YOUR PRISMA TENANT API URL"
logstr = "{\n  \"password\": \"YOURACCESSKEYSECRET\",\n  \"username\": \"YOURACCESSKEY\"\n}"

def auth_func():
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json; charset=UTF-8'
    }
    log_url = f'{base_url}/login'
    login_response = requests.request("POST", log_url, headers=headers, data=logstr)
    token_json = json.loads(login_response.content)
    token = token_json['token']
    return token
