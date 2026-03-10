"""
comparativo.py – Vista de comparativo multi-sede.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config import THEME, CURRENCY_FORMAT, PERCENT_FORMAT


def render_comparativo(service, df_filtrado: pd.DataFrame) -> None:
    """Renderiza la vista de comparativo entre farmacias."""

    st.markdown("### 🔄 Comparativo Multi-Sede")

    # ── Tabla Comparativa ────────────────────────────────────────────
    comp = service.comparativo(df_filtrado)

    if comp.empty:
        st.info("No hay datos para mostrar con los filtros seleccionados.")
        return

    # Tabla formateada
    st.markdown("#### 📋 Resumen Comparativo")

    tabla = comp[
        ["ranking", "semaforo", "Unidad", "venta_total", "meta",
         "cumplimiento_pct", "brecha", "transacciones",
         "ticket_promedio", "venta_diaria", "dias_venta"]
    ].copy()

    tabla.columns = [
        "#", "Estado", "Farmacia", "Venta Total (S/)", "Meta (S/)",
        "Cumplimiento %", "Brecha (S/)", "Transacciones",
        "Ticket Prom. (S/)", "Venta Diaria (S/)", "Días"
    ]

    st.dataframe(
        tabla.style.format({
            "Venta Total (S/)": "S/ {:,.2f}",
            "Meta (S/)": "S/ {:,.2f}",
            "Cumplimiento %": "{:.1f}%",
            "Brecha (S/)": "S/ {:,.2f}",
            "Transacciones": "{:,.0f}",
            "Ticket Prom. (S/)": "S/ {:,.2f}",
            "Venta Diaria (S/)": "S/ {:,.2f}",
        }).background_gradient(
            cmap="RdYlGn",
            subset=["Cumplimiento %"],
        ),
        width="stretch",
        hide_index=True,
        height=300,
    )

    st.divider()

    # ── Fila 1: Barras agrupadas + Radar ─────────────────────────────
    col_bar, col_radar = st.columns(2)

    with col_bar:
        st.markdown("#### 📊 Venta vs Meta por Farmacia")

        fig_bar = go.Figure()

        fig_bar.add_trace(go.Bar(
            name="Venta Real",
            x=comp["Unidad"],
            y=comp["venta_total"],
            marker_color=THEME.accent,
            text=comp["venta_total"].apply(lambda v: f"S/ {v:,.0f}"),
            textposition="outside",
        ))

        fig_bar.add_trace(go.Bar(
            name="Meta",
            x=comp["Unidad"],
            y=comp["meta"],
            marker_color="rgba(255,255,255,0.2)",
            text=comp["meta"].apply(lambda v: f"S/ {v:,.0f}"),
            textposition="outside",
        ))

        fig_bar.update_layout(
            barmode="group",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=400,
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.2,
                xanchor="center", x=0.5,
            ),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=""),
            xaxis=dict(title=""),
        )
        st.plotly_chart(fig_bar, width="stretch")

    with col_radar:
        st.markdown("#### 🕸️ Radar de Rendimiento")

        # Normalizar métricas a 0-100 para radar
        metrics = ["venta_total", "transacciones", "ticket_promedio", "venta_diaria", "cumplimiento_pct"]
        labels = ["Venta Total", "Transacciones", "Ticket Prom.", "Venta Diaria", "Cumplimiento %"]

        fig_radar = go.Figure()

        for i, row in comp.iterrows():
            values_normalized = []
            for m in metrics:
                max_val = comp[m].max()
                values_normalized.append(
                    (row[m] / max_val * 100) if max_val > 0 else 0
                )
            values_normalized.append(values_normalized[0])  # Cerrar el radar

            fig_radar.add_trace(go.Scatterpolar(
                r=values_normalized,
                theta=labels + [labels[0]],
                name=row["Unidad"],
                fill="toself",
                opacity=0.6,
            ))

        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    visible=True,
                    range=[0, 110],
                    gridcolor="rgba(255,255,255,0.1)",
                ),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=40, r=40, t=20, b=40),
            height=400,
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.3,
                xanchor="center", x=0.5, font=dict(size=10),
            ),
            colorway=THEME.chart_colors,
        )
        st.plotly_chart(fig_radar, width="stretch")

    st.divider()

    # ── Fila 2: Cumplimiento visual + Tendencia ──────────────────────
    col_cumpl, col_trend = st.columns(2)

    with col_cumpl:
        st.markdown("#### 🎯 Cumplimiento por Farmacia")

        fig_cumpl = go.Figure()

        for _, row in comp.iterrows():
            color = (
                THEME.success if row["cumplimiento_pct"] >= 90
                else THEME.warning if row["cumplimiento_pct"] >= 70
                else THEME.danger
            )
            fig_cumpl.add_trace(go.Bar(
                x=[row["cumplimiento_pct"]],
                y=[row["Unidad"]],
                orientation="h",
                marker_color=color,
                text=[f"{row['cumplimiento_pct']:.1f}% {row['semaforo']}"],
                textposition="auto",
                showlegend=False,
            ))

        # Líneas de referencia
        fig_cumpl.add_vline(x=100, line_dash="dash", line_color="white", opacity=0.5)
        fig_cumpl.add_vline(x=90, line_dash="dot", line_color=THEME.success, opacity=0.3)
        fig_cumpl.add_vline(x=70, line_dash="dot", line_color=THEME.warning, opacity=0.3)

        fig_cumpl.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=350,
            xaxis=dict(title="% Cumplimiento", gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(title=""),
        )
        st.plotly_chart(fig_cumpl, width="stretch")

    with col_trend:
        st.markdown("#### 📈 Tendencia Mensual por Farmacia")
        df_crec = service.crecimiento(df_filtrado)

        if not df_crec.empty:
            fig_trend = px.line(
                df_crec,
                x="Anio_Mes",
                y="venta_total",
                color="Unidad",
                markers=True,
                labels={"venta_total": "Venta (S/)", "Anio_Mes": "Periodo"},
                color_discrete_sequence=THEME.chart_colors,
            )
            fig_trend.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=350,
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)", title=""),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=""),
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.3,
                    xanchor="center", x=0.5, font=dict(size=10),
                ),
            )
            st.plotly_chart(fig_trend, width="stretch")

    st.divider()

    # ── Fila 3: Mix línea por farmacia ───────────────────────────────
    st.markdown("#### 🧩 Mix por Línea de Negocio – Comparativo")

    df_mix_comp = (
        df_filtrado.groupby(["Unidad", "LINEA DE NEGOCIO"], as_index=False, observed=True)
        .agg(venta_total=("T. ITEM S/.", "sum"))
    )

    if not df_mix_comp.empty:
        fig_mix = px.bar(
            df_mix_comp,
            x="Unidad",
            y="venta_total",
            color="LINEA DE NEGOCIO",
            barmode="stack",
            labels={"venta_total": "Venta (S/)", "Unidad": ""},
            color_discrete_sequence=THEME.chart_colors,
        )
        fig_mix.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color=THEME.text_secondary,
            margin=dict(l=20, r=20, t=10, b=20),
            height=400,
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=""),
            legend=dict(
                orientation="h", yanchor="bottom", y=-0.3,
                xanchor="center", x=0.5, font=dict(size=10),
            ),
        )
        st.plotly_chart(fig_mix, width="stretch")
