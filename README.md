# Voice AI — starter para doblaje de vídeo

Aplicación web móvil instalable (PWA) para preparar proyectos de doblaje con IA.

## Estado real
Esta entrega es un **prototipo funcional de interfaz**, no un servicio de doblaje terminado. Permite cargar y previsualizar vídeos, elegir modo, idioma, voz y resolución, y enviar un trabajo al backend. El backend actual recibe el archivo y crea un registro temporal en memoria; todavía no ejecuta transcripción, separación de audio, síntesis de voz ni renderizado final.

## Incluye
- Interfaz en español, adaptable a móvil.
- Carga de MP4, MOV y WebM y previsualización local.
- Modos de doblaje automático y con guion aportado por el usuario.
- Selección de voz, idioma y resolución (original, 1080p, 4K).
- Opción para conservar música y efectos (pendiente de integración real).
- PWA instalable.
- API FastAPI básica para crear y consultar trabajos.

## Ejecutar la interfaz
Abre `public/index.html` en un servidor estático. Por ejemplo, desde la carpeta del proyecto:
```bash
python -m http.server 8080 --directory public
```
Visita `http://localhost:8080`.

## Ejecutar el backend
Requiere Python 3.11+:
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```
La API queda en `http://127.0.0.1:8000`; documentación en `/docs`.

## Para convertirlo en un doblador real
Hay que integrar proveedores de transcripción y TTS, separación de voz/música, almacenamiento persistente, cola de trabajos y FFmpeg. Los trabajos largos (hasta una hora) deben procesarse en un servidor, no solo en el móvil. Las claves de API deben guardarse en el servidor, nunca en JavaScript del navegador.

La exportación 4K no recupera detalle que no exista en el vídeo original.
