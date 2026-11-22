"""Servidor efímero PC -> móvil, independiente del importador QR existente.

Sólo comparte archivos expresamente elegidos en Revelo, sin nube, sin cambios en
los originales y sin explorar rutas arbitrarias desde el navegador del móvil.
"""
from __future__ import annotations

import html
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit
from zipfile import ZipFile, ZIP_STORED

MAX_FILES = 300
MAX_TOTAL_BYTES = 4 * 1024 ** 3
CHUNK_BYTES = 256 * 1024
ALLOWED_EXTENSIONS = frozenset({
    '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif', '.tiff', '.tif',
    '.bmp', '.gif', '.pdf', '.docx',
})


def _display_name(filename: str) -> str:
    """Nombre plano y seguro, sin caracteres de control ni rutas relativas."""
    name = str(filename).replace('\\', '/').split('/')[-1]
    name = ''.join(c if ord(c) >= 32 and c not in '\x7f/\\' else '_' for c in name)
    name = name.strip(' .')[:145]
    return name or 'documento'


def _distinct(items: list[str]) -> list[str]:
    names, used = [], set()
    for value in items:
        value = _display_name(value)
        stem, suffix = os.path.splitext(value)
        name = value
        i = 2
        while name.casefold() in used:
            name = f'{stem} ({i}){suffix}'
            i += 1
        used.add(name.casefold())
        names.append(name)
    return names


class DownloadServer:
    """HTTP local con token de sesión y manifiesto inmutable de archivos."""

    def __init__(self, files, *, host=None):
        if host is None:
            # Se usa exactamente el mismo descubrimiento LAN que en el QR de subida.
            from mobile_import import local_ip
            host = local_ip()
        if not host:
            raise RuntimeError('No se ha encontrado una red local para conectar el móvil.')
        paths = [Path(p).resolve() for p in files]
        if not paths:
            raise ValueError('No hay archivos para enviar al móvil.')
        if len(paths) > MAX_FILES:
            raise ValueError(f'Se pueden compartir como máximo {MAX_FILES} archivos a la vez.')
        total = 0
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise ValueError(f'Archivo no válido o no compatible: {path.name}')
            total += path.stat().st_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError('El tamaño total supera el máximo de 4 GB por sesión.')
        self.host = host
        self.token = secrets.token_urlsafe(32)
        labels = _distinct([p.name for p in paths])
        self.items = {secrets.token_urlsafe(12): (p, label)
                      for p, label in zip(paths, labels)}
        self._closed = False
        self._temp = tempfile.TemporaryDirectory(prefix='Revelo_DescargaQR_')
        owner = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'ReveloDownload/1.0'
            sys_version = ''

            def log_message(self, *_):
                pass

            def _headers(self, status, size, content_type, *, filename=None):
                self.send_response(status)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(size))
                self.send_header('Cache-Control', 'no-store, private, max-age=0')
                self.send_header('Pragma', 'no-cache')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Frame-Options', 'DENY')
                self.send_header('Content-Security-Policy',
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'self'")
                if filename:
                    fallback = ''.join(c if 32 <= ord(c) < 127 and c not in '\"\\' else '_'
                                       for c in filename)
                    self.send_header('Content-Disposition',
                        f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename)}')
                self.end_headers()

            def _error(self, status, message):
                payload = message.encode('utf-8')
                self._headers(status, len(payload), 'text/plain; charset=utf-8')
                self.wfile.write(payload)

            def _transfer(self, path, name):
                try:
                    with path.open('rb') as source:
                        size = os.fstat(source.fileno()).st_size
                        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
                        self._headers(200, size, mime, filename=name)
                        shutil.copyfileobj(source, self.wfile, CHUNK_BYTES)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    # El móvil puede cancelar una descarga sin afectar a la sesión.
                    pass

            def _page(self):
                rows = []
                for i, (fid, (path, label)) in enumerate(owner.items.items()):
                    size = path.stat().st_size
                    item_url = f'/archivo/{fid}?t={quote(owner.token)}'
                    rows.append(f'<label class="file"><input type="checkbox" class="pick" '
                                f'data-id="{fid}" checked><span><strong>{html.escape(label)}</strong>'
                                f'<small>{size / 1024 / 1024:.1f} MB</small></span>'
                                f'<a href="{item_url}" download>Descargar</a></label>')
                body = '''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Revelo · Descargar desde PC</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#081928;color:#f1f6fb;margin:0;padding:20px}main{max-width:660px;margin:auto}h1{font-size:29px;margin:20px 0 4px}.a{color:#4ce8d4}.sub{color:#b2c5d2;line-height:1.55}section{background:#103044;border:1px solid #346477;border-radius:15px;padding:16px;margin:22px 0}.file{display:flex;align-items:center;gap:12px;padding:13px 0;border-bottom:1px solid #285066}.file:last-child{border:0}.file span{min-width:0;overflow-wrap:anywhere;flex:1}.file strong{display:block;font-size:15px}.file small{color:#a4b7c7}.file input{width:20px;height:20px;accent-color:#4ce8d4}.file a{color:#4ce8d4;font-size:13px}.btn{background:#4ce8d4;color:#0b202e;border:0;border-radius:11px;width:100%;padding:15px;font-size:16px;font-weight:700;cursor:pointer}.btn:disabled{opacity:.5}#status{color:#bed2df;font-size:14px;margin:15px 0}</style></head><body><main><h1><span class="a">R</span>evelo · PC → móvil</h1><p class="sub">Selecciona los archivos que quieras conservar en el móvil. La transferencia se realiza directamente por Wi-Fi, sin subirlos a Internet.</p><section>'''
                body += ''.join(rows)
                body += '''</section><button class="btn" id="get">Descargar selección (.zip)</button><p id="status">Los archivos originales mantienen sus bytes y su calidad.</p><p class="sub">En iPhone, la descarga se guarda normalmente en Archivos → Descargas. Puedes guardar fotos desde allí en Fotos.</p><script>
const btn=document.getElementById('get'), status=document.getElementById('status');
btn.addEventListener('click',()=>{const ids=[...document.querySelectorAll('.pick:checked')].map(e=>e.dataset.id);if(!ids.length){status.textContent='Selecciona al menos un archivo.';return;}const u='/lote?t=' + encodeURIComponent(''' + repr(owner.token) + ''') + '&ids=' + encodeURIComponent(ids.join(','));window.location.href=u;status.textContent='Preparando la descarga. Si has elegido varias fotografías se guardarán en un ZIP.';});</script></main></body></html>'''
                payload = body.encode('utf-8')
                self._headers(200, len(payload), 'text/html; charset=utf-8')
                self.wfile.write(payload)

            def do_GET(self):
                url = urlsplit(self.path)
                args = parse_qs(url.query)
                if owner._closed or not secrets.compare_digest(
                        args.get('t', [''])[0], owner.token):
                    return self._error(403, 'Sesión cerrada o enlace no autorizado.')
                if url.path == '/':
                    return self._page()
                if url.path.startswith('/archivo/'):
                    file_id = url.path.removeprefix('/archivo/')
                    item = owner.items.get(file_id)
                    if item is None:
                        return self._error(404, 'Archivo no incluido en esta sesión.')
                    if not item[0].is_file():
                        return self._error(410, 'El archivo ya no está disponible en el PC.')
                    return self._transfer(*item)
                if url.path == '/lote':
                    raw = args.get('ids', [''])[0].split(',')
                    ids = list(dict.fromkeys(raw))
                    if not ids or len(ids) > MAX_FILES or any(i not in owner.items for i in ids):
                        return self._error(400, 'Selección de archivos no válida.')
                    # Construir el ZIP en disco, nunca íntegramente en memoria.
                    archive = Path(owner._temp.name) / (secrets.token_hex(12) + '.zip')
                    try:
                        with ZipFile(archive, 'w', compression=ZIP_STORED, allowZip64=True) as z:
                            for fid in ids:
                                source, label = owner.items[fid]
                                if not source.is_file():
                                    return self._error(410, 'Hay un archivo que ya no existe.')
                                z.write(source, arcname=label)
                        return self._transfer(archive, 'Revelo_Fotos.zip')
                    except (OSError, ValueError):
                        return self._error(500, 'No se pudo preparar el paquete de descarga.')
                    finally:
                        archive.unlink(missing_ok=True)
                return self._error(404, 'Dirección no reconocida.')

        bind = '127.0.0.1' if host == '127.0.0.1' else '0.0.0.0'
        try:
            self.http = ThreadingHTTPServer((bind, 0), Handler)
        except OSError:
            self._temp.cleanup()
            raise RuntimeError('No se pudo abrir una conexión local para el código QR.')
        self.http.daemon_threads = True
        self.port = self.http.server_address[1]
        self.url = f'http://{host}:{self.port}/?t={quote(self.token)}'
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True,
                                       name='Revelo-QR-Descarga')
        self.thread.start()

    def stop(self):
        if self._closed:
            return
        self._closed = True
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=3)
        self._temp.cleanup()
