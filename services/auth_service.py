"""
Lógica de negocio del login.
La ventana de Qt (ui) llama SOLO a esta función; nunca toca el repositorio
ni la base de datos directamente.
"""
import base64
#import bcrypt
from typing import Optional
from models.usuarios import Usuario
from repositories import usuarios_repository


def autenticar(nombre_usuario: str, clave_ingresada: str) -> Optional[Usuario]:
    """
    Devuelve el Usuario si las credenciales son correctas y está activo.
    Devuelve None si el login falla (usuario no existe, clave incorrecta o inactivo).
    """
    usuario = usuarios_repository.buscar_por_nombre_usuario(nombre_usuario)

    if usuario is None:
        return None

    if not usuario.activo:
        return None

    clave_decodificada = base64.b64decode(usuario.clave_hash).decode("utf-8")

    if clave_ingresada != clave_decodificada:
        return None

    return usuario

    #clave_valida = bcrypt.checkpw(
    #    clave_ingresada.encode("utf-8"),
    #    usuario.clave_hash.encode("utf-8"),
    #)

    #if not clave_valida:
    #    return None

    #usuarios_repository.actualizar_ultimo_acceso(usuario.nombre_usuario)
    #return usuario