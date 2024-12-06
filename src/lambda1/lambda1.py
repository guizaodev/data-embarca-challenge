import boto3
import requests
import os
from uuid6 import uuid7

s3 = boto3.client('s3')

def lambda_handler(event, context):
    file_url = event['file_url']
    bucket_name = os.environ['BUCKET_NAME']
    file_name = f"{uuid7()}.csv"

    response = requests.get(file_url)
    response.raise_for_status()

    s3.put_object(Bucket=bucket_name, Key=file_name, Body=response.content)
    return {"bucket_name": bucket_name, "file_name": file_name}