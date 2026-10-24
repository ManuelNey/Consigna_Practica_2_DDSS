"""
Genero imagen_con_script_oculto.jpg a partir de afiche_valido.jpg.
Copio la imagen tal cual y le agrego un script al final del archivo.
La imagen sigue siendo valida porque el decoder deja de leer cuando
encuentra el marcador de fin de imagen, antes de llegar al script.
"""
from pathlib import Path

CARPETA_DESTINO = Path(__file__).parent.parent  # carpeta archivos_prueba/
SCRIPT_A_PEGAR = b"<script>alert('Soy un script metido en una imagen')</script>"

if __name__ == "__main__":
    afiche_original = CARPETA_DESTINO / "afiche_valido.jpg"

    # Primero reviso que la imagen original exista.
    if not afiche_original.exists():
        raise FileNotFoundError(
            "Falta afiche_valido.jpg en archivos_prueba/: hay que poner "
            "la foto real de Avengers antes de correr este script."
        )

    # Leo los bytes originales sin modificar ni comprimir la imagen.
    contenido_imagen = afiche_original.read_bytes()

    # Agrego el script al final y guardo el archivo nuevo.
    (CARPETA_DESTINO / "imagen_con_script_oculto.jpg").write_bytes(
        contenido_imagen + SCRIPT_A_PEGAR
    )

    print("imagen_con_script_oculto.jpg generado en", CARPETA_DESTINO)