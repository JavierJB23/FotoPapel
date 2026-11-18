"""Regresiones de Revelo 1.5.2: selección en dos clics y editor libre."""
from pathlib import Path
import pytest
from PIL import Image
from ordering_rules import click_move
from special_pages import validate_special_spec, render_special_page
from project_io import save_project, load_project


def test_two_clicks_then_move_and_cancel():
    a,b,c,cover = map(Path,['uno.png','dos.png','tres.png','portada.png'])
    specs={cover:{'kind':'Portada'}}
    original=[cover,a,b,c]
    arranged, selected, changed=click_move(original,None,c,specs)
    assert arranged==original and selected==c and not changed
    arranged, selected, changed=click_move(arranged,selected,a,specs)
    assert arranged==[cover,c,a,b] and selected is None and changed
    arranged,selected,changed=click_move(arranged,None,b,specs)
    arranged2,selected2,changed2=click_move(arranged,selected,b,specs)
    assert arranged2==arranged and selected2 is None and not changed2
    # Portada inamovible, no se puede mandar contenido a su puesto 1.
    assert click_move(arranged,None,cover,specs)[1] is None
    arranged,selected,_=click_move(arranged,None,b,specs)
    arranged,selected,changed=click_move(arranged,selected,cover,specs)
    assert arranged[0]==cover and arranged[1]==b and changed


def make_spec(path):
    return validate_special_spec({
        'kind':'Portada','theme':'Personalizar','title':'RECETARIO','subtitle':'',
        'background_type':'imagen','background_image':str(path),
        'background_color':'#123456','text_color':'#FFFFFF',
        'show_title':False, 'show_subtitle':False,
        'image_mode':'Libre','image_zoom_x':.4, 'image_zoom_y':.6,
        'image_x':.18, 'image_y':.7
    })


def test_photo_fits_over_custom_colored_background_at_position(tmp_path):
    photo=tmp_path/'foto.png'
    Image.new('RGB',(400,400),'red').save(photo)
    spec=make_spec(photo)
    out=render_special_page(spec,(1000,700))
    assert out.getpixel((999,0)) == (18,52,86)
    assert out.getpixel((180,490))[0] > 200
    assert out.getpixel((820,490)) == (18,52,86)
    out.close()
    spec2={**spec,'image_mode':'Encajar'}
    out=render_special_page(spec2,(1000,700))
    assert out.getpixel((500,350))[0] > 200
    assert out.getpixel((5,5)) == (18,52,86)
    out.close()
    spec3={**spec,'image_mode':'Cubrir'}
    out=render_special_page(spec3,(1000,700))
    assert out.getpixel((5,5))[0] > 200
    out.close()


def test_old_custom_specs_have_same_cover_mode(tmp_path):
    photo=tmp_path/'photo.png'
    Image.new('RGB',(100,100),'red').save(photo)
    bare={'kind':'Portada','theme':'Personalizar','title':'Hola',
          'background_type':'imagen','background_image':str(photo)}
    normalized=validate_special_spec(bare)
    assert normalized['image_mode']=='Cubrir'
    assert normalized['image_zoom_x']==normalized['image_zoom_y']==1.0
    with pytest.raises(ValueError):
        validate_special_spec({**bare, 'image_zoom_x':9})


def test_portable_revelo_project_remembers_freely_transformed_image(tmp_path):
    photo=tmp_path/'photo.png'
    Image.new('RGB',(200,120),'red').save(photo)
    page=tmp_path/'cover.png'
    Image.new('RGB',(600,840),'white').save(page)
    spec=make_spec(photo)
    file=tmp_path/'portable.revelo'
    save_project(file, paths=[page], ordered=[page], labels={page:'Portada'},
                 pdf_origins={}, special_pages={page:spec},
                 settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
                           'dpi':150,'fmt':'PDF','binding':False,'photos_per_page':1})
    photo.unlink()
    res=load_project(file,tmp_path/'out')
    recovered=next(iter(res['special_pages'].values()))
    assert recovered['image_mode']=='Libre'
    assert recovered['image_zoom_x']==.4
    assert recovered['image_zoom_y']==.6
    assert recovered['image_x']==.18
    assert Path(recovered['background_image']).exists()
