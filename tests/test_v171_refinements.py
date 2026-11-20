"""Revelo 1.7.1: pies sin recuadros, editor libre y libro visual."""
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from advanced_layout import validate_caption, draw_caption, footer_height_px
from book_renderer import render_book
from processor import ExportOptions, export_pdf, export_word, render_layout_page
from project_io import save_project, load_project
from pdf_sources import recover_sources


def test_caption_old_version_still_loads():
    old={'title':'Recetario','detail':'Navidad','placement':'Debajo'}
    assert validate_caption(old)==old


def test_caption_fonts_colors_sizes_positions():
    data={'title':'Alicante','detail':'Agosto 2026', 'placement':'Personalizado',
          'title_font':'Georgia','detail_font':'Courier New','title_color':'#FFDD44',
          'detail_color':'#1caabb','title_size':19,'detail_size':12,'title_x':.26,
          'title_y':.35,'detail_x':.82,'detail_y':.85,'align':'Derecha'}
    validated=validate_caption(data)
    assert validated['detail_color']=='#1CAABB'
    assert validated['title_x']==.26
    for key,value in [('title_size',300),('detail_font','FuturaX'),('title_color','red'),
                      ('title_x',1.5),('align','diagonal'),('placement','nuevo')]:
        with pytest.raises(ValueError):validate_caption(dict(data,**{key:value}))


def test_no_opaque_caption_background():
    sheet=Image.new('RGB',(480,300),'#F1DDC4')
    before=sheet.getpixel((5,280))
    spec={'title':'Madrid','detail':'Atardecer','placement':'Debajo','title_color':'#000000'}
    draw_caption(sheet,(20,10,460,280),spec,mode='Debajo',px_per_mm=2.8)
    # Los píxeles fuera de las letras conservan exactamente el fondo anterior.
    assert sheet.getpixel((5,280))==before
    assert sheet.getpixel((30,260))==(241,221,196) or sheet.getpixel((31,270))==(241,221,196)
    # También sin panel negro cuando el texto va superpuesto.
    sheet2=Image.new('RGB',(480,300),'#4477AA')
    draw_caption(sheet2,(20,10,460,280),{'title':'Tenis','placement':'Sobre foto'},
                 mode='Sobre foto',px_per_mm=2.8)
    assert sheet2.getpixel((455,260))==(68,119,170)
    sheet.close();sheet2.close()


def test_caption_custom_positions_draw_onto_photo():
    source=Image.new('RGB',(520,360),'#DAD6BD')
    mod=source.copy()
    draw_caption(mod,(0,0,520,360),{'title':'Lago','detail':'2026','placement':'Personalizado',
                                   'title_x':.5,'title_y':.25,'detail_x':.5,'detail_y':.8,
                                   'title_color':'#153E61','detail_color':'#153E61'},
                 mode='Personalizado',px_per_mm=3)
    # Debe dibujar algo cerca de ambas posiciones, manteniendo intactos los bordes.
    assert ImageChops.difference(source,mod).getbbox() is not None
    assert source.getpixel((3,3))==mod.getpixel((3,3))
    source.close();mod.close()


def test_book_cover_has_no_fake_left_page_and_open_has_real_spine():
    left=Image.new('RGB',(480,610),'#F7F2E8')
    right=Image.new('RGB',(480,610),'#6F9EAB')
    cover=render_book((None,left),cover=True)
    open_=render_book((left,right),cover=False)
    assert cover.width>cover.height
    # Izquierda de la cubierta: mesa oscura, no un folio crema falso.
    sample=cover.getpixel((cover.width//5,cover.height//2))
    assert max(sample)<90
    # Los folios abiertos reproducen colores originales y el lomo es oscuro.
    assert open_.getpixel((open_.width//5,open_.height//2))[0]>200
    assert open_.getpixel((open_.width*4//5,open_.height//2))[2]>130
    assert max(open_.getpixel((open_.width//2,open_.height//2)))<135
    cover.close();open_.close();left.close();right.close()


def test_project_and_pdf_keep_custom_caption_settings(tmp_path):
    paths=[]
    for i in range(3):
        p=tmp_path/f'original_{i}.png'
        Image.new('RGB',(700,400),(60+i*35,90+i*30,120+i*30)).save(p)
        paths.append(p)
    spec=validate_caption({'title':'Lisboa','detail':'Primavera 2026',
        'placement':'Personalizado','title_font':'Verdana',
        'detail_font':'Georgia','title_size':22,'detail_size':11,
        'title_color':'#FFFFFF','detail_color':'#112233',
        'title_x':.45,'title_y':.33,'detail_x':.80,'detail_y':.86})
    settings={'paper':'A4','orientation':'Horizontal','fit':'Ajustar (sin recortar)',
              'dpi':120,'fmt':'PDF','binding':False,'photos_per_page':3,
              'layout_template':'Grande arriba + 2 abajo'}
    saved=tmp_path/'viaje.revelo'
    save_project(saved,paths,paths,{}, {},settings,captions={paths[0]:spec})
    for p in paths:p.unlink()
    loaded=load_project(saved,tmp_path/'originales_extraidos')
    assert loaded['captions'][loaded['pages'][0]]==spec
    opts=ExportOptions(**settings,captions=loaded['captions'])
    png,_,_=render_layout_page(loaded['pages'],opts,preview_max_size=(920,620))
    png.close()
    pdf,_=export_pdf(loaded['pages'],opts,tmp_path/'viaje.pdf')
    extracted=recover_sources(pdf,tmp_path/'pdf_sources',include_specials=True,
                              include_edits=True,include_captions=True)
    assert extracted is not None
    assert extracted[5][extracted[0][0]]==spec
    docx,_=export_word(loaded['pages'],opts,tmp_path/'viaje.docx')
    assert docx.stat().st_size>1000


def test_caption_dialog_has_visual_mode_under_xvfb(tmp_path):
    import os
    if not os.environ.get('DISPLAY'):
        pytest.skip('Necesita pantalla Tk')
    import tkinter as tk
    from tkinter import ttk
    from caption_editor import edit_caption
    root=tk.Tk()
    root.withdraw()
    photo=tmp_path/'photo.png'
    Image.new('RGB',(600,440),'#758A8D').save(photo)
    received=[]
    editor=edit_caption(root,photo,{'title':'Versalles','detail':'Francia',
        'placement':'Personalizado'},ExportOptions(dpi=120),lambda val:received.append(val))
    root.update()
    combos=[]
    buttons=[]
    def find(w):
        for child in w.winfo_children():
            if isinstance(child,ttk.Combobox):combos.append(child)
            if isinstance(child,tk.Button):buttons.append(child)
            find(child)
    find(editor)
    assert any('Personalizado' in c['values'] for c in combos)
    assert any('Guardar texto' in b.cget('text') for b in buttons)
    assert any('Abrir editor visual' in b.cget('text') for b in buttons)
    # Guardar conserva el modo y los valores por defecto de tipografía.
    next(b for b in buttons if b.cget('text')=='Guardar texto').invoke()
    assert received[0]['placement']=='Personalizado'
    assert received[0]['title_font']=='Georgia'
    root.destroy()
