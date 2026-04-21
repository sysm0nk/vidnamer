# 🎬 Vidnamer -> Video Renamer con IA

<img width="409" height="405" alt="image" align="center" display="block" src="https://github.com/user-attachments/assets/fc680fdd-c8ff-4201-83da-37a61724a54b" />
<br/>

Renombra automáticamente tus videos usando Google Gemini. El script analiza frames de cada video y sugiere nombres descriptivos con el formato `sujeto-accion-lugar`.

**No renombra los archivos directamente** — genera un script bash para que lo revises y ejecutes vos. ✅

---

## ¿Cómo funciona?

1. Extrae 3 frames clave de cada video (al 10%, 50% y 90% de su duración)
2. Los envía a Gemini para obtener un nombre descriptivo
3. Genera un script `ejecutar_renombrado.sh` con los comandos `mv` listos

```
VID_20240815_103022.mp4  →  perro-corriendo-parque.mp4
clip_final_v3.mov        →  nino-saltando-pileta.mov
```


<img width="1284" height="811" alt="image" src="https://github.com/user-attachments/assets/409d88ac-93d5-41f1-8c37-e5244fe38dfc" />




---
## Requisitos
- GNU/Linux 🐧
- Python 🐍

---
## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/sysm0nk/vidnamer.git
cd vidnamer
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar la API Key

Conseguí tu API Key gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).

```bash
cp .env.example .env
# Editá .env y pegá tu clave
```

O exportala directamente en tu terminal:

```bash
export GEMINI_API_KEY="tu_clave_aqui"
```

---

## Uso

### Uso básico

```bash
python rename_videos.py
```

Procesa todos los `.mp4`, `.mov` y `.mkv` dentro de `./mis_videos/`.

### Opciones disponibles

```
python rename_videos.py [--dir CARPETA] [--model MODELO] [--dry-run] [--output ARCHIVO]
```

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--dir` | `./mis_videos` | Carpeta con los videos |
| `--model` | `gemini-flash-lite-latest` | Modelo Gemini a usar |
| `--dry-run` | `False` | Muestra sugerencias sin generar el .sh |
| `--context` | `context.txt` |Archivo .txt con contexto personal (personas, mascotas, lugares) |

### Ejemplos

```bash
# Analizar una carpeta específica
python rename_videos.py --dir ~/Videos/vacaciones

# Ver sugerencias sin generar el script (modo prueba)
python rename_videos.py --dry-run

# Usar un modelo diferente
python rename_videos.py --model gemini-2.0-flash

# Todo junto
python rename_videos.py --dir ~/Videos --dry-run --model gemini-2.0-flash
```

### Usar contexto personal

Si tus videos tienen personas, mascotas o lugares que querés que la IA reconozca, creá un archivo de contexto:

```bash
cp context.example.txt context.txt
# Editá context.txt con tus descripciones
```

```text
Si ves una mujer alta de pelo rubio es Carmen
Si ves un niño de 8 años es Gerónimo
Si ves un perro golden retriever es Bobby
Si el ambiente parece tropical con palmeras es Brasil
```

Luego usá el flag `--context`:

```bash
python rename_videos.py --dir ~/Videos --context context.txt
```

Resultado con contexto vs sin contexto:

```
Sin contexto:  mujer-corriendo-parque.mp4
Con contexto:  carmen-corriendo-parque.mp4
```

> `context.txt` está en el `.gitignore` para proteger tu privacidad.

### Ejecutar el renombrado

Una vez revisado el script generado:

```bash
bash ejecutar_renombrado.sh
```

---

## Ejemplo de salida

```
🎬 Video Renamer — Modelo: gemini-flash-lite-latest
   Carpeta: /home/usuario/mis_videos
   Videos encontrados: 4

Procesando videos: 100%|████████████| 4/4 [00:32<00:00]
  → Analizando: VID_001.mp4
  ✓ Sugerido: gato-durmiendo-sofa.mp4
  → Analizando: clip_playa.mov
  ✓ Sugerido: familia-nadando-mar.mov

──────────────────────────────────────────────────
✅ 4 video(s) procesados.

📄 Script generado: ejecutar_renombrado.sh
   Ejecutalo con: bash ejecutar_renombrado.sh
```

---

## Notas

- El Free Tier de Gemini permite ~15 requests por minuto. El script espera 5s entre videos automáticamente.
- Si recibís error 429 (cuota excedida), el script espera 60 segundos y continúa.
- Los archivos temporales se limpian automáticamente al finalizar.

---

## Modelos recomendados

| Modelo | Velocidad | Notas |
|--------|-----------|-------|
| `gemini-flash-lite-latest` | ⚡ Muy rápido | Recomendado, estable en producción |
| `gemini-2.0-flash` | ⚡ Rápido | Mejor calidad de análisis |
| `gemini-1.5-pro` | 🐢 Más lento | Mayor precisión, más costoso |

---

## Licencia

MIT
