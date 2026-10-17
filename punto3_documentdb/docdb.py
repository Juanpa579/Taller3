import json
import boto3
from pymongo import MongoClient

SECRET_NAME = "rds!cluster-c86d09de-19cd-4aae-b75d-ec3a32ee7aac"
REGION = "us-east-2"
CA_FILE = "global-bundle.pem"

sm = boto3.client("secretsmanager", region_name=REGION)
secret = json.loads(sm.get_secret_value(SecretId=SECRET_NAME)["SecretString"])

client = MongoClient(
    host="localhost",
    port=27018,
    username=secret["username"],
    password=secret["password"],
    tls=True,
    tlsCAFile=CA_FILE,
    tlsAllowInvalidHostnames=True,
    directConnection=True,
    retryWrites=False,
)

db = client["escuela"]
col = db["estudiantes"]
col.delete_many({})

docs = [
    {"nombre": "Ana",    "carrera": "Ingeniería de Sistemas", "semestre": 5, "promedio": 4.2},
    {"nombre": "Luis",   "carrera": "Ingeniería Civil",       "semestre": 3, "promedio": 3.8},
    {"nombre": "María",  "carrera": "Ingeniería de Sistemas", "semestre": 7, "promedio": 4.5},
    {"nombre": "Carlos", "carrera": "Ingeniería Mecánica",    "semestre": 2, "promedio": 3.5},
    {"nombre": "Sofía",  "carrera": "Ingeniería Civil",       "semestre": 6, "promedio": 4.0},
    {"nombre": "Juan",   "carrera": "Ingeniería de Sistemas", "semestre": 4, "promedio": 3.9},
    {"nombre": "Laura",  "carrera": "Ingeniería Mecánica",    "semestre": 8, "promedio": 4.7},
    {"nombre": "Pedro",  "carrera": "Ingeniería Civil",       "semestre": 1, "promedio": 3.2},
    {"nombre": "Camila", "carrera": "Ingeniería de Sistemas", "semestre": 9, "promedio": 4.8},
    {"nombre": "Diego",  "carrera": "Ingeniería Mecánica",    "semestre": 5, "promedio": 3.7},
]
result = col.insert_many(docs)
print("Insertados:", len(result.inserted_ids))

print("\n--- FILTRO (promedio >= 4.0) ---")
for d in col.find({"promedio": {"$gte": 4.0}}, {"_id": 0}):
    print(d)

print("\n--- ORDENACIÓN (promedio desc) ---")
for d in col.find({}, {"_id": 0}).sort("promedio", -1):
    print(d)

print("\n--- AGREGACIÓN (por carrera) ---")
pipeline = [
    {"$group": {
        "_id": "$carrera",
        "total_estudiantes": {"$sum": 1},
        "promedio_general": {"$avg": "$promedio"},
    }},
    {"$sort": {"promedio_general": -1}},
]
for r in col.aggregate(pipeline):
    print(r)

client.close()