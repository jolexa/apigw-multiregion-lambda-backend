import os
from botocore.vendored import requests

def handler(event, context):
    try:
        requests.get('https://' + os.environ['PrimaryUrl'] + "/ting")
    except Exception as e:
        print("Received an error, not retrying")
        print(e)
