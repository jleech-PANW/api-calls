import requests, json, configparser, openpyxl
def auth_func():
    config = configparser.ConfigParser()
    config.read('config.ini')
    login_url = config.get('prismacloud', 'cspm_api_url')
    username = config.get('prismacloud', 'username')
    password = config.get('prismacloud', 'password')
    print("Logging In...")
    try:
        url = f'{login_url}/login'
        payload = f"{{\n  \"password\": \"{password}\",\n  \"username\": \"{username}\"\n}}"
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json; charset=UTF-8'
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        response_json = response.json()
        if 'token' in response_json:
            print("Login Successful")
            return response_json['token']
        else:
            print("Failed to get authentication token")
            return None 
    except Exception as e:
        print(f"Failed to get authentication token: {e}")
        return None    
token = auth_func()


def report():
    config = configparser.ConfigParser()
    config.read('config.ini')
    login_url = config.get('prismacloud', 'cspm_api_url')
    url = f"{login_url}/v2/alert?timeType=relative&timeAmount=2&timeUnit=week&detailed=false&policy.severity=critical&policy.type=config"
    payload = {}
    headers = {
      'Accept': '*/*',
      'x-redlock-auth': token
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    print(response.text)

report()

