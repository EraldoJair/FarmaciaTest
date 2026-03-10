"""
data_loader.py – Módulo de carga y validación de datos.

Maneja la ingesta desde CSV, controlando errores y optimizando tipos.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Optional, List
from pathlib import Path

from app.config import CSV_PATH, REQUIRED_COLUMNS, COLUMN_DTYPES, DATE_COLUMNS


@st.cache_data(ttl=3600, show_spinner=False)
def cargar_datos_csv(ruta: Optional[str] = None) -> pd.DataFrame:
    """
    Carga datos desde archivo CSV con manejo de errores y optimización.
    
    Args:
        ruta: Ruta opcional al archivo. Si no se da, usa CSV_PATH de config.
        
    Returns:
        DataFrame limpio y validado.
        
    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si faltan columnas requeridas o formato inválido.
    """
    path = Path(ruta) if ruta else CSV_PATH

    if not path.exists():
        # Intentar buscar en parientes si estamos en subdirectorio
        if not ruta:
            alt_path = Path("..") / path.name
            if alt_path.exists():
                path = alt_path
            else:
                raise FileNotFoundError(f"No se encontró el archivo de datos: {path}")
        else:
             raise FileNotFoundError(f"No se encontró el archivo de datos: {path}")

    try:
        # Carga optimizada usando dtypes del config
        # parse_dates es más lento en read_csv, mejor hacerlo post-carga si es muy grande
        # pero para ~100MB es aceptable.
        df = pd.read_csv(
            path, 
            dtype=COLUMN_DTYPES, 
            parse_dates=DATE_COLUMNS,
            dayfirst=True, # Asumimos formato Latam DD/MM/YYYY
            low_memory=False,
        )
    except Exception as e:
        raise ValueError(f"Error leyendo el archivo CSV: {e}")

    # Validar columnas
    _validar_columnas(df)

    # Limpieza básica
    df = _limpiar_datos(df)

    return df


def cargar_datos_upload(uploaded_file) -> pd.DataFrame:
    """Carga datos desde un archivo subido por el usuario (Streamlit)."""
    try:
        if uploaded_file.name.endswith('.csv'):
             df = pd.read_csv(
                uploaded_file,
                dtype=COLUMN_DTYPES, 
                parse_dates=DATE_COLUMNS,
                dayfirst=True
            )
        else:
             df = pd.read_excel(uploaded_file) # Excel no soporta dtype dict igual que csv a veces
             
    except Exception as e:
        raise ValueError(f"Error procesando el archivo subido: {e}")

    _validar_columnas(df)
    return _limpiar_datos(df)


def _validar_columnas(df: pd.DataFrame) -> None:
    """Verifica que existan las columnas críticas."""
    faltantes = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    
    # Permitimos que falten algunas si no son criticas para todo, 
    # pero por ahora somos estrictos con las definidas en config.
    # Filtramos solo las que son claves para kpis:
    criticas = ["Unidad", "T. ITEM S/.", "F. VENTA", "Año", "Mes"]
    faltantes_criticas = [col for col in criticas if col not in df.columns]
    
    if faltantes_criticas:
        raise ValueError(f"El archivo data faltan columnas críticas: {faltantes_criticas}")


def _limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Limpieza base: duplicados, nulos en claves."""
    # Eliminar duplicados exactos
    df = df.drop_duplicates()
    
    # Eliminar registros sin fecha o sin venta
    df = df.dropna(subset=["F. VENTA", "T. ITEM S/."])
    
    # Asegurar que Unidad sea string limpio
    if "Unidad" in df.columns:
        df["Unidad"] = df["Unidad"].astype(str).str.strip()
        
    return df
