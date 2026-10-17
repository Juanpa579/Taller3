# Actividad AWS — Ingeniería de Datos 2026-2 (Universidad EIA)

**Autores:** Juan Pablo Londoño Zea · Miguel Vallejo Duque

Este repositorio contiene el código, las consultas, las instrucciones, los resultados y las evidencias de los seis puntos de la actividad. Cada carpeta tiene su propio `README.md` para reproducir el punto correspondiente.

## Contenido

| Punto | Tema | Carpeta | Región | Estado |
|---|---|---|---|---|
| 1 | AWS Secrets Manager | [`punto1_secrets_manager`](punto1_secrets_manager/) | us-east-2 | ✅ Completo |
| 2 | Terraform, Boto3 y AWS CLI (S3 + EC2 + RDS) | [`punto2_terraform_sdk_cli`](punto2_terraform_sdk_cli/) | us-east-2 | ✅ Completo (ver nota) |
| 3 | Amazon DocumentDB | [`punto3_documentdb`](punto3_documentdb/) | us-east-2 | ✅ Completo |
| 4 | Amazon Neptune | [`punto4_neptune`](punto4_neptune/) | us-east-1 | 🟡 Infraestructura y túnel listos; falta captura de resultados y eliminación |
| 5 | Amazon Redshift | [`punto5_redshift`](punto5_redshift/) | us-east-1 | 🟡 Infraestructura y secreto listos; falta ejecutar el ETL y eliminar |
| 6 | AWS Glue Data Catalog + Athena | [`punto6_glue_athena`](punto6_glue_athena/) | us-east-1 | 🟡 Crawler y consultas listos; falta agregar registros y eliminar |

> Dentro de cada punto se usó **una sola región**. Los puntos 1-3 se desarrollaron en us-east-2 y los puntos 4-6 en us-east-1.

Los README de los puntos 4, 5 y 6 indican en una sección **«Estado»** qué está evidenciado con capturas y qué está pendiente, para no presentar como ejecutado algo que no se ejecutó.

## Estructura

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── punto1_secrets_manager/      # script Boto3, política de acceso, evidencia
├── punto2_terraform_sdk_cli/    # terraform/, boto3/, cli/, permisos.json, evidencias
├── punto3_documentdb/           # docdb.py, certificado CA, evidencias
├── punto4_neptune/              # neptune_queries.py, evidencias
├── punto5_redshift/             # generate_data.py, redshift_etl.py, CSV, evidencias
└── punto6_glue_athena/          # scripts de datos, CSV, evidencias
```

## Requisitos generales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
aws configure            # usuario IAM (NO la cuenta raíz); verificar con:
aws sts get-caller-identity
```

## Seguridad: qué NO se publica

- Contraseñas, llaves de acceso de IAM y llaves privadas (`*.pem`). El único `.pem` incluido es `global-bundle.pem`, el **certificado público de la CA** de Amazon RDS/DocumentDB.
- Archivos de estado de Terraform (`*.tfstate`) y la carpeta `.terraform/`. Están excluidos por `.gitignore`.
- Capturas con credenciales. Las capturas de Secrets Manager muestran únicamente los metadatos del secreto, nunca su valor.
- Los programas recuperan toda contraseña desde **AWS Secrets Manager** en tiempo de ejecución; ningún script la lleva escrita.

## Pendientes antes de la entrega final
- [ ] **Punto 4:** ejecutar `neptune_queries.py` con el túnel activo, guardar la salida en `punto4_neptune/evidencias/` y eliminar los recursos.
- [ ] **Punto 5:** sincronizar usuario y contraseña del namespace con el secreto, ejecutar `redshift_etl.py` y eliminar los recursos.
- [ ] **Punto 6:** capturar el esquema del crawler, ejecutar `glue_add_records.py` + re-crawl y eliminar los recursos.
- [ ] **General:** captura del dashboard de *Billing* sin cargos activos después de eliminar todo.
# Taller3
