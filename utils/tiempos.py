import logging
import time
from contextlib import contextmanager
import functools

@contextmanager
def medir(etiqueta: str):
    inicio = time.perf_counter()
    try:
        yield
    finally:
        duracion = time.perf_counter() - inicio
        logging.info("[TIEMPO] %s: %.2f s", etiqueta, duracion)
        print(f"[TIEMPO] {etiqueta}: {duracion:.2f} s")

def cronometrar(funcion):
    @functools.wraps(funcion)
    def envoltura(*args, **kwargs):
        with medir(funcion.__qualname__):
            return funcion(*args, **kwargs)
    return envoltura