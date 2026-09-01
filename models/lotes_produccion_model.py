from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Lotes_produccion:
    lote: str
    fecha_produccion: Optional[date] = None
    numEspecie: Optional[int] = None
    especie: Optional[str] = None