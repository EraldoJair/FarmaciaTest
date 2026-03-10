"""
dashboard.py – Dashboard Ejecutivo principal.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config import THEME, CURRENCY_FORMAT, PERCENT_FORMAT, NUMBER_FORMAT


from app.ui.sede_tabs import render_with_sede_tabs

def render_dashboard(service, df_filtrado: pd.DataFrame) -> None:
    """Renderiza el dashboard ejecutivo con pestañas por sede."""
    render_with_sede_tabs(df_filtrado, _render_dashboard_content, service)


def _render_dashboard_content(service, df: pd.DataFrame, tab_key: str = "default") -> None:
    """Contenido real del dashboard (interno)."""
    
    # ── Exportar Datos ───────────────────────────────────────────────
    # col_header, col_btn = st.columns([5, 1])
    # with col_header:
    #     st.markdown("### 📊 Indicadores Principales")
    # with col_btn:
    #     csv = df.to_csv(index=False).encode('utf-8')
    #     st.download_button(
    #         label="📥 Exportar CSV",
    #         data=csv,
    #         file_name="farmacia_analytics_data.csv",
    #         mime="text/csv",
    #         key=f"download_csv_{tab_key}",
    #     )

    # ── KPI Cards ────────────────────────────────────────────────────
    kpi = service.resumen_ejecutivo(df)

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    def mostrar_metrica(label, key, formato):
        data = kpi.get(key)
        if isinstance(data, (tuple, list)):
            val, delta = data
        else:
            val = data
            delta = 0.0
            
        st.metric(
            label,
            formato.format(val) if val is not None else "0",
            # delta=f"{delta:+.1f}%" if delta != 0 else None,
        )

    with c1:
        mostrar_metrica("💰 Venta Total", "venta_total", CURRENCY_FORMAT)
    with c2:
        mostrar_metrica("🧾 Transacciones", "transacciones", NUMBER_FORMAT)
    with c3:
        mostrar_metrica("🎫 Ticket Promedio", "ticket_promedio", CURRENCY_FORMAT)
    with c4:
        mostrar_metrica("📦 Ítems Vendidos", "cantidad_items", NUMBER_FORMAT)
    with c5:
        mostrar_metrica("📅 Días con Venta", "dias_venta", NUMBER_FORMAT)
    with c6:
        mostrar_metrica("📈 Venta Diaria Prom. ", "venta_diaria", CURRENCY_FORMAT)

    st.divider()

    # ── Fila 1: Evolución temporal + Ranking ─────────────────────────
    col_evo, col_rank = st.columns([3, 2])

    with col_evo:
        st.markdown("#### 📈 Evolución de Ventas")
        df_fecha = service.ventas_por_fecha(df)

        if not df_fecha.empty:
            # Calcular promedios móviles
            df_fecha = df_fecha.sort_values("Fecha")
            df_fecha["MA_7"] = df_fecha["venta_total"].rolling(window=7, min_periods=1).mean()
            df_fecha["MA_30"] = df_fecha["venta_total"].rolling(window=30, min_periods=1).mean()

            fig_evo = go.Figure()

            # Área de ventas diarias
            fig_evo.add_trace(go.Scatter(
                x=df_fecha["Fecha"],
                y=df_fecha["venta_total"],
                fill="tozeroy",
                mode="lines",
                name="Venta Diaria",
                line=dict(color=THEME.accent, width=1),
                fillcolor="rgba(0, 191, 165, 0.15)",
            ))

            # Media móvil 7 días
            fig_evo.add_trace(go.Scatter(
                x=df_fecha["Fecha"],
                y=df_fecha["MA_7"],
                mode="lines",
                name="Media 7 días",
                line=dict(color="#FF6D00", width=2, dash="dot"),
            ))

            # Media móvil 30 días
            fig_evo.add_trace(go.Scatter(
                x=df_fecha["Fecha"],
                y=df_fecha["MA_30"],
                mode="lines",
                name="Media 30 días",
                line=dict(color="#F50057", width=2.5),
            ))

            fig_evo.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=350,
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Venta (S/)"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.25,
                    xanchor="center", x=0.5, font=dict(size=10),
                ),
                hovermode="x unified",
            )
            st.plotly_chart(fig_evo, width="stretch")

    with col_rank:
        st.markdown("#### 🏆 Ranking Farmacias")
        cumpl = service.cumplimiento(df)

        if not cumpl.empty:
            fig_rank = px.bar(
                cumpl.sort_values("venta_total", ascending=True),
                x="venta_total",
                y="Unidad",
                orientation="h",
                text=cumpl.sort_values("venta_total", ascending=True)["venta_total"].apply(
                    lambda v: CURRENCY_FORMAT.format(v)
                ),
                color="venta_total",
                color_continuous_scale=["#1E88E5", "#00BFA5"],
            )
            fig_rank.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=350,
                showlegend=False,
                coloraxis_showscale=False,
                xaxis=dict(visible=False),
                yaxis=dict(title=""),
            )
            fig_rank.update_traces(textposition="auto")
            st.plotly_chart(fig_rank, width="stretch")

    st.divider()

    # ── Fila 2: Top Productos + Mix Línea de Negocio ─────────────────
    col_prod, col_mix = st.columns([3, 2])

    with col_prod:
        st.markdown("#### 🏅 Top 10 Productos")
        df_top = service.top_productos(df, 10)

        if not df_top.empty:
            fig_top = px.bar(
                df_top.sort_values("venta_total", ascending=True),
                x="venta_total",
                y="DESCRIPCION",
                orientation="h",
                text=df_top.sort_values("venta_total", ascending=True)["venta_total"].apply(
                    lambda v: CURRENCY_FORMAT.format(v)
                ),
                color_discrete_sequence=[THEME.chart_colors[2]],
            )
            fig_top.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=400,
                xaxis=dict(visible=False),
                yaxis=dict(title=""),
            )
            fig_top.update_traces(textposition="auto")
            st.plotly_chart(fig_top, width="stretch")

    with col_mix:
        st.markdown("#### 🧩 Mix por Categoría (Treemap)")
        from app import transformations 
        df_tree = transformations.agrupar_por_categoria(df)

        if not df_tree.empty:
            fig_mix = px.treemap(
                df_tree,
                path=[px.Constant("Todas"), "LINEA DE NEGOCIO", "CATEGORIA 1"],
                values="venta_total",
                color="venta_total",
                color_continuous_scale="Mint",
            )
            fig_mix.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                height=400,
                font_color=THEME.text_secondary,
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_mix, width="stretch")

    st.divider()

    # ── Fila 3: Distribución Horaria + Forma de Pago ─────────────────
    with st.expander("🔥 Mapa de Calor & 💳 Forma de Pago", expanded=False):
        col_hora, col_pago = st.columns(2)

        with col_hora:
            st.markdown("#### 🔥 Mapa de Calor (Día vs Hora)")
            df_hm = service.heatmap_dia_hora(df)

            if not df_hm.empty:
                fig_hm = px.density_heatmap(
                    df_hm,
                    x="Hora",
                    y="Dia",
                    z="venta_total",
                    histfunc="sum",
                    color_continuous_scale="Teal",
                    labels={"venta_total": "Venta", "Dia": "Día", "Hora": "Hora"},
                )
                fig_hm.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color=THEME.text_secondary,
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=320,
                    xaxis=dict(dtick=1),
                    yaxis=dict(categoryorder="array", categoryarray=["Domingo", "Sábado", "Viernes", "Jueves", "Miércoles", "Martes", "Lunes"]),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(fig_hm, width="stretch")

        with col_pago:
            st.markdown("#### 💳 Distribución por Forma de Pago")
            df_pago = service.dist_forma_pago(df)

            if not df_pago.empty:
                df_pago["FORMA DE PAGO"] = df_pago["FORMA DE PAGO"].str.strip()
                fig_pago = px.pie(
                    df_pago,
                    values="venta_total",
                    names="FORMA DE PAGO",
                    hole=0.45,
                    color_discrete_sequence=THEME.chart_colors,
                )
                fig_pago.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color=THEME.text_secondary,
                    margin=dict(l=20, r=20, t=10, b=20),
                    height=320,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.4,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=10),
                    ),
                )
                st.plotly_chart(fig_pago, width="stretch")


    # ── Fila 4: Top Vendedores + Evolución por Farmacia ──────────────
    col_vend, col_farm = st.columns(2)

    with col_vend:
        st.markdown("#### 👤 Top 10 Vendedores")
        df_vend = service.top_vendedores(df, 10)

        if not df_vend.empty:
            fig_vend = px.bar(
                df_vend.sort_values("venta_total", ascending=True),
                x="venta_total",
                y="VENDEDOR",
                orientation="h",
                text=df_vend.sort_values("venta_total", ascending=True)["venta_total"].apply(
                    lambda v: CURRENCY_FORMAT.format(v)
                ),
                color_discrete_sequence=[THEME.chart_colors[3]],
            )
            fig_vend.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=380,
                xaxis=dict(visible=False),
                yaxis=dict(title=""),
            )
            fig_vend.update_traces(textposition="auto")
            st.plotly_chart(fig_vend, width="stretch")

    with col_farm:
        st.markdown("#### 📊 Evolución por Farmacia")
        df_ff = service.ventas_farmacia_fecha(df)

        if not df_ff.empty:
            fig_ff = px.line(
                df_ff,
                x="Fecha",
                y="venta_total",
                color="Unidad",
                labels={"venta_total": "Venta (S/)", "Fecha": ""},
                color_discrete_sequence=THEME.chart_colors,
            )
            fig_ff.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color=THEME.text_secondary,
                margin=dict(l=20, r=20, t=10, b=20),
                height=380,
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="center",
                    x=0.5,
                ),
            )
            st.plotly_chart(fig_ff, width="stretch")

    st.divider()

    # ── Fila 5: Análisis por Día de la Semana ────────────────────────
    with st.expander("📅 Análisis por Día de la Semana", expanded=False):
        col_dia, col_dia_farm = st.columns(2)

        dias_orden = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        with col_dia:
            st.markdown("#### 📅 Venta Promedio por Día de la Semana")

            if "Dia" in df.columns:
                df_dia = df.copy()
                df_dia["Dia"] = pd.Categorical(df_dia["Dia"], categories=dias_orden, ordered=True)

                venta_por_fecha = df_dia.groupby(["Fecha", "Dia"], as_index=False, observed=True).agg(
                    venta_total=("T. ITEM S/.", "sum")
                )
                venta_promedio_dia = venta_por_fecha.groupby("Dia", as_index=False, observed=True).agg(
                    venta_promedio=("venta_total", "mean"),
                    n_dias=("venta_total", "count"),
                ).sort_values("Dia")

                if not venta_promedio_dia.empty:
                    max_val = venta_promedio_dia["venta_promedio"].max()
                    min_val = venta_promedio_dia["venta_promedio"].min()
                    colors = []
                    for v in venta_promedio_dia["venta_promedio"]:
                        if v == max_val:
                            colors.append(THEME.success)
                        elif v == min_val:
                            colors.append(THEME.danger)
                        else:
                            colors.append(THEME.accent)

                    fig_dia = go.Figure(go.Bar(
                        x=venta_promedio_dia["Dia"],
                        y=venta_promedio_dia["venta_promedio"],
                        marker_color=colors,
                        text=venta_promedio_dia["venta_promedio"].apply(
                            lambda v: CURRENCY_FORMAT.format(v)
                        ),
                        textposition="outside",
                        hovertemplate=(
                            "<b>%{x}</b><br>"
                            "Venta Promedio: S/ %{y:,.2f}<br>"
                            "<extra></extra>"
                        ),
                    ))

                    fig_dia.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=THEME.text_secondary,
                        margin=dict(l=20, r=20, t=10, b=20),
                        height=350,
                        xaxis=dict(title=""),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="Promedio (S/)"),
                    )
                    st.plotly_chart(fig_dia, width="stretch")

        with col_dia_farm:
            st.markdown("#### 📊 Día de Semana por Farmacia")

            if "Dia" in df.columns:
                df_dia2 = df.copy()
                df_dia2["Dia"] = pd.Categorical(df_dia2["Dia"], categories=dias_orden, ordered=True)

                venta_dia_farm = df_dia2.groupby(["Dia", "Unidad"], as_index=False, observed=True).agg(
                    venta_total=("T. ITEM S/.", "sum")
                )

                if not venta_dia_farm.empty:
                    fig_dia_farm = px.bar(
                        venta_dia_farm,
                        x="Dia",
                        y="venta_total",
                        color="Unidad",
                        barmode="group",
                        labels={"venta_total": "Venta (S/)", "Dia": ""},
                        color_discrete_sequence=THEME.chart_colors,
                    )
                    fig_dia_farm.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color=THEME.text_secondary,
                        margin=dict(l=20, r=20, t=10, b=20),
                        height=350,
                        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", title=""),
                        legend=dict(
                            orientation="h", yanchor="bottom", y=-0.3,
                            xanchor="center", x=0.5, font=dict(size=10),
                        ),
                    )
                    st.plotly_chart(fig_dia_farm, width="stretch")

    # ── Fila 6: Análisis Pareto ──────────────────────────────────────
    with st.expander("📦 Principio de Pareto (80/20) - Productos", expanded=False):
        from app.kpis import calculate_pareto
        import numpy as np

        # Pareto por Monto
        pareto_df = calculate_pareto(df, "T. ITEM S/.", "DESCRIPCION")

        if not pareto_df.empty:
            col_pareto_metrics, col_pareto_chart = st.columns([1, 2])

            top_80_count = len(pareto_df[pareto_df['classification'] == 'Top 80%'])
            total_count = len(pareto_df)
            top_80_pct = (top_80_count / total_count * 100) if total_count > 0 else 0

            with col_pareto_metrics:
                st.info(f"💡 **Insight:** El **80%** de las ventas es generado por solo **{top_80_count}** productos (el **{top_80_pct:.1f}%** de todo el catálogo).")

                with st.expander(f"📋 Ver Top 80% ({top_80_count} prods)"):
                    st.dataframe(
                        pareto_df[pareto_df['classification'] == "Top 80%"][['DESCRIPCION', 'T. ITEM S/.', 'cumulative_percent']]
                        .rename(columns={"T. ITEM S/.": "Venta", "cumulative_percent": "% Acum"})
                        .style.format({'Venta': 'S/ {:,.2f}', '% Acum': '{:.1f}%'}),
                        width="stretch"
                    )

            with col_pareto_chart:
                # Gráfico Top 50 productos Pareto
                top_view = pareto_df.head(50)

                fig_pareto = go.Figure()

                # Barras
                fig_pareto.add_trace(go.Bar(
                    x=top_view["DESCRIPCION"],
                    y=top_view["T. ITEM S/."],
                    name="Venta",
                    marker_color=[THEME.success if c == "Top 80%" else THEME.secondary for c in top_view["classification"]]
                ))

                # Línea acumulada
                fig_pareto.add_trace(go.Scatter(
                    x=top_view["DESCRIPCION"],
                    y=top_view["cumulative_percent"],
                    name="% Acumulado",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color=THEME.warning, width=2)
                ))

                # Línea 80%
                fig_pareto.add_hline(y=80, line_dash="dash", line_color="white", opacity=0.8, yref="y2", annotation_text="80%")

                fig_pareto.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color=THEME.text_secondary,
                    height=400,
                    showlegend=True,
                    xaxis=dict(showticklabels=False, title="Productos (Top 50)"),
                    yaxis=dict(title="Venta (S/)", gridcolor="rgba(255,255,255,0.08)"),
                    yaxis2=dict(
                        title="% Acumulado",
                        overlaying="y",
                        side="right",
                        range=[0, 110],
                        showgrid=False
                    ),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02,
                        xanchor="right", x=1
                    ),
                    margin=dict(l=20, r=20, t=30, b=20),
                )
                st.plotly_chart(fig_pareto, width="stretch")

