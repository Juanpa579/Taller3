"""
Punto 6 - Agrega registros nuevos al conjunto de datos en S3 y vuelve a ejecutar el crawler.

Sube un segundo archivo (sales_data_2.csv, 5 registros nuevos) al mismo prefijo que el original.
Luego inicia el crawler para que el catálogo se actualice. Usa solo permisos IAM (sin secretos).
"""
import csv
import time
from datetime import datetime, timedelta

import boto3

REGION = "us-east-1"
S3_BUCKET = "juanpa-aws-workshop-data"
S3_KEY = "glue_data/sales_data_2.csv"
CRAWLER = "sales-crawler"


def main():
    filename = "sales_data_2.csv"
    base_date = datetime(2026, 10, 2)  # fechas posteriores al archivo original
    regions = ["North", "South", "East", "West"]
    products = ["Widget A", "Widget B", "Gadget X", "Gadget Y"]

    rows = [
        {
            "transaction_id": 8025 + i,
            "region": regions[i % 4],
            "product": products[i % 4],
            "revenue": 400.0 + i * 10.5,
            "date": (base_date + timedelta(days=i)).strftime("%Y-%m-%d"),
        }
        for i in range(5)
    ]
    with open(filename, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["transaction_id", "region", "product", "revenue", "date"])
        w.writeheader()
        w.writerows(rows)

    print(f"Subiendo {filename} -> s3://{S3_BUCKET}/{S3_KEY}")
    boto3.client("s3", region_name=REGION).upload_file(filename, S3_BUCKET, S3_KEY)

    glue = boto3.client("glue", region_name=REGION)
    print(f"Iniciando crawler {CRAWLER}...")
    glue.start_crawler(Name=CRAWLER)
    while True:
        state = glue.get_crawler(Name=CRAWLER)["Crawler"]["State"]
        print(f"  Estado: {state}")
        if state == "READY":
            break
        time.sleep(15)

    last = glue.get_crawler(Name=CRAWLER)["Crawler"]["LastCrawl"]
    print(f"Último resultado: {last.get('Status')}")
    print("Verifica en Athena: SELECT COUNT(*) FROM workshop_glue_db.glue_data;  (esperado: 30)")


if __name__ == "__main__":
    main()
