# Data Catalog — Gold Layer (CITE)

## 1) Convenciones generales

* **Capa:** GOLD
* **Propósito:** Dataset limpio, enriquecido y listo para analítica/BI (Star Schema).
* **Grano del modelo:** 1 fila en el fact = **1 ejecución de servicio** (registro operativo) con medidas (horas, montos, participantes).
* **Claves:**

  * **Surrogate keys**: `*_key` (INT/BIGINT)
  * **Natural keys**: columnas operativas (RUC, tipo_servicio, etc.) usadas para unir desde SILVER.

---

# 2) Dimensiones

## 2.1 `gold.dim_cliente`

**Tipo:** Dimensión
**Fuente:** `silver.cliente`
**Grano:** 1 fila por **RUC** (cliente único)
**Clave primaria:** `cliente_key`
**Clave natural:** `ruc`

### Columnas

* `cliente_key` — Surrogate key del cliente.
* `ruc` — Identificador tributario del cliente (natural key).
* `razon_social` — Nombre legal / razón social.
* `tipo_contribuyente` — Clasificación tributaria del cliente.
* `direccion_cliente` — Dirección declarada.
* `region_cliente` — Región.
* `provincia_cliente` — Provincia.
* `distrito_cliente` — Distrito.
* `ubigeo_cliente` — Código ubigeo.
* `telefono_cliente` — Teléfono de contacto.
* `correo_cliente` — Email de contacto.
* `contacto_cliente` — Persona de contacto.

**Uso típico (BI):** segmentación por geografía, tipo de contribuyente, cartera de clientes.

---

## 2.2 `gold.dim_servicio`

**Tipo:** Dimensión
**Fuente:** `silver.servicio`
**Grano:** 1 fila por **servicio de catálogo**
**Clave primaria:** `servicio_key`
**Clave natural (recomendada para tu fact actual):**

* `tipo_servicio`, `tipo_tarea`, `tarifario`

> Nota: si incluyes `denominacion` como parte de la natural key, necesitas que también exista en el fact para enlazar 100%.

### Columnas

* `servicio_key` — Surrogate key del servicio.
* `tipo_servicio` — Macro tipo (ej. “01. Asistencia técnica”).
* `tipo_tarea` — Subtipo / tarea específica.
* `tarifario` — Código/etiqueta de tarifario.
* `denominacion` — Nombre comercial / denominación del servicio (catálogo).
* `tema_abordado` — Tema técnico.
* `perfil_competencia_laboral` — Perfil asociado.
* `estandar_competencia_laboral` — Estándar asociado.
* `complejidad_servicio` — Nivel (baja/media/alta).

**Uso típico (BI):** mix de servicios, complejidad, temas, performance por tipo de tarea.

---

## 2.3 `gold.dim_proyecto`

**Tipo:** Dimensión
**Fuente:** `silver.proyecto`
**Grano:** 1 fila por **esquema de financiamiento/promoción**
**Clave primaria:** `proyecto_key`
**Clave natural:**

* `fuente_financiamiento_servicio`, `servicio_aplico_esquema_prom`, `tipo_regimen_esquema_prom`

### Columnas

* `proyecto_key` — Surrogate key del esquema/proyecto.
* `fuente_financiamiento_servicio` — Fuente (ej. descuento/promoción/subvención).
* `servicio_aplico_esquema_prom` — Indicador/valor (ej. “Sí/No”).
* `tipo_regimen_esquema_prom` — Tipo de régimen.
* `estadio_proyecto` — Estado/estadio (propuesta/ejecución/etc.).
* `participacion_cite_proyecto` — Rol del CITE.
* `fuente_subvencion_proyecto` — Fuente (ej. CONCYTEC u otra).
* `tipo_concurso` — Tipo de concurso.

**Uso típico (BI):** reportes por fuente de financiamiento, concurso, participación CITE.

---

## 2.4 `gold.dim_tiempo`

**Tipo:** Dimensión
**Fuente:** `silver.tiempo`
**Grano:** 1 fila por **combinación temporal** (periodo)
**Clave primaria:** `tiempo_key`
**Clave natural:** `año`, `mes`, `fecha_inicial`, `fecha_final`

### Columnas

* `tiempo_key` — Surrogate key del periodo.
* `año` — Año (INT).
* `mes` — Mes (texto).
* `fecha_inicial` — Inicio del periodo.
* `fecha_final` — Fin del periodo.
* `año_emision_ssipro` — Año de emisión SSIPRO (si aplica).

**Uso típico (BI):** análisis temporal por periodos/mes/año.

---

# 3) Hechos

## 3.1 `gold.fact_servicio_ejecutado`

**Tipo:** Fact (hechos)
**Fuente:** `silver.servicio_ejecutado`
**Grano:** 1 fila por **ejecución de servicio** (registro operativo depurado)
**Claves foráneas:**

* `cliente_key` → `gold.dim_cliente`
* `servicio_key` → `gold.dim_servicio`
* `proyecto_key` → `gold.dim_proyecto`
* `tiempo_key` → `gold.dim_tiempo`

### Columnas (Keys)

* `cliente_key` — FK a dimensión cliente.
* `servicio_key` — FK a dimensión servicio.
* `proyecto_key` — FK a dimensión proyecto/esquema.
* `tiempo_key` — FK a dimensión tiempo.

### Columnas (Medidas)

* `numero_total_horas` — Horas ejecutadas (DECIMAL).
* `cantidad_servicios_ejecutados` — Conteo de servicios ejecutados (INT).
* `numero_matriculados` — Participantes matriculados (INT).
* `numero_culminaron` — Participantes que culminaron (INT).
* `valor_facturado_igv` — Monto facturado (DECIMAL).
* `valor_ingresado_igv` — Monto ingresado/cobrado (DECIMAL).

### Columnas (Trazabilidad / Drill-through)

* `serie` — Serie de comprobante.
* `numero_comprobante_pago` — Número de comprobante.
* `estado` — Estado del servicio.
* `cod_id` — Código interno.
* `fuente_datos` — Fuente/identificador de origen.

### Reglas/KPIs derivados típicos (para BI)

* **Tasa de culminación:** `numero_culminaron / NULLIF(numero_matriculados,0)`
* **Brecha cobro:** `valor_facturado_igv - valor_ingresado_igv`
* **Horas promedio por servicio:** `numero_total_horas / NULLIF(cantidad_servicios_ejecutados,0)`

---

# 4) Relaciones del modelo (Cardinalidad)

* `dim_cliente (1)` → `fact_servicio_ejecutado (N)`
* `dim_servicio (1)` → `fact_servicio_ejecutado (N)`
* `dim_proyecto (1)` → `fact_servicio_ejecutado (N)`
* `dim_tiempo (1)` → `fact_servicio_ejecutado (N)`

---

# 5) Notas de diseño importantes (para tu caso)

* En tu SILVER actual, `servicio_ejecutado` **no incluye `denominacion`**, por lo que:

  * si `denominacion` es parte de la llave natural de servicio, el join puede quedar incompleto.
  * recomendación GOLD: usar como natural key de servicio **(tipo_servicio, tipo_tarea, tarifario)** y dejar `denominacion` como atributo.

