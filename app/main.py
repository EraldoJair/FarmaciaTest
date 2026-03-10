
"""
main.py – Punto de entrada de la aplicación Streamlit.

Farmacia Analytics: Dashboard Ejecutivo Multi-Sede.
Refactorizado para limpieza y delegación de lógica.
"""
from __future__ import annotations

import sys
import datetime
from pathlib import Path

# Asegurar que el directorio raíz esté en el path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# ── Configuración de página (DEBE ser lo primero) ────────────────────
st.set_page_config(
    page_title="Farmacia Analytics | Dashboard Ejecutivo",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.services import get_service
from app.transformations import filtrar_datos
from app.ui.dashboard import render_dashboard
from app.ui.comparativo import render_comparativo
from app.ui.metas import render_metas
from app.ui.temporal import render_temporal
from app.ui.crecimiento import render_crecimiento
from app.config import THEME, CURRENCY_FORMAT


# ── CSS Personalizado (Tema Oscuro Empresarial) ──────────────────────
# TO-DO: Mover a archivo .css independiente en futuro refactor
def inject_custom_css():
    st.markdown(f"""
    <style>
        /* ─── Fondo general ───────────────────────── */
        .stApp {{
            background: linear-gradient(135deg, {THEME.bg_dark} 0%, #0D2137 50%, {THEME.bg_dark} 100%);
        }}

        /* ─── Sidebar ─────────────────────────────── */
        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, #0D2137 0%, {THEME.bg_card} 100%);
            border-right: 1px solid rgba(0, 191, 165, 0.2);
        }}
        section[data-testid="stSidebar"] .stMarkdown h1,
        section[data-testid="stSidebar"] .stMarkdown h2,
        section[data-testid="stSidebar"] .stMarkdown h3 {{
            color: {THEME.accent} !important;
        }}

        /* ─── Métricas / KPI Cards ────────────────── */
        div[data-testid="stMetric"] {{
            background: linear-gradient(135deg, {THEME.bg_card} 0%, #1A3A5C 100%);
            border: 1px solid rgba(0, 191, 165, 0.15);
            border-radius: 12px;
            padding: 16px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 191, 165, 0.15);
        }}
        div[data-testid="stMetric"] label {{
            color: {THEME.text_secondary} !important;
            font-size: 0.8rem !important;
            font-weight: 500 !important;
            letter-spacing: 0.5px;
        }}
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            color: {THEME.text_primary} !important;
            font-size: 1.4rem !important;
            font-weight: 700 !important;
        }}

        /* ─── Headers ─────────────────────────────── */
        .stMarkdown h1 {{ color: {THEME.text_primary} !important; }}
        .stMarkdown h2 {{ color: #E0F7FA !important; }}
        .stMarkdown h3 {{ color: #B2EBF2 !important; }}
        .stMarkdown h4 {{ color: #80DEEA !important; }}

        /* ─── Buttons ─────────────────────────────── */
        .stButton > button {{
            background: linear-gradient(135deg, {THEME.accent} 0%, {THEME.secondary} 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }}
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────
def render_sidebar(service) -> dict:
    """Renderiza el sidebar con navegación y filtros globales."""

    with st.sidebar:
        # Branding
        st.markdown("""
        <div style="text-align:center; padding: 10px 0 20px 0;">
            <span style="font-size:2.5rem;">💊</span>
            <h2 style="margin:0; color:#00BFA5; font-size:1.3rem;">
                Farmacia Analytics
            </h2>
            <p style="color:#78909C; font-size:0.75rem; margin-top:4px;">
                Dashboard Ejecutivo Multi-Sede
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()

        # Navegación
        st.markdown("##### 🧭 Navegación")
        pagina = st.radio(
            "Seleccione vista:",
            ["📊 Dashboard Ejecutivo", "🔄 Comparativo Multi-Sede",
             "📅 Análisis Temporal", "📈 Crecimiento y Proyecciones", "🎯 Gestión de Metas"],
            label_visibility="collapsed",
        )
        st.divider()

        # Filtros
        st.markdown("##### 🔍 Filtros")
        df = service.datos # Carga lazy si no esta cargado

        # Filtro Farmacias
        farmacias_disponibles = sorted(df["Unidad"].unique())
        farmacias = st.multiselect(
            "📍 Farmacias",
            options=farmacias_disponibles,
            default=farmacias_disponibles,
        )

        # Filtro Fechas
        st.markdown("###### ⚡ Periodo")
        fecha_min_data = df["F. VENTA"].min().date()
        fecha_max_data = df["F. VENTA"].max().date()
        hoy = datetime.date.today()
        
        # Opciones predefinidas
        periodo_rapido = st.selectbox(
            "Rango Rápido",
             ["🌐 Todos", "📅 Hoy", "📆 Esta Semana", "🗓️ Este Mes", "📊 Último Trimestre", "🗃️ Este Año", "📋 Personalizado"],
             index=0
        )
        
        # Lógica de fechas (usar 'in' porque las opciones tienen emoji)
        if "Hoy" in periodo_rapido:
            d_ini, d_fin = hoy, hoy
        elif "Esta Semana" in periodo_rapido:
            d_ini = hoy - datetime.timedelta(days=hoy.weekday())
            d_fin = hoy
        elif "Este Mes" in periodo_rapido:
            d_ini = hoy.replace(day=1)
            d_fin = hoy
        elif "Último Trimestre" in periodo_rapido:
            d_ini = hoy - datetime.timedelta(days=90)
            d_fin = hoy
        elif "Este Año" in periodo_rapido:
            d_ini = hoy.replace(month=1, day=1)
            d_fin = hoy
        elif "Personalizado" in periodo_rapido:
             d_ini, d_fin = fecha_min_data, fecha_max_data
        else:  # Todos
             d_ini, d_fin = fecha_min_data, fecha_max_data
             
        # Clamp dates
        d_ini = max(fecha_min_data, min(d_ini, fecha_max_data))
        d_fin = max(fecha_min_data, min(d_fin, fecha_max_data))

        es_personalizado = "Personalizado" in periodo_rapido
        c1, c2 = st.columns(2)
        with c1:
            fecha_inicio = st.date_input("Desde", value=d_ini, min_value=fecha_min_data, max_value=fecha_max_data, disabled=(not es_personalizado))
        with c2:
            fecha_fin = st.date_input("Hasta", value=d_fin, min_value=fecha_min_data, max_value=fecha_max_data, disabled=(not es_personalizado))

        # Filtros Categoricos
        lineas = st.multiselect("🏷️ Línea de Negocio", sorted(df["LINEA DE NEGOCIO"].unique()), default=[])
        
        cats_dispo = sorted(df[df["LINEA DE NEGOCIO"].isin(lineas)]["CATEGORIA 1"].unique()) if lineas else sorted(df["CATEGORIA 1"].unique())
        categorias = st.multiselect("📂 Categoría", cats_dispo, default=[])

        vendedores = st.multiselect("👤 Vendedores", sorted(df["VENDEDOR"].unique()), default=[])
        
        st.divider()
        
        # Upload
        uploaded = st.file_uploader("📂 Cargar Nuevo CSV/Excel", type=["csv", "xlsx"])
        if uploaded:
            try:
                from app.data_loader import cargar_datos_upload
                df_new = cargar_datos_upload(uploaded)
                # Hacky: inyectar en servicio. Idealmente metodo service.actualizar_datos(df)
                service._df_raw = df_new
                service._df = None # Forzar recalculo
                st.success("Datos actualizados!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    return {
        "pagina": pagina,
        "farmacias": farmacias,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "lineas_negocio": lineas,
        "categorias": categorias,
        "vendedores": vendedores,
    }


# ── Main Application ────────────────────────────────────────────────
def main():
    inject_custom_css()
    
    # Obtener servicio (Singleton)
    service = get_service()

    # Cargar datos con manejo de error UI
    try:
        # service.datos # Trigger carga esto crea la tabla donde se muestran los datos
        print("Datos cargados correctamente")
    except Exception as e:
        st.error(f"❌ Error crítico: No se pudieron cargar los datos. {e}")
        st.stop()

    # Render Sidebar
    filtros = render_sidebar(service)

    # Filtrar Datos (Vectorizado)
    df_filtrado = filtrar_datos(
        service.datos,
        farmacias=filtros["farmacias"],
        fecha_inicio=filtros["fecha_inicio"],
        fecha_fin=filtros["fecha_fin"],
        lineas_negocio=filtros["lineas_negocio"],
        categorias=filtros["categorias"],
        vendedores=filtros["vendedores"],
    )

    if df_filtrado.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        st.stop()
        
    # Header Resumen
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:10px;">
        <span style="font-size:1.8rem;">💊</span>
        <div>
            <h1 style="margin:0; font-size:1.6rem; color:#FFFFFF;">Farmacia Analytics</h1>
            <p style="margin:0; color:#78909C; font-size:0.8rem;">
                {len(df_filtrado):,} registros · {df_filtrado['Unidad'].nunique()} sedes · {filtros['fecha_inicio']} a {filtros['fecha_fin']}
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Router
    pagina = filtros["pagina"]
    
    if "Dashboard" in pagina:
        render_dashboard(service, df_filtrado)
    elif "Comparativo" in pagina:
        render_comparativo(service, df_filtrado)
    elif "Temporal" in pagina:
        render_temporal(service, service.datos)
    elif "Crecimiento" in pagina:
         render_crecimiento(service, service.datos)
    elif "Metas" in pagina:
        render_metas(service, df_filtrado)


if __name__ == "__main__":
    main()
