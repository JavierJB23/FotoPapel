"""Regresiones del servidor PC->móvil y de la nueva selección de modos QR."""
from __future__ import annotations

from http.client import HTTPConnection
import io
from pathlib import Path
import tkinter as tk
from urllib.parse import urlsplit
from zipfile import ZipFile

import pytest
from PIL import Image

from revelo_mobile_export import DownloadServer, _distinct, _display_name


def req(server, endpoint, token=None):
    conn=HTTPConnection('127.0.0.1',server.port,timeout=5)
    try:
        suffix= ('?t='+ (token if token is not None else server.token))
        with_query = endpoint + ('&' if '?' in endpoint else '?') + suffix[1:]
        conn.request('GET',with_query)
        r=conn.getresponse()
        return r.status, r.read(), dict(r.getheaders())
    finally:
        conn.close()


def photo(tmp_path,name,bytes_data):
    p=tmp_path/name
    p.write_bytes(bytes_data)
    return p


def test_descarga_originales_sin_modificar_un_solo_byte(tmp_path):
    photos=[photo(tmp_path,'a.jpg',b'JPG-original-001'),
            photo(tmp_path,'b.png',b'PNG-original-222')]
    before=[p.read_bytes() for p in photos]
    srv=DownloadServer(photos,host='127.0.0.1')
    try:
        assert srv.http.server_address[0]=='127.0.0.1'
        status,page,headers=req(srv,'/')
        assert status==200 and b'Revelo' in page and b'Descargar' in page
        assert headers['Cache-Control'].startswith('no-store')
        for idx, fid in enumerate(srv.items):
            code,data,h=req(srv,'/archivo/'+fid)
            assert code==200 and data==before[idx]
            assert 'attachment' in h['Content-Disposition']
        assert [p.read_bytes() for p in photos]==before
    finally:srv.stop()


def test_zip_de_seleccion_sin_recomprimir_originales(tmp_path):
    a=photo(tmp_path,'uno.png',bytes(range(100)))
    b=photo(tmp_path,'dos.pdf',b'%PDF-1.4 valid contents sample')
    srv=DownloadServer([a,b],host='127.0.0.1')
    try:
        ids=list(srv.items)
        status,data,headers=req(srv,'/lote?ids='+','.join(ids))
        assert status==200 and 'Revelo_Fotos.zip' in headers['Content-Disposition']
        with ZipFile(io.BytesIO(data)) as z:
            assert z.read('uno.png')==a.read_bytes()
            assert z.read('dos.pdf')==b.read_bytes()
            assert len(z.namelist())==2
        status,data,_=req(srv,'/lote?ids='+ids[1])
        assert status==200
        with ZipFile(io.BytesIO(data)) as z:
            assert z.namelist()==['dos.pdf']
    finally:srv.stop()


def test_enlace_temporal_estricto_y_no_explora_el_pc(tmp_path):
    p=photo(tmp_path,'prueba.heic',b'contenido_original')
    srv=DownloadServer([p],host='127.0.0.1')
    try:
        fid=next(iter(srv.items))
        assert req(srv,'/archivo/'+fid,'incorrecto')[0]==403
        assert req(srv,'/archivo/otro_id')[0]==404
        assert req(srv,'/archivo/../../otros')[0]==404
        assert req(srv,'/lote?ids='+fid+',otro')[0]==400
        assert req(srv,'/archivo/'+fid)[0]==200
    finally:srv.stop()
    assert srv._closed


def test_nombres_peligrosos_y_duplicados():
    assert _display_name('../abc.png')=='abc.png'
    assert _display_name('titulo\r\n.pdf')=='titulo__.pdf'
    assert _distinct(['foto.jpg','FOTO.jpg','otra.jpg'])==[
        'foto.jpg','FOTO (2).jpg','otra.jpg']


def test_no_admite_archivos_fuera_del_manifest(tmp_path):
    p=photo(tmp_path,'malware.exe',b'fake')
    with pytest.raises(ValueError):DownloadServer([p],host='127.0.0.1')
    with pytest.raises(ValueError):DownloadServer([],host='127.0.0.1')


def test_interfaz_revelo_ofrece_los_dos_sentidos_y_mantiene_importador():
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('No hay sesión gráfica Tk')
    try:
        from main import ReveloApp
    except ModuleNotFoundError as exc:
        root.destroy()
        if exc.name != 'main':
            raise
        pytest.skip('El proyecto completo se integra en GitHub Actions')
    try:
        app=ReveloApp(root)
        root.update()
        assert app.mobile_btn.cget('text')=='Conectar móvil QR'
        assert callable(app.open_mobile_import)
        app.open_mobile_connection()
        root.update()
        dialog=app._qr_mode_window
        buttons=[]
        def walk(w):
            if isinstance(w,tk.Button):buttons.append(w)
            for child in w.winfo_children():walk(child)
        walk(dialog)
        labels={x.cget('text') for x in buttons}
        assert 'Importar desde móvil' in labels
        assert 'Exportar desde PC' in labels
        app._close_qr_mode()
        assert not dialog.winfo_exists()
    finally:root.destroy()
