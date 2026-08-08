"""
Repositorio de usuarios: es la ÚNICA capa que conoce el SQL de la tabla `usuarios`.
El resto del sistema (services, ui) nunca escribe una consulta directamente;
siempre pasa por estas funciones.
"""

from typing import Optional
from models.database import obtener_conexion
from models.usuarios import Usuario


def buscar_por_nombre_usuario(nombre_usuario: str) -> Optional[Usuario]:
    consulta = """
        SELECT u.nombr_usua,
               u.contr_usua,
                 u.descr_usua, u.estdo, u.cdgo_dep  FROM usuarios u
        WHERE u.nombr_usua = ?
    """
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        # El "?" evita SQL injection: nunca concatenar el valor directo en el string
        cursor.execute(consulta, nombre_usuario)
        fila = cursor.fetchone()

        if fila is None:
            return None

        return Usuario(
            nombre_usuario=fila.nombr_usua,
            clave_hash=fila.contr_usua,
            nombre_completo=fila.descr_usua,
            activo=fila.estdo,
            codigo_departamento=fila.cdgo_dep,
        )

#u.actlzcion
def actualizar_ultimo_acceso(usuario_id: str) -> None:
    consulta = """
        UPDATE usuarios
        SET ultimo_acceso = GETDATE()
        WHERE id = ?
    """
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(consulta, usuario_id)
        conn.commit()