import getpass
from intranet_db import IntranetDB

usuario = input("Usuario Intranet: ").strip()
password = getpass.getpass("Contraseña: ")

db = IntranetDB(usuario="sugeyk", password="Maka123", entorno="pruebas")

tablas = db.tablas_disponibles()
print(f"\n{len(tablas)} tablas disponibles:\n")
for t in tablas:
    print(f"{t['tabla']:<35} {t['base_datos']:<20} "
          f"lectura={t['lectura']}  escritura={t['escritura']}")