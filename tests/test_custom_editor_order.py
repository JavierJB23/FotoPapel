"""Revelo v1.5.1: portada anclada, selección y páginas personalizadas portables."""
from pathlib import Path
from types import SimpleNamespace
import os

import pytest
from PIL import Image, ImageChops

from special_pages import (CUSTOM_THEME, validate_special_spec, render_special_page,
                           save_special_thumbnail)
from ordering_rules import cover_path, anchored_order, move_item
from processor import ExportOptions, export_pdf, render_layout_page
from project_io import save_project, load_project
from pdf_sources import recover_sources


def test_custom_page_color_position_and_optional_text():
    spec = {'kind':'Portada', 'theme':CUSTOM_THEME, 'title':'Mi recetario',
            'subtitle':'Edición 2026', 'title_x':.25,'title_y':.27,
            'subtitle_x':.7,'subtitle_y':.72,'title_size':18,
            'subtitle_size':6,'background_color':'#EEAC77',
            'text_color':'#000000','subtitle_color':'#002030'}
    clean=validate_special_spec(spec)
    page=render_special_page(clean,(640,850))
    assert page.getpixel((0,0)) == (238,172,119)
    centered=render_special_page({**clean,'title_x':.5,'title_y':.6},(640,850))
    diff=ImageChops.difference(page,centered)
    assert diff.getbbox() is not None
    page.close()
    centered.close()
    no_title=validate_special_spec({**spec,'show_title':False,'show_subtitle':False})
    assert no_title['title'] == no_title['subtitle'] == ''
    img=render_special_page(no_title,(640,850))
    assert img.getpixel((320,425)) == (238,172,119)
    img.close()


def test_cover_pinned_and_cannot_be_reordered():
    p=[Path('imagen_1.png'),Path('imagen_2.png'),Path('portada.png'),Path('imagen_3.png')]
    special={p[2]:{'kind':'Portada','theme':'Crema','title':'Recetas'}}
    correct=anchored_order(p,special)
    assert correct[0] == p[2]
    assert cover_path(special) == p[2]
    assert move_item(correct,p[2],3,special)==correct
    assert move_item(correct,p[0],0,special)[0]==p[2]
    assert move_item(correct,p[1],1,special)==[p[2],p[1],p[0],p[3]]
    assert move_item(correct,p[3],2,special)==[p[2],p[0],p[3],p[1]]


def test_custom_background_survives_deleted_original_in_project_and_pdf(tmp_path):
    bg=tmp_path/'fondo_original.jpg'
    Image.new('RGB',(1100,700),(11,85,164)).save(bg,'JPEG',quality=90)
    pic=tmp_path/'receta.png'
    Image.new('RGB',(400,650),'purple').save(pic)
    cover=tmp_path/'portada.png'
    spec=validate_special_spec({
        'kind':'Portada','theme':CUSTOM_THEME,'title':'Mis recetas','subtitle':'2026',
        'background_type':'imagen','background_image':str(bg),
        'title_x':.22,'title_y':.28, 'title_size':14,'subtitle_size':7,
        'background_color':'#F6EBDC','text_color':'#FFFFFF',
        'subtitle_color':'#FFFF00'})
    save_special_thumbnail(cover,spec)
    ordered=[cover,pic]
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':120,'fmt':'PDF','binding':True,'photos_per_page':1}
    pr=tmp_path/'portable.revelo'
    save_project(pr,ordered,ordered,{}, {}, settings,special_pages={cover:spec})
    original_pdf=tmp_path/'original.pdf'
    export_pdf(ordered,ExportOptions(**settings,special_pages={cover:spec}), original_pdf)
    bg.unlink()
    cover.unlink()
    loaded=load_project(pr,tmp_path/'restored')
    newcover=loaded['pages'][0]
    recovered_spec=loaded['special_pages'][newcover]
    assert Path(recovered_spec['background_image']).exists()
    assert recovered_spec['title_x']==.22
    rendered,_,_=render_layout_page((newcover,),ExportOptions(**settings,
                             special_pages=loaded['special_pages']))
    assert rendered.getpixel((0,0))[2] > 100
    rendered.close()
    items,sizes,per_sheet,pdf_specs=recover_sources(original_pdf,tmp_path/'pdfimport',include_specials=True)
    assert len(items)==2 and len(pdf_specs)==1
    assert Path(next(iter(pdf_specs.values()))['background_image']).is_file()
    img,_,_=render_layout_page((items[0],),ExportOptions(**settings,special_pages=pdf_specs))
    assert img.size[0]>200
    img.close()


def test_import_legacy_preset_still_valid(tmp_path):
    cover=tmp_path/'cover.png'
    classic={'kind':'Portada','theme':'Crema','title':'Libro','subtitle':'Cocina'}
    save_special_thumbnail(cover,classic)
    opts={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
          'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1}
    archive=tmp_path/'classic.revelo'
    save_project(archive,[cover],[cover],{}, {},opts,special_pages={cover:classic})
    result=load_project(archive,tmp_path/'unpacked')
    assert next(iter(result['special_pages'].values()))==validate_special_spec(classic)


@pytest.mark.skipif(bool(os.environ.get("CI")), reason="La prueba visual requiere sesión de escritorio")
def test_selections_are_independent_in_actual_tk_window(tmp_path):
    import tkinter as tk
    from main import ReveloApp
    root=tk.Tk()
    root.geometry('1400x860')
    app=None
    try:
        app=ReveloApp(root)
        paths=[]
        for i in range(3):
            p=tmp_path/f'img{i}.png'
            Image.new('RGB',(550,700),(60+i*50,80,100)).save(p)
            paths.append(p)
        app.paths=paths[:]
        app.pages=paths[:]
        for p in paths:
            app.path_labels[p]=p.name
            app.details[p]=(550,700)
        app.selected=paths[0]
        app.order_selected=None
        app.render_library()
        app.render_order()
        root.update()
        # Un clic en el panel derecho NO reordena la foto seleccionada a la izquierda.
        ev=SimpleNamespace(x_root=20,y_root=20,widget=app.order_area.inner.winfo_children()[1])
        app._drag_press(ev,paths[1],'order')
        app._drag_release(ev)
        assert app.selected==paths[0]
        assert app.order_selected==paths[1]
        assert app.pages==paths
        # seleccionar izquierda tampoco cambia la selección de la derecha.
        app._drag_press(ev,paths[2],'library')
        app._drag_release(ev)
        assert app.selected==paths[2] and app.order_selected==paths[1]
        assert app.pages==paths
    finally:
        if app:
            app._close_preview()
            app._close_mobile_import()
            app.pdf_temp.cleanup()
            app.special_temp.cleanup()
            app.mobile_temp.cleanup()
            app.project_temp.cleanup()
        root.destroy()
