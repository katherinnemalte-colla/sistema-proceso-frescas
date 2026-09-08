class Colores:
    """Paleta de colores centralizada para toda la aplicación."""

    # Colores principales
    PRIMARIO = "#1a6b6b"
    PRIMARIO_OSCURO = "#134f4f"
    PRIMARIO_CLARO = "#e6f2f2"

    # Estados
    SELECCIONADO = "#1a6b6b"

    # Neutros / estructura
    BORDE = "#dfe6e6"
    TEXTO_SECUNDARIO = "#8a97a0"
    FONDO = "#eef3f3"

    @classmethod
    def to_rgb(cls, hex_color: str) -> tuple[int, int, int]:
        """Convierte un color hex (#rrggbb) a una tupla RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def to_rgba_str(cls, hex_color: str, alpha: float = 1.0) -> str:
        """Devuelve un string rgba(...) usable en QSS/CSS."""
        r, g, b = cls.to_rgb(hex_color)
        return f"rgba({r}, {g}, {b}, {alpha})"

    @classmethod
    def aclarar(cls, hex_color: str, factor: float = 0.2) -> str:
        """Aclara un color mezclándolo con blanco (factor entre 0 y 1)."""
        r, g, b = cls.to_rgb(hex_color)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    @classmethod
    def oscurecer(cls, hex_color: str, factor: float = 0.2) -> str:
        """Oscurece un color mezclándolo con negro (factor entre 0 y 1)."""
        r, g, b = cls.to_rgb(hex_color)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f"#{r:02x}{g:02x}{b:02x}"