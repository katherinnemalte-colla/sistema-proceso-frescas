from dataclasses import dataclass
from typing import Optional


@dataclass
class Lotes_produccion:
    lote: str
    fecha_produccion: Optional[str] = None
    numEspecie: Optional[int] = None
    especie: Optional[str] = None