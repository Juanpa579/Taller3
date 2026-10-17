import csv
import random
from datetime import datetime, timedelta
import os

def generate_redshift_data():
    # Fechas base: Simulamos Q3 2026 (Julio - Septiembre 2026)
    start_date = datetime(2026, 7, 1)
    end_date = datetime(2026, 9, 30)
    
    users_file = "users.csv"
    orders_file = "orders.csv"

    print(f"Generando datos para Redshift (Periodo: {start_date.year})...")

    # --- Generar Usuarios ---
    users = []
    user_ids = []
    for i in range(50):
        uid = 1001 + i
        user_ids.append(uid)
        users.append({
            'user_id': uid,
            'user_name': f"Usuario_{i}",
            'signup_date': (start_date - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d')
        })
    
    with open(users_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["user_id", "user_name", "signup_date"])
        writer.writeheader()
        writer.writerows(users)

    # --- Generar Pedidos ---
    orders = []
    for i in range(200):
        uid = random.choice(user_ids)
        # Generar orden entre Q3 2026
        random_days = random.randint(0, (end_date - start_date).days)
        order_date = start_date + timedelta(days=random_days)
        orders.append({
            'order_id': 5001 + i,
            'user_id': uid,
            'order_date': order_date.strftime('%Y-%m-%d'),
            'amount': round(random.uniform(10.50, 500.00), 2),
            'product_category': random.choice(['Electronics', 'Books', 'Home', 'Sports'])
        })

    with open(orders_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["order_id", "user_id", "order_date", "amount", "product_category"])
        writer.writeheader()
        writer.writerows(orders)

    print(f"Datos creados: {users_file} y {orders_file}")

if __name__ == "__main__":
    generate_redshift_data()
