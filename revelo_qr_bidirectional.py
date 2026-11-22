"""Interfaz unificada de QR para Revelo.

Se instala como extensión mínima de ReveloApp para conservar intacto el
importador QR previamente validado (FIX13). El servidor de salida es independiente.
"""
from __future__ import annotations

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path

import qrcode
from PIL import Image, ImageTk

import revelo_dialogs as messagebox
from editorial_theme import apply_window_skin
from revelo_mobile_export import DownloadServer, ALLOWED_EXTENSIONS, MAX_TOTAL_BYTES
from processor import page_groups, render_layout_page
from advanced_layout import numbers_for_groups

BG = '#081928'
SURFACE = '#103044'
MUTED = '#9CB1C7'
TEXT = '#F1F6FB'
ACCENT = '#4CE8D4'


def _center(dialog, parent, width, height):
    parent.update_idletasks()
    x = max(0, parent.winfo_rootx() + (parent.winfo_width()-width)//2)
    y = max(0, parent.winfo_rooty() + (parent.winfo_height()-height)//2)
    dialog.geometry(f'{width}x{height}+{x}+{y}')


def install(ReveloApp):
    """Añade modos de QR sin reemplazar open_mobile_import ni PhoneTransferServer."""

    def _close_qr_mode(self):
        dialog = getattr(self, '_qr_mode_window', None)
        self._qr_mode_window = None
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def open_mobile_connection(self):
        if self.is_busy:
            return
        dialog = getattr(self, '_qr_mode_window', None)
        if dialog is not None and dialog.winfo_exists():
            dialog.lift()
            dialog.focus_set()
            return
        dialog = tk.Toplevel(self.root)
        self._qr_mode_window = dialog
        dialog.configure(bg=BG)
        dialog.title('Revelo · Conectar móvil QR')
        _center(dialog, self.root, 530, 365)
        dialog.minsize(460, 340)
        frame = tk.Frame(dialog, bg=BG, padx=28, pady=27)
        frame.pack(fill='both', expand=True)
        self._label(frame, 'CONECTAR MÓVIL QR', size=17, weight='bold').pack(anchor='w')
        self._label(frame, 'Transfiere fotografías directamente entre el PC y el móvil por Wi-Fi.',
                    color=MUTED, size=10, wraplength=450, justify='left').pack(anchor='w', pady=(9,21))

        def launch(callback):
            _close_qr_mode(self)
            callback()

        self._button(frame, 'Importar desde móvil',
                     lambda: launch(self.open_mobile_import), accent=True).pack(fill='x', pady=(0,12))
        self._button(frame, 'Exportar desde PC',
                     lambda: launch(self.open_mobile_export)).pack(fill='x', pady=(0,12))
        bottom = tk.Frame(frame, bg=BG)
        bottom.pack(fill='x', side='bottom')
        self._button(bottom, 'Cerrar', lambda:_close_qr_mode(self),small=True).pack(side='right')
        dialog.protocol('WM_DELETE_WINDOW', lambda:_close_qr_mode(self))
        apply_window_skin(dialog, compact=True)

    def _close_mobile_export(self):
        session = getattr(self, '_qr_export_state', None)
        self._qr_export_state = None
        if session is not None:
            session['cancel'].set()
            server = session.get('server')
            if server is not None:
                server.stop()
                session['server'] = None
            # Si aún se generan hojas, el hilo limpia su carpeta al terminar.
            temporary = session.get('temporary')
            if temporary is not None:
                if session.get('working') and session.get('thread') is not None:
                    # No borrar los PNG mientras el renderizador todavía escribe.
                    worker = session['thread']
                    def clean_after_worker():
                        worker.join()
                        temporary.cleanup()
                    threading.Thread(target=clean_after_worker, daemon=True,
                                     name='Revelo-QR-Limpieza').start()
                else:
                    temporary.cleanup()
                session['temporary'] = None
            window = session.get('window')
            if window is not None and window.winfo_exists():
                window.destroy()

    def open_mobile_export(self):
        if self.is_busy:
            messagebox.showinfo('Conectar móvil QR', 'Termina la operación actual antes de exportar.',
                                parent=self.root)
            return
        prev = getattr(self, '_qr_export_state', None)
        if prev is not None:
            w = prev.get('window')
            if w is not None and w.winfo_exists():
                w.lift()
                w.focus_set()
                return
            self._close_mobile_export()
        window = tk.Toplevel(self.root)
        window.title('Revelo · Exportar desde PC')
        window.configure(bg=BG)
        _center(window, self.root, 560, 570)
        window.minsize(485, 515)
        state = {'window':window, 'cancel':threading.Event(), 'temporary':None,
                 'working':False, 'server':None, 'queue':queue.Queue(), 'thread':None}
        self._qr_export_state = state
        outer = tk.Frame(window, bg=BG, padx=26, pady=19)
        outer.pack(fill='both',expand=True)
        self._label(outer, 'EXPORTAR DESDE PC', size=18, weight='bold').pack(anchor='w')
        self._label(outer, 'Elige qué quieres enviar al móvil. Solo será visible durante esta conexión.',
                    color=MUTED,size=10,wraplength=490,justify='left').pack(anchor='w',pady=(9,18))
        choice_frame = tk.Frame(outer,bg=SURFACE,padx=16,pady=15)
        choice_frame.pack(fill='x')
        mode=tk.StringVar(value='originales' if self.pages else 'elegir')
        options = (
            ('originales', 'Fotografías cargadas', 'Envía los archivos originales sin modificar su calidad.'),
            ('hojas', 'Hojas maquetadas', 'Envía cada hoja como PNG con el diseño y las ediciones de Revelo.'),
            ('resultado', 'Última exportación', 'Envía el PDF, Word o las imágenes que hayas exportado.'),
            ('elegir', 'Elegir archivos del PC', 'Selecciona fotos, PDF o Word aunque no estén cargados.'),
        )
        for key, name, hint in options:
            line = tk.Frame(choice_frame,bg=SURFACE)
            line.pack(fill='x',pady=(0,8))
            tk.Radiobutton(line,text=name,value=key,variable=mode, bg=SURFACE,fg=TEXT,
                           selectcolor=SURFACE,activebackground=SURFACE,activeforeground=ACCENT,
                           font=('Segoe UI',10,'bold'),anchor='w').pack(fill='x')
            self._label(line, hint,color=MUTED,size=9,wraplength=440,justify='left').pack(anchor='w',padx=(25,0))
        status = tk.StringVar(value='La transferencia conserva los archivos originales.')
        self._label(outer,'',textvariable=status,color=ACCENT,size=10,wraplength=490,
                    justify='left').pack(anchor='w',fill='x',pady=(13,0))
        buttons=tk.Frame(outer,bg=BG)
        buttons.pack(side='bottom',fill='x',pady=(12,0))
        self._button(buttons,'Cerrar',lambda:self._close_mobile_export(),small=True).pack(side='right')
        prepare = self._button(buttons,'Generar QR',lambda: prepare_choice(),accent=True,small=True)
        prepare.pack(side='right',padx=(0,10))

        def display_qr(paths):
            if state['cancel'].is_set() or not window.winfo_exists():
                return
            try:
                server = DownloadServer(paths)
            except (OSError,RuntimeError,ValueError) as exc:
                status.set(str(exc))
                prepare.configure(state='normal')
                return
            state['server']=server
            choice_frame.pack_forget()
            for child in buttons.winfo_children():
                child.destroy()
            self._label(outer, f'{len(paths)} archivo(s) preparados para descargar',
                        color=MUTED,size=10).pack(anchor='w',pady=(4,8))
            qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                            box_size=10,border=4)
            qr.add_data(server.url);qr.make(fit=True)
            photo=qr.make_image(fill_color='#102234',back_color='white').convert('RGB')
            photo=photo.resize((315,315),Image.Resampling.NEAREST)
            window._revelo_export_qr=ImageTk.PhotoImage(photo)
            tk.Label(outer,image=window._revelo_export_qr,bg='white',bd=0,
                     padx=8,pady=8).pack(pady=(5,8))
            status.set('Escanea el QR desde el móvil y elige los archivos que quieras descargar.')
            self._label(outer,'El ordenador y el móvil deben estar en la misma red Wi-Fi. '
                        'El enlace dejará de funcionar al cerrar esta ventana.',
                        color=MUTED,size=9,wraplength=490,justify='left').pack(anchor='w')
            self._button(buttons,'Cerrar conexión',lambda:self._close_mobile_export(),small=True).pack(side='right')
            def copy_url():
                self.root.clipboard_clear()
                self.root.clipboard_append(server.url)
                self.root.update_idletasks()
                status.set('Enlace copiado. Ábrelo desde el móvil conectado a la misma red.')
            self._button(buttons,'Copiar enlace',copy_url,small=True).pack(side='left')
            # Aplicar también el tema editorial a los controles añadidos tras
            # preparar los archivos, no solo a la ventana inicial.
            window.after_idle(lambda: apply_window_skin(window,compact=True)
                              if window.winfo_exists() else None)

        def poll_preparation():
            if state['cancel'].is_set() or not window.winfo_exists():
                return
            try:
                while True:
                    event=state['queue'].get_nowait()
                    if event[0]=='progress':
                        status.set(f'Preparando hoja {event[1]} de {event[2]}…')
                    elif event[0]=='done':
                        state['working']=False
                        display_qr(event[1])
                        return
                    elif event[0]=='error':
                        state['working']=False
                        status.set('No se pudieron preparar las hojas: '+event[1])
                        prepare.configure(state='normal')
                        return
            except queue.Empty:
                pass
            window.after(120,poll_preparation)

        def prepare_choice():
            if self.is_busy or state['working']:
                return
            selected=mode.get()
            paths=[]
            if selected=='originales':
                paths=[Path(p) for p in self.pages
                       if p not in self.special_pages and Path(p).suffix.lower() in ALLOWED_EXTENSIONS]
                if not paths:
                    status.set('Primero añade fotografías a Revelo o elige archivos del PC.')
                    return
            elif selected=='resultado':
                result=getattr(self,'output_path',None)
                if result and Path(result).is_file():
                    paths=[Path(result)]
                elif result and Path(result).is_dir():
                    paths=[p for p in sorted(Path(result).iterdir())
                           if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS]
                if not paths:
                    status.set('Todavía no hay una exportación disponible. Prueba otra opción.')
                    return
            elif selected=='elegir':
                from tkinter import filedialog
                chosen=filedialog.askopenfilenames(parent=window,title='Archivos para enviar al móvil',
                    filetypes=[('Fotos y documentos', '*.jpg *.jpeg *.png *.heic *.heif *.webp *.tif *.tiff *.bmp *.gif *.pdf *.docx'),
                               ('Todos los archivos', '*.*')])
                if not chosen:
                    return
                paths=[Path(p) for p in chosen]
            elif selected=='hojas':
                if not self.pages:
                    status.set('No hay hojas para compartir. Añade fotografías primero.')
                    return
                try:
                    opts=self._options()
                    groups=page_groups(self.pages.copy(),opts.photos_per_page,opts.special_pages)
                    numbers=numbers_for_groups(groups,opts.special_pages,
                        enabled=opts.numbering_enabled,start=opts.numbering_start,
                        skip_special=opts.numbering_skip_special)
                    if len(groups)>300:
                        raise ValueError('El máximo por sesión es de 300 hojas.')
                except (ValueError,OSError) as exc:
                    status.set(str(exc));return
                temporary=tempfile.TemporaryDirectory(prefix='Revelo_HojasQR_')
                state['temporary']=temporary
                state['working']=True
                prepare.configure(state='disabled')
                status.set('Preparando las hojas en calidad de impresión…')
                def worker():
                    prepared=[]
                    total_bytes=0
                    try:
                        for i,group in enumerate(groups):
                            if state['cancel'].is_set():
                                return
                            rendered,_,_=render_layout_page(group,opts,page_index=i,
                                                           printed_number=numbers[i])
                            target=Path(temporary.name)/f'Revelo_hoja_{i+1:03d}.png'
                            try:
                                rendered.save(target,format='PNG',compress_level=3,
                                              dpi=(opts.dpi,opts.dpi))
                            finally:
                                rendered.close()
                            total_bytes += target.stat().st_size
                            if total_bytes > MAX_TOTAL_BYTES:
                                raise ValueError('Las hojas superan 4 GB. Exporta menos páginas por sesión.')
                            prepared.append(target)
                            state['queue'].put(('progress',i+1,len(groups)))
                        state['queue'].put(('done',prepared))
                    except (OSError,ValueError,RuntimeError,MemoryError) as exc:
                        state['queue'].put(('error',str(exc)))
                state['thread']=threading.Thread(target=worker,daemon=True,
                                                 name='Revelo-Preparar-QR')
                state['thread'].start()
                window.after(120,poll_preparation)
                return
            try:
                # Validar los archivos ANTES de cambiar de pantalla.
                for p in paths:
                    if not p.is_file() or p.suffix.lower() not in ALLOWED_EXTENSIONS:
                        raise ValueError(f'Archivo no compatible: {p.name}')
                if len(paths)>300:
                    raise ValueError('El máximo por sesión es de 300 archivos.')
            except (OSError,ValueError) as exc:
                status.set(str(exc));return
            display_qr(paths)

        window.protocol('WM_DELETE_WINDOW',lambda:self._close_mobile_export())
        apply_window_skin(window,compact=True)

    ReveloApp._close_qr_mode = _close_qr_mode
    ReveloApp.open_mobile_connection = open_mobile_connection
    ReveloApp.open_mobile_export = open_mobile_export
    ReveloApp._close_mobile_export = _close_mobile_export
