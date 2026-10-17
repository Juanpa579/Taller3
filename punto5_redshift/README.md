# Punto 5 — Amazon Redshift (Serverless + Data API)

Región: **us-east-1** · Namespace `default-namespace` · Workgroup `default-workgroup` · Base de datos `dev`

## Estado

| Entregable | Estado | Evidencia |
|---|---|---|
| Namespace y workgroup Serverless desplegados | ✅ | [`02_namespace_default_namespace.png`](evidencias/02_namespace_default_namespace.png) |
| Secreto en Secrets Manager (valor oculto) | ✅ | [`01_secreto_RedshiftAdminSecret.png`](evidencias/01_secreto_RedshiftAdminSecret.png) |
| Rol IAM `RedshiftCopyRole` para leer S3 | ✅ configurado | — (pendiente captura) |
| Conjunto de datos (2 tablas relacionadas) | ✅ | [`users.csv`](users.csv), [`orders.csv`](orders.csv) |
| Programa Python con Data API | ✅ corregido | [`redshift_etl.py`](redshift_etl.py) |
| Ejecución del ETL y resultados | 🟡 pendiente | Ver «Problema encontrado» |
| Eliminación de recursos | 🟡 pendiente de captura | — |

### Problema encontrado en la ejecución

Al ejecutar el programa, Redshift respondió `FATAL: password authentication failed for user "awsuser"`. La causa fue una **desincronización entre el secreto y el namespace**:

- El namespace tiene como usuario administrador **`admin`** (ver [`02_namespace_default_namespace.png`](evidencias/02_namespace_default_namespace.png)). En Redshift Serverless el nombre del administrador no se puede cambiar después de crear el namespace.
- El secreto `RedshiftAdminSecret` se había creado a mano con el usuario `awsuser` y una contraseña que no estaba fijada en el namespace.

**Solución:**
1. Namespace → *Actions → Edit admin credentials → Customize admin user credentials* y fijar la contraseña.
2. Editar el secreto para que contenga exactamente `{"username": "admin", "password": "<la misma contraseña>"}`.
3. O, mejor, usar la opción integrada: *Manage admin credentials in AWS Secrets Manager*. Redshift crea el secreto (`redshift!...`) y mantiene usuario y contraseña sincronizados. En ese caso se pasa su nombre en `REDSHIFT_SECRET_NAME` y se ajusta el `Resource` de la política IAM.

Un error previo (`Redshift endpoint doesn't exist in this region`) venía de usar un nombre de workgroup inexistente (`default`); el nombre real es `default-workgroup`.

---

## 1. Qué es Redshift, para qué se usa y sus componentes

Amazon Redshift es un **almacén de datos (*data warehouse*)** administrado de AWS. Está diseñado para **análisis (OLAP)**: consultas complejas con uniones y agregaciones sobre millones o miles de millones de filas. Es útil para reportes, tableros de BI y análisis histórico.

Lo hace posible su arquitectura:
- **Almacenamiento columnar**: lee solo las columnas que la consulta necesita y comprime mejor.
- **Procesamiento masivamente paralelo (MPP)**: reparte el trabajo entre varios nodos de cómputo.

**Componentes principales**

| Componente | Función |
|---|---|
| Cluster (aprovisionado) | Un nodo *líder* que planifica y coordina, más nodos de cómputo que ejecutan en paralelo |
| **Namespace** (Serverless) | Contiene los datos y objetos: bases de datos, esquemas, tablas, usuarios y roles IAM asociados |
| **Workgroup** (Serverless) | Contiene los recursos de cómputo (RPU), red, VPC y grupos de seguridad |
| Redshift Managed Storage | Almacenamiento administrado, desacoplado del cómputo en RA3 y Serverless |
| `COPY` | Carga masiva y paralela desde S3 (necesita un rol IAM con acceso al bucket) |
| Redshift Spectrum | Consulta datos que permanecen en S3 sin cargarlos |
| **Data API** | API HTTP (sin conexión JDBC/ODBC) para enviar SQL, consultar su estado y leer resultados |
| Query Editor v2 | Editor SQL en el navegador |

## 2. Redshift frente a Amazon RDS

| | Amazon Redshift | Amazon RDS |
|---|---|---|
| Propósito | Análisis (OLAP) sobre grandes volúmenes | Transacciones de aplicaciones (OLTP) |
| Organización | Columnar | Por filas |
| Patrón de acceso | Lecturas masivas, agregaciones, cargas por lotes | Muchas lecturas y escrituras pequeñas por fila, baja latencia |
| Escala típica | Terabytes a petabytes | Gigabytes a pocos terabytes |
| Motores | Redshift (basado en PostgreSQL, con diferencias) | PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, Aurora |

- **Elegiría RDS** para el backend de una tienda en línea que registra pedidos, actualiza inventario y necesita transacciones rápidas y consistentes.
- **Elegiría Redshift** para un área de analítica que debe calcular las ventas por categoría y por mes de los últimos cinco años sobre cientos de millones de pedidos.

## 3. Serverless frente a aprovisionado: elección

Se eligió **Redshift Serverless**.

- **Serverless** factura el cómputo en **RPU-hora, por segundo** (mínimo de 60 s por consulta) y **no cobra cómputo mientras no hay consultas**. El almacenamiento se cobra aparte.
- **Aprovisionado** factura **cada hora** por nodo mientras el cluster exista (aunque no reciba consultas). Se justifica con cargas constantes 24/7, o si se puede reservar capacidad.

Para una práctica de pocas horas con unas cuantas consultas, Serverless resulta más económico. **Importante:** el valor por defecto de la capacidad base es de **128 RPU**; el mínimo permitido es **4 RPU**. Para el taller se debe configurar **4 RPU** y, de ser posible, un límite de uso (*usage limit*) de RPU-horas, para evitar cargos inesperados.

## 4. Contraseña de administración con Secrets Manager

- El programa **no contiene la contraseña**. Obtiene el ARN del secreto con `describe_secret` y se lo entrega al Data API (`SecretArn`). Es Redshift quien lee el secreto y autentica.
- Con `SecretArn` **no se debe pasar `DbUser`**: son dos métodos de autenticación excluyentes.
- El secreto (tipo *Other*) debe tener las claves `username` y `password`. La captura [`01_secreto_RedshiftAdminSecret.png`](evidencias/01_secreto_RedshiftAdminSecret.png) muestra solo sus metadatos (nombre, ARN, clave de cifrado `aws/secretsmanager`); el valor no se expone.
- Alternativa más robusta: *Manage admin credentials in AWS Secrets Manager*, que mantiene el secreto sincronizado con el namespace.

### Permisos IAM

**Rol `RedshiftCopyRole`** (para que Redshift lea S3 durante el `COPY`):
- Tipo de entidad de confianza: *AWS Service → Redshift* (confía en `redshift.amazonaws.com`).
- Política adjunta: `AmazonS3ReadOnlyAccess`.
- Debe estar **asociado al namespace** (*Security and encryption → Permissions*).

**Política del usuario que ejecuta el programa** (reemplazar `<ACCOUNT_ID>`; si se usa el secreto administrado, el recurso es `secret:redshift!*`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadSecret",
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
      "Resource": "arn:aws:secretsmanager:us-east-1:<ACCOUNT_ID>:secret:RedshiftAdminSecret*"
    },
    {
      "Sid": "AllowRedshiftDataApi",
      "Effect": "Allow",
      "Action": [
        "redshift-data:ExecuteStatement",
        "redshift-data:DescribeStatement",
        "redshift-data:GetStatementResult"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowS3Upload",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::juanpa-aws-workshop-data/*"
    },
    {
      "Sid": "AllowWhoAmI",
      "Effect": "Allow",
      "Action": "sts:GetCallerIdentity",
      "Resource": "*"
    }
  ]
}
```

## 5. Conjunto de datos

Se generan con [`generate_data.py`](generate_data.py) dos tablas **relacionadas**: `orders.user_id` referencia a `users.user_id`.

| Tabla | Filas | Columnas |
|---|---|---|
| `users` | 50 | `user_id`, `user_name`, `signup_date` |
| `orders` | 200 | `order_id`, `user_id`, `order_date`, `amount`, `product_category` (`Electronics`, `Books`, `Home`, `Sports`) |

Los pedidos corresponden al tercer trimestre de 2026 (julio a septiembre), con importes aleatorios entre 10.50 y 500.00.

## 6. Cómo reproducirlo

```bash
cd punto5_redshift
pip install boto3
export REDSHIFT_WORKGROUP=default-workgroup
export REDSHIFT_DATABASE=dev
export REDSHIFT_SECRET_NAME=RedshiftAdminSecret      # o 'redshift!...' si es el secreto administrado (comillas simples)
python redshift_etl.py
```

El programa ([`redshift_etl.py`](redshift_etl.py)) hace, en orden:
1. Genera los CSV si no existen y los **sube a S3** (`s3://juanpa-aws-workshop-data/redshift_data/`).
2. **Crea** el esquema `workshop_schema` y las tablas `users` y `orders` (con `DROP IF EXISTS`, así se puede repetir).
3. **Carga** con `COPY ... FORMAT AS CSV IGNOREHEADER 1` usando el rol `RedshiftCopyRole`.
4. Ejecuta las **consultas** y, por cada sentencia: envía el SQL con `execute_statement`, **espera** con `describe_statement` hasta `FINISHED` y **recupera** el resultado con `get_statement_result` (con paginación).

### Errores que se corrigieron en el script

- Se pasaban `DbUser` y `SecretArn` a la vez. Ahora solo `SecretArn`.
- El workgroup y la base de datos eran incorrectos; ahora se configuran por variables de entorno.
- Los valores se leían como `scalarValue`; el Data API devuelve `stringValue`, `longValue`, etc.
- Nunca se subían los CSV ni se cargaba `users`, necesaria para el `JOIN`.
- Faltaba `IGNOREHEADER 1` en el `COPY` (los CSV tienen encabezado).
- No se esperaba a que terminara cada sentencia y se usaba `eval` sobre el secreto.

## 7. Consultas e interpretación

| # | Tipo | Pregunta que responde | SQL |
|---|---|---|---|
| Q1 | Filtro | ¿Qué pedidos son de alto valor (monto > 400)? | `SELECT order_id, user_id, product_category, amount FROM workshop_schema.orders WHERE amount > 400.00 ORDER BY amount DESC LIMIT 10;` |
| Q2 | Unión + agregación | ¿Quiénes son los 5 usuarios que más gastan? | `SELECT u.user_name, COUNT(*) AS pedidos, SUM(o.amount) AS total FROM workshop_schema.users u JOIN workshop_schema.orders o ON u.user_id = o.user_id GROUP BY u.user_name ORDER BY total DESC LIMIT 5;` |
| Q3 | Agregación | ¿Qué categoría genera más ingresos? | `SELECT product_category, COUNT(*) AS pedidos, SUM(amount) AS ventas, ROUND(AVG(amount), 2) AS ticket_prom FROM workshop_schema.orders GROUP BY product_category ORDER BY ventas DESC;` |

**Cómo interpretar los resultados** (los valores concretos están **pendientes de ejecución**):
- **Q1.** Como los importes se generan de forma uniforme entre 10.50 y 500.00, aproximadamente el 20 % de los pedidos supera 400. La consulta muestra los 10 más altos.
- **Q2.** Cada usuario tiene en promedio unos 4 pedidos (200 pedidos entre 50 usuarios). El ranking identifica a los clientes de mayor gasto acumulado, que serían los candidatos a una campaña de fidelización.
- **Q3.** Las cuatro categorías se asignan al azar con la misma probabilidad. Se espera entonces que ventas y ticket promedio sean parecidos entre categorías, sin una dominante clara. La diferencia entre la primera y la última se debe al azar, no a un patrón de negocio.

## 8. Conexión desde un cliente SQL en el computador (opcional)

No se usó. Se inspeccionó con Query Editor v2 y con el Data API, que no requieren abrir la red. De querer conectar con DBeaver, DataGrip, etc., se necesita:

1. En el **workgroup**: *Turn on publicly accessible* y subredes con ruta `0.0.0.0/0` hacia un **Internet Gateway** (la VPC por defecto lo cumple).
2. En el **grupo de seguridad del workgroup**: regla de entrada **TCP 5439** con origen *mi IP* (nunca `0.0.0.0/0`).
3. Conectar al endpoint del workgroup (`default-workgroup.<cuenta>.us-east-1.redshift-serverless.amazonaws.com:5439`) con el usuario y la contraseña del secreto. La contraseña se copia desde Secrets Manager, no se guarda en archivos del proyecto.

## 9. Costos

Valores aproximados para **us-east-1** (octubre de 2026). Confirmar en la [calculadora de AWS](https://calculator.aws/).

| Componente | Precio aproximado | Observación |
|---|---|---|
| Cómputo Serverless | ≈ US$0.375 por RPU-hora, por segundo (mínimo 60 s por consulta) | 4 RPU ≈ **US$1.50/h activa**. Con la base por defecto (128 RPU) serían ≈ US$48/h activa |
| Cómputo en reposo | US$0 | No se cobra cómputo sin consultas |
| Almacenamiento administrado (RMS) | ≈ US$0.024 por GB-mes | Los datos de esta práctica son de kilobytes |
| Cluster aprovisionado (alternativa) | Se cobra por nodo-hora, 24/7, mientras exista | No se usó |

**¿Qué modalidad cuesta menos para esta práctica?** Serverless con 4 RPU. Diez consultas de unos 60 s facturan ≈ 10 minutos de cómputo: **≈ US$0.25**. Si la base fuera 128 RPU, las mismas consultas costarían ≈ US$8.

**¿Qué podría seguir generando cargos después de las consultas?**
- El **almacenamiento** del namespace mientras existan los datos y las copias de recuperación.
- Los **objetos en S3** (`redshift_data/`) y los registros en CloudWatch.
- El **secreto** de Secrets Manager (≈ US$0.40/mes).
- Un cluster aprovisionado, si se hubiera usado, **sigue cobrando por nodo-hora** aunque no reciba consultas. Pausarlo detiene el cómputo, pero no el almacenamiento.

## 10. Eliminación de recursos

```bash
# Workgroup primero y luego el namespace
aws redshift-serverless delete-workgroup --workgroup-name default-workgroup --region us-east-1
aws redshift-serverless delete-namespace --namespace-name default-namespace --region us-east-1

# Datos en S3
aws s3 rm s3://juanpa-aws-workshop-data/redshift_data/ --recursive

# Rol y secreto
aws iam detach-role-policy --role-name RedshiftCopyRole --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
aws iam delete-role --role-name RedshiftCopyRole
aws secretsmanager delete-secret --secret-id RedshiftAdminSecret --force-delete-without-recovery --region us-east-1

# Verificación
aws redshift-serverless list-workgroups --region us-east-1
aws redshift-serverless list-namespaces --region us-east-1
```

Esperar a que el workgroup termine de eliminarse antes de borrar el namespace. Si el secreto era el administrado (`redshift!...`), se elimina junto con el namespace. **Pendiente:** adjuntar la captura de la eliminación en `evidencias/`.
