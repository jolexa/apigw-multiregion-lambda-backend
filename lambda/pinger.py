import os
from botocore.vendored import requests

def handler(event, context):
    requests.get('https://' + os.environ['PrimaryUrl'] + "/ting")
