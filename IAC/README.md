## iac-missconf.py
This is the main file to be run. Requires the auth.py file to be present in the same directory and to be filled out with the login details of your prisma tenant, access-key, and secret. 
This script will use the auth module (included) to log into prisma, it will then pull down CAS IAC miss-configurations and sort them by repository. By default this is limited to 10. Adjust the limit at your need and at your own risk. 
This script only looks for Critical and High miss-configurations this can be adjusted by changing the filters section within the payload json variable. 

##auth.py
**!! This is not a production ready solution. Use best practices for obfuscating credentials dependent on your environment**
You will need to fillout your base_url variable with your tenant's base url. Found here: https://pan.dev/prisma-cloud/api/cspm/api-urls/
Your login string (logstr) will need to be filled out with an access key and secret from your prisma tenant. Do not store these credentials in source control. 
