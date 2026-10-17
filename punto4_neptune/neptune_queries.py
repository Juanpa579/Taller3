"""
Punto 4 - Amazon Neptune (Gremlin)

Requisitos:
    pip install "gremlinpython==3.7.*" boto3
    Túnel SSH activo:  ssh -i llave.pem ec2-user@IP_EC2 -L 8182:NEPTUNE_ENDPOINT:8182
    /etc/hosts con:    127.0.0.1  NEPTUNE_ENDPOINT   (para que el certificado TLS valide)
"""
import json

import boto3
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import __
from gremlin_python.process.traversal import T

REGION = "us-east-1"
SECRET_NAME = "NeptuneSecret"


def get_traversal_source(conn):
    src = traversal()
    # with_remote en 3.5-3.7; with_ en 3.8+
    return src.with_remote(conn) if hasattr(src, "with_remote") else src.with_(conn)


def main():
    # 1. Host y puerto desde Secrets Manager (nada hardcodeado)
    sm = boto3.client("secretsmanager", region_name=REGION)
    try:
        secret = json.loads(sm.get_secret_value(SecretId=SECRET_NAME)["SecretString"])
    except Exception as e:
        print(f"Error obteniendo secreto: {e}")
        return

    host = secret["host"]
    port = int(secret.get("port", 8182))  # Neptune usa 8182 (no 7697)
    url = f"wss://{host}:{port}/gremlin"
    print(f"Conectando a {url} (vía túnel SSH -> localhost:{port})")

    conn = DriverRemoteConnection(url, "g")
    g = get_traversal_source(conn)

    try:
        # Limpiar para poder re-ejecutar sin duplicados
        g.V().drop().iterate()

        print("--- Insertando datos ---")
        vertices = [
            ("Alice", "Person"), ("Bob", "Person"), ("Charlie", "Person"),
            ("Diana", "Person"), ("Eve", "Person"),
            ("TechCorp", "Company"), ("DataInc", "Company"), ("CloudSys", "Company"),
            ("AI_Lab", "Company"), ("BioGen", "Company"),
        ]
        for name, label in vertices:
            # T.id fija el ID del vértice, así g.V("Alice") funciona
            g.add_v(label).property(T.id, name).property("name", name).next()

        relationships = [
            ("Alice", "Bob", "MANAGES"), ("Alice", "Charlie", "MANAGES"),
            ("Bob", "Diana", "MENTORS"), ("Charlie", "Eve", "MENTORS"),
            ("Alice", "TechCorp", "WORKS_FOR"), ("Bob", "TechCorp", "WORKS_FOR"),
            ("Charlie", "TechCorp", "WORKS_FOR"),
            ("Diana", "DataInc", "WORKS_FOR"), ("Eve", "DataInc", "WORKS_FOR"),
            ("Diana", "CloudSys", "CONSULTS_FOR"), ("Eve", "CloudSys", "CONSULTS_FOR"),
            ("Alice", "AI_Lab", "INVESTS_IN"), ("Bob", "AI_Lab", "INVESTS_IN"),
            ("Charlie", "BioGen", "INVESTS_IN"),
            ("Bob", "Charlie", "COLLEAGUE_OF"),  # 15ª relación (el enunciado pide >= 15)
        ]
        for src, dst, label in relationships:
            g.V(src).add_e(label).to(__.V(dst)).next()

        print(f"Vértices: {g.V().count().next()} | Aristas: {g.E().count().next()}")

        print("\n--- Consultas ---")
        q1 = g.V("Alice").out("MANAGES").values("name").to_list()
        print(f"1. Personas a cargo de Alice: {q1}")

        q2 = g.V("Diana").out("WORKS_FOR").values("name").to_list()
        print(f"2. Empresas donde trabaja Diana: {q2}")

        # Inversores de AI_Lab que además son mentores de alguien
        q3 = (g.V("AI_Lab").in_("INVESTS_IN")
                .where(__.out("MENTORS"))
                .values("name").to_list())
        print(f"3. Inversores de AI_Lab que son mentores: {q3}")

        # Extra (3 saltos): empresas de los mentorados de los subordinados de Alice
        q4 = (g.V("Alice").out("MANAGES").out("MENTORS")
                .out("WORKS_FOR").dedup().values("name").to_list())
        print(f"4. Empresas de los mentorados de los subordinados de Alice: {q4}")

    except Exception as e:
        print(f"Error en Neptune: {type(e).__name__}: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
