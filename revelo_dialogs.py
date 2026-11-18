"""Ventanas modales coherentes con la interfaz de Revelo.

Reemplaza avisos y preguntas de tkinter.messagebox; no modifica el selector de
archivos ni la paleta de colores del sistema. No necesita dependencias nuevas.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

BG = '#0B1422'
PANEL = '#142236'
BORDER = '#2D4960'
TEXT = '#F1F6FB'
MUTED = '#B1C5D5'
ACCENT = '#4CD9B5'
WARN = '#F5C96A'
ERR = '#F58E90'


def _modal(title: str, message: str, *, parent=None, kind='info', question=False):
    master = parent or tk._default_root
    if master is None:
        # En arranque antes de Tk, no crear una segunda ventana raíz a escondidas.
        raise RuntimeError('Revelo necesita una ventana principal para mostrar avisos')
    dialog = tk.Toplevel(master)
    dialog.title(f'Revelo · {title}')
    dialog.configure(bg=BG)
    dialog.resizable(False, False)
    dialog.transient(master)
    result = [False]
    tone = ACCENT if kind == 'info' else (ERR if kind == 'error' else WARN)
    outer = tk.Frame(dialog, bg=BG, padx=24, pady=19)
    outer.pack(fill='both', expand=True)
    header = tk.Frame(outer, bg=BG)
    header.pack(fill='x')
    tk.Label(header, text={'info':'✓','warning':'!','error':'×','question':'?'}[kind],
             bg=tone, fg=BG, font=('Segoe UI',17,'bold'),
             width=2, height=1).pack(side='left', padx=(0,13))
    tk.Label(header, text=title, bg=BG, fg=TEXT, anchor='w',
             font=('Segoe UI',14,'bold')).pack(side='left', fill='x', expand=True)
    line = tk.Frame(outer, height=1, bg=BORDER)
    line.pack(fill='x', pady=(16,12))
    tk.Message(outer, text=str(message), width=450, bg=BG, fg=MUTED,
               font=('Segoe UI',10), anchor='w', justify='left').pack(fill='x', anchor='w')
    actions = tk.Frame(outer, bg=BG)
    actions.pack(fill='x', pady=(20,0))

    def finish(value):
        result[0] = value
        try: dialog.grab_release()
        except tk.TclError: pass
        dialog.destroy()

    def button(caption, value, accented=False):
        btn = tk.Button(actions, text=caption, command=lambda:finish(value),
                        bg=ACCENT if accented else PANEL, fg=BG if accented else TEXT,
                        activebackground='#62E6C5' if accented else '#233B55',
                        activeforeground=BG if accented else TEXT,
                        relief='flat', bd=0, padx=17, pady=9,
                        cursor='hand2', font=('Segoe UI',10,'bold'))
        btn.pack(side='right', padx=(8,0))
        return btn

    if question:
        button('Cancelar', False)
        confirm = button('Sí, continuar', True, True)
    else:
        confirm = button('Aceptar', True, True)
    dialog.update_idletasks()
    width = max(390, min(590, max(dialog.winfo_reqwidth(), 460)))
    height = dialog.winfo_reqheight()
    try:
        master.update_idletasks()
        x = master.winfo_rootx() + max(0,(master.winfo_width()-width)//2)
        y = master.winfo_rooty() + max(0,(master.winfo_height()-height)//2)
    except tk.TclError:
        x,y = 120,120
    dialog.geometry(f'{width}x{height}+{x}+{y}')
    dialog.protocol('WM_DELETE_WINDOW', lambda: finish(False))
    dialog.bind('<Escape>', lambda _: finish(False))
    dialog.bind('<Return>', lambda _: finish(True))
    dialog.grab_set()
    confirm.focus_set()
    master.wait_window(dialog)
    return result[0]


def showinfo(title, message, **kwargs):
    return _modal(title, message, parent=kwargs.get('parent'), kind='info')


def showwarning(title, message, **kwargs):
    return _modal(title, message, parent=kwargs.get('parent'), kind='warning')


def showerror(title, message, **kwargs):
    return _modal(title, message, parent=kwargs.get('parent'), kind='error')


def askyesno(title, message, **kwargs):
    return _modal(title, message, parent=kwargs.get('parent'), kind='question', question=True)
