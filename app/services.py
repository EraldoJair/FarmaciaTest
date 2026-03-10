
"""
services.py – Capa de orquestación y lógica de negocio (Singleton).

Maneja carga de datos,filtrado, cálculo de KPIs y persistencia de metas.
Optimizado con ST Cache Resource.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import streamlit as st

from app.config import DATA_DIR, DEFAULT_METAS
from app.data_loader import cargar_datos_csv
from app import transformations, kpis


class AnalyticsService:
    """Servicio central para manejo de datos y lógica de negocio."""

    def __init__(self):
        self._df_raw: Optional[pd.DataFrame] = None
        self._df: Optional[pd.DataFrame] = None
        self.metas_path = DATA_DIR / "goals.json"
        self.metas_df: pd.DataFrame = pd.DataFrame()
        self._cargar_metas_iniciales()

    def cargar(self, ruta: Optional[str] = None) -> pd.DataFrame:
        """Carga y enriquece los datos iniciales."""
        try:
            self._df_raw = cargar_datos_csv(ruta)
            self._df = transformations.enriquecer_datos(self._df_raw)
            return self._df
        except Exception as e:
            st.error(f"Error crítico cargando datos: {e}")
            raise e

    @property
    def datos(self) -> pd.DataFrame:
        """Devuelve el DataFrame procesado. Carga si es necesario."""
        if self._df is None:
            self.cargar()
        return self._df

    # ── Metas ────────────────────────────────────────────────────────
    def _cargar_metas_iniciales(self) -> None:
        """Carga metas desde JSON o crea defecto."""
        if self.metas_path.exists():
            try:
                with open(self.metas_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.metas_df = pd.DataFrame(data)
            except Exception as e:
                st.warning(f"No se pudo cargar metas.json: {e}")
                self.metas_df = pd.DataFrame()
        else:
            # Crear metas default basadas en config
            rows = []
            import datetime
            anio_actual = datetime.date.today().year
            
            for farmacia, monto_mensual in DEFAULT_METAS.items():
                for mes in range(1, 13):
                    rows.append({
                        "Unidad": farmacia,
                        "Anio": anio_actual,
                        "Mes": mes,
                        "Meta": monto_mensual
                    })
            self.metas_df = pd.DataFrame(rows)
            # Intentar guardar
            self.guardar_metas(self.metas_df)

    def guardar_metas(self, df_nuevas: pd.DataFrame) -> None:
        """Guarda nuevas metas y actualiza estado."""
        self.metas_df = df_nuevas
        try:
            # Convertir a dict records para json
            data = df_nuevas.to_dict(orient="records")
            with open(self.metas_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            st.error(f"Error guardando metas: {e}")

    def cargar_metas(self) -> None:
        """Recarga forzada de metas (alias de iniciales)."""
        self._cargar_metas_iniciales()


    # ── Métodos Proxy a KPIs (Fachada) ───────────────────────────────
    # Mantienen la interfaz limpia para la UI

    def resumen_ejecutivo(self, df: pd.DataFrame) -> Dict[str, Any]:
        return kpis.resumen_con_deltas(df)

    def cumplimiento(self, df: pd.DataFrame) -> pd.DataFrame:
        # Calcular cumplimiento usando metas cargadas
        # Filtrar metas relevantes al df pasado (mismo año/mes) es hecho dentro de kpis
        return kpis.calcular_cumplimiento(df, self.metas_df)

    def calcular_cumplimiento(self, df: pd.DataFrame, metas: pd.DataFrame) -> pd.DataFrame:
        return kpis.calcular_cumplimiento(df, metas)

    def comparativo(self, df: pd.DataFrame) -> pd.DataFrame:
        return kpis.comparativo_farmacias(df, self.metas_df)

    def mix_negocio(self, df: pd.DataFrame) -> pd.DataFrame:
        return kpis.mix_linea_negocio(df)

    def crecimiento(self, df: pd.DataFrame) -> pd.DataFrame:
        return kpis.crecimiento_periodos(df)
    
    def top_productos(self, df: pd.DataFrame, n=10) -> pd.DataFrame:
        return transformations.top_productos(df, n)

    def top_vendedores(self, df: pd.DataFrame, n=10) -> pd.DataFrame:
        return transformations.top_vendedores(df, n)

    def heatmap_dia_hora(self, df: pd.DataFrame) -> pd.DataFrame:
        return transformations.agrupar_dia_hora(df)

    def dist_forma_pago(self, df: pd.DataFrame) -> pd.DataFrame:
        return transformations.distribucion_forma_pago(df)

    def ventas_por_fecha(self, df: pd.DataFrame) -> pd.DataFrame:
        return transformations.agrupar_por_fecha(df)
        
    def ventas_farmacia_fecha(self, df: pd.DataFrame) -> pd.DataFrame:
        return transformations.agrupar_por_farmacia_fecha(df)


# ── Singleton Pattern (Streamlit Safe) ───────────────────────────────
@st.cache_resource(show_spinner=False)
def get_service() -> AnalyticsService:
    """Obtiene la instancia única del servicio (Singleton)."""
    return AnalyticsService()
