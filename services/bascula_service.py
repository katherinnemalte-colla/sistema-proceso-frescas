"""
Servicio de báscula.

Centraliza la obtención del peso neto: usa la lectura real de la báscula
cuando esté conectada, y mientras tanto genera un peso aleatorio de prueba.
Funciona como singleton para que el mismo peso se comparta entre
ficha_tecnica.py y frescas_100x45.py sin generarlo dos veces.
"""

import random
from typing import Optional


class BasculaService:
    def __init__(self):
        self._ultimo_peso: Optional[float] = None

    def leer_bascula(self) -> Optional[float]:
        """
        Lectura real del hardware (puerto serie/USB/etc).
        Por ahora retorna None porque la báscula física no está conectada.
        """
        # TODO: reemplazar con la lectura real, por ejemplo:
        # return self._leer_puerto_serie()
        return None

    def obtener_peso_neto(self, forzar_nuevo: bool = False) -> float:
        """
        Devuelve el peso neto actual.
        Si ya se calculó uno y no se fuerza, reutiliza el mismo (para que
        ficha_tecnica.py y frescas_100x45.py coincidan).
        """
        if forzar_nuevo or self._ultimo_peso is None:
            peso_bascula = self.leer_bascula()
            if peso_bascula is not None:
                self._ultimo_peso = round(float(peso_bascula), 3)
            else:
                self._ultimo_peso = round(random.uniform(0.5, 8.0), 3)
        return self._ultimo_peso

    def obtener_ultimo_peso(self) -> Optional[float]:
        """Devuelve el último peso ya calculado, sin generar uno nuevo."""
        return self._ultimo_peso

    def reiniciar(self) -> None:
        """Limpia el peso guardado (por ejemplo, al abrir una ficha nueva)."""
        self._ultimo_peso = None


# Instancia única compartida por toda la aplicación
bascula_service = BasculaService()