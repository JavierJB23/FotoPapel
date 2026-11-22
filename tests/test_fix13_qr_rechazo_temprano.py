"""FIX13: Rechazar cargas evidentemente corruptas ANTES de invocar Pillow.

No se relajan los controles de formato, tamaño de carga ni sesión del QR.
"""
from __future__ import annotations

from http.client import HTTPConnection
from PIL import Image
from mobile_import import PhoneTransferServer


def test_jpg_de_tres_bytes_se_rechaza_sin_decodificar(tmp_path, monkeypatch):
    calls=[]

    def decoder_must_not_run(*args, **kwargs):
        calls.append(args)
        raise AssertionError('No debe llamarse al decodificador de imágenes para 3 bytes')

    monkeypatch.setattr(Image, 'open', decoder_must_not_run)
    received=[]
    server=PhoneTransferServer(tmp_path/'in', received.append, host='127.0.0.1')
    try:
        for extension, data, expected in (
            ('no_es_una_foto.jpg', b'xxx', 422),
            ('script.exe', b'contenido_de_prueba_que_no_es_una_foto', 415),
        ):
            conn=HTTPConnection('127.0.0.1',server.port,timeout=3)
            try:
                conn.request('POST', '/upload?t='+server.token,body=data,
                             headers={'X-Filename':extension,
                                      'Content-Type':'application/octet-stream'})
                response=conn.getresponse()
                payload=response.read()
                assert response.status==expected,(extension,response.status,payload)
                assert b'error' in payload
            finally:
                conn.close()
        assert not calls, 'Una carga corrupta se envió a Image.open'
        assert not received
        assert not list((tmp_path/'in').iterdir())
        assert server.count==0
        assert server.total_bytes==0
    finally:
        server.stop()
