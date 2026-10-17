import csv
import os
from datetime import datetime, timedelta

def generate_glue_data():
    filename = "sales_data.csv"
    print(f"Generando {filename} con datos de 2026...")

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

    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["transaction_id", "region", "product", "revenue", "date"])
        writer.writeheader()
        writer.writerows(records)
    
    print("Datos listos.")

if __name__ == "__main__":
    generate_glue_data()
