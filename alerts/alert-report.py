import requests, json, configparser, time
#Using config.ini pull credentials and get an api token.
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


def main():
# Set Job Variables
    config = configparser.ConfigParser()
    config.read('config.ini')
    login_url = config.get('prismacloud', 'cspm_api_url')
    url = f"{login_url}/alert/csv"
# This is how the filter is set.
    payload = "{\n  \"detailed\": true,\n  \"filters\": [\n    {\n      \"name\": \"alert.status\",\n      \"operator\": \"=\",\n      \"value\": \"open\"\n    },\n    {\n      \"name\": \"timeRange.type\",\n      \"operator\": \"=\",\n      \"value\": \"ALERT_OPENED\"\n    },\n    {\n      \"name\": \"policy.type\",\n      \"operator\": \"=\",\n      \"value\": \"config\"\n    }\n  ],\n  \"timeRange\": {\n    \"type\": \"relative\",\n    \"value\": {\n      \"unit\": \"hour\",\n      \"amount\": \"24\"\n    }\n  },\n  \"limit\": 0,\n  \"offset\": 0\n}"   
    headers = {
      'Content-Type': 'application/json; charset=UTF-8',
      'Accept': 'application/json; charset=UTF-8',
      'x-redlock-auth': token
    }
# Queue Download Job
    response = requests.request("POST", url, headers=headers, data=payload)
    
    job_data = json.loads(response.text)
    job_id = job_data['id']
    job_status = job_data['status']
    print(job_id)
    
    status_url = job_data['statusUri']
    url2 = f"{login_url}{status_url}"
    payload2 = {}
    headers2 = {
      'Accept': 'application/json; charset=UTF-8',
      'x-redlock-auth': token
    }
# Get Job status every 15 seconds until the download is ready    
    while job_status != "READY_TO_DOWNLOAD":
        response2 = requests.request("GET", url2, headers=headers2, data=payload2)
        status_data = json.loads(response2.text)
        job_status = status_data['status']
        if job_status != "READY_TO_DOWNLOAD":
            print("Waiting for download...")
            print(job_status)
            time.sleep(15)
    
    print("Download Ready")
# Reseting Variables
    payload3 = {}
    headers3 = {
        'x-redlock-auth': token
    }
    url3 = f"{login_url}/alert/csv/{job_id}/download"
# Download    
    response3 = requests.request("GET", url3, headers=headers3, data=payload3)
    open('alert_report.csv', 'wb').write(response3.content)
    print("Download Complete!")
main()

