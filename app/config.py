
"""
config.py – Configuración centralizada de la aplicación.
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List

# ─── Rutas ───────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR
CSV_FILENAME = "DATA Ventas detallado x farmacia - Feb 26.csv"
CSV_PATH = DATA_DIR / CSV_FILENAME

# ─── SQL Server (opcional, se usa si CSV no está disponible) ─────────
SQL_SERVER_DRIVER = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")
SQL_SERVER_HOST = os.getenv("SQL_HOST", "localhost")
SQL_SERVER_DB = os.getenv("SQL_DB", "ERP_FHIN")
SQL_SERVER_USER = os.getenv("SQL_USER", "")
SQL_SERVER_PASS = os.getenv("SQL_PASS", "")

# ─── Tipos de Datos (Optimización de Memoria) ────────────────────────
# Definir tipos para pd.read_csv mejora rendimiento y uso de memoria
COLUMN_DTYPES = {
    "Unidad": "category",
    "Año": "int16",  # Ahorra memoria vs int64 default
    "Mes": "int8",
    "Semana": "int8",
    "Dia": "category",
    "Dia 2": "int8",
    "Hora": "int8",
    "TRANSACCIONES": "float32",
    "HORA": "object", # Hora como string HH:MM
    "CONDI. VENTA": "category",
    "COD. DOCU": "category",
    "DOCUMENTO": "object",
    "VENDEDOR": "category",
    "CODIGO": "category", # Muchos códigos repetidos
    "DESCRIPCION": "object",
    "LABORATORIO": "category",
    "CANTIDAD": "float32",
    "T. ITEM S/.": "float32",
    "TOTAL  S/": "float32",
    "FORMA DE PAGO": "category",
    "COBRADO S/.": "float32",
    "LINEA DE NEGOCIO": "category",
    "CATEGORIA 1": "category",
    "CATEGORIA 2": "category",
    "VALOR VENDIDO": "float32",
    "INCENTIVO": "float32",
    "CANAL": "category",
    "ORIGEN VENTA": "category",
}

# Columnas con fechas para parsear
DATE_COLUMNS = ["F. VENTA"]

# ─── Columnas obligatorias para validación ───────────────────────────
REQUIRED_COLUMNS = list(COLUMN_DTYPES.keys()) + DATE_COLUMNS

# ─── Tema visual ─────────────────────────────────────────────────────
@dataclass
class ThemeConfig:
    """Paleta de colores empresarial."""
    primary: str = "#0D47A1"
    secondary: str = "#1565C0"
    accent: str = "#00BFA5"
    success: str = "#00C853"
    warning: str = "#FFD600"
    danger: str = "#FF1744"
    bg_dark: str = "#0A1929"
    bg_card: str = "#132F4C"
    text_primary: str = "#FFFFFF"
    text_secondary: str = "#B0BEC5"
    chart_colors: list = field(default_factory=lambda: [
        "#00BFA5", "#1E88E5", "#7C4DFF", "#FF6D00",
        "#F50057", "#00E5FF", "#76FF03", "#FFD600",
    ])

THEME = ThemeConfig()

# ─── Metas mensuales por defecto (S/) ────────────────────────────────
DEFAULT_METAS: Dict[str, float] = {
    "Cruz 1": 250_000.0,
    "Cruz 2": 220_000.0,
    "Cruz 3": 200_000.0,
    "Desamparados": 180_000.0,
    "Juliaca 1": 230_000.0,
    "Juliaca 2": 210_000.0,
}

# ─── Formatos ────────────────────────────────────────────────────────
CURRENCY_FORMAT = "S/ {:,.2f}"
PERCENT_FORMAT = "{:.1f}%"
NUMBER_FORMAT = "{:,.0f}"

# ─── Semáforo de cumplimiento ────────────────────────────────────────
SEMAFORO = {
    "verde": 0.90,   # >= 90%
    "amarillo": 0.70, # >= 70%
    # < 70% = rojo
}
