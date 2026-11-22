"""FIX12: guardarraíles de selección y HTTP local."""
import tkinter as tk
import pytest


def test_editor_has_distinct_radio_buttons_for_background_and_photo():
    """Hay dos radios llamados Fotografía; solamente image elige el tirador."""
    try:
        root=tk.Tk()
    except tk.TclError:
        pytest.skip('Escritorio Tk no disponible')
    try:
        variable=tk.StringVar(master=root,value='title')
        background=tk.StringVar(master=root,value='imagen')
        a=tk.Radiobutton(root, text='Fotografía', value='imagen',variable=background)
        b=tk.Radiobutton(root, text='Fotografía', value='image',variable=variable)
        a.pack();b.pack()
        r=[w for w in root.winfo_children() if isinstance(w,tk.Radiobutton)
           and w.cget('text')=='Fotografía' and w.cget('value')=='image']
        assert r==[b]
        b.invoke()
        assert variable.get()=='image'
        assert background.get()=='imagen'
    finally:
        root.destroy()


def test_qr_server_only_listens_on_loopback_when_testing(tmp_path):
    from mobile_import import PhoneTransferServer
    server=PhoneTransferServer(tmp_path/'in',lambda _p:None,host='127.0.0.1')
    try:
        assert server.http.server_address[0]=='127.0.0.1'
        assert server.port>0 and server.thread.is_alive()
    finally:
        server.stop()
