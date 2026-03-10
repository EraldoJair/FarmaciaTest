
"""
transformations.py – Transformación y enriquecimiento de datos.

Optimizaciones: Vectorización con NumPy/Pandas.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
import streamlit as st


@st.cache_data(show_spinner=False)
def enriquecer_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega columnas derivadas útiles para análisis.
    """
    # Copia explícita para evitar SettingWithCopy
    df = df.copy()

    # Asegurar que F. VENTA sea datetime (ya lo hacemos en data_loader, 
    # pero por seguridad si viene de otra fuente)
    if not np.issubdtype(df["F. VENTA"].dtype, np.datetime64):
         df["F. VENTA"] = pd.to_datetime(df["F. VENTA"], errors="coerce")

    # Vectorización fechas
    # dt accessor ya es vectorizado en pandas
    df["Periodo"] = df["F. VENTA"].dt.to_period("M").astype(str)
    df["Fecha"] = df["F. VENTA"].dt.date # Esto devuelve objetos date, aceptable
    
    # Nombre de mes vectorizado
    # Usamos dt.month_name es_ES o map directo que es muy rápido
    meses_map = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    df["Mes_Nombre"] = df["Mes"].map(meses_map)

    # Rango horario usando pd.cut que es vectorizado
    df["Rango_Horario"] = pd.cut(
        df["Hora"],
        bins=[0, 6, 9, 12, 15, 18, 21, 24],
        labels=["00-06", "06-09", "09-12", "12-15", "15-18", "18-21", "21-24"],
        right=False,
    )

    # Vectorizado concat string
    df["Anio_Mes"] = df["Año"].astype(str) + "-" + df["Mes"].astype(str).str.zfill(2)

    return df


def agrupar_por_farmacia(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupar ventas por Unidad."""
    return (
        df.groupby("Unidad", as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            total_soles=("TOTAL  S/", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
            cantidad_items=("CANTIDAD", "sum"),
            n_registros=("T. ITEM S/.", "count"),
        )
        .sort_values("venta_total", ascending=False)
    )


def agrupar_por_fecha(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("Fecha", as_index=False)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
            n_registros=("T. ITEM S/.", "count"),
        )
        .sort_values("Fecha")
    )


def agrupar_por_farmacia_fecha(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["Unidad", "Fecha"], as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
        )
        .sort_values(["Unidad", "Fecha"])
    )


def agrupar_por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["LINEA DE NEGOCIO", "CATEGORIA 1"], as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            cantidad=("CANTIDAD", "sum"),
        )
        .sort_values("venta_total", ascending=False)
    )


def top_productos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby(["CODIGO", "DESCRIPCION", "LABORATORIO"], as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            cantidad=("CANTIDAD", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
        )
        .sort_values("venta_total", ascending=False)
        .head(n)
    )


def top_vendedores(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (
        df.groupby("VENDEDOR", as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
            n_registros=("T. ITEM S/.", "count"),
        )
        .sort_values("venta_total", ascending=False)
        .head(n)
    )


def distribucion_horaria(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("Hora", as_index=False)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            transacciones=("TRANSACCIONES", "sum"),
        )
        .sort_values("Hora")
    )


def distribucion_forma_pago(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("FORMA DE PAGO", as_index=False, observed=True)
        .agg(
            venta_total=("T. ITEM S/.", "sum"),
            n_registros=("T. ITEM S/.", "count"),
        )
        .sort_values("venta_total", ascending=False)
    )


def agrupar_dia_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupación para Heatmap."""
    # Usamos observed=True si hay categóricas para rendimiento
    # Pero aseguramos copia para manipular categorías
    df_hm = df.copy()
    
    dias_orden = [
        "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"
    ]
    
    # Castear a categórico ordenado si no lo es
    if not isinstance(df_hm["Dia"].dtype, pd.CategoricalDtype):
         df_hm["Dia"] = pd.Categorical(
            df_hm["Dia"], 
            categories=dias_orden, 
            ordered=True
        )

    return (
        df_hm.groupby(["Dia", "Hora"], as_index=False, observed=True)
        .agg(venta_total=("T. ITEM S/.", "sum"))
        .sort_values(["Dia", "Hora"])
    )


def filtrar_datos(
    df: pd.DataFrame,
    farmacias: list | None = None,
    fecha_inicio=None,
    fecha_fin=None,
    lineas_negocio: list | None = None,
    categorias: list | None = None,
    vendedores: list | None = None,
) -> pd.DataFrame:
    """Aplica filtros al DataFrame de forma vectorizada."""
    if df.empty: return df
    
    # Empezamos con mascara total True
    mask = pd.Series(True, index=df.index)

    if farmacias:
        mask &= df["Unidad"].isin(farmacias)
    
    # Fechas: asegurarse ser Timestamp para comparar
    if fecha_inicio:
        ts_inicio = pd.Timestamp(fecha_inicio)
        mask &= (df["F. VENTA"] >= ts_inicio)
    
    if fecha_fin:
        ts_fin = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) # Fin del dia
        mask &= (df["F. VENTA"] <= ts_fin)

    if lineas_negocio:
        mask &= df["LINEA DE NEGOCIO"].isin(lineas_negocio)

    if categorias:
        mask &= df["CATEGORIA 1"].isin(categorias)

    if vendedores:
        mask &= df["VENDEDOR"].isin(vendedores)

    return df.loc[mask]
