"""Regresiones v1.10: transparencia, geometría, proyectos y fuentes intactas."""
from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile
import pytest
from PIL import Image, ImageChops

from revelo_backgrounds import validate_background_spec


def photo(folder, name, color, size=(350, 110)):
    file=folder/name
    Image.new('RGB',size,color).save(file)
    return file


@pytest.mark.parametrize('bad', [
    {'mode':'Imagen','image':''},
    {'mode':'Color','color':'RED'},
    {'mode':'Color','opacity':-1},
    {'mode':'Color','opacity':101},
    {'mode':'Color','opacity':float('nan')},
    {'mode':'Color','opacity':True},
    {'mode':'Ejecutar'},
    {'mode':'Color','extra':8},
])
def test_reject_invalid_backgrounds(bad):
    with pytest.raises(ValueError):validate_background_spec(bad)


def test_legacy_without_new_layers_is_identical(tmp_path):
    from processor import ExportOptions, render_layout_page
    p=photo(tmp_path,'a.png','#B8212B')
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=100,
           fit='Ajustar (sin recortar)',paper_background='Crema')
    original,_,_=render_layout_page((p,),opts,preview_max_size=(240,330))
    same,_,_=render_layout_page((p,),replace(opts,background_global={},
           background_overrides={}),preview_max_size=(240,330))
    try:
        assert ImageChops.difference(original,same).getbbox() is None
    finally:original.close();same.close()


def test_color_background_and_opacity_alter_paper_but_not_photo(tmp_path):
    from processor import ExportOptions, render_layout_page
    p=photo(tmp_path,'a.png',(204,33,38))
    base=ExportOptions(paper='A5',orientation='Vertical',dpi=100,
                       fit='Ajustar (sin recortar)')
    plain,_,_=render_layout_page((p,),base,preview_max_size=(250,320))
    full,_,_=render_layout_page((p,),replace(base,background_global={
        'mode':'Color','color':'#123456','opacity':100}),preview_max_size=(250,320))
    half,_,_=render_layout_page((p,),replace(base,background_global={
        'mode':'Color','color':'#000000','opacity':50}),preview_max_size=(250,320))
    zero,_,_=render_layout_page((p,),replace(base,background_global={
        'mode':'Color','color':'#123456','opacity':0}),preview_max_size=(250,320))
    try:
        assert plain.getpixel((1,1))==(255,255,255)
        assert full.getpixel((1,1))==(18,52,86)
        assert half.getpixel((1,1)) in ((127,127,127),(128,128,128))
        assert ImageChops.difference(zero,plain).getbbox() is None
        x,y=full.width//2,full.height//2
        assert plain.getpixel((x,y)) == full.getpixel((x,y)) == half.getpixel((x,y))
    finally:
        for im in (plain,full,half,zero):im.close()


def test_individual_backgrounds_do_not_override_other_cells(tmp_path):
    from processor import ExportOptions, render_layout_page
    a=photo(tmp_path,'a.png',(180,20,20));b=photo(tmp_path,'b.png',(20,180,20))
    opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',photos_per_page=2,
        fit='Ajustar (sin recortar)',background_global={
          'mode':'Color','color':'#224488','opacity':100},
        background_overrides={a:{'mode':'Color','color':'#AA3355','opacity':100}})
    sheet,_,_=render_layout_page((a,b),opts,preview_max_size=(270,400))
    try:
        colors={rgb for rgb in sheet.getdata()}
        assert (170,51,85) in colors, 'La primera foto tiene su propio fondo'
        assert (34,68,136) in colors, 'La segunda hereda el fondo general'
        assert (180,20,20) in colors and (20,180,20) in colors
    finally:sheet.close()


def test_image_background_used_as_watermark_without_changing_original(tmp_path):
    from processor import ExportOptions,render_layout_page
    p=photo(tmp_path,'photo.png',(230,30,25))
    background=photo(tmp_path,'fondodelibro.png',(20,75,140),(160,240))
    before=p.read_bytes();before_bg=background.read_bytes()
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=90,
                       fit='Ajustar (sin recortar)',background_global={
                        'mode':'Imagen','image':str(background),'opacity':30,'fit':'Cubrir'})
    result,_,_=render_layout_page((p,),opts,preview_max_size=(240,310))
    try:
        corner=result.getpixel((1,1))
        assert 20<corner[0]<255 and 75<corner[1]<255 and 140<corner[2]<=255
        assert result.getpixel((result.width//2,result.height//2))==(230,30,25)
        assert p.read_bytes()==before and background.read_bytes()==before_bg
    finally:result.close()


def test_project_roundtrip_includes_individual_background_images(tmp_path):
    from project_io import save_project,load_project
    p=photo(tmp_path,'original.png',(230,30,25))
    wallpaper=photo(tmp_path,'fondo.png',(18,80,135))
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1}
    dest=tmp_path/'libro.revelo'
    save_project(dest,[p],[p],{p:p.name},{},settings,
        background_global={'mode':'Imagen','image':str(wallpaper),'opacity':28},
        background_overrides={p:{'mode':'Color','color':'#556677','opacity':55}})
    with ZipFile(dest) as z:
        assert any(n.startswith('layer_backdrops/global.') for n in z.namelist())
    loaded=load_project(dest,tmp_path/'unpacked')
    newwall=Path(loaded['background_global']['image'])
    assert newwall.exists() and newwall.read_bytes()==wallpaper.read_bytes()
    assert loaded['background_global']['opacity']==28
    assert loaded['background_overrides'][loaded['paths'][0]]['opacity']==55


def test_legacy_project_loads_without_background_data(tmp_path):
    from project_io import save_project,load_project
    p=photo(tmp_path,'original.png',(200,40,70))
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1}
    dest=tmp_path/'antiguo.revelo'
    save_project(dest,[p],[p],{p:'a'},{},settings)
    loaded=load_project(dest,tmp_path/'loaded')
    assert loaded['background_global']=={}
    assert loaded['background_overrides']=={}


def test_editor_button_exposes_background_options_in_main():
    import tkinter as tk
    from main import ReveloApp
    try:
        root=tk.Tk()
    except tk.TclError:
        pytest.skip('El runner no ofrece escritorio Tk')
    try:
        app=ReveloApp(root)
        assert 'Fondos por foto' in app.background_btn.cget('text')
        assert app.background_global=={} and app.background_overrides=={}
        app.background_global={'mode':'Color','color':'#123456','opacity':40}
        assert app._options().background_global['opacity']==40
    finally:
        root.destroy()


def test_project_embeds_two_independent_background_images(tmp_path):
    from project_io import save_project,load_project
    a=photo(tmp_path,'a.png',(230,40,30))
    b=photo(tmp_path,'b.png',(20,180,30))
    bg1=photo(tmp_path,'fondo1.png',(38,65,175))
    bg2=photo(tmp_path,'fondo2.png',(156,60,95))
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':2}
    dest=tmp_path/'two.revelo'
    save_project(dest,[a,b],[a,b],{a:a.name,b:b.name},{},settings,
         background_overrides={a:{'mode':'Imagen','image':str(bg1),'opacity':25},
                               b:{'mode':'Imagen','image':str(bg2),'opacity':85}})
    with ZipFile(dest) as z:
        layerfiles=[name for name in z.namelist() if name.startswith('layer_backdrops/')]
        assert len(layerfiles)==2
    loaded=load_project(dest,tmp_path/'restored')
    new_a,new_b=loaded['paths']
    assert Path(loaded['background_overrides'][new_a]['image']).read_bytes()==bg1.read_bytes()
    assert Path(loaded['background_overrides'][new_b]['image']).read_bytes()==bg2.read_bytes()


def test_modified_project_background_is_rejected(tmp_path):
    from project_io import save_project,load_project,ProjectError
    a=photo(tmp_path,'source.png',(200,20,15))
    bg=photo(tmp_path,'background.png',(30,100,180))
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1}
    valid=tmp_path/'valid.revelo';corrupt=tmp_path/'corrupt.revelo'
    save_project(valid,[a],[a],{a:a.name},{},settings,
         background_global={'mode':'Imagen','image':str(bg),'opacity':80})
    with ZipFile(valid) as src,ZipFile(corrupt,'w') as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename.startswith('layer_backdrops/'):
                data=b'corrupted background'+data
            dst.writestr(info.filename,data)
    with pytest.raises(ProjectError):
        load_project(corrupt,tmp_path/'invalid')


def test_direct_photo_thumbnail_uses_same_background_as_print(tmp_path):
    from processor import ExportOptions,render_print_image
    from thumbnail_preview import render_photo_thumbnail
    p=photo(tmp_path,'img.png',(240,65,33))
    opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',
           fit='Ajustar (sin recortar)',background_overrides={p:{
           'mode':'Color','color':'#223344','opacity':100}})
    full,_,_=render_print_image(p,opts,preview_max_size=(220,300))
    thumb=render_photo_thumbnail(p,opts,max_size=(220,300))
    try:
        assert full.size==thumb.size
        assert ImageChops.difference(full,thumb).getbbox() is None
        assert thumb.getpixel((0,0))==(34,51,68)
    finally:full.close();thumb.close()
