"""
crecimiento.py – Vista de Crecimiento y Proyecciones.
Incorpora lógica de proyección y comparación Real vs Meta vs Año Anterior.
Filtros internos independientes de los filtros globales del sidebar.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import datetime

from app.config import THEME, CURRENCY_FORMAT, NUMBER_FORMAT
from app.transformations import filtrar_datos
from app.ui.sede_tabs import render_with_sede_tabs


def _render_local_filters_crec(df_raw: pd.DataFrame, tab_key: str) -> pd.DataFrame:
    """Renderiza filtros locales para Crecimiento y retorna el df filtrado."""
    prefix = f"crec_{tab_key}_"

    with st.expander("🔍 Filtros de Crecimiento y Proyecciones", expanded=False):
        fc1, fc2, fc3 = st.columns([2, 2, 2])

        with fc1:
            farmacias_disp = sorted(df_raw["Unidad"].unique())
            farmacias = st.multiselect(
                "📍 Farmacias",
                options=farmacias_disp,
                default=farmacias_disp,
                key=f"{prefix}farmacias",
            )

        with fc2:
            lineas_disp = sorted(df_raw["LINEA DE NEGOCIO"].unique())
            lineas = st.multiselect(
                "🏷️ Línea de Negocio",
                options=lineas_disp,
                default=[],
                key=f"{prefix}lineas",
            )

        with fc3:
            cats_src = df_raw[df_raw["LINEA DE NEGOCIO"].isin(lineas)] if lineas else df_raw
            cats_disp = sorted(cats_src["CATEGORIA 1"].unique())
            categorias = st.multiselect(
                "📂 Categoría",
                options=cats_disp,
                default=[],
                key=f"{prefix}categorias",
            )

        # Fila de fechas
        fd1, fd2, fd3 = st.columns([2, 2, 2])

        fecha_min = df_raw["F. VENTA"].min().date()
        fecha_max = df_raw["F. VENTA"].max().date()
        hoy = datetime.date.today()

        with fd1:
            periodo = st.selectbox(
                "⚡ Periodo",
                ["🌐 Todos", "📅 Hoy", "📆 Esta Semana", "🗓️ Este Mes",
                 "📊 Último Trimestre", "🗃️ Este Año", "📋 Personalizado"],
                index=0,
                key=f"{prefix}periodo",
            )

        # Calcular fechas
        if "Hoy" in periodo:
            d_ini, d_fin = hoy, hoy
        elif "Esta Semana" in periodo:
            d_ini = hoy - datetime.timedelta(days=hoy.weekday())
            d_fin = hoy
        elif "Este Mes" in periodo:
            d_ini = hoy.replace(day=1)
            d_fin = hoy
        elif "Último Trimestre" in periodo:
            d_ini = hoy - datetime.timedelta(days=90)
            d_fin = hoy
        elif "Este Año" in periodo:
            d_ini = hoy.replace(month=1, day=1)
            d_fin = hoy
        elif "Personalizado" in periodo:
            d_ini, d_fin = fecha_min, fecha_max
        else:  # Todos
            d_ini, d_fin = fecha_min, fecha_max

        d_ini = max(fecha_min, min(d_ini, fecha_max))
        d_fin = max(fecha_min, min(d_fin, fecha_max))

        with fd2:
            fecha_inicio = st.date_input(
                "Desde", value=d_ini,
                min_value=fecha_min, max_value=fecha_max,
                disabled=("Personalizado" not in periodo),
                key=f"{prefix}fecha_ini",
            )
        with fd3:
            fecha_fin = st.date_input(
                "Hasta", value=d_fin,
                min_value=fecha_min, max_value=fecha_max,
                disabled=("Personalizado" not in periodo),
                key=f"{prefix}fecha_fin",
            )

    # Aplicar filtros localmente
    df_filtrado = filtrar_datos(
        df_raw,
        farmacias=farmacias,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        lineas_negocio=lineas,
        categorias=categorias,
    )
    return df_filtrado


def render_crecimiento(service, df_completo: pd.DataFrame) -> None:
    """Renderiza la vista de Crecimiento y Proyecciones con pestañas por sede."""
    render_with_sede_tabs(df_completo, _render_crecimiento_content, service)


def _render_crecimiento_content(service, df: pd.DataFrame, tab_key: str = "default") -> None:
    """Contenido interno de la vista de crecimiento."""
    st.markdown("### 📈 Crecimiento y Proyecciones")

    if df.empty:
        st.info("No hay datos disponibles.")
        return

    # ── Filtros locales (independientes del sidebar) ──────────────────
    df = _render_local_filters_crec(df, tab_key)

    if df.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        return

    # Asegurar columnas
    df = df.copy()
    if "Año" not in df.columns:
        st.warning("Falta columna 'Año' en los datos.")
        return

    anios = sorted(df["Año"].unique())
    anio_actual = datetime.date.today().year
    
    # Si el año actual no está en los datos, usar el máximo disponible
    if anio_actual not in anios:
        anio_actual = max(anios) if anios else anio_actual
    
    anio_previo = anio_actual - 1

    # ── KPIs Globales de Crecimiento ─────────────────────────────────
    # Calcular totales por año
    ventas_por_anio = df.groupby("Año")["T. ITEM S/."].sum()
    
    venta_actual = ventas_por_anio.get(anio_actual, 0.0)
    venta_previo = ventas_por_anio.get(anio_previo, 0.0)
    
    crecimiento_abs = venta_actual - venta_previo
    crecimiento_pct = (crecimiento_abs / venta_previo * 100) if venta_previo != 0 else 0.0

    # Proyección simple (regla de tres según avance del año)
    # Suponemos proyección lineal simple para demo
    mes_actual = datetime.date.today().month
    # Si estamos viendo histórico (ej 2023 completo), proyección es igual a real
    # Si es año en curso, proyectamos
    es_anio_curso = (anio_actual == datetime.date.today().year)
    factor_proyeccion = 1.0
    if es_anio_curso:
        # Aprox por mes concluido (ej. estamos en marzo, factor = 12/2 si feb terminó?)
        # Usamos día del año para más precisión
        dia_anio = datetime.date.today().timetuple().tm_yday
        if dia_anio > 0:
            factor_proyeccion = 365 / dia_anio
    
    proyeccion_cierre = venta_actual * factor_proyeccion if es_anio_curso else venta_actual

    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            f"Venta {anio_actual} (YTD)",
            CURRENCY_FORMAT.format(venta_actual),
            delta=f"{crecimiento_pct:+.1f}% vs {anio_previo}"
        )
    with col2:
        st.metric(
            f"Venta {anio_previo} (Total)",
            CURRENCY_FORMAT.format(venta_previo),
            help="Venta total del año anterior completo (si existe)"
        )
    with col3:
        st.metric(
            "Crecimiento Absoluto",
            CURRENCY_FORMAT.format(crecimiento_abs),
            delta_color="normal"
        )
    with col4:
        st.metric(
            f"Proyección Cierre {anio_actual}",
            CURRENCY_FORMAT.format(proyeccion_cierre),
            delta=f"{(proyeccion_cierre - venta_previo)/venta_previo*100:+.1f}% vs {anio_previo}" if venta_previo > 0 else None,
            help="Proyección lineal basada en el avance del año actual."
        )

    st.divider()

    # ── Gráfico: Evolución Mensual Comparativa (Real vs Meta vs Año Anterior) ──
    st.markdown(f"#### 📊 Evolución Mensual: {anio_actual} vs {anio_previo}")
    
    # Datos mensuales
    mensual = (
        df.groupby(["Año", "Mes"], as_index=False)
        .agg(venta=("T. ITEM S/.", "sum"))
    )
    
    # Pivotar para gráfico
    pivot = mensual.pivot(index="Mes", columns="Año", values="venta").fillna(0)
    
    # Traer Metas
    # Necesitamos metas del año actual agrupadas por mes
    # Metas están en service.metas_df o service.cargar_metas (que devuelve o guarda en self.metas_df/json)
    # Sin embargo AnalyticsService ya tiene metas cargadas
    metas_df = getattr(service, "metas_df", pd.DataFrame())
    
    metas_mes = pd.Series(0.0, index=range(1, 13))
    if not metas_df.empty:
        # Filtrar metas para año actual y unidades del filtro actual
        unidades_filtro = df["Unidad"].unique()
        mask_meta = (
            (metas_df["Anio"] == anio_actual) & 
            (metas_df["Unidad"].isin(unidades_filtro))
        )
        metas_filtradas = metas_df[mask_meta]
        if not metas_filtradas.empty:
            metas_mes = metas_filtradas.groupby("Mes")["Meta"].sum()
    
    # Construir DF para gráfico
    # Ejes X: 1..12
    meses_nombres = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    fig = go.Figure()
    
    # Barra Año Anterior
    if anio_previo in pivot.columns:
        fig.add_trace(go.Bar(
            x=[meses_nombres[m] for m in pivot.index],
            y=pivot[anio_previo],
            name=f"Venta {anio_previo}",
            marker_color="rgba(255, 255, 255, 0.3)",
        ))
        
    # Barra Año Actual
    if anio_actual in pivot.columns:
        fig.add_trace(go.Bar(
            x=[meses_nombres[m] for m in pivot.index],
            y=pivot[anio_actual],
            name=f"Venta {anio_actual}",
            marker_color=THEME.secondary,
            text=[CURRENCY_FORMAT.format(v) for v in pivot[anio_actual]],
            textposition="auto",
        ))
        
    # Línea Meta
    # Asegurar que metas_mes tenga valores para los meses en el gráfico
    y_meta = [metas_mes.get(m, 0) for m in pivot.index]
    # Si todos son 0, no mostrar línea meta
    if sum(y_meta) > 0:
        fig.add_trace(go.Scatter(
            x=[meses_nombres[m] for m in pivot.index],
            y=y_meta,
            name=f"Meta {anio_actual}",
            mode="lines+markers",
            line=dict(color=THEME.warning, width=3, dash="dash"),
        ))

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color=THEME.text_secondary,
        margin=dict(l=20, r=20, t=10, b=20),
        height=450,
        legend=dict(orientation="h", y=1.1),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Soles (S/)"),
    )
    st.plotly_chart(fig, width="stretch")

    st.divider()

    # ── Análisis de Brecha por Sede (Waterfall o Barras) ────────────────
    st.markdown("#### 🎯 Cumplimiento y Brecha por Sede (Año Actual)")
    
    # Cumplimiento acumulado año actual
    # Reutilizamos la lógica de kpis pero limitamos al año actual
    df_actual = df[df["Año"] == anio_actual]
    
    # Metas año actual
    df_metas_actual = pd.DataFrame()
    if not metas_df.empty:
        df_metas_actual = metas_df[metas_df["Anio"] == anio_actual].copy()
    
    # Calcular cumplimiento usando el servicio helper
    # Pero el helper de kpis.calcular_cumplimiento usa merge por año/mes
    # Así que si pasamos df_actual (solo 202X) y df_metas_actual, funcionará
    cumplimiento = service.calcular_cumplimiento(df_actual, df_metas_actual)
    
    if not cumplimiento.empty:
        col_brecha_chart, col_brecha_data = st.columns([3, 2])
        
        with col_brecha_chart:
            # Gráfico de barras: Venta vs Meta
            fig_brecha = go.Figure()
            
            fig_brecha.add_trace(go.Bar(
                x=cumplimiento["Unidad"],
                y=cumplimiento["venta_total"],
                name="Venta Real",
                marker_color=THEME.secondary
            ))
            
            fig_brecha.add_trace(go.Bar(
                x=cumplimiento["Unidad"],
                y=cumplimiento["meta"],
                name="Meta",
                marker_color="rgba(255,255,255,0.1)",
                marker_line_width=1,
                marker_line_color="white"
            ))
            
            fig_brecha.update_layout(
                barmode="group",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                height=400,
                legend=dict(orientation="h", y=1.1),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            )
            st.plotly_chart(fig_brecha, width="stretch")
            
        with col_brecha_data:
            st.dataframe(
                cumplimiento[["Unidad", "venta_total", "meta", "cumplimiento_pct", "brecha"]]
                .sort_values("cumplimiento_pct", ascending=False)
                .style.format({
                    "venta_total": "S/ {:,.2f}",
                    "meta": "S/ {:,.2f}",
                    "cumplimiento_pct": "{:.1f}%",
                    "brecha": "S/ {:,.2f}"
                })
                .background_gradient(cmap="RdYlGn", subset=["cumplimiento_pct"], vmin=50, vmax=110),
                width="stretch",
                height=400
            )

