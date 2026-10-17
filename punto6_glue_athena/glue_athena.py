import boto3
import os
import csv
from datetime import datetime, timedelta

# Configuración S3
S3_BUCKET = 'juanpa-aws-workshop-data'
S3_KEY = 'glue_data/sales_data.csv'

def generate_and_upload():
    # 1. Generar datos (Simulando Octubre 2026)
    filename = 'sales_data.csv'
    records = []
    base_date = datetime(2026, 10, 1)
    
    for i in range(25):
        records.append({
            'transaction_id': 8000 + i,
            'region': ['North', 'South', 'East', 'West'][i % 4],
            'product': ['Widget A', 'Widget B', 'Gadget X', 'Gadget Y'][i % 4],
            'revenue': 100.0 + (i * 10.5),
            'date': (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
        })

    print(f"Generando {filename} con {len(records)} registros...")
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "region", "product", "revenue", "date"])
        writer.writeheader()
        writer.writerows(records)

    # 2. Subir a S3
    print(f"Subiendo {filename} a s3://{S3_BUCKET}/{S3_KEY}")
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.upload_file(filename, S3_BUCKET, S3_KEY)
    print("¡Datos cargados correctamente en S3!")

if __name__ == "__main__":
    generate_and_upload()
