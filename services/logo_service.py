from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw


@lru_cache(maxsize=1)
def obtener_logo_png() -> bytes:
    ruta_logo = Path(__file__).resolve().parent.parent / "img" / "image.png"
    with Image.open(ruta_logo) as imagen:
        imagen = imagen.convert("RGBA")
        mascara = Image.new("L", imagen.size, 0)
        ImageDraw.Draw(mascara).ellipse(
            (1, 1, imagen.width - 2, imagen.height - 2),
            fill=255,
        )
        imagen.putalpha(mascara)

        salida = BytesIO()
        imagen.save(salida, format="PNG", optimize=True)
        return salida.getvalue()
