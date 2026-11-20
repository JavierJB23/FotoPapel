"""Regresión de v1.7.2: lienzos libres, tamaño de foto y números sin fondo."""
from pathlib import Path
from PIL import Image, ImageChops
import pytest

from advanced_layout import NUMBER_FORMATS, validate_caption, draw_page_number
from layout_editor import (validate_layout_item, free_default,
                           editable_template_rects)
from processor import ExportOptions, render_layout_page, export_pdf, export_word
from project_io import save_project,load_project
from pdf_sources import recover_sources


def samples(folder, count=4):
    colors=['#DD4422','#229966','#3366CC','#F0C84F','#663399']
    result=[]
    for i in range(count):
        p=folder/f'{i}.png';Image.new('RGB',(600,380),colors[i]).save(p)
        result.append(p)
    return result


@pytest.mark.parametrize('style',NUMBER_FORMATS)
def test_number_format_without_rectangle(style):
    img=Image.new('RGB',(600,800),'white')
    draw_page_number(img,8,placement='Centro',physical_mm=(148,210),page_index=0,number_format=style)
    # El papel alrededor del número sigue blanco; no se dibuja una pastilla crema.
    assert img.getpixel((300,746))==(255,255,255)
    assert ImageChops.difference(img,Image.new('RGB',img.size,'white')).getbbox() is not None
    img.close()


def test_custom_layout_validation_and_defaults():
    assert validate_layout_item({'rect':[.5,.3,.7,.4],'angle':-32.5})['angle']==-32.5
    assert validate_layout_item({'split_main':.66,'split_small':.38})['split_main']==.66
    for val in ({'rect':[.2,.2,0,.6]}, {'angle':235}, {'split_small':1.1}, {'rect':[0,1,1,'no']}):
        with pytest.raises(ValueError):validate_layout_item(val)
    assert free_default(0,4)['rect']!=free_default(1,4)['rect']


def test_irregular_rects_adjust_without_overlaps():
    bounds=(20,20,780,540)
    for template in ('Grande arriba + 2 abajo','Grande izquierda + 2 derecha','2 arriba + grande abajo'):
        base=editable_template_rects(bounds,9,9,template,{})
        changed=editable_template_rects(bounds,9,9,template,{'split_main':.71,'split_small':.32})
        assert base != changed
        for i,(x,y,r,b) in enumerate(changed):
            assert 20<=x<r<=780 and 20<=y<b<=540
            for a,c,d,e in changed[:i]:
                assert r<=a or d<=x or b<=c or e<=y


def test_free_layout_changes_render_and_preserves_originals(tmp_path):
    paths=samples(tmp_path,3)
    original=[p.read_bytes() for p in paths]
    base=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,photos_per_page=3,
                       layout_template='Diseño libre')
    changed=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,photos_per_page=3,
                          layout_template='Diseño libre',layout_items={paths[0]:{'rect':[.5,.5,.8,.66],'angle':33}})
    before,_,_=render_layout_page(paths,base,preview_max_size=(820,520))
    after,_,_=render_layout_page(paths,changed,preview_max_size=(820,520))
    try:
        assert before.size==after.size
        assert ImageChops.difference(before,after).getbbox() is not None
    finally:
        before.close();after.close()
    assert [p.read_bytes() for p in paths]==original
    out_pdf,_=export_pdf(paths,changed,tmp_path/'free.pdf')
    out_doc,_=export_word(paths,changed,tmp_path/'free.docx')
    assert out_pdf.stat().st_size>1000 and out_doc.stat().st_size>1000


def test_caption_photo_scale_changes_image_size(tmp_path):
    p=samples(tmp_path,1)[0]
    cap={'title':'Verano','placement':'Debajo','photo_scale':.55}
    assert validate_caption(cap)['photo_scale']==.55
    with pytest.raises(ValueError):validate_caption(dict(cap,photo_scale=1.4))
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,
                       captions={p:cap})
    scaled,_,_=render_layout_page((p,),opts,preview_max_size=(770,530))
    cap2={p:dict(cap,photo_scale=1)}
    normal,_,_=render_layout_page((p,),__import__('dataclasses').replace(opts,captions=cap2),preview_max_size=(770,530))
    try:assert ImageChops.difference(scaled,normal).getbbox() is not None
    finally:scaled.close();normal.close()


def test_portable_project_and_pdf_roundtrip_free_layout(tmp_path):
    photos=samples(tmp_path,3)
    geometry={photos[0]:{'rect':[.32,.38,.75,.65],'angle':-18},
              photos[1]:{'rect':[.75,.66,.35,.3],'angle':12}}
    settings={'paper':'A5','orientation':'Horizontal','fit':'Ajustar (sin recortar)',
              'dpi':120,'fmt':'PDF','binding':False,'photos_per_page':3,
              'layout_template':'Diseño libre','numbering_format':'[1]',
              'numbering_enabled':True}
    out=tmp_path/'album.revelo'
    save_project(out,photos,photos,{}, {},settings,layout_items=geometry)
    for p in photos:p.unlink()
    loaded=load_project(out,tmp_path/'unpacked')
    assert loaded['settings']['numbering_format']=='[1]'
    assert loaded['layout_items'][loaded['pages'][0]]['angle']==-18
    opts=ExportOptions(**settings,layout_items=loaded['layout_items'])
    exported,_=export_pdf(loaded['pages'],opts,tmp_path/'album.pdf')
    recovered=recover_sources(exported,tmp_path/'pdf_originals',include_specials=True,
                              include_edits=True,include_captions=True,include_layout=True)
    assert len(recovered)==8
    assert recovered[6][recovered[0][0]]['angle']==-18
    assert recovered[7]=='Diseño libre'


def test_layout_editor_window_controls_under_tk(tmp_path):
    import os
    if not os.environ.get('DISPLAY'):pytest.skip('Necesita pantalla Tk')
    import tkinter as tk
    from layout_editor import edit_sheet
    photos=samples(tmp_path,3)
    root=tk.Tk();root.withdraw()
    recorded=[]
    dialog=edit_sheet(root,photos,'Diseño libre',{},ExportOptions(dpi=120),lambda data:recorded.append(data))
    root.update()
    buttons=[]
    def find(w):
        for x in w.winfo_children():
            if isinstance(x,tk.Button):buttons.append(x)
            find(x)
    find(dialog)
    assert any('Guardar composición'==b.cget('text') for b in buttons)
    next(b for b in buttons if b.cget('text')=='Guardar composición').invoke()
    assert len(recorded)==1 and len(recorded[0])==3
    root.destroy()


def test_main_composition_button_changes_with_template():
    import os
    if not os.environ.get('DISPLAY'):pytest.skip('Necesita pantalla Tk')
    import tkinter as tk
    from main import ReveloApp
    root=tk.Tk();root.withdraw()
    app=ReveloApp(root)
    root.update()
    try:
        assert app.layout_edit_btn.cget('state')=='disabled'
        app.per_sheet.set('3')
        app.layout_template.set('Grande arriba + 2 abajo')
        assert app.layout_edit_btn.cget('state')=='normal'
        assert app.layout_edit_btn.cget('text')=='Tamaño de fotos'
        app.per_sheet.set('4')
        assert app.layout_template.get()=='Cuadrícula'
        app.layout_template.set('Diseño libre')
        assert app.per_sheet.get()=='4'
        assert app.layout_edit_btn.cget('text')=='Editar diseño libre'
        assert app.layout_edit_btn.cget('state')=='normal'
    finally:
        root.destroy()


def test_photo_editor_print_scale_applies_even_without_caption(tmp_path):
    from photo_edits import validate_edits,has_edits
    path=samples(tmp_path,1)[0]
    spec=validate_edits({'print_scale':.55})
    assert spec['print_scale']==.55 and has_edits(spec)
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,
                       photo_edits={path:spec})
    scaled,_,_=render_layout_page((path,),opts,preview_max_size=(750,540))
    default,_,_=render_layout_page((path,),ExportOptions(paper='A5',orientation='Horizontal',dpi=120),
                                   preview_max_size=(750,540))
    try:
        assert ImageChops.difference(scaled,default).getbbox() is not None
        # Al reducir, el borde de la hoja queda blanco sin formar un recuadro
        # artificial sobre la fotografía.
        assert scaled.getpixel((10,10))==(255,255,255)
    finally:scaled.close();default.close()
