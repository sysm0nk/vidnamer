import sys
import os
import shutil
import time
import argparse
import cv2
from google import genai
from PIL import Image
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()  # Carga automáticamente el archivo .env si existe

# --- CONFIGURACIÓN ---
VIDEO_DIR_DEFAULT = "./mis_videos"
TEMP_DIR = "./temp_frames"
PERCENTAGES = [0.1, 0.5, 0.9]
OUTPUT_SH = "ejecutar_renombrado.sh"
MODEL_NAME = "gemini-flash-lite-latest"


def parse_args():
    parser = argparse.ArgumentParser(
        description="🎬 Renombrador automático de videos con IA (Gemini)",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--dir",
        default=VIDEO_DIR_DEFAULT,
        help=f"Carpeta con los videos a analizar (default: {VIDEO_DIR_DEFAULT})"
    )
    parser.add_argument(
        "--model",
        default=MODEL_NAME,
        help=f"Modelo Gemini a usar (default: {MODEL_NAME})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra los renombres sugeridos sin generar el script .sh"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_SH,
        help=f"Nombre del script bash de salida (default: {OUTPUT_SH})"
    )
    parser.add_argument(
        "--context",
        default=None,
        metavar="ARCHIVO",
        help="Archivo .txt con contexto personal para identificar personas, mascotas y lugares"
    )
    return parser.parse_args()


def get_api_key():
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        print("[!] Error: No se encontró la API Key.")
        print("    Seteá la variable de entorno GEMINI_API_KEY o GOOGLE_API_KEY.")
        print("    Ejemplo: export GEMINI_API_KEY='tu_clave_aqui'")
        sys.exit(1)
    return key


def extract_frames(video_path, video_id):
    frames_pil = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_subfolder = os.path.join(TEMP_DIR, video_id)
    os.makedirs(video_subfolder, exist_ok=True)
    for i, p in enumerate(PERCENTAGES):
        frame_id = int(total_frames * p)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(video_subfolder, f"frame_{i}.jpg")
            # Redimensionamos a 720p para no saturar la cuota de tokens por minuto (TPM)
            frame = cv2.resize(frame, (1280, 720))
            cv2.imwrite(frame_path, frame)
            frames_pil.append(Image.open(frame_path))
    cap.release()
    return frames_pil


def load_context(context_path):
    """Carga el archivo de contexto personal y lo formatea para el prompt."""
    if not context_path:
        return ""
    if not os.path.isfile(context_path):
        print(f"[!] Advertencia: No se encontró el archivo de contexto '{context_path}'. Se ignorará.")
        return ""
    with open(context_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return ""
    return (
        "\n\nCONTEXTO PERSONAL (úsalo para identificar personas, mascotas y lugares):\n"
        + content
    )


def sanitize_name(text):
    """Limpia el texto sugerido para que sea un nombre de archivo válido."""
    result = text.strip().lower().replace(" ", "-")
    result = "".join(e for e in result if e.isalnum() or e == "-")
    # Eliminar guiones múltiples o al inicio/fin
    while "--" in result:
        result = result.replace("--", "-")
    return result.strip("-")


def unique_name(base_name, extension, used_names):
    """Evita colisiones de nombres agregando un sufijo numérico si es necesario."""
    candidate = f"{base_name}{extension}"
    counter = 2
    while candidate in used_names:
        candidate = f"{base_name}-{counter}{extension}"
        counter += 1
    return candidate


def main():
    args = parse_args()
    api_key = get_api_key()
    client = genai.Client(api_key=api_key)

    video_dir = args.dir
    if not os.path.isdir(video_dir):
        print(f"[!] Error: La carpeta '{video_dir}' no existe.")
        sys.exit(1)

    videos = [
        f for f in os.listdir(video_dir)
        if f.lower().endswith((".mp4", ".mov", ".mkv"))
    ]

    if not videos:
        print(f"[!] No se encontraron videos en '{video_dir}'.")
        sys.exit(0)

    context_snippet = load_context(args.context)

    print(f"\n🎬 Video Renamer — Modelo: {args.model}")
    print(f"   Carpeta: {os.path.abspath(video_dir)}")
    print(f"   Videos encontrados: {len(videos)}")
    if args.context and context_snippet:
        print(f"   Contexto: {args.context} ✓")
    if args.dry_run:
        print("   Modo: DRY RUN (no se generará el script .sh)\n")
    else:
        print()

    # Limpiar carpeta temporal al inicio
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

    commands = []
    used_names = set()
    base_prompt = "Analiza estos frames y sugiere un nombre corto: sujeto-accion-lugar. Solo minúsculas y guiones. Responde SOLO con el nombre, sin explicaciones."
    prompt = base_prompt + context_snippet

    try:
        for filename in tqdm(videos, desc="Procesando videos", unit="video"):
            video_id = os.path.splitext(filename)[0]
            video_path = os.path.join(video_dir, filename)
            extension = os.path.splitext(filename)[1]

            tqdm.write(f"  → Analizando: {filename}")
            frames = extract_frames(video_path, video_id)
            if not frames:
                tqdm.write(f"  ✗ No se pudo abrir: {filename}")
                continue

            MAX_RETRIES = 3
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    response = client.models.generate_content(
                        model=args.model,
                        contents=[prompt, *frames]
                    )

                    base_name = sanitize_name(response.text)
                    new_name = unique_name(base_name, extension, used_names)
                    used_names.add(new_name)

                    commands.append(f'mv -v "{filename}" "{new_name}"')
                    tqdm.write(f"  ✓ Sugerido: {new_name}")

                    # Rate limiting preventivo (Free Tier: ~15 RPM)
                    time.sleep(5)
                    break  # Éxito, salir del loop de reintentos

                except Exception as e:
                    if "429" in str(e):
                        tqdm.write("  ⚠ Cuota excedida. Esperando 60s...")
                        time.sleep(60)
                        # El 429 no cuenta como intento fallido, sigue reintentando
                    elif "503" in str(e) or "UNAVAILABLE" in str(e):
                        wait = 15 * attempt  # 15s, 30s, 45s
                        if attempt < MAX_RETRIES:
                            tqdm.write(f"  ⚠ Servicio no disponible. Reintento {attempt}/{MAX_RETRIES} en {wait}s...")
                            time.sleep(wait)
                        else:
                            tqdm.write(f"  ✗ Falló tras {MAX_RETRIES} intentos: {filename}")
                    else:
                        tqdm.write(f"  ✗ Error inesperado: {e}")
                        break  # Error desconocido, no reintentar

    finally:
        # Limpiar frames temporales siempre, incluso si hay error
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)

    if not commands:
        print("\n[!] No se generaron sugerencias.")
        sys.exit(0)

    print(f"\n{'─'*50}")
    print(f"✅ {len(commands)} video(s) procesados.\n")

    if args.dry_run:
        print("📋 Renombres sugeridos (dry run):")
        for cmd in commands:
            print(f"   {cmd}")
    else:
        output_path = args.output
        with open(output_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'cd "{os.path.abspath(video_dir)}" || exit\n\n')
            for cmd in commands:
                f.write(cmd + "\n")
        os.chmod(output_path, 0o755)
        print(f"📄 Script generado: {output_path}")
        print(f"   Ejecutalo con: bash {output_path}")


if __name__ == "__main__":
    main()
