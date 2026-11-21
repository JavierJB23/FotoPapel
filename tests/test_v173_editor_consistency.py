"""Regresiones v1.7.3: recortes, escala visible y capas libres."""
from pathlib import Path
import pytest
from PIL import Image, ImageChops

from photo_edits import crop_after_transform, crop_after_straighten, apply_edits,validate_edits
from layout_editor import visible_photo_geometry,validate_layout_item,free_sheet_background
from advanced_layout import has_caption
from processor import ExportOptions,render_layout_page,export_pdf
from special_pages import validate_special_spec,render_special_page
from project_io import save_project,load_project
from pdf_sources import recover_sources


def _solid(folder,name,color,size=(720,440)):
    p=folder/name
    Image.new('RGB',size,color).save(p)
    return p


@pytest.mark.parametrize('mode', (1,-1,'h','v'))
def test_rotating_confirmed_crop_retains_the_same_image_content(mode):
    source=Image.new('RGB',(600,320))
    for x in range(600):
        for y in range(320):
            source.putpixel((x,y),(x%256,y%256,(x//3+y//2)%256))
    crop=[.14,.21,.72,.86]
    before=apply_edits(source,{'crop':crop})
    new_spec={'crop':crop_after_transform(crop,mode)}
    if mode in (1,-1):
        new_spec['turns']=mode%4
        expected=before.transpose(Image.Transpose.ROTATE_270 if mode==1 else Image.Transpose.ROTATE_90)
    else:
        new_spec['flip_h']=mode=='h'
        new_spec['flip_v']=mode=='v'
        from PIL import ImageOps
        expected=ImageOps.mirror(before) if mode=='h' else ImageOps.flip(before)
    result=apply_edits(source,new_spec)
    try:
        assert abs(result.width-expected.width)<=1
        assert abs(result.height-expected.height)<=1
        if result.size==expected.size:
            assert ImageChops.difference(result,expected).getbbox() is None
    finally:source.close();before.close();expected.close();result.close()


def test_straightening_does_not_throw_away_crop():
    original=[.22,.18,.82,.77]
    result=crop_after_straighten(original,(800,500),0,8)
    assert result is not None
    assert result[0] < result[2] and result[1] < result[3]
    assert result[2]-result[0]<.9
    assert crop_after_straighten(result,(800,500),8,0)[0] > .05


def test_cover_photo_edit_scale_affects_page_even_when_no_text(tmp_path):
    photo=_solid(tmp_path,'cover.png',(20,130,90),size=(1000,600))
    base={'kind':'Portada','theme':'Personalizar','title':'',
          'background_type':'imagen','background_image':str(photo),
          'background_color':'#F6EBDC','background_fill':'color',
          'image_mode':'Encajar','show_title':False,'show_subtitle':False}
    large=render_special_page(validate_special_spec(base),(700,500))
    reduced=render_special_page(validate_special_spec({**base,
                        'background_edits':{'print_scale':.40}}),(700,500))
    try:
        def colored(im):
            return sum(1 for pixel in im.getdata() if pixel==(20,130,90))
        assert colored(reduced)<colored(large)*.5
        assert colored(reduced)>1000
    finally:large.close();reduced.close()


def test_photo_scale_alone_is_persisted_and_changes_output(tmp_path):
    path=_solid(tmp_path,'solo.png',(90,140,220))
    spec={'photo_scale':.42,'placement':'Debajo'}
    assert has_caption(spec)
    opts=ExportOptions(paper='A5',dpi=100,captions={path:spec})
    small,_,_=render_layout_page([path],opts,preview_max_size=(550,620))
    normal,_,_=render_layout_page([path],ExportOptions(paper='A5',dpi=100),preview_max_size=(550,620))
    try:
        assert ImageChops.difference(small,normal).getbbox() is not None
        assert small.getpixel((small.width//2,small.height//2))==(90,140,220)
        assert small.getpixel((20,small.height//2))==(255,255,255)
    finally:small.close();normal.close()


def test_selected_rect_matches_actual_photo_aspect():
    photo,outline=visible_photo_geometry((0,0,800,400),(.5,.5,.35,.8),(1600,600),0)
    rw,rh=photo[2]-photo[0],photo[3]-photo[1]
    assert abs(rw/rh-1600/600)<.025
    assert photo==outline
    # El viejo marco podía tener proporción 280x320 aunque la foto fuera panorámica.
    assert rh<120
    turned,out=visible_photo_geometry((0,0,800,400),(.5,.5,.35,.8),(1600,600),90)
    assert (out[2]-out[0]) < (turned[2]-turned[0])
    assert (out[3]-out[1]) > (turned[3]-turned[1])


def test_free_layout_background_and_z_order_overlaps_are_reversible(tmp_path):
    green=_solid(tmp_path,'green.png',(10,200,60))
    red=_solid(tmp_path,'red.png',(230,20,60))
    common={'rect':[.50,.50,.6,.65],'angle':0}
    items={green:{**common,'background':'Crema','z':1},red:{**common,'z':2}}
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=95,
                       layout_template='Diseño libre',photos_per_page=2,
                       layout_items=items)
    page,_,_=render_layout_page((green,red),opts,preview_max_size=(700,500))
    try:
        assert page.getpixel((page.width//2,page.height//2))==(230,20,60)
        assert page.getpixel((4,4))==tuple(bytes.fromhex('F6EBDC'))
    finally:page.close()
    items2={green:{**common,'background':'Aguamarina','z':3},red:{**common,'z':2}}
    opts2=ExportOptions(paper='A5',orientation='Horizontal',dpi=95,
                        layout_template='Diseño libre',photos_per_page=2,
                        layout_items=items2)
    page,_,_=render_layout_page((green,red),opts2,preview_max_size=(700,500))
    try:
        assert page.getpixel((page.width//2,page.height//2))==(10,200,60)
        assert page.getpixel((4,4))==tuple(bytes.fromhex('DDF8EF'))
    finally:page.close()
    assert validate_layout_item(items[green])['background']=='Crema'
    export_path=tmp_path/'reversible.pdf'
    export_pdf((green,red),opts,export_path)
    extracted=recover_sources(export_path,tmp_path/'extract',include_edits=True,
                              include_captions=True,include_specials=True,include_layout=True)
    assert extracted is not None


def test_editor_live_gui_has_preview_and_interactive_scale(tmp_path):
    import os
    if not os.environ.get('DISPLAY'):pytest.skip('Sin pantalla Tk')
    import tkinter as tk
    from caption_editor import edit_caption
    photo=_solid(tmp_path,'image.png',(35,100,210))
    root=tk.Tk()
    root.geometry('1350x820')
    try:
        dialog=edit_caption(root,photo,{'title':'Mi álbum'},
            ExportOptions(paper='A4',orientation='Horizontal',dpi=100),lambda s:None)
        root.update()
        root.after(250,lambda:None)
        root.update()
        found=[]
        def walk(w):
            found.append(w)
            for child in w.winfo_children():walk(child)
        walk(dialog)
        labels=[w.cget('text') for w in found if isinstance(w,tk.Label)]
        assert 'VISTA PREVIA DE LA HOJA · EN DIRECTO' in labels
        assert any(isinstance(w,tk.Canvas) and w.winfo_width()>400 for w in found)
        dialog.destroy()
    finally:root.destroy()
