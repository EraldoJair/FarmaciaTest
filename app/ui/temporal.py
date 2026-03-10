"""
temporal.py – Vista de Análisis Temporal avanzado.

Comparativos interanuales, YTD acumulado, análisis semanal.
Filtros internos independientes de los filtros globales del sidebar.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config import THEME, CURRENCY_FORMAT
from app.transformations import filtrar_datos

from app.ui.sede_tabs import render_with_sede_tabs
import datetime


def _render_local_filters_temporal(df_raw: pd.DataFrame, tab_key: str) -> pd.DataFrame:
    """Renderiza filtros locales para Análisis Temporal y retorna el df filtrado."""
    prefix = f"temporal_{tab_key}_"

    with st.expander("🔍 Filtros de Análisis Temporal", expanded=False):
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


def render_temporal(service, df_completo: pd.DataFrame) -> None:
    """Renderiza la vista de análisis temporal con pestañas por sede."""
    render_with_sede_tabs(df_completo, _render_temporal_content, service)


def _render_temporal_content(service, df: pd.DataFrame, tab_key: str = "default") -> None:
    """Contenido real del análisis temporal."""
    
    st.markdown("### 📅 Análisis Temporal")

    if df.empty:
        st.info("No hay datos disponibles.")
        return

    # ── Filtros locales (independientes del sidebar) ──────────────────
    df = _render_local_filters_temporal(df, tab_key)

    if df.empty:
        st.warning("⚠️ No hay datos para los filtros seleccionados.")
        return

    # Asegurar columnas necesarias
    df = df.copy()
    if "Año" not in df.columns or "Mes" not in df.columns:
        st.warning("Columnas 'Año' y 'Mes' no encontradas.")
        return

    # Asegurar columnas de fecha adicionales
    if "F. VENTA" in df.columns:
        df["DiaNum"] = df["F. VENTA"].dt.day
        df["DiaSemanaNum"] = df["F. VENTA"].dt.weekday
        dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        df["DiaNombre"] = df["F. VENTA"].dt.day_name().map({
            "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
        }).fillna(df["F. VENTA"].dt.day_name())
        
        if "Dia" not in df.columns:
             df["Dia"] = df["DiaNombre"]

    anios_disponibles = sorted(df["Año"].unique())

    # ── Tabs de análisis ───────────────────────────────────────────────
    tab_interanual, tab_ytd, tab_semanal, tab_diario = st.tabs([
        "📊 Comparativo Interanual",
        "📈 YTD Acumulado",
        "📆 Análisis Semanal",
        "📅 Análisis Diario & Heatmap",
    ])

    # ═══════════════════════════════════════════════════════════════════
    # TAB 1: Comparativo Interanual (Mes vs Mes entre Años)
    # ═══════════════════════════════════════════════════════════════════
    with tab_interanual:
        st.markdown("#### 📊 Comparativo Mes a Mes entre Años")
        st.caption("Compara el rendimiento del mismo mes en diferentes años.")

        # Agrupar por Año y Mes
        df_mensual = (
            df.groupby(["Año", "Mes"], as_index=False)
            .agg(
                venta_total=("T. ITEM S/.", "sum"),
                transacciones=("TRANSACCIONES", "sum"),
                cantidad=("CANTIDAD", "sum"),
            )
        )

        meses_nombres = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
            5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
            9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
        }
        df_mensual["Mes_Nombre"] = df_mensual["Mes"].map(meses_nombres)
        df_mensual["Año_str"] = df_mensual["Año"].astype(str)

        # ── Gráfico de líneas: Ventas por mes, una línea por año ──
        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            fig_inter = px.line(
                df_mensual.sort_values(["Año", "Mes"]),
                x="Mes",
                y="venta_total",
                color="Año_str",
                markers=True,
                labels={"venta_total": "Venta (S/)", "Mes": "Mes", "Año_str": "Año"},
                color_discrete_sequence=THEME.chart_colors,
            )
            fig_inter.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=400,
                xaxis=dict(
                    tickmode="array",
                    tickvals=list(range(1, 13)),
                    ticktext=list(meses_nombres.values()),
                    gridcolor="rgba(255,255,255,0.05)",
                ),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Venta (S/)"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.2,
                    xanchor="center", x=0.5,
                ),
                hovermode="x unified",
            )
            st.plotly_chart(fig_inter, width="stretch")

        with col_table:
            # Tabla pivotada: Meses x Años
            pivot = df_mensual.pivot_table(
                index="Mes_Nombre",
                columns="Año_str",
                values="venta_total",
                aggfunc="sum",
            )
            # Reordenar meses
            mes_order = list(meses_nombres.values())
            pivot = pivot.reindex([m for m in mes_order if m in pivot.index])

            # Calcular variación si hay 2+ años
            if len(anios_disponibles) >= 2:
                ultimo = str(anios_disponibles[-1])
                penultimo = str(anios_disponibles[-2])
                if ultimo in pivot.columns and penultimo in pivot.columns:
                    pivot["Var %"] = (
                        (pivot[ultimo] - pivot[penultimo]) / pivot[penultimo] * 100
                    ).round(1)

            # Formatear
            format_dict = {str(a): "S/ {:,.0f}" for a in anios_disponibles}
            if "Var %" in pivot.columns:
                format_dict["Var %"] = "{:+.1f}%"

            st.dataframe(
                pivot.style.format(format_dict, na_rep="—").background_gradient(
                    cmap="RdYlGn",
                    subset=["Var %"] if "Var %" in pivot.columns else [],
                ),
                width="stretch",
                height=400,
            )

        st.divider()

        # ── Barras agrupadas por mes ──
        st.markdown("#### 📊 Comparativo en Barras")
        fig_bar_inter = px.bar(
            df_mensual.sort_values(["Mes", "Año"]),
            x="Mes_Nombre",
            y="venta_total",
            color="Año_str",
            barmode="group",
            text=df_mensual.sort_values(["Mes", "Año"])["venta_total"].apply(
                lambda v: f"S/ {v:,.0f}"
            ),
            labels={"venta_total": "Venta (S/)", "Mes_Nombre": "", "Año_str": "Año"},
            color_discrete_sequence=THEME.chart_colors,
            category_orders={"Mes_Nombre": list(meses_nombres.values())},
        )
        fig_bar_inter.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=380,
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=""),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.2,
                xanchor="center", x=0.5,
            ),
        )
        fig_bar_inter.update_traces(textposition="outside", textfont_size=9)
        st.plotly_chart(fig_bar_inter, width="stretch")

    # ═══════════════════════════════════════════════════════════════════
    # TAB 2: YTD Acumulado
    # ═══════════════════════════════════════════════════════════════════
    with tab_ytd:
        st.markdown("#### 📈 Year-to-Date (YTD) Acumulado")
        st.caption("Venta acumulada en el año: ¿vamos mejor o peor que el año pasado?")

        # Agrupar por Año y día del año
        df_ytd = df.copy()
        df_ytd["DiaDelAnio"] = df_ytd["F. VENTA"].dt.dayofyear

        ytd_diario = (
            df_ytd.groupby(["Año", "DiaDelAnio"], as_index=False)
            .agg(venta_total=("T. ITEM S/.", "sum"))
            .sort_values(["Año", "DiaDelAnio"])
        )

        # Acumulado por año
        ytd_diario["venta_acumulada"] = (
            ytd_diario.groupby("Año")["venta_total"].cumsum()
        )
        ytd_diario["Año_str"] = ytd_diario["Año"].astype(str)

        fig_ytd = px.line(
            ytd_diario,
            x="DiaDelAnio",
            y="venta_acumulada",
            color="Año_str",
            labels={
                "venta_acumulada": "Venta Acumulada (S/)",
                "DiaDelAnio": "Día del Año",
                "Año_str": "Año",
            },
            color_discrete_sequence=THEME.chart_colors,
        )
        fig_ytd.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=420,
            xaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                title="Día del Año",
                tickmode="array",
                tickvals=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
                ticktext=["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                          "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"],
            ),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Acumulado (S/)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.15,
                xanchor="center", x=0.5,
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig_ytd, width="stretch")

        # ── Resumen YTD por año ──
        st.markdown("#### 📋 Resumen YTD por Año")
        resumen_ytd = (
            ytd_diario.groupby("Año_str", as_index=False)
            .agg(
                venta_total=("venta_total", "sum"),
                dias=("DiaDelAnio", "nunique"),
                max_dia=("DiaDelAnio", "max"),
            )
        )
        resumen_ytd["venta_diaria_prom"] = resumen_ytd["venta_total"] / resumen_ytd["dias"]
        resumen_ytd.columns = ["Año", "Venta Total", "Días con Venta", "Último Día", "Venta Diaria Prom."]

        st.dataframe(
            resumen_ytd.style.format({
                "Venta Total": "S/ {:,.2f}",
                "Días con Venta": "{:,.0f}",
                "Último Día": "{:.0f}",
                "Venta Diaria Prom.": "S/ {:,.2f}",
            }),
            width="stretch",
            hide_index=True,
        )

    # ═══════════════════════════════════════════════════════════════════
    # TAB 3: Análisis Semanal
    # ═══════════════════════════════════════════════════════════════════
    with tab_semanal:
        st.markdown("#### 📆 Comparativo Semanal entre Años")
        st.caption("Ventas agrupadas por número de semana, comparando entre años.")

        df_sem = (
            df.groupby(["Año", "Semana"], as_index=False)
            .agg(venta_total=("T. ITEM S/.", "sum"))
            .sort_values(["Año", "Semana"])
        )
        df_sem["Año_str"] = df_sem["Año"].astype(str)

        fig_sem = px.line(
            df_sem,
            x="Semana",
            y="venta_total",
            color="Año_str",
            markers=False,
            labels={"venta_total": "Venta (S/)", "Semana": "Semana #", "Año_str": "Año"},
            color_discrete_sequence=THEME.chart_colors,
        )
        fig_sem.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=400,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", dtick=4),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Venta (S/)"),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.15,
                xanchor="center", x=0.5,
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig_sem, width="stretch")

        # ── Tabla semanal pivotada ──
        pivot_sem = df_sem.pivot_table(
            index="Semana",
            columns="Año_str",
            values="venta_total",
            aggfunc="sum",
        )

        if len(anios_disponibles) >= 2:
            ultimo = str(anios_disponibles[-1])
            penultimo = str(anios_disponibles[-2])
            if ultimo in pivot_sem.columns and penultimo in pivot_sem.columns:
                pivot_sem["Var %"] = (
                    (pivot_sem[ultimo] - pivot_sem[penultimo]) / pivot_sem[penultimo] * 100
                ).round(1)

        format_dict_sem = {str(a): "S/ {:,.0f}" for a in anios_disponibles}
        if "Var %" in pivot_sem.columns:
            format_dict_sem["Var %"] = "{:+.1f}%"

        st.dataframe(
            pivot_sem.style.format(format_dict_sem, na_rep="—").background_gradient(
                cmap="RdYlGn",
                subset=["Var %"] if "Var %" in pivot_sem.columns else [],
            ),
            width="stretch",
            height=400,
        )

    # ═══════════════════════════════════════════════════════════════════
    # TAB 4: Análisis Diario & Heatmap
    # ═══════════════════════════════════════════════════════════════════
    with tab_diario:
        st.markdown("#### 🔥 Mapa de Calor: Día vs Mes")
        
        # Agrupar por Mes y Día de la Semana
        # Aseguramos que tenemos Mes_Nombre y Dia
        df_hm = df.copy()
        
        # Mapa de días y meses ordenados
        dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses_orden = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        df_hm["DiaNombre"] = pd.Categorical(df_hm["DiaNombre"], categories=dias_orden, ordered=True)
        # Si Mes_Nombre no existe, crearlo
        if "Mes_Nombre" not in df_hm.columns:
             mapa_meses = {i: m for i, m in enumerate(meses_orden, 1)}
             df_hm["Mes_Nombre"] = df_hm["Mes"].map(mapa_meses)
             
        df_hm["Mes_Nombre"] = pd.Categorical(df_hm["Mes_Nombre"], categories=meses_orden, ordered=True)
        
        hm_data = (
            df_hm.groupby(["Mes_Nombre", "DiaNombre"], as_index=False, observed=True)
            .agg(venta_promedio=("T. ITEM S/.", "mean")) # Promedio para normalizar por número de ocurrencias
        )
        
        if not hm_data.empty:
            fig_hm = px.density_heatmap(
                hm_data,
                x="Mes_Nombre",
                y="DiaNombre",
                z="venta_promedio",
                histfunc="sum",
                color_continuous_scale="Viridis",
                labels={"venta_promedio": "Venta Promedio", "Mes_Nombre": "Mes", "DiaNombre": "Día"},
                title="Intensidad de Ventas Promedio (Día vs Mes)"
            )
            fig_hm.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                height=400,
                xaxis=dict(title=""),
                yaxis=dict(title=""),
            )
            st.plotly_chart(fig_hm, width="stretch")
            
        st.divider()
        
        # ── Comparativa Diaria Mes Actual ──
        current_month = datetime.date.today().month
        current_month_name = months_map = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                                           7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}[current_month]
        
        st.markdown(f"#### 🗓️ Comparativa Diaria: {current_month_name} (Histórico)")
        st.caption(f"Comparación del rendimiento diario para el mes de {current_month_name} en diferentes años.")
        
        df_diario_mes = df[df["Mes"] == current_month].copy()
        
        if df_diario_mes.empty:
             st.info(f"No hay datos para el mes de {current_month_name}.")
        else:
             df_diario_mes["Año_str"] = df_diario_mes["Año"].astype(str)
             # Agrupar por dia del mes (1-31)
             daily_comp = (
                 df_diario_mes.groupby(["Año_str", "DiaNum"], as_index=False)
                 .agg(venta_total=("T. ITEM S/.", "sum"))
                 .sort_values("DiaNum")
             )
             
             fig_daily = px.line(
                 daily_comp,
                 x="DiaNum",
                 y="venta_total",
                 color="Año_str",
                 markers=True,
                 labels={"venta_total": "Venta (S/)", "DiaNum": f"Día de {current_month_name}", "Año_str": "Año"},
                 color_discrete_sequence=THEME.chart_colors
             )
             
             fig_daily.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                height=400,
                xaxis=dict(
                    gridcolor="rgba(255,255,255,0.05)",
                    tickmode="linear",
                    dtick=1
                ),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Venta (S/)"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1
                ),
                hovermode="x unified",
            )
             st.plotly_chart(fig_daily, width="stretch")
             
        # ── Comparativa Facetada por Día Semana ──
        st.divider()
        st.markdown(f"#### 📌 Comparativa por Día de Semana: {current_month_name}")
        st.caption("Comparación alineada por ocurrencia del día (ej. 1er Lunes, 2do Lunes...)")
        
        if df_diario_mes.empty:
            # Orden del día en el mes (ej: 1er lunes, 2do lunes)
            df_diario_mes = df_diario_mes.sort_values("F. VENTA")
            df_diario_mes["OrdenDia"] = (
                df_diario_mes.groupby(["Año", "Mes", "DiaNombre"]).cumcount() + 1
            )
            
            # Agrupar para el gráfico
            facet_data = (
                df_diario_mes.groupby(["Año_str", "DiaNombre", "OrdenDia"], as_index=False)
                .agg(venta_total=("T. ITEM S/.", "sum"))
            )
            
            # Orden de facetas
            facet_data["DiaNombre"] = pd.Categorical(facet_data["DiaNombre"], categories=dias_orden, ordered=True)
            facet_data = facet_data.sort_values(["DiaNombre", "OrdenDia"])
            
            fig_facet = px.line(
                facet_data,
                x="OrdenDia",
                y="venta_total",
                color="Año_str",
                facet_col="DiaNombre",
                facet_col_wrap=4,
                markers=True,
                color_discrete_sequence=THEME.chart_colors,
                category_orders={"DiaNombre": dias_orden}
            )
            
            fig_facet.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                height=600,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1
                ),
            )
            fig_facet.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
            st.plotly_chart(fig_facet, width="stretch")
