"""
metas.py – Gestión de metas comerciales y seguimiento.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import datetime

from app.config import THEME, CURRENCY_FORMAT


def render_metas(service, df_filtrado: pd.DataFrame) -> None:
    """Renderiza la vista de gestión de metas."""

    st.markdown("### 🎯 Gestión de Metas Comerciales")

    # ── 1. Selector de Año para Edición ──────────────────────────────
    col_anio, _ = st.columns([1, 4])
    with col_anio:
        anio_actual = datetime.date.today().year
        anio_seleccionado = st.selectbox("Seleccionar Año", [anio_actual, anio_actual + 1], index=0)

    # ── 2. Editor de Metas (Grid) ────────────────────────────────────
    with st.expander("⚙️ Editar Metas Mensuales", expanded=True):
        st.caption(f"Edite las metas para el año {anio_seleccionado}. Los cambios se guardan automáticamente al hacer clic en 'Guardar'.")

        # Preparar datos para el editor: Pivotar (Unidad x Mes)
        df_metas = service.metas_df.copy()
        
        # Filtrar año y asegurar tipos
        if not df_metas.empty:
            df_metas["Anio"] = df_metas["Anio"].astype(int)
            df_grid = df_metas[df_metas["Anio"] == anio_seleccionado]
        else:
            df_grid = pd.DataFrame()

        # Obtener lista completa de unidades (desde ventas o metas existentes)
        unidades_ventas = df_filtrado["Unidad"].unique() if not df_filtrado.empty else []
        unidades_metas = df_metas["Unidad"].unique() if not df_metas.empty else []
        todas_unidades = sorted(list(set(unidades_ventas) | set(unidades_metas)))

        # Crear estructura base si faltan datos
        rows = []
        for unidad in todas_unidades:
            row = {"Unidad": unidad}
            # Llenar mes 1..12
            for mes in range(1, 13):
                # Buscar valor existente
                val = 0.0
                if not df_grid.empty:
                    match = df_grid[(df_grid["Unidad"] == unidad) & (df_grid["Mes"] == mes)]
                    if not match.empty:
                        val = match.iloc[0]["Meta"]
                row[f"Mes {mes}"] = val
            rows.append(row)
        
        df_editor = pd.DataFrame(rows)
        if not df_editor.empty:
            df_editor = df_editor.set_index("Unidad")

        # Mostrar Data Editor
        edited_df = st.data_editor(
            df_editor,
            column_config={
                f"Mes {i}": st.column_config.NumberColumn(
                    f"{pd.to_datetime(f'2024-{i}-01').strftime('%b')}", # Nombre mes abrev
                    min_value=0,
                    format="S/ %.0f"
                ) for i in range(1, 13)
            },
            width="stretch",
            height=300
        )

        # Guardar cambios
        if st.button("💾 Guardar Cambios", type="primary"):
            # 1. Convertir editor de vuelta a long format
            df_long = edited_df.reset_index().melt(
                id_vars=["Unidad"], 
                var_name="Mes_Label", 
                value_name="Meta"
            )
            # 2. Extraer número de mes ("Mes 1" -> 1)
            df_long["Mes"] = df_long["Mes_Label"].str.replace("Mes ", "").astype(int)
            df_long["Anio"] = anio_seleccionado
            
            # 3. Actualizar DataFrame principal de metas
            # Eliminar registros viejos de este año
            df_final = service.metas_df.copy()
            if not df_final.empty:
                df_final = df_final[df_final["Anio"] != anio_seleccionado]
            
            # Concatenar nuevos
            df_update = df_long[["Unidad", "Anio", "Mes", "Meta"]]
            df_final = pd.concat([df_final, df_update], ignore_index=True)
            
            # 4. Persistir
            service.guardar_metas(df_final)
            st.success(f"✅ Metas del año {anio_seleccionado} guardadas correctamente.")
            st.rerun()

    st.divider()

    # ── 3. Visualización de Cumplimiento (Gauges) ────────────────────
    st.markdown("#### 🏷️ Cumplimiento Actual (vs Meta Mensual)")

    cumpl = service.cumplimiento(df_filtrado)

    if cumpl.empty:
        st.info("No hay datos de ventas para mostrar cumplimiento.")
        return

    # Crear gauges en filas de 3
    for row_start in range(0, len(cumpl), 3):
        cols_gauge = st.columns(3)
        for j, col in enumerate(cols_gauge):
            idx = row_start + j
            if idx >= len(cumpl):
                break

            row = cumpl.iloc[idx]
            with col:
                _render_gauge(
                    farmacia=row["Unidad"],
                    venta=row["venta_total"],
                    meta=row["meta"],
                    cumplimiento=row["cumplimiento_pct"],
                    semaforo=row["semaforo"],
                )


def _render_gauge(
    farmacia: str,
    venta: float,
    meta: float,
    cumplimiento: float,
    semaforo: str,
) -> None:
    """Renderiza un gauge chart individual."""
    # Color dinámico
    if cumplimiento >= 90:
        bar_color = THEME.success
    elif cumplimiento >= 70:
        bar_color = THEME.warning
    else:
        bar_color = THEME.danger

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=cumplimiento,
        number={"suffix": "%", "font": {"size": 24, "color": "white"}},
        delta={"reference": 100, "suffix": "%", "increasing": {"color": THEME.success}},
        title={"text": f"{semaforo} {farmacia}", "font": {"size": 14, "color": "white"}},
        gauge=dict(
            axis=dict(range=[0, max(120, cumplimiento)], tickcolor="rgba(255,255,255,0.3)"),
            bar=dict(color=bar_color),
            bgcolor="rgba(255,255,255,0.05)",
            borderwidth=0,
            steps=[
                dict(range=[0, 70], color="rgba(255,23,68,0.1)"),
                dict(range=[70, 90], color="rgba(255,214,0,0.1)"),
                # dict(range=[90, 120], color="rgba(0,200,83,0.1)"),
            ],
            threshold=dict(
                line=dict(color="white", width=2),
                thickness=0.75,
                value=100,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=200,
        margin=dict(l=20, r=20, t=40, b=10),
    )

    st.plotly_chart(fig, width="stretch")
    
    st.markdown(f"""
    <div style="text-align:center; margin-top:-10px; font-size:0.8rem; color:#B0BEC5;">
        Real: <b>{CURRENCY_FORMAT.format(venta)}</b><br>
        Meta: {CURRENCY_FORMAT.format(meta)}
    </div>
    """, unsafe_allow_html=True)
