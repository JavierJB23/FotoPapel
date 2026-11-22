"""Pruebas de la subida por QR: transporte y control de accesos sin Internet."""
from __future__ import annotations

import io
import json
import socket
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

from mobile_import import PhoneTransferServer, _safe_filename, _mobile_page
from processor import SUPPORTED_EXTENSIONS


def _image_bytes(color=(22, 120, 200)):
    bio = io.BytesIO()
    Image.new('RGB', (160, 90), color).save(bio, format='PNG')
    return bio.getvalue()


def test_security_token_and_mobile_page(tmp_path):
    server = PhoneTransferServer(tmp_path / 'incoming', lambda path: None, host='127.0.0.1')
    try:
        with urlopen(server.url, timeout=5) as r:
            page = r.read().decode('utf-8')
            assert r.status == 200
            assert 'Selecciona las fotografías' in page
            assert 'sin conexión' not in page.lower()  # la conexión local sí es necesaria
            assert 'image/*,.heic,.heif' in page
        try:
            urlopen(f'http://127.0.0.1:{server.port}/', timeout=5)
            assert False, 'El enlace sin token debería rechazarse'
        except HTTPError as err:
            assert err.code == 403
        request = Request(f'http://127.0.0.1:{server.port}/upload?t=mal',
                          method='POST', data=_image_bytes(),
                          headers={'X-Filename': 'imagen.png'})
        try:
            urlopen(request, timeout=5)
            assert False, 'Una petición no autorizada no debe escribir archivos'
        except HTTPError as err:
            assert err.code == 403
        assert list((tmp_path / 'incoming').iterdir()) == []
    finally:
        server.stop()


def test_upload_multiple_images_preserves_original_bytes_order(tmp_path):
    received = []
    server = PhoneTransferServer(tmp_path / 'incoming', lambda path: received.append(path), host='127.0.0.1')
    try:
        originals = [_image_bytes((200, 0, 0)), _image_bytes((0, 200, 0)), _image_bytes((0, 0, 200))]
        for idx, data in enumerate(originals, start=1):
            request = Request(server.url.replace('/?t=', '/upload?t='),
                              method='POST', data=data,
                              headers={'X-Filename': f'foto_{idx:02}.png',
                                       'Content-Type': 'application/octet-stream'})
            with urlopen(request, timeout=5) as r:
                assert json.load(r)['ok']
        assert len(received) == 3
        for i, path in enumerate(received):
            assert path.read_bytes() == originals[i]
            with Image.open(path) as im:
                assert im.size == (160, 90)
    finally:
        server.stop()


def test_invalid_file_and_bad_extension_rejected(tmp_path):
    received = []
    server = PhoneTransferServer(tmp_path / 'incoming', received.append, host='127.0.0.1')
    try:
        url = server.url.replace('/?t=', '/upload?t=')
        for name, contents, code in [('no_es_una_foto.jpg', b'xxx', 422),
                                     ('script.exe', _image_bytes(), 415)]:
            request = Request(url, method='POST', data=contents,
                              headers={'X-Filename': name})
            # Los runners Windows compartidos pueden detener temporalmente
            # los hilos del servidor QR. Reintentamos únicamente un timeout
            # de transporte; una respuesta con código incorrecto sigue
            # haciendo fallar la prueba (nunca se ignora el control de acceso).
            for attempt in range(3):
                try:
                    with urlopen(request, timeout=12) as response:
                        raise AssertionError(f'{name}: el servidor lo aceptó ({response.status})')
                except HTTPError as err:
                    assert err.code == code, (name, err.code, code)
                    break
                except (TimeoutError, socket.timeout):
                    if attempt == 2:
                        raise
                    time.sleep(0.25 * (attempt + 1))
        assert len(received) == 0
        assert list((tmp_path / 'incoming').iterdir()) == []
    finally:
        server.stop()


def test_safe_names_and_revelo_exts():
    assert _safe_filename('../../privada.png') == 'privada.png'
    assert _safe_filename(r'C:\\Fotos\\primera.heic') == 'primera.heic'
    assert '.heic' in SUPPORTED_EXTENSIONS and '.heif' in SUPPORTED_EXTENSIONS
    assert b'Enviar fotos' in _mobile_page()


def test_qr_generation():
    import qrcode
    img = qrcode.make('http://192.168.1.50:12345/?t=clave_aleatoria')
    assert img.size[0] > 100


def test_heic_iPhone_when_decoder_is_available(tmp_path):
    """En la compilación Windows se instala pillow-heif y se prueba HEIC real."""
    import pytest
    pytest.importorskip('pillow_heif')
    from processor import source_dimensions, render_print_image, ExportOptions
    file = tmp_path / 'foto_iphone.heic'
    Image.new('RGB', (240, 180), (31, 115, 90)).save(file, format='HEIF', quality=90)
    assert source_dimensions(file) == (240, 180)
    rendered, _, _ = render_print_image(file, ExportOptions(paper='A5', dpi=100),
                                        preview_max_size=(400, 400))
    assert rendered.width > 0
    rendered.close()
