import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# ==============================================================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="Tablero CITE (Gold)", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Monitor de Servicios Ejecutados - CITE")
st.markdown("---")

# ==============================================================================
# 2. CONEXIÓN A SQL SERVER
# ==============================================================================
SERVER = 'localhost'       
DATABASE = 'DataWarehouseCITE'   

@st.cache_data
def load_data():
    try:
        # Cadena de conexión (Autenticación de Windows)
        connection_string = f"mssql+pyodbc://{SERVER}/{DATABASE}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        engine = create_engine(connection_string)
        
        # ------------------------------------------------------------------
        # QUERY SQL ACTUALIZADA (Nombres exactos de tus Vistas Gold)
        # ------------------------------------------------------------------
        query = """
        SELECT 
            -- Cliente (Usamos los nombres de la Vista Gold)
            c.nombre_cliente,    
            c.ruc_cliente,
            c.telefono,
            c.email,
            c.region,
            
            -- Servicio
            s.nombre_comercial,
            s.categoria_servicio,
            
            -- Tiempo
            t.anio,
            t.mes_nombre,
            
            -- Métricas (Hechos)
            f.horas_ejecutadas,
            f.monto_facturado,
            f.cantidad_servicios,
            f.sistema_origen
            
        FROM gold.fact_servicio_ejecutado f
        
        -- JOINS usando los IDs generados en las Vistas
        LEFT JOIN gold.dim_cliente c  ON f.id_cliente = c.id_cliente
        LEFT JOIN gold.dim_servicio s ON f.id_servicio = s.id_servicio
        LEFT JOIN gold.dim_tiempo t   ON f.id_tiempo = t.id_tiempo
        """
        
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        return df

    except Exception as e:
        st.error(f"❌ Error conectando a la base de datos: {e}")
        return pd.DataFrame()

# Cargar datos
df = load_data()

if df.empty:
    st.warning("⚠️ No se encontraron datos. Verifica que las vistas 'gold' existan y tengan datos.")
    st.stop()

# ==============================================================================
# 3. INTERFAZ EN PESTAÑAS (TABS)
# ==============================================================================
tab_cliente, tab_servicio = st.tabs(["👤 Cliente", "🛠️ Servicios y Proyectos"])

# ------------------------------------------------------------------------------
# PESTAÑA 1: CLIENTE (Búsqueda de Perfil)
# ------------------------------------------------------------------------------
with tab_cliente:
    st.header("Perfil del Cliente")
    st.info("Busca por RUC o Razón Social para ver la ficha completa del cliente.")
    
    search_term_cli = st.text_input("🔍 Buscar Cliente (RUC o Nombre):", key="search_cli")
    
    if search_term_cli:
        try:
            # Consulta directa a gold.dim_cliente
            query_cli = """
            SELECT 
                ruc_cliente, nombre_cliente, tipo_contribuyente,
                direccion, region, provincia, distrito, ubigeo,
                telefono, email, contacto_principal, fecha_creacion_registro
            FROM gold.dim_cliente
            WHERE nombre_cliente LIKE :term OR ruc_cliente LIKE :term
            """
            
            # Usamos engine temporal para consultas directas
            engine = create_engine(f"mssql+pyodbc://{SERVER}/{DATABASE}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes")
            with engine.connect() as conn:
                df_cli = pd.read_sql(text(query_cli), conn, params={"term": f"%{search_term_cli}%"})
                
            if not df_cli.empty:
                st.success(f"Encontramos {len(df_cli)} coincidencia(s).")
                st.dataframe(df_cli, use_container_width=True)
            else:
                st.warning("No se encontraron clientes con ese criterio.")
                
        except Exception as e:
            st.error(f"Error buscando cliente: {e}")

# ------------------------------------------------------------------------------
# PESTAÑA 2: SERVICIOS (Historial de Servicios)
# ------------------------------------------------------------------------------
with tab_servicio:
    st.header("Historial de Servicios Utilizados")
    
    col_search, col_filter = st.columns([2, 1])
    
    with col_search:
        search_term_srv = st.text_input("🔍 Buscar Cliente en Servicios (RUC o Nombre):", key="search_srv")
        
    with col_filter:
        # Cargamos años disponibles para el filtro opcional
        if not df.empty:
            years_avail = sorted(df['anio'].dropna().unique())
            years_opts = ["Todos"] + years_avail
            year_sel = st.selectbox("📅 Filtro de Año (Opcional)", years_opts)
        else:
            year_sel = "Todos"

    if search_term_srv:
        # Filtramos el DataFrame Principal (que ya tiene Joins de Fact + Dims)
        # 1. Filtro por Cliente (Texto)
        mask_client = (
            df['nombre_cliente'].astype(str).str.contains(search_term_srv, case=False, na=False) |
            df['ruc_cliente'].astype(str).str.contains(search_term_srv, case=False, na=False)
        )
        df_srv_filtered = df[mask_client].copy()
        
        # 2. Filtro por Año (si no es 'Todos')
        if year_sel != "Todos":
            df_srv_filtered = df_srv_filtered[df_srv_filtered['anio'] == year_sel]
            
        if not df_srv_filtered.empty:
            # Métricas Resumen
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Servicios", len(df_srv_filtered))
            m1.metric("Total Servicios", f"{df_srv_filtered['cantidad_servicios'].sum():,.0f}")
            m2.metric("Horas Ejecutadas", f"{df_srv_filtered['horas_ejecutadas'].sum():,.0f}")
            m3.metric("Monto Facturado", f"S/ {df_srv_filtered['monto_facturado'].sum():,.2f}")
            
            st.subheader("� Detalle de Servicios")
            
            # Seleccionamos columnas relevantes para la vista de servicios
            cols_srv = [
                'anio', 'mes_nombre', 
                'nombre_comercial',    # Nombre del servicio
                'categoria_servicio', 
                # 'tarea_especifica',  # Si estuviera en el load_data inicial
                'horas_ejecutadas', 
                'monto_facturado',
                'systena_origen' if 'sistema_origen' in df_srv_filtered.columns else 'sistema_origen'
            ]
            # Validamos columnas existentes
            existing_cols = [c for c in cols_srv if c in df_srv_filtered.columns]
            
            st.dataframe(
                df_srv_filtered[existing_cols].sort_values(by=['anio', 'mes_nombre'], ascending=False), 
                use_container_width=True
            )
        else:
            st.info("No se encontraron servicios para este cliente con los filtros seleccionados.")
    else:
        st.info("Ingresa un RUC o Nombre para ver el historial de servicios.")

st.caption(f"Conectado a: {SERVER} | BD: {DATABASE}")
