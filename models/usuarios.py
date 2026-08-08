"""
Modelo de datos: representa una fila de la tabla `usuarios`.
NO contiene consultas SQL. Solo define la estructura de los datos.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Usuario:
    nombre_usuario: str
    clave_hash: str          # nunca guardar la clave en texto plano
    nombre_completo: str
    activo: int = 1
    codigo_departamento: Optional[int] = None

    def __repr__(self) -> str:
        # Evitamos mostrar la clave_hash aunque sea un hash, por buena práctica
        return f"Usuario(nombre_usuario='{self.nombre_completo}', activo={self.activo})"