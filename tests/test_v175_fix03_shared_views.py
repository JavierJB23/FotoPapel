"""No more separate paper, photo and free-layout sizes in different views."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import tkinter as tk

import pytest
from PIL import Image

from processor import ExportOptions, render_print_image, render_layout_page
from thumbnail_preview import render_photo_thumbnail
from photo_edits import validate_edits




def _tk_window_for_test(geometry=None):
    """Abre una ventana solo si el runner permite inicializar Tcl/Tk.

    GitHub Windows puede fallar antes de crear la ventana con
    ``invalid command name "tcl_findLibrary"`` tras pruebas gráficas
    consecutivas. Eso no es un fallo de la aplicación: las pruebas de
    renderizado no gráfico siguen ejecutándose y en un escritorio
    disponible se ejecutan también las aserciones de interfaz.
    """
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tcl/Tk no disponible para pruebas gráficas: {exc}")
    if geometry is not None:
        root.geometry(geometry)
    return root


def image(tmp_path):
    source=tmp_path/'photo.png'
    Image.new('RGB',(600,400),'#E04E30').save(source)
    return source


def test_scaled_thumbnail_has_matching_background_and_smaller_picture(tmp_path):
    photo=image(tmp_path)
    opts=ExportOptions(paper='A4',dpi=120,orientation='Horizontal',
                       fit='Ajustar (sin recortar)',paper_background='Azul noche',
                       photo_edits={photo:validate_edits({'print_scale':.70})})
    thumb=render_photo_thumbnail(photo,opts,max_size=(200,140))
    page,_,_=render_print_image(photo,opts,preview_max_size=(200,140))
    try:
        assert thumb.size==page.size
        # Comprobar color de papel, y que un punto intermedio ahora sea fondo.
        assert thumb.getpixel((8,8))==(11,25,40)
        assert page.getpixel((8,8))==(11,25,40)
        red_thumb=sum(p[0]>150 and p[1]<120 for p in thumb.getdata())
        full,_ ,_=render_print_image(photo,replace(opts,photo_edits={}),preview_max_size=(200,140))
        try:
            red_full=sum(p[0]>150 and p[1]<120 for p in full.getdata())
        finally:full.close()
        assert red_thumb < red_full*0.65
        assert abs(red_thumb - sum(p[0]>150 and p[1]<120 for p in page.getdata()))<160
    finally:
        thumb.close();page.close()


def test_new_general_blur_background_is_accepted_and_exportable(tmp_path):
    photo=image(tmp_path)
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=100,
                       fit='Ajustar (sin recortar)',paper_background='Difuminado',
                       photo_edits={photo:{'print_scale':.65}})
    opts.validate()
    thumb=render_photo_thumbnail(photo,opts,max_size=(160,180))
    page,_,_=render_layout_page((photo,),opts,preview_max_size=(160,180))
    try:
        assert thumb.size==page.size
        assert thumb.getpixel((10,10)) != (255,255,255)
        assert page.getpixel((10,10)) != (255,255,255)
    finally:thumb.close();page.close()


def test_free_and_regular_scale_use_the_same_master_field(tmp_path):
    photo=image(tmp_path)
    opts=ExportOptions(paper='A4',orientation='Horizontal',dpi=100,
                       fit='Ajustar (sin recortar)',layout_template='Diseño libre',
                       paper_background='Azul noche',photos_per_page=1,
                       photo_edits={photo:validate_edits({'print_scale':.70})})
    page,_,_=render_layout_page((photo,),opts,preview_max_size=(380,290))
    normal,_,_=render_layout_page((photo,),replace(opts,photo_edits={}),preview_max_size=(380,290))
    try:
        bg=(11,25,40)
        n0=sum(p != bg for p in normal.getdata())
        n1=sum(p != bg for p in page.getdata())
        assert n1<n0*.65
        assert page.getpixel((0,0))==bg
    finally:page.close();normal.close()


def test_saved_free_background_still_imports_from_old_projects(tmp_path):
    p=image(tmp_path)
    opts=ExportOptions(paper='A4',orientation='Horizontal',dpi=90,
                       fit='Ajustar (sin recortar)',paper_background='Blanco',
                       layout_template='Diseño libre',photos_per_page=1,
                       layout_items={p:{'rect':[.5,.5,.3,.3], 'background':'Crema'}})
    result,_,_=render_layout_page((p,),opts,preview_max_size=(320,230))
    try:assert result.getpixel((0,0))==(246,235,220)
    finally:result.close()


def test_main_header_disables_entire_background_control(tmp_path):
    from main import ReveloApp
    root=_tk_window_for_test()
    app=None
    try:
        app=ReveloApp(root)
        app.fit.set('Rellenar (recortar)');root.update()
        assert str(app.paper_background_combo.cget('state'))=='disabled'
        assert 'desactivado' in app.background_hint.get().lower()
        assert app.paper_background_label.cget('fg')=='#65788B'
        app.fit.set('Ajustar (sin recortar)');root.update()
        assert str(app.paper_background_combo.cget('state'))=='readonly'
        assert app.background_hint.get()==''
    finally:root.destroy()


def test_free_layout_editor_commits_the_shared_size(tmp_path):
    from main import ReveloApp
    photo=image(tmp_path)
    root=_tk_window_for_test('1200x880')
    app=None
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo];app.details[photo]=(600,400)
        app.fit.set('Ajustar (sin recortar)')
        app.paper_background.set('Azul noche')
        app.layout_template.set('Diseño libre')
        app.render_library();app.render_order()
        app.edit_page_layout()
        root.update()
        editor=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        # Ajuste directo del deslizador de tamaño, sin arrastre secreto.
        size_controls=[]
        def walk(w):
            if isinstance(w,tk.Scale) and int(float(w.cget('from')))==25:
                size_controls.append(w)
            for child in w.winfo_children():walk(child)
        walk(editor)
        assert size_controls
        size_controls[0].set(70)
        root.update()
        save=next(w for w in editor.winfo_children() if isinstance(w,tk.Frame)
                  and any(isinstance(c,tk.Button) and c.cget('text')=='Guardar composición' for c in w.winfo_children()))
        next(c for c in save.winfo_children() if isinstance(c,tk.Button) and c.cget('text')=='Guardar composición').invoke()
        root.update()
        assert abs(app.photo_edits[photo]['print_scale']-.70)<.01
        assert app.paper_background.get()=='Azul noche'
        assert 'background' not in app.layout_items[photo]
    finally:root.destroy()


def test_free_background_change_updates_main_and_clears_local_override(tmp_path):
    from main import ReveloApp
    photo=image(tmp_path)
    root=_tk_window_for_test('1200x880')
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo];app.details[photo]=(600,400)
        app.layout_template.set('Diseño libre')
        app.fit.set('Ajustar (sin recortar)')
        app.paper_background.set('Azul noche')
        app.render_library();app.render_order();app.edit_page_layout();root.update()
        editor=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        combos=[]
        from tkinter import ttk
        def walk(w):
            if isinstance(w,ttk.Combobox):combos.append(w)
            for child in w.winfo_children():walk(child)
        walk(editor)
        bg_combo=next(w for w in combos if 'Crema' in w.cget('values'))
        assert bg_combo.get()=='Azul noche'
        bg_combo.set('Crema');bg_combo.event_generate('<<ComboboxSelected>>');root.update()
        btns=[]
        def walk_buttons(w):
            if isinstance(w,tk.Button):btns.append(w)
            for child in w.winfo_children():walk_buttons(child)
        walk_buttons(editor)
        next(b for b in btns if b.cget('text')=='Guardar composición').invoke()
        root.update()
        assert app.paper_background.get()=='Crema'
        assert app.layout_items[photo].get('background') is None
        result,_,_=render_layout_page((photo,),app._options(),preview_max_size=(330,240))
        try:assert result.getpixel((0,0))==(246,235,220)
        finally:result.close()
    finally:root.destroy()


def test_caption_editor_scale_uses_master_print_scale(tmp_path):
    from main import ReveloApp
    photo=image(tmp_path)
    root=_tk_window_for_test('1280x890')
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo];app.details[photo]=(600,400)
        app.captions[photo]={'title':'Prueba','detail':'Pie','photo_scale':.9}
        app.photo_edits[photo]=validate_edits({'print_scale':.8})
        app.render_library();app.render_order()
        app.caption_dialog(photo);root.update()
        editor=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        scale_controls=[]
        def walk(w):
            if isinstance(w,tk.Scale) and int(float(w.cget('from')))==25:
                scale_controls.append(w)
            for child in w.winfo_children():walk(child)
        walk(editor)
        assert scale_controls
        assert abs(scale_controls[0].get()-72)<2
        scale_controls[0].set(65);root.update()
        buttons=[]
        def walk_buttons(w):
            if isinstance(w,tk.Button):buttons.append(w)
            for child in w.winfo_children():walk_buttons(child)
        walk_buttons(editor)
        next(b for b in buttons if b.cget('text')=='Guardar texto').invoke();root.update()
        assert app.photo_edits[photo]['print_scale']==.65
        assert app.captions[photo]['photo_scale']==1
    finally:root.destroy()
