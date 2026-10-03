"""
intranet_db.py
================
Módulo cliente para consultar/modificar datos de Intranet (Cialta S.A.S)
SIN necesitar credenciales de SQL Server.

CÓMO USARLO EN UN PROYECTO NUEVO
---------------------------------
1. Copia este archivo (intranet_db.py) dentro de tu proyecto.
2. Copia también el archivo cert.pem en la misma carpeta (o en una
   subcarpeta llamada "certs").
3. Instala la única dependencia que necesita:
       pip install requests
4. Úsalo así:

    from intranet_db import IntranetDB

    # Por defecto conecta a PRODUCCIÓN (con el usuario/permisos que te
    # hayan asignado - normalmente solo lectura, o escritura en tablas
    # puntuales de tu módulo, nunca en usuarios).
    db = IntranetDB(usuario="TU_USUARIO_INTRANET", password="TU_CLAVE")

    # Si estás desarrollando y quieres trabajar contra la BD de PRUEBAS
    # (copia separada, sin riesgo para datos reales), solo agrega:
    db = IntranetDB(usuario="TU_USUARIO_INTRANET", password="TU_CLAVE", entorno="pruebas")

    # Ver qué tablas tienes disponibles:
    print(db.tablas_disponibles())

    # Consultar datos:
    empleados = db.consultar("Empldos", limite=50)

    # Consultar un solo registro:
    uno = db.obtener("Empldos", 938)

    # Insertar (solo en tablas habilitadas para escritura):
    db.insertar("PruebasDev", {"Descripcion": "prueba"})

    # Actualizar:
    db.actualizar("PruebasDev", 1, {"Descripcion": "prueba editada"})

    # Eliminar:
    db.eliminar("PruebasDev", 1)

IMPORTANTE PARA EL DESARROLLADOR
---------------------------------
- Este archivo NO contiene ninguna contraseña de base de datos.
- Te autenticas con tu propio usuario y clave de Intranet (el mismo
  que usas en los demás sistemas de la compañía). Cada acción queda
  registrada con tu usuario en el servidor.
- Solo puedes ver/editar las tablas que el área de Sistemas haya
  habilitado explícitamente para tu grupo. Si necesitas una tabla
  que no aparece en tablas_disponibles(), pide que la habiliten.
- No intentes ni necesitas conocer la IP ni el usuario de SQL Server:
  todo pasa por esta API, protegida con HTTPS y autenticación.
"""
import os
import requests

# URLs de la API interna, según el entorno. "produccion" es la BD real de
# Cialta (usar con cuidado); "pruebas" es una copia separada pensada para
# desarrollo activo, sin riesgo para datos reales.
# Si en algún momento no existe todavía la instancia de pruebas, deja
# ENTORNOS["pruebas"] apuntando al mismo valor que "produccion" por ahora.
ENTORNOS = {
    "produccion": "https://200.150.50.84:8001",
    "pruebas": "https://200.150.50.84:8002",   # instancia de pruebas, otro puerto
}
API_URL = ENTORNOS["produccion"]

_CERT_CANDIDATOS = [
    "cert.pem",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert.pem"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs", "cert.pem"),
]


def _ruta_certificado() -> str:
    for ruta in _CERT_CANDIDATOS:
        if os.path.isfile(ruta):
            return ruta
    raise FileNotFoundError(
        "No se encontró 'cert.pem'. Colócalo junto a intranet_db.py "
        "o dentro de una carpeta 'certs/' al lado de este archivo."
    )


class IntranetDB:
    """Cliente sencillo para el módulo de datos genéricos de la API Intranet."""

    def __init__(self, usuario: str, password: str, entorno: str = "produccion", api_url: str = None):
        """
        entorno: "produccion" o "pruebas" (ver diccionario ENTORNOS arriba).
        api_url: si se indica, ignora "entorno" y usa esta URL directamente
                 (útil si tu equipo levanta una tercera instancia propia).
        """
        if api_url:
            self._api_url = api_url.rstrip("/")
        elif entorno in ENTORNOS:
            self._api_url = ENTORNOS[entorno].rstrip("/")
        else:
            raise ValueError(f"Entorno desconocido: '{entorno}'. Usa uno de {list(ENTORNOS)}")

        self._cert = _ruta_certificado()
        self._token = self._login(usuario, password)

    # ---------- interno ----------

    def _login(self, usuario: str, password: str) -> str:
        r = requests.post(
            f"{self._api_url}/auth/login",
            data={"username": usuario, "password": password},
            verify=self._cert,
            timeout=10,
        )
        if r.status_code == 401:
            raise PermissionError("Usuario o contraseña incorrectos")
        r.raise_for_status()
        return r.json()["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    # ---------- API pública ----------

    def tablas_disponibles(self) -> list:
        r = requests.get(
            f"{self._api_url}/datos/tablas", headers=self._headers(),
            verify=self._cert, timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def consultar(self, tabla: str, limite: int = 100, offset: int = 0) -> list:
        r = requests.get(
            f"{self._api_url}/datos/{tabla}",
            params={"limite": limite, "offset": offset},
            headers=self._headers(), verify=self._cert, timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def consultar_todo(self, tabla: str, tamano_pagina: int = 1000) -> list:
        """Trae TODOS los registros de una tabla, paginando automáticamente.

        La API limita cada llamada a un máximo de 1000 registros (para no
        saturar el servidor con una sola consulta gigante), así que este
        método hace varias llamadas por debajo y las une. Úsalo cuando
        necesites la tabla completa, no solo una página.
        """
        registros = []
        offset = 0
        while True:
            pagina = self.consultar(tabla, limite=tamano_pagina, offset=offset)
            registros.extend(pagina)
            if len(pagina) < tamano_pagina:
                break  # ya no hay más páginas
            offset += tamano_pagina
        return registros

    def obtener(self, tabla: str, valor_clave):
        r = requests.get(
            f"{self._api_url}/datos/{tabla}/{valor_clave}",
            headers=self._headers(), verify=self._cert, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def insertar(self, tabla: str, datos: dict) -> dict:
        r = requests.post(
            f"{self._api_url}/datos/{tabla}", json=datos,
            headers=self._headers(), verify=self._cert, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def actualizar(self, tabla: str, valor_clave, datos: dict) -> dict:
        r = requests.put(
            f"{self._api_url}/datos/{tabla}/{valor_clave}", json=datos,
            headers=self._headers(), verify=self._cert, timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def eliminar(self, tabla: str, valor_clave) -> bool:
        r = requests.delete(
            f"{self._api_url}/datos/{tabla}/{valor_clave}",
            headers=self._headers(), verify=self._cert, timeout=15,
        )
        r.raise_for_status()
        return True

    @classmethod
    def desde_token(cls, token: str, entorno: str = "produccion", api_url: str = None):
        """Reconstruye un cliente ya autenticado a partir de un token JWT
        existente, sin volver a llamar a /auth/login.

        Pensado para apps web (Flask/FastAPI) que guardan el token en la
        sesión del usuario: en cada request solo hace falta reconstruir
        el cliente con el token que ya se obtuvo al iniciar sesión, en
        vez de pedirle usuario/clave de nuevo en cada clic.
        """
        instancia = cls.__new__(cls)
        if api_url:
            instancia._api_url = api_url.rstrip("/")
        elif entorno in ENTORNOS:
            instancia._api_url = ENTORNOS[entorno].rstrip("/")
        else:
            raise ValueError(f"Entorno desconocido: '{entorno}'. Usa uno de {list(ENTORNOS)}")
        instancia._cert = _ruta_certificado()
        instancia._token = token
        return instancia


if __name__ == "__main__":
    # Prueba rápida manual: python intranet_db.py
    usuario = input("Usuario Intranet: ")
    import getpass
    password = getpass.getpass("Contraseña: ")

    db = IntranetDB(usuario, password)
    print("\nTablas disponibles para tu usuario:")
    for t in db.tablas_disponibles():
        print(" -", t["tabla"], "| lectura:", t["lectura"], "| escritura:", t["escritura"])
