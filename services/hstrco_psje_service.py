from repositories.hstrco_psje_repository import guardar_historico_pesaje


def registrar_historico_pesaje(parametros_etiqueta: dict, oprdor: str = "", nmro_psta: int = 0) -> None:
    producto = parametros_etiqueta.get("producto")
    cdgo_plu = getattr(producto, "cdgo_plu", 0) if producto else 0
    nmbre_plu = getattr(producto, "nom_prog", "") if producto else ""
    es_cong = parametros_etiqueta.get("tipo_conservacion") == "congelado"
    fecha_vto = parametros_etiqueta.get("fecha_vencimiento_str")

    datos = {
        
        "cdgo_plu": cdgo_plu,
        "nmbre_plu": nmbre_plu,
        "nmro_lte": parametros_etiqueta.get("lote", 0),
        "fcha_prdccion": parametros_etiqueta.get("fecha_produccion", "1900-01-01"),
        "fcha_vnce_ref": None if es_cong else fecha_vto,
        "fcha_vnce_cong": fecha_vto if es_cong else None,
        "fcha_scrfcio": parametros_etiqueta.get("fecha_sacrificio", "1900-01-01"),
        "pso_nto": parametros_etiqueta.get("peso_bascula", 0),
        "cdgo_emprsa": parametros_etiqueta.get("cod_empresa", 0),
        "tpo_lmpza": parametros_etiqueta.get("tipo_limpieza_seleccionado", 0),
        "oprdor": oprdor,
        "nmro_psta": nmro_psta,
    }
    guardar_historico_pesaje(datos)