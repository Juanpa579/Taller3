"""
Punto 5 - Amazon Redshift Serverless + Data API

Configuración por variables de entorno (o edita los valores por defecto):
    REDSHIFT_WORKGROUP     nombre del workgroup (consola: Redshift Serverless > Workgroups)
    REDSHIFT_DATABASE      base de datos (por defecto en Serverless: dev)
    REDSHIFT_SECRET_NAME   secreto con {"username": ..., "password": ...}
    REDSHIFT_COPY_ROLE     nombre del rol IAM asociado al namespace
"""
import os
import sys
import time

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
BUCKET = os.getenv("S3_BUCKET", "juanpa-aws-workshop-data")
S3_PREFIX = "redshift_data/"
SECRET_NAME = os.getenv("REDSHIFT_SECRET_NAME", "RedshiftAdminSecret")
WORKGROUP = os.getenv("REDSHIFT_WORKGROUP", "default-workgroup")
DATABASE = os.getenv("REDSHIFT_DATABASE", "dev")
COPY_ROLE_NAME = os.getenv("REDSHIFT_COPY_ROLE", "RedshiftCopyRole")

FILES = ["users.csv", "orders.csv"]


def ensure_data_files():
    if all(os.path.exists(f) for f in FILES):
        return
    print("CSV no encontrados, generándolos...")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generate_data import generate_redshift_data
    generate_redshift_data()


def upload_to_s3(s3, filename):
    key = f"{S3_PREFIX}{filename}"
    print(f"Subiendo {filename} -> s3://{BUCKET}/{key}")
    s3.upload_file(filename, BUCKET, key)


class RedshiftRunner:
    def __init__(self, secret_arn):
        self.client = boto3.client("redshift-data", region_name=REGION)
        self.secret_arn = secret_arn

    def run(self, sql, label=""):
        """Envía el SQL, espera a que termine y devuelve el id. Lanza error si falla."""
        print(f"\n> {label or sql.strip()[:60]}")
        # Con SecretArn NO se debe pasar DbUser (son métodos de auth excluyentes)
        sid = self.client.execute_statement(
            WorkgroupName=WORKGROUP,
            Database=DATABASE,
            SecretArn=self.secret_arn,
            Sql=sql,
        )["Id"]
        while True:
            d = self.client.describe_statement(Id=sid)
            if d["Status"] in ("FINISHED", "FAILED", "ABORTED"):
                break
            time.sleep(1.5)
        print(f"  Estado: {d['Status']}")
        if d["Status"] != "FINISHED":
            raise RuntimeError(d.get("Error", "Sentencia no terminó correctamente"))
        return sid

    def fetch(self, sid):
        cols, rows, token = None, [], None
        while True:
            kw = {"Id": sid}
            if token:
                kw["NextToken"] = token
            r = self.client.get_statement_result(**kw)
            cols = cols or [c["name"] for c in r["ColumnMetadata"]]
            for rec in r["Records"]:
                # cada campo es {'stringValue': ..} / {'longValue': ..} / {'isNull': True}
                rows.append([None if f.get("isNull") else next(iter(f.values())) for f in rec])
            token = r.get("NextToken")
            if not token:
                return cols, rows

    def query(self, sql, label):
        cols, rows = self.fetch(self.run(sql, label))
        print("  " + " | ".join(cols))
        for row in rows:
            print("  " + " | ".join(str(v) for v in row))
        return rows


def main():
    s3 = boto3.client("s3", region_name=REGION)
    sm = boto3.client("secretsmanager", region_name=REGION)
    account_id = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{COPY_ROLE_NAME}"

    # El Data API necesita el ARN del secreto (no el contenido). Se obtiene del propio secreto.
    secret = sm.describe_secret(SecretId=SECRET_NAME)
    secret_arn = secret["ARN"]
    print(f"Secreto: {SECRET_NAME} | Workgroup: {WORKGROUP} | DB: {DATABASE} | Región: {REGION}")

    # --- 0. Datos y S3 ---
    ensure_data_files()
    for f in FILES:
        upload_to_s3(s3, f)

    rs = RedshiftRunner(secret_arn)

    # --- 1. Esquema y tablas ---
    print("\n=== 1. Creando schema y tablas ===")
    rs.run("CREATE SCHEMA IF NOT EXISTS workshop_schema;", "CREATE SCHEMA")
    rs.run("DROP TABLE IF EXISTS workshop_schema.orders;", "DROP orders")
    rs.run("DROP TABLE IF EXISTS workshop_schema.users;", "DROP users")
    rs.run("""CREATE TABLE workshop_schema.users (
                user_id INT PRIMARY KEY, user_name VARCHAR(50), signup_date DATE);""",
           "CREATE users")
    rs.run("""CREATE TABLE workshop_schema.orders (
                order_id INT PRIMARY KEY, user_id INT, order_date DATE,
                amount DECIMAL(10,2), product_category VARCHAR(50));""",
           "CREATE orders")

    # --- 2. COPY desde S3 (los CSV tienen encabezado -> IGNOREHEADER 1) ---
    print("\n=== 2. Cargando datos con COPY ===")
    for table, f in (("users", "users.csv"), ("orders", "orders.csv")):
        rs.run(f"""COPY workshop_schema.{table}
                   FROM 's3://{BUCKET}/{S3_PREFIX}{f}'
                   IAM_ROLE '{role_arn}'
                   FORMAT AS CSV IGNOREHEADER 1 REGION '{REGION}';""",
               f"COPY {table}")
    rs.query("SELECT (SELECT COUNT(*) FROM workshop_schema.users) AS users, "
             "(SELECT COUNT(*) FROM workshop_schema.orders) AS orders;", "Conteo de filas cargadas")

    # --- 3. Consultas analíticas ---
    print("\n=== 3. Consultas analíticas ===")
    rs.query("""SELECT order_id, user_id, product_category, amount
                FROM workshop_schema.orders
                WHERE amount > 400.00 ORDER BY amount DESC LIMIT 10;""",
             "Q1 (filtro): ¿qué pedidos son de alto valor (> 400)?")

    rs.query("""SELECT u.user_name, COUNT(*) AS pedidos, SUM(o.amount) AS total
                FROM workshop_schema.users u
                JOIN workshop_schema.orders o ON u.user_id = o.user_id
                GROUP BY u.user_name ORDER BY total DESC LIMIT 5;""",
             "Q2 (JOIN + agregación): ¿quiénes son los 5 usuarios que más gastan?")

    rs.query("""SELECT product_category, COUNT(*) AS pedidos,
                       SUM(amount) AS ventas, ROUND(AVG(amount), 2) AS ticket_prom
                FROM workshop_schema.orders
                GROUP BY product_category ORDER BY ventas DESC;""",
             "Q3 (agregación): ¿qué categoría genera más ingresos?")


if __name__ == "__main__":
    main()
