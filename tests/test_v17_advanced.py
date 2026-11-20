"""Pruebas Revelo 1.7: composición, libro, caption, numeración y portabilidad."""
from dataclasses import replace
from pathlib import Path
import pytest
from PIL import Image, ImageChops, ImageStat

from advanced_layout import (
    book_spreads, template_rects, numbers_for_groups, validate_caption, has_caption,
)
from processor import ExportOptions, export_pdf, export_word, render_layout_page, page_groups
from project_io import save_project, load_project
from pdf_sources import recover_sources


def samples(tmp):
    out=[]
    for idx, color in enumerate(((221,65,54), (24,143,155), (78,51,131), (255,169,58))):
        p=tmp / f'Foto {idx+1}.png'
        Image.new('RGB',(720,460), color).save(p)
        out.append(p)
    return out


def test_book_spreads():
    assert book_spreads(0)==[]
    assert book_spreads(1)==[(None,0)]
    assert book_spreads(2)==[(None,0),(1,None)]
    assert book_spreads(5)==[(None,0),(1,2),(3,4)]


@pytest.mark.parametrize('template',[
    'Cuadrícula', 'Grande arriba + 2 abajo', 'Grande izquierda + 2 derecha',
    '2 arriba + grande abajo'])
def test_asymmetric_geometry(template):
    bounds=(30,20,760,540)
    cells=template_rects(bounds,9,10,template=template,count=3,landscape=True)
    assert len(cells)==3
    for i, (a,b,c,d) in enumerate(cells):
        assert 30 <= a < c <= 760 and 20 <= b < d <= 540
        for x,y,z,t in cells[:i]:
            assert c <= x or z <= a or d <= y or t <= b
    if template!='Cuadrícula':
        sizes=[(c-a)*(d-b) for a,b,c,d in cells]
        primary = 2 if template == '2 arriba + grande abajo' else 0
        assert sizes[primary] > sizes[(primary+1)%3] and sizes[primary] > sizes[(primary+2)%3]


def test_caption_validation():
    assert validate_caption(None)['placement']=='Debajo'
    assert has_caption(validate_caption({'title':'Roma','detail':'2026','placement':'Sobre foto'}))
    for spec in ({'title':'a'*121},{'title':5},{'placement':'infinito'}):
        with pytest.raises(ValueError):validate_caption(spec)


def test_numbering_skips_specials(tmp_path):
    images=samples(tmp_path)
    specials={images[1]:{'kind':'Portada'}}
    groups=[(images[1],),(images[0],),(images[2],),(images[3],)]
    assert numbers_for_groups(groups,specials,enabled=True,start=12,skip_special=True)==[None,12,13,14]
    assert numbers_for_groups(groups,specials,enabled=True,start=1,skip_special=False)==[1,2,3,4]


@pytest.mark.parametrize('template',[
    'Grande arriba + 2 abajo','Grande izquierda + 2 derecha','2 arriba + grande abajo'])
def test_three_photo_export(template,tmp_path):
    paths=samples(tmp_path)[:3]
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,photos_per_page=3,
                       layout_template=template,numbering_enabled=True,
                       captions={paths[0]:{'title':'Alpes','detail':'Verano · 2026','placement':'Debajo'}})
    image,dims,low=render_layout_page(paths,opts,preview_max_size=(810,550),page_index=0,printed_number=1)
    assert image.width>image.height
    assert image.size[0]<=810 and image.size[1]<=550
    assert dims==(210,148)
    image.close()
    out,_=export_pdf(paths,opts,tmp_path/'album.pdf')
    import pypdfium2
    pdf=pypdfium2.PdfDocument(str(out))
    try: assert len(pdf)==1
    finally:pdf.close()


def test_old_project_compatible_and_new_caption_roundtrip(tmp_path):
    paths=samples(tmp_path)[:3]
    settings={'paper':'A5','orientation':'Horizontal','fit':'Ajustar (sin recortar)',
              'dpi':150,'fmt':'PDF','binding':False,'photos_per_page':3,
              'layout_template':'Grande arriba + 2 abajo', 'numbering_enabled':True,
              'numbering_position':'Exterior', 'numbering_skip_special':True,
              'numbering_start':8}
    cap={paths[1]:{'title':'Un día en Madrid','detail':'Navidad 2026','placement':'Sobre foto'}}
    target=tmp_path/'revelo.revelo'
    save_project(target,paths,paths,{}, {},settings,captions=cap)
    for path in paths:path.unlink()
    data=load_project(target,tmp_path/'recuperadas')
    assert data['settings']['numbering_start']==8
    assert data['captions'][data['paths'][1]]==cap[next(iter(cap))]
    out,_=export_pdf(data['pages'],ExportOptions(**settings,captions=data['captions']),tmp_path/'reversible.pdf')
    recovered=recover_sources(out,tmp_path/'pdf_extract',include_specials=True,
                              include_edits=True,include_captions=True)
    assert recovered is not None
    assert len(recovered[0])==3 and recovered[2]==3
    assert recovered[5][recovered[0][1]]['title']=='Un día en Madrid'


def test_caption_renders_in_word_and_page_count(tmp_path):
    paths=samples(tmp_path)
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=120,
                       photos_per_page=3,captions={paths[0]:{'title':'Fotografía 1'}})
    out,_=export_word(paths,opts,tmp_path/'album.docx')
    from zipfile import ZipFile
    with ZipFile(out) as z:
        assert len([n for n in z.namelist() if n.startswith('word/media/')])==2


def test_invalid_template_rejected():
    with pytest.raises(ValueError): ExportOptions(photos_per_page=4,layout_template='Grande arriba + 2 abajo').validate()


def test_file_drop_parses_paths_with_spaces_and_folders(tmp_path):
    import tkinter as tk
    from types import SimpleNamespace
    from main import ReveloApp
    pictures = tmp_path/'Fotos del verano'
    pictures.mkdir()
    two = pictures/'segunda foto.png'
    one = pictures/'primera foto.jpg'
    one.write_bytes(b'image1');two.write_bytes(b'image2')
    other = tmp_path/'un documento.pdf'; other.write_bytes(b'pdf')
    fake = ReveloApp.__new__(ReveloApp)
    fake.is_busy=False
    fake.root=SimpleNamespace(tk=tk.Tcl())
    calls=[]
    fake.import_paths = lambda items: calls.append(items)
    fake._on_file_drop(SimpleNamespace(data=f'{{{pictures}}} {{{other}}}'))
    assert len(calls)==1
    assert set(calls[0])=={one,two,other}
