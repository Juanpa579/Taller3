# Punto 6 — AWS Glue Data Catalog + Athena

Región: **us-east-1** · Bucket `juanpa-aws-workshop-data` · Base `workshop_glue_db` · Crawler `sales-crawler` · Tabla `glue_data`

## Estado

| Entregable | Estado | Evidencia |
|---|---|---|
| Archivo CSV con ≥ 20 registros en S3 (25) | ✅ | [`sales_data.csv`](sales_data.csv) |
| Base de datos y crawler (ejecución exitosa, 1 tabla creada) | ✅ | [`01_crawler_ready.png`](evidencias/01_crawler_ready.png) |
| Consulta con filtro en Athena | ✅ | [`02_athena_filtro.png`](evidencias/02_athena_filtro.png) |
| Consulta con agrupación en Athena | ✅ | [`03_athena_agrupacion.png`](evidencias/03_athena_agrupacion.png) |
| Revisión del esquema inferido | 🟡 pendiente de captura | — |
| Agregar registros, re-ejecutar el crawler y verificar | 🟡 script listo, falta ejecutarlo | [`glue_add_records.py`](glue_add_records.py) |
| Eliminación de recursos | 🟡 pendiente de captura | — |

---

## 1. Qué almacena Glue Data Catalog

El **Data Catalog** guarda **metadatos**, no datos: nombres de bases de datos y tablas, columnas y tipos, formato del archivo, ubicación en S3 y particiones. Los **datos** (aquí `sales_data.csv`) siguen en **S3**.

| | Archivos de datos (S3) | Metadatos (Data Catalog) |
|---|---|---|
| Qué son | Los registros: filas del CSV | La descripción: «la tabla `glue_data` tiene estas columnas, está en esta ruta y es CSV» |
| Dónde viven | `s3://juanpa-aws-workshop-data/glue_data/` | Servicio Glue |
| Si se borra | Se pierden los datos | Los datos siguen en S3; la tabla queda sin ubicación válida |

| Concepto | Función |
|---|---|
| **Base de datos** | Agrupa tablas de forma lógica (`workshop_glue_db`). No contiene datos |
| **Tabla** | Define el esquema y apunta a la ubicación en S3 (`glue_data`) |
| **Crawler** | Recorre una ruta de S3, infiere formato y esquema y crea o actualiza las tablas |

Athena consulta la tabla: lee el esquema del catálogo y los datos directamente de S3.

## 2. Datos

[`generate_glue_data.py`](generate_glue_data.py) genera `sales_data.csv` (25 registros) y [`glue_athena.py`](glue_athena.py) lo sube a `s3://juanpa-aws-workshop-data/glue_data/`.

| Columna | Contenido |
|---|---|
| `transaction_id` | 8000 a 8024 |
| `region` | North, South, East, West (rotando) |
| `product` | Widget A, Widget B, Gadget X, Gadget Y |
| `revenue` | `100 + 10.5 × i` (de 100.0 a 352.0) |
| `date` | Un día por registro, hacia atrás desde 2026-10-01 |

## 3. Cómo reproducirlo

1. **Bucket** `juanpa-aws-workshop-data` en S3 y datos:
   ```bash
   cd punto6_glue_athena
   python glue_athena.py            # genera sales_data.csv y lo sube a glue_data/
   ```
2. **Rol del crawler** `GlueServiceRole-Crawler` (IAM → Roles → *AWS service → Glue*), con esta política propia `Policy-GlueCrawlerAccess`. Alternativa: la política administrada `AWSGlueServiceRole` más acceso de lectura al bucket.
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       { "Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
         "Resource": ["arn:aws:s3:::juanpa-aws-workshop-data", "arn:aws:s3:::juanpa-aws-workshop-data/*"] },
       { "Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": "*" },
       { "Effect": "Allow",
         "Action": ["glue:CreateTable", "glue:UpdateTable", "glue:GetTable", "glue:GetTables",
                    "glue:BatchCreatePartition", "glue:GetDatabase", "glue:StartCrawler",
                    "glue:GetCrawler", "glue:TagResource"],
         "Resource": "*" }
     ]
   }
   ```
3. **Base de datos:** Glue → *Databases → Add database* → `workshop_glue_db`.
4. **Crawler:** Glue → *Crawlers → Create crawler* → nombre `sales-crawler`, origen S3 `s3://juanpa-aws-workshop-data/glue_data/`, rol `GlueServiceRole-Crawler`, base `workshop_glue_db`, ejecución *On demand*. Ejecutar con **Run** y esperar `Ready`.
5. **Athena** (workgroup `primary`, base `workshop_glue_db`; requiere una ubicación S3 para los resultados de las consultas).

### Revisión del esquema inferido (pendiente de captura)

En Glue → *Tables → `glue_data` → Schema*, comprobar:

| Columna | Tipo esperado | Qué revisar |
|---|---|---|
| `transaction_id` | `bigint` | — |
| `region`, `product` | `string` | — |
| `revenue` | `double` | — |
| `date` | `string` (o `date`) | Si quedó `string`, se puede **corregir** con *Edit schema* → `date`, o consultarla con `CAST(date AS date)` |

También verificar que el crawler haya reconocido la primera fila como **encabezado** (los nombres de columna deben ser `transaction_id`, `region`…, y no `col0`, `col1`…). Si hay errores, se corrigen con *Edit schema*; tener en cuenta que una nueva ejecución del crawler puede sobrescribir las modificaciones manuales según su política de actualización.

## 4. Consultas en Athena y resultados

Capturas reales: [`02_athena_filtro.png`](evidencias/02_athena_filtro.png) y [`03_athena_agrupacion.png`](evidencias/03_athena_agrupacion.png).

**Consulta 1 — filtro.** *¿Qué transacciones tienen ingresos mayores a 300?*

```sql
select * from workshop_glue_db.glue_data where revenue > 300;
```

Resultado: **5 filas** (8020 a 8024), con ingresos de 310.0 a 352.0. Datos escaneados: 0.96 KB.

| transaction_id | region | product | revenue | date |
|---|---|---|---|---|
| 8020 | North | Widget A | 310.0 | 2026-09-11 |
| 8021 | South | Widget B | 320.5 | 2026-09-10 |
| 8022 | East | Gadget X | 331.0 | 2026-09-09 |
| 8023 | West | Gadget Y | 341.5 | 2026-09-08 |
| 8024 | North | Widget A | 352.0 | 2026-09-07 |

*Interpretación:* los ingresos crecen con el índice (`100 + 10.5 × i`), así que superan 300 solo los 5 últimos registros (i = 20 a 24).

**Consulta 2 — agrupación.** *¿Cuánto ingreso suma cada región?*

```sql
select region, SUM(revenue) as total from workshop_glue_db.glue_data group by region;
```

| region | total |
|---|---|
| East | 1356.0 |
| South | 1293.0 |
| North | 1582.0 |
| West | 1419.0 |

*Interpretación:* **North** lidera porque tiene 7 transacciones y las demás regiones 6 (25 registros repartidos de forma rotativa), no porque venda más por transacción. La suma de las cuatro regiones es 5650.0, igual al total de los 25 registros.

## 5. Agregar registros y actualizar el catálogo (pendiente de ejecución)

```bash
python glue_add_records.py
```

El script sube `sales_data_2.csv` (5 registros, `transaction_id` 8025 a 8029) al **mismo prefijo** y ejecuta el crawler. El usuario necesita permisos `glue:StartCrawler` y `glue:GetCrawler`. Equivalente con la CLI:

```bash
aws s3 cp sales_data_2.csv s3://juanpa-aws-workshop-data/glue_data/
aws glue start-crawler --name sales-crawler --region us-east-1
aws glue get-crawler --name sales-crawler --query 'Crawler.State' --region us-east-1
```

**Verificación en Athena** (esperado: 30 filas, antes 25):

```sql
select count(*) from workshop_glue_db.glue_data;
select region, SUM(revenue) as total from workshop_glue_db.glue_data group by region;
```

El esquema no cambia, porque el archivo nuevo tiene las mismas columnas, y Athena lee los dos archivos del prefijo como una sola tabla. El nuevo crawler es necesario cuando cambian columnas o aparecen particiones; para solo añadir filas con el mismo esquema Athena ya las ve sin ejecutarlo.

## 6. Crawler frente a creación manual de la tabla

| | Crawler | Tabla manual (consola, DDL en Athena o API) |
|---|---|---|
| Esfuerzo inicial | Bajo: infiere formato y tipos | Mayor: se escribe cada columna y el formato |
| Control del esquema | Puede inferir mal (p. ej. `date` como `string`) | Total: se definen los tipos exactos |
| Cambios en los datos | Detecta columnas y particiones nuevas al volver a ejecutarse | Hay que modificar la tabla a mano |
| Costo | Se factura por DPU-hora de cada ejecución | Sin costo de cómputo |
| Cuándo conviene | Datos de esquema desconocido o que cambia | Esquema estable y conocido, o cuando se necesita precisión de tipos |

## 7. ¿Se necesita alguna credencial de aplicación?

**No se creó otro secreto.** Todos los recursos de este punto (S3, Glue y Athena) se manejan **solo con permisos IAM**:

- El **usuario** que ejecuta los scripts se autentica con sus credenciales de IAM (`aws configure`) y sus políticas le permiten usar S3, Glue y Athena.
- El **crawler** asume el rol IAM `GlueServiceRole-Crawler`; no hay usuario ni contraseña.
- **Athena** lee el catálogo y S3 con los permisos del usuario que consulta.
- No hay una base de datos con usuario y contraseña (como RDS o Redshift) ni una conexión JDBC. Un secreto guarda credenciales de *aplicación* (base de datos, API); aquí no existen.

Si se usara un crawler contra una base de datos JDBC, esa conexión **sí** requeriría usuario y contraseña, y estos se guardarían en Secrets Manager.

## 8. Costos

Valores aproximados para **us-east-1** (octubre de 2026). Confirmar en la [calculadora de AWS](https://calculator.aws/).

| Componente | Precio aproximado | En esta práctica |
|---|---|---|
| **Crawler** | US$0.44 por DPU-hora, por segundo, con **mínimo de 10 min por ejecución** | 2 DPU × 10 min ≈ **US$0.15 por ejecución** (aunque termine en 30 s) |
| **Data Catalog** | Gratis hasta 1 millón de objetos y 1 millón de peticiones al mes. Después, US$1 por 100 000 objetos o por millón de peticiones | **US$0**: una base y una tabla |
| **S3** | ≈ US$0.023 por GB-mes, más peticiones | Kilobytes: centavos o menos |
| **Athena** | **US$5 por TB escaneado** (se redondea a MB, mínimo 10 MB por consulta) | 0.96 KB escaneados se facturan como 10 MB ≈ **US$0.00005** por consulta |

**Efecto del volumen de datos examinados.** En Athena el costo es proporcional a los datos que la consulta **lee**, no al tamaño de la tabla ni al resultado. Un CSV de 1 TB leído completo cuesta ≈ US$5 por consulta. Para reducirlo:
- usar formatos **columnares y comprimidos** (Parquet, ORC), de modo que se lea solo las columnas necesarias;
- **particionar** por fecha o región para que el filtro descarte archivos completos;
- seleccionar solo las columnas necesarias (evitar `SELECT *`).

El crawler no cobra por el tamaño de los datos, sino por el tiempo de ejecución.

## 9. Eliminación de recursos

```bash
aws glue delete-crawler  --name sales-crawler --region us-east-1
aws glue delete-table    --database-name workshop_glue_db --name glue_data --region us-east-1
aws glue delete-database --name workshop_glue_db --region us-east-1

aws s3 rm s3://juanpa-aws-workshop-data --recursive
aws s3 rb s3://juanpa-aws-workshop-data

aws iam detach-role-policy --role-name GlueServiceRole-Crawler --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/Policy-GlueCrawlerAccess
aws iam delete-role   --role-name GlueServiceRole-Crawler
aws iam delete-policy --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/Policy-GlueCrawlerAccess
```

También se debe borrar el **bucket de resultados de Athena** (si se creó uno aparte), el grupo de logs `/aws-glue/crawlers` en CloudWatch y comprobar en Billing que no quedan cargos. **Pendiente:** adjuntar la captura de la eliminación en `evidencias/`.
