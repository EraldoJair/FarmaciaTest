"""
sede_tabs.py – Sistema de sub-tabs por Sede (Unidad).

Permite ver datos generales + una pestaña por cada sede filtrada.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd
import streamlit as st


def render_with_sede_tabs(
    df: pd.DataFrame,
    render_fn: Callable,
    *args,
    **kwargs,
) -> None:
    """
    Envuelve una función de renderizado con sub-tabs por Unidad.

    Crea tabs dinámicos:
      - "🌐 Vista General" → llama render_fn(df, *args, **kwargs)
      - Una pestaña por cada Unidad → llama render_fn(df_filtrado, *args, **kwargs)

    Args:
        df: DataFrame completo (filtrado por sidebar).
        render_fn: Función de renderizado que acepta (service_or_args, df, **kwargs).
        *args: Argumentos posicionales para render_fn (antes de df).
        **kwargs: Argumentos de keyword para render_fn.
    """
    if "Unidad" not in df.columns or df.empty:
        render_fn(*args, df=df, tab_key="only", **kwargs)
        return

    unidades = sorted(df["Unidad"].unique())

    # Si solo hay una unidad, no crear tabs
    if len(unidades) <= 1:
        render_fn(*args, df=df, tab_key="only", **kwargs)
        return

    tab_labels = ["🌐 Vista General"] + [f"🏥 {u}" for u in unidades]
    tabs = st.tabs(tab_labels)

    # Tab general
    with tabs[0]:
        render_fn(*args, df=df, tab_key="general", **kwargs)

    # Tab por sede
    for i, unidad in enumerate(unidades, start=1):
        with tabs[i]:
            df_sede = df[df["Unidad"] == unidad].copy()
            if df_sede.empty:
                st.info(f"No hay datos para {unidad} con los filtros seleccionados.")
            else:
                st.caption(f"📍 Datos filtrados para: **{unidad}**")
                render_fn(*args, df=df_sede, tab_key=unidad, **kwargs)
