from dataclasses import dataclass
from models.database import obtener_conexion


@dataclass
class ConsecutivoParametros:
    tabla: str
    tabla_eva: str
    campo_eva: str
    proceso: int = 0


class ConsecutivoRepository:

    def obtener_consecutivo(self, params: ConsecutivoParametros) -> int:
        sql = """
            DECLARE @Resultado INT;
            EXEC [dbo].[CONSECUTIVO_SQL]
                @cTabla = ?,
                @cTablaEva = ?,
                @cCampoEva = ?,
                @cProceso = ?,
                @nUltimo = @Resultado OUTPUT;
            SELECT @Resultado AS nUltimo;
        """

        with obtener_conexion() as conexion:
            cursor = conexion.cursor()
            try:
                cursor.execute(
                    sql,
                    params.tabla,
                    params.tabla_eva,
                    params.campo_eva,
                    params.proceso,
                )
                fila = cursor.fetchone()

                if fila is None or fila.nUltimo is None:
                    raise ValueError(
                        "CONSECUTIVO_SQL no devolvió un valor para nUltimo."
                    )

                return int(fila.nUltimo)
            finally:
                cursor.close()