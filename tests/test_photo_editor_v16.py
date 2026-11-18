"""Regresiones para el editor no destructivo y los PDF recuperables de v1.6."""
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from photo_edits import DEFAULT, apply_edits, auto_white_crop, geometry_image, validate_edits
from processor import ExportOptions, render_print_image, render_layout_page, export_pdf, source_dimensions
from project_io import save_project, load_project
from pdf_sources import recover_sources


def scene(path: Path):
    im = Image.new('RGB', (800, 500), '#123046')
    dr=ImageDraw.Draw(im)
    dr.rectangle((0,0,100,499),fill='red')
    dr.rectangle((650,0,799,499),fill='lime')
    dr.rectangle((300,130,490,420),fill='yellow')
    im.save(path)
    im.close()
    return path


def test_crop_rotate_flip_color_and_original_unchanged(tmp_path):
    path = scene(tmp_path/'foto.png')
    before = path.read_bytes()
    opts = dict(DEFAULT, turns=1, flip_h=True, crop=[0,0,.5,1], brightness=.6,
                contrast=1.3,saturation=.5,sharpness=1.1)
    with Image.open(path) as original:
        edited=apply_edits(original.convert('RGB'),opts)
        assert edited.size == (250,800)
        edited.close()
    assert path.read_bytes() == before


def test_validated_edits_reject_invalid_payloads():
    for payload in ({'crop':[-1,0,1,1]}, {'brightness':float('nan')},
                    {'turns':'90'}, {'flip_h':'yes'}, {'crop':[0,0,0,1]},
                    {'unknown':'not_allowed'}, {'straighten':90}):
        with pytest.raises(ValueError):validate_edits(payload)


def test_auto_white_border_detects_unequal_margins():
    img=Image.new('RGB',(700,500),'white')
    dr=ImageDraw.Draw(img);dr.rectangle((0,55,699,445),fill='#123456')
    box=auto_white_crop(img)
    assert box is not None
    assert box[0] == 0 and box[2] == 1
    assert .08 < box[1] < .12
    assert .88 < box[3] < .92
    assert auto_white_crop(Image.new('RGB',(400,400),'white')) is None
    img.close()


def test_single_sheet_uses_edit_and_auto_orientation(tmp_path):
    src=scene(tmp_path/'f.png')
    spec=dict(DEFAULT,turns=1,crop=[0,0,1,.5])
    options=ExportOptions(paper='A5',orientation='Automática',dpi=150,photo_edits={src:spec})
    rendered,physical,_=render_print_image(src,options)
    assert physical==(210,148)  # crop after 90° changes aspect from 500×800 to 500×400
    assert rendered.size[0]>rendered.size[1]
    rendered.close()


def test_grid_uses_edits_and_preview_matches_export(tmp_path):
    p1=scene(tmp_path/'1.png');p2=scene(tmp_path/'2.png')
    spec=dict(DEFAULT,turns=1,saturation=0)
    opts=ExportOptions(paper='A5',orientation='Horizontal',photos_per_page=2,dpi=150,
                       fit='Ampliar fondo (sin recortar)',photo_edits={p1:spec})
    full,size,_=render_layout_page([p1,p2],opts)
    preview,psize,_=render_layout_page([p1,p2],opts,preview_max_size=(650,480))
    assert size==psize
    assert full.width>full.height and preview.width<=650
    # Primera mitad en escala de grises; segunda sigue con saturación.
    mid1=full.getpixel((full.width//4,full.height//2))
    mid2=full.getpixel((full.width*3//4,full.height//2))
    assert max(mid1)-min(mid1)<5
    assert max(mid2)-min(mid2)>20
    full.close();preview.close()


def test_project_edits_survive_source_deletion(tmp_path):
    original=scene(tmp_path/'original.png')
    edits=dict(DEFAULT,turns=1,contrast=1.4,crop=[.1,.1,.9,.9])
    project=tmp_path/'Album.revelo'
    save_project(project,[original],[original],{original:'Imagen uno'}, {},
                 {'paper':'A4','orientation':'Automática','fit':'Ajustar (sin recortar)',
                  'dpi':150,'fmt':'PDF','binding':False,'photos_per_page':1},
                 photo_edits={original:edits})
    original.unlink()
    recovered=load_project(project,tmp_path/'loaded')
    assert recovered['photo_edits'][recovered['paths'][0]]['crop']==edits['crop']
    assert recovered['paths'][0].exists()
    options=ExportOptions(dpi=150,photo_edits=recovered['photo_edits'])
    image,_,_=render_print_image(recovered['paths'][0],options)
    assert image.size[0]<image.size[1]
    image.close()


def test_pdf_reimport_recovers_edit_spec_and_original(tmp_path):
    src=scene(tmp_path/'source.png')
    before=src.read_bytes()
    edit=dict(DEFAULT,turns=1,brightness=.7,crop=[0,.2,1,.8])
    opts=ExportOptions(paper='A5',orientation='Automática',dpi=120,
                       fit='Ampliar fondo (sin recortar)',photo_edits={src:edit})
    pdf=tmp_path/'Revelo_A5.pdf'
    export_pdf([src],opts,pdf)
    restored=recover_sources(pdf,tmp_path/'recovered',include_specials=True,include_edits=True)
    assert restored is not None
    paths,sizes,num,specs,edits=restored
    assert len(paths)==1 and num==1
    assert paths[0].read_bytes()==before
    assert edits[paths[0]]['crop']==edit['crop']
    new_opts=ExportOptions(paper='A5',orientation='Automática',dpi=120,photo_edits=edits)
    result,_,_=render_print_image(paths[0],new_opts)
    assert result.width>result.height
    result.close()


def test_legacy_no_edits_is_still_accepted(tmp_path):
    original=scene(tmp_path/'f.png')
    settings={'paper':'A4','orientation':'Automática','fit':'Ajustar (sin recortar)',
             'dpi':150,'fmt':'PDF','binding':False,'photos_per_page':1}
    p=tmp_path/'old.revelo'
    save_project(p,[original],[original],{original:'normal'}, {},settings)
    loaded=load_project(p,tmp_path/'oldfiles')
    assert loaded['photo_edits']=={}


def test_photo_editor_window_opens_and_crop_ui(tmp_path):
    import tkinter as tk
    src=scene(tmp_path/'f.png')
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('Sin pantalla gráfica')
    root.geometry('1280x800')
    root.withdraw()
    from photo_editor_ui import edit_photo
    changes=[]
    editor=edit_photo(root,src,None,lambda s:changes.append(s))
    root.update()
    assert editor.winfo_exists()
    editor.crop_mode.set('1:1 · Cuadrado')
    editor._aspect_changed()
    assert editor.spec['crop'] is not None
    editor.spec['brightness']=1.3
    editor.save()
    assert changes and changes[0]['brightness']==1.3
    root.destroy()
