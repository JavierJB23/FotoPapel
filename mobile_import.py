"""Transferencia local de fotos del móvil al ordenador, sin servidores externos.

Servidor HTTP efímero, protegido mediante un token aleatorio de sesión.
Solo se activa al abrir la ventana QR de Revelo y se detiene al cerrarla.
"""
from __future__ import annotations

import html
import json
import os
import secrets
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlsplit

from PIL import Image, UnidentifiedImageError
from processor import SUPPORTED_EXTENSIONS

MAX_FILE_SIZE = 120 * 1024 * 1024  # 120 MiB por imagen (incluye HEIC de alta calidad)
MAX_SESSION_SIZE = 3 * 1024 * 1024 * 1024
MAX_FILES = 500


def local_ip() -> str | None:
    """Obtiene la IP que usa el equipo en su red local, sin enviar datos a Internet."""
    candidates: list[str] = []
    # UDP connect no envía paquetes; solo consulta la ruta local elegida por SO.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 80))  # dirección reservada de documentación
            candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    try:
        candidates.extend(info[4][0] for info in socket.getaddrinfo(
            socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM))
    except OSError:
        pass
    import ipaddress
    valid = []
    for candidate in dict.fromkeys(candidates):
        try:
            ip = ipaddress.ip_address(candidate)
            if ip.version == 4 and ip.is_private and not ip.is_loopback and not ip.is_link_local:
                valid.append(candidate)
        except ValueError:
            pass
    # Se prefiere interfaz de LAN/Wi-Fi habitual a direcciones VPN/virtuales.
    for prefix in ("192.168.", "10.", "172."):
        for address in valid:
            if address.startswith(prefix):
                return address
    return valid[0] if valid else None


def _safe_filename(raw: str) -> str:
    # El nombre enviado por HTTP jamás se utiliza como ruta sin sanear.
    filename = unquote(raw).replace("\\", "/").split("/")[-1]
    import re
    filename = re.sub(r'[^\w\-.() ]', '_', filename, flags=re.UNICODE).strip(' .')
    if not filename:
        filename = 'foto.jpg'
    return filename[-100:]


def _mobile_page() -> bytes:
    # HTML, CSS y JavaScript integrados: el teléfono no necesita Internet.
    markup = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<title>Revelo · Enviar fotos</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;padding:30px 18px;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
background:#0b1422;color:#f1f6fb}main{max-width:550px;margin:15px auto}
h1{font-size:34px;margin:0 0 4px}.mark{color:#4cd9b5}.desc{color:#afc1d4;line-height:1.5}
section{background:#142236;border:1px solid #2c415a;border-radius:14px;padding:22px;margin-top:22px}
input[type=file]{display:block;width:100%;margin:18px 0;color:#cce0ee;font-size:16px}
button{background:#4cd9b5;color:#0b1422;border:0;border-radius:9px;padding:15px 20px;
font-size:17px;font-weight:700;width:100%}button:disabled{opacity:.45}
progress{width:100%;height:15px;accent-color:#4cd9b5;margin:18px 0 5px}
.small{color:#adbdcc;font-size:14px;line-height:1.6}#status{min-height:52px;line-height:1.5}
</style></head><body><main><h1><span class="mark">R</span>evelo</h1>
<p class="desc">Envía fotos al ordenador por la red Wi-Fi local. No se envía nada a la nube.</p>
<section><strong>1. Selecciona las fotografías</strong><input id="files" type="file" multiple
accept="image/*,.heic,.heif,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff"/>
<p class="small" id="picked">Puedes seleccionar muchas a la vez, también fotografías HEIC del iPhone.</p>
<strong>2. Envíalas a Revelo</strong><button id="send" disabled>Enviar fotos</button>
<progress id="progress" value="0" max="100"></progress>
<p id="status" aria-live="polite">Esperando selección de imágenes.</p>
</section><p class="small">Mantén Revelo abierto en el ordenador y ambos dispositivos en la misma red.
Si Windows pregunta, permite el acceso a la red <b>privada</b> de casa.
Puedes cerrar esta página después de transferir las imágenes.</p></main>
<script>
(function(){
 const files=document.getElementById('files'),send=document.getElementById('send'),
  bar=document.getElementById('progress'),status=document.getElementById('status'),
  picked=document.getElementById('picked');
 const token=new URLSearchParams(location.search).get('t')||'';
 files.addEventListener('change',function(){
  const n=files.files.length;send.disabled=!n;
  picked.textContent=n===1?'1 fotografía seleccionada':n+' fotografías seleccionadas';
  status.textContent=n?'Listo para enviar.':'Esperando selección de imágenes.';bar.value=0;
 });
 function sendOne(file,updated){return new Promise(function(resolve,reject){
  const xhr=new XMLHttpRequest();xhr.open('POST','/upload?t='+encodeURIComponent(token));
  xhr.setRequestHeader('X-Filename',encodeURIComponent(file.name));
  xhr.setRequestHeader('Content-Type','application/octet-stream');
  xhr.upload.onprogress=function(e){if(e.lengthComputable)updated(e.loaded)};
  xhr.onload=function(){let result;try{result=JSON.parse(xhr.responseText)}catch(e){result={error:'Respuesta no válida'} }
   if(xhr.status===200&&result.ok)resolve();else reject(new Error(result.error||'Error '+xhr.status));};
  xhr.onerror=function(){reject(new Error('No se puede conectar con el PC. Comprueba la Wi-Fi y el firewall.'))};
  xhr.ontimeout=function(){reject(new Error('La transferencia ha tardado demasiado.'))};
  xhr.timeout=180000;xhr.send(file);
 });}
 send.addEventListener('click',async function(){
  const items=Array.from(files.files);if(!items.length)return;
  send.disabled=true;files.disabled=true;let done=0,received=0;
  const total=items.reduce((v,f)=>v+f.size,0)||1;
  for(let i=0;i<items.length;i++){
   const f=items[i];status.textContent='Enviando '+(i+1)+' de '+items.length+': '+f.name;
   try{await sendOne(f,function(sent){bar.value=Math.round(100*(done+sent)/total)});
    done+=f.size;received++;bar.value=Math.round(100*done/total);
   }catch(e){status.textContent='Enviadas '+received+' de '+items.length+'. Error en «'+f.name+'»: '+e.message;
    send.disabled=false;files.disabled=false;return;}
  }
  status.textContent='✓ '+received+' fotografía(s) enviadas. Ya aparecen en Revelo en el ordenador.';
  files.value='';files.disabled=false;picked.textContent='Puedes enviar otra tanda de fotografías.';
 });
})();
</script></body></html>"""
    return markup.encode('utf-8')


class PhoneTransferServer:
    """Servidor de duración limitada, una sola sesión QR a la vez."""

    def __init__(self, folder: Path, on_received: Callable[[Path], None], host: str | None = None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.on_received = on_received
        self.host = host or local_ip()
        if self.host is None:
            raise RuntimeError('No se ha encontrado una dirección de red local. Conecta el PC a tu router.')
        self.token = secrets.token_urlsafe(32)
        self.total_bytes = 0
        self.count = 0
        self._lock = threading.Lock()
        self._closed = False
        parent = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'ReveloMobile/1.3'
            sys_version = ''

            def log_message(self, *_args):
                pass  # sin registros de nombres de fotografías ni tokens

            def _headers(self, status: int, mime: str, length: int):
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(length))
                self.send_header('Cache-Control', 'no-store, max-age=0')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Frame-Options', 'DENY')
                self.send_header('Content-Security-Policy',
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
                self.end_headers()

            def _json(self, status: int, **kwargs):
                payload = json.dumps(kwargs, ensure_ascii=False).encode('utf-8')
                self._headers(status, 'application/json; charset=utf-8', len(payload))
                self.wfile.write(payload)

            def _authorized(self, path: str) -> bool:
                query = parse_qs(urlsplit(path).query)
                return secrets.compare_digest(query.get('t', [''])[0], parent.token)

            def do_GET(self):
                if urlsplit(self.path).path != '/' or not self._authorized(self.path):
                    return self._json(403, error='Enlace no autorizado o caducado')
                payload = _mobile_page()
                self._headers(200, 'text/html; charset=utf-8', len(payload))
                self.wfile.write(payload)

            def do_POST(self):
                if urlsplit(self.path).path != '/upload' or not self._authorized(self.path):
                    return self._json(403, error='Enlace no autorizado o caducado')
                if parent._closed:
                    return self._json(410, error='Sesión de Revelo cerrada')
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    return self._json(400, error='Tamaño de archivo no válido')
                if length <= 0 or length > MAX_FILE_SIZE:
                    return self._json(413, error='Foto vacía o demasiado grande (máximo 120 MB)')
                name = _safe_filename(self.headers.get('X-Filename', ''))
                ext = Path(name).suffix.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    return self._json(415, error='Formato no admitido. Se permiten JPG, PNG, HEIC, HEIF, WEBP y TIFF.')
                with parent._lock:
                    if parent.count >= MAX_FILES or parent.total_bytes + length > MAX_SESSION_SIZE:
                        return self._json(413, error='Límite de sesión alcanzado. Cierra y vuelve a abrir el QR.')
                    parent.total_bytes += length
                    parent.count += 1
                file = parent.folder / (uuid.uuid4().hex + '_' + name)
                okay = False
                try:
                    with file.open('xb') as output:
                        remaining = length
                        while remaining > 0:
                            chunk = self.rfile.read(min(1024 * 1024, remaining))
                            if not chunk:
                                raise OSError('Transferencia interrumpida')
                            output.write(chunk)
                            remaining -= len(chunk)
                    # Se comprueba el contenido, no solo la extensión indicada por el móvil.
                    with Image.open(file) as pic:
                        if pic.width * pic.height > 220_000_000:
                            raise ValueError('La imagen supera la resolución máxima admitida')
                        pic.verify()
                    okay = True
                    parent.on_received(file)
                    return self._json(200, ok=True, name=name)
                except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
                    return self._json(422, error='No se pudo importar la foto. Comprueba el formato y vuelve a intentarlo.')
                finally:
                    if not okay:
                        file.unlink(missing_ok=True)
                        with parent._lock:
                            parent.total_bytes -= length
                            parent.count -= 1

        try:
            self.http = ThreadingHTTPServer(('0.0.0.0', 0), Handler)
        except OSError as error:
            raise RuntimeError('No se pudo abrir un puerto local para recibir las fotografías.') from error
        self.http.daemon_threads = True
        self.port = self.http.server_address[1]
        self.url = f'http://{self.host}:{self.port}/?t={self.token}'
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True, name='Revelo-QR')
        self.thread.start()

    def stop(self):
        self._closed = True
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)
