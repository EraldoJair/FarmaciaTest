
"""
kpis.py – Motor de cálculo de KPIs comerciales (Vectorizado).

Optimizaciones: Reemplazo de .apply() por operaciones vectorizadas.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

from app.config import DEFAULT_METAS, SEMAFORO


# ── KPIs Globales ────────────────────────────────────────────────────

def venta_total(df: pd.DataFrame) -> float:
    """Venta total en soles."""
    if df.empty: return 0.0
    return float(df["T. ITEM S/."].sum())

def venta_total_items(df: pd.DataFrame) -> float:
    """Venta total con impuestos."""
    if df.empty: return 0.0
    return float(df["T. ITEM S/."].sum())

def total_transacciones(df: pd.DataFrame) -> int:
    """Número total de transacciones únicas."""
    if df.empty: return 0
    return int(df["TRANSACCIONES"].sum())

def ticket_promedio(df: pd.DataFrame) -> float:
    """Ticket promedio = Venta total / Transacciones."""
    trans = total_transacciones(df)
    if trans == 0:
        return 0.0
    return venta_total_items(df) / trans

def cantidad_total(df: pd.DataFrame) -> int:
    """Total de ítems vendidos."""
    if df.empty: return 0
    return int(df["CANTIDAD"].sum())

def dias_con_venta(df: pd.DataFrame) -> int:
    """Número de días con al menos una venta."""
    if df.empty: return 0
    # Usar columna Fecha pre-calculada si existe (más rápido que .dt.date)
    if "Fecha" in df.columns:
        return df["Fecha"].nunique()
    return df["F. VENTA"].dt.date.nunique()

def venta_diaria_promedio(df: pd.DataFrame) -> float:
    """Venta promedio por día."""
    dias = dias_con_venta(df)
    if dias == 0:
        return 0.0
    return venta_total(df) / dias


# ── Cumplimiento de Metas ────────────────────────────────────────────

def calcular_cumplimiento(
    df: pd.DataFrame,
    df_metas: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Calcula cumplimiento de meta por farmacia.
    """
    if df.empty:
        return pd.DataFrame()

    # 1. Agrupar ventas reales
    ventas = (
        df.groupby(["Unidad", "Año", "Mes"], as_index=False, observed=True)
        .agg(venta_total=("T. ITEM S/.", "sum"))
    )

    # 2. Preparar metas
    metas = df_metas if df_metas is not None else pd.DataFrame()
    
    if not metas.empty:
        # Optimización de tipos para merge
        # Usamos cadenas para asegurar match si hay diferencias de tipo int/str
        # Aunque lo ideal es int, str es seguro.
        # Mejor castear ambos a int si es posible
        try:
            metas["Anio"] = metas["Anio"].astype(int)
            metas["Mes"] = metas["Mes"].astype(int)
            ventas["Año"] = ventas["Año"].astype(int)
            ventas["Mes"] = ventas["Mes"].astype(int)
        except:
            pass # Si falla, intentará merge tal cual

        merged = ventas.merge(
            metas, 
            left_on=["Unidad", "Año", "Mes"], 
            right_on=["Unidad", "Anio", "Mes"], 
            how="left"
        )
        merged["Meta"] = merged["Meta"].fillna(0)
    else:
        merged = ventas.copy()
        merged["Meta"] = 0.0

    # 3. Agrupar final por Unidad
    resumen = (
        merged.groupby("Unidad", as_index=False, observed=True)
        .agg(
            venta_total=("venta_total", "sum"),
            meta=("Meta", "sum")
        )
    )

    # Vectorización: cálculo de columnas completas sin .apply
    # Cumplimiento
    # np.where(condicion, valor_si_true, valor_si_false)
    resumen["cumplimiento_pct"] = np.where(
        resumen["meta"] > 0,
        (resumen["venta_total"] / resumen["meta"]) * 100,
        0.0
    )
    
    resumen["brecha"] = resumen["meta"] - resumen["venta_total"]

    # Semáforo Vectorizado
    cond_verde = resumen["cumplimiento_pct"] >= SEMAFORO["verde"] * 100
    cond_amarillo = resumen["cumplimiento_pct"] >= SEMAFORO["amarillo"] * 100
    
    resumen["semaforo"] = np.select(
        [cond_verde, cond_amarillo],
        ["🟢", "🟡"],
        default="🔴"
    )

    # Ranking
    resumen = resumen.sort_values("venta_total", ascending=False).reset_index(drop=True)
    resumen["ranking"] = resumen.index + 1

    return resumen


# ── Crecimiento ──────────────────────────────────────────────────────

def crecimiento_periodos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el crecimiento porcentual mes a mes para cada farmacia.
    """
    if df.empty: return pd.DataFrame()

    mensual = (
        df.groupby(["Unidad", "Anio_Mes"], as_index=False, observed=True)
        .agg(venta_total=("T. ITEM S/.", "sum"))
        .sort_values(["Unidad", "Anio_Mes"])
    )
    
    # pct_change vectorizado por grupos
    mensual["crecimiento_pct"] = (
        mensual.groupby("Unidad")["venta_total"]
        .pct_change() * 100
    )
    return mensual


# ── Mix por Línea de Negocio ─────────────────────────────────────────

def mix_linea_negocio(df: pd.DataFrame) -> pd.DataFrame:
    """Participación porcentual por línea de negocio."""
    if df.empty: return pd.DataFrame()

    resumen = (
        df.groupby("LINEA DE NEGOCIO", as_index=False, observed=True)
        .agg(venta_total=("T. ITEM S/.", "sum"))
        .sort_values("venta_total", ascending=False)
    )
    total = resumen["venta_total"].sum()
    
    resumen["participacion_pct"] = np.where(
        total > 0,
        (resumen["venta_total"] / total) * 100,
        0.0
    )
    return resumen


# ── Comparativo Multi-sede ───────────────────────────────────────────

def comparativo_farmacias(
    df: pd.DataFrame,
    df_metas: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Genera tabla comparativa completa."""
    cumplimiento = calcular_cumplimiento(df, df_metas)
    
    if cumplimiento.empty:
         return pd.DataFrame()
         
    basico = (
        df.groupby("Unidad", as_index=False, observed=True)
        .agg(
            transacciones=("TRANSACCIONES", "sum"),
            cantidad_items=("CANTIDAD", "sum"),
            n_registros=("T. ITEM S/.", "count"),
        )
    )
    
    resumen = cumplimiento.merge(basico, on="Unidad", how="left")

    # Vectorización
    resumen["ticket_promedio"] = np.where(
        resumen["transacciones"] > 0,
        resumen["venta_total"] / resumen["transacciones"],
        0.0
    )

    # Días venta — usar columna Fecha pre-calculada (vectorizado, sin lambda)
    if "Fecha" in df.columns:
        dias_venta = df.groupby("Unidad")["Fecha"].nunique().reset_index(name="dias_venta")
    else:
        dias_venta = (
            df.groupby("Unidad")["F. VENTA"]
            .apply(lambda x: x.dt.date.nunique())
        ).reset_index(name="dias_venta")
    
    resumen = resumen.merge(dias_venta, on="Unidad", how="left")

    resumen["venta_diaria"] = np.where(
        resumen["dias_venta"] > 0,
        resumen["venta_total"] / resumen["dias_venta"],
        0.0
    )

    cols = [
        "ranking", "Unidad", "venta_total", "meta", "cumplimiento_pct", "semaforo", 
        "brecha", "transacciones", "ticket_promedio", "venta_diaria", "dias_venta"
    ]
    cols = [c for c in cols if c in resumen.columns]
    
    return resumen[cols]


# ── Crecimiento KPIs (Vectorizados) ────────────────────────────────

def _calcular_deltas_generico(df: pd.DataFrame, col_valor: str, agg: str = "sum") -> float:
    """Helper genérico para variación periodo actual vs anterior."""
    if "Periodo" not in df.columns or df.empty:
        return 0.0
        
    agrupado = df.groupby("Periodo")[col_valor].agg(agg).sort_index()
    if len(agrupado) < 2:
        return 0.0
        
    actual = agrupado.iloc[-1]
    prev = agrupado.iloc[-2]
    
    if prev == 0: return 0.0
    return ((actual - prev) / prev) * 100

def crecimiento_ventas(df: pd.DataFrame) -> float:
    return _calcular_deltas_generico(df, "T. ITEM S/.", "sum")

def crecimiento_transacciones(df: pd.DataFrame) -> float:
    return _calcular_deltas_generico(df, "TRANSACCIONES", "sum")

def crecimiento_cantidad(df: pd.DataFrame) -> float:
    return _calcular_deltas_generico(df, "CANTIDAD", "sum")

def crecimiento_ticket(df: pd.DataFrame) -> float:
    """Crecimiento de ticket promedio."""
    if "Periodo" not in df.columns or df.empty: return 0.0
    
    periodos = df.groupby("Periodo").agg(
        venta=("T. ITEM S/.", "sum"),
        trans=("TRANSACCIONES", "sum"),
    ).sort_index()
    
    # Vectorizado
    periodos["ticket"] = np.where(
        periodos["trans"] > 0,
        periodos["venta"] / periodos["trans"],
        0.0
    )
    
    if len(periodos) < 2: return 0.0
    return ((periodos["ticket"].iloc[-1] - periodos["ticket"].iloc[-2]) / 
            periodos["ticket"].iloc[-2] * 100) if periodos["ticket"].iloc[-2] != 0 else 0.0

def crecimiento_venta_diaria(df: pd.DataFrame) -> float:
    if "Periodo" not in df.columns or df.empty: return 0.0
    
    # Usar columna Fecha pre-calculada si existe para evitar lambda costoso
    if "Fecha" in df.columns:
        venta_per = df.groupby("Periodo")["T. ITEM S/."].sum()
        dias_per = df.groupby("Periodo")["Fecha"].nunique()
        periodos = pd.DataFrame({"venta": venta_per, "dias": dias_per}).sort_index()
    else:
        periodos = df.groupby("Periodo").agg(
            venta=("T. ITEM S/.", "sum"),
            dias=("F. VENTA", lambda x: x.dt.date.nunique()),
        ).sort_index()
    
    periodos["venta_diaria"] = np.where(
        periodos["dias"] > 0,
        periodos["venta"] / periodos["dias"],
        0.0
    )
    
    if len(periodos) < 2: return 0.0
    actual = periodos["venta_diaria"].iloc[-1]
    prev = periodos["venta_diaria"].iloc[-2]
    return ((actual - prev) / prev) * 100 if prev != 0 else 0.0


def resumen_con_deltas(df: pd.DataFrame) -> Dict[str, Tuple[float, float]]:
    """Versión optimizada: un solo pase de agregación para los valores base."""
    if df.empty:
        return {
            "venta_total": (0.0, 0.0),
            "transacciones": (0, 0.0),
            "ticket_promedio": (0.0, 0.0),
            "cantidad_items": (0, 0.0),
            "dias_venta": (0, 0.0),
            "venta_diaria": (0.0, 0.0),
        }

    # Un solo pase para los valores base (evita 6 groupby separados)
    vt = float(df["T. ITEM S/."].sum())
    vv = float(df["T. ITEM S/."].sum())
    trans = int(df["TRANSACCIONES"].sum())
    cant = int(df["CANTIDAD"].sum())
    dias = int(df["Fecha"].nunique()) if "Fecha" in df.columns else int(df["F. VENTA"].dt.date.nunique())
    ticket = vt / trans if trans > 0 else 0.0
    v_diaria = vv / dias if dias > 0 else 0.0

    # Deltas (estos sí necesitan groupby por Periodo, pero son rápidos)
    d_ventas = crecimiento_ventas(df)
    d_trans = crecimiento_transacciones(df)
    d_ticket = crecimiento_ticket(df)
    d_cant = crecimiento_cantidad(df)
    d_vdiaria = crecimiento_venta_diaria(df)

    return {
        "venta_total": (vt, d_ventas),
        "transacciones": (trans, d_trans),
        "ticket_promedio": (ticket, d_ticket),
        "cantidad_items": (cant, d_cant),
        "dias_venta": (dias, 0.0),
        "venta_diaria": (v_diaria, d_vdiaria),
    }


# ── Análisis Pareto ─────────────────────────────────────────────────

def calculate_pareto(
    df: pd.DataFrame,
    value_col: str,
    key_col: str,
) -> pd.DataFrame:
    """
    Calcula análisis Pareto 80/20.
    """
    if df.empty: return pd.DataFrame()

    pareto = (
        df.groupby(key_col, observed=True)[value_col]
        .sum()
        .reset_index()
        .sort_values(value_col, ascending=False)
    )
    
    pareto["cumulative_sum"] = pareto[value_col].cumsum()
    total = pareto[value_col].sum()
    
    pareto["cumulative_percent"] = (
        (pareto["cumulative_sum"] / total) * 100 if total > 0 else 0
    )

    # Vectorizado 80/20
    # Marcamos donde se cruza el umbral
    # En realidad queremos "Top 80%" para todos los acumulados <= 80
    # Y el primer producto que se pase es el de corte.
    # Pero simplificamos: acumulado < 80 es Top.
    
    pareto["classification"] = np.where(
        pareto["cumulative_percent"] <= 80,
        "Top 80%",
        "Resto 20%"
    )
    
    # Ajuste fino: el primer producto que cruza 80 también suele considerarse del grupo A
    # Pero con lógica simple > 80 funciona bien para visualización.
    
    return pareto
