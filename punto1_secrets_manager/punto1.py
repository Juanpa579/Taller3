import boto3
import json

client = boto3.client('secretsmanager', region_name='us-east-2')
response = client.get_secret_value(SecretId='ejemplo-secreto')
secret = json.loads(response['SecretString'])

print("Usuario:", secret['username'])
print("Contraseña:", secret['password'])