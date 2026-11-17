"""Revelo v1.5: portadas, separadores y hojas independientes."""
from pathlib import Path
from zipfile import ZipFile
from PIL import Image, ImageDraw
import pytest

from processor import ExportOptions, page_groups, render_layout_page, export_pdf, export_word, export_images, pixel_size
from project_io import save_project, load_project
from pdf_sources import recover_sources
from special_pages import render_special_page, save_special_thumbnail, validate_special_spec, THEMES


def make_set(tmp_path):
    files = []
    for i in range(8):
        path = tmp_path / f"foto_{i}.jpg"
        Image.new("RGB", (740,490), (90+i*14, 80, 130)).save(path)
        files.append(path)
    special = tmp_path / "separador.png"
    spec = {"kind":"Separador", "title":"Postres", "subtitle":"Tartas, galletas y otros dulces", "theme":"Crema"}
    save_special_thumbnail(special,spec,landscape=False)
    return files[:4] + [special] + files[4:], {special: spec}


def test_special_spec_validation():
    spec = validate_special_spec({"kind":"Página en blanco", "title":"No lo pongas", "theme":"Blanco"})
    assert spec["title"] == ""
    assert spec["subtitle"] == ""
    with pytest.raises(ValueError):
        validate_special_spec({"kind":"Separador", "title":""})
    with pytest.raises(ValueError):
        validate_special_spec({"kind":"Portada", "title":"x" * 121})
    with pytest.raises(ValueError):
        validate_special_spec({"kind":"Código", "title":"x"})


@pytest.mark.parametrize("per_sheet, expected", [(1,9),(2,5),(4,3),(6,3),(9,3)])
def test_breaks_group_always_standalone(tmp_path, per_sheet, expected):
    items, specials = make_set(tmp_path)
    groups = page_groups(items, per_sheet, specials)
    assert len(groups) == expected
    assert any(group == (items[4],) for group in groups)
    assert groups[0][0] == items[0] and groups[-1][-1] == items[-1]
    assert all(len(group)==1 for group in groups if items[4] in group)


def test_full_bleed_chapter_and_blank_in_binding(tmp_path):
    items,specials = make_set(tmp_path)
    opts = ExportOptions(paper="A5",orientation="Vertical",dpi=150,photos_per_page=4,
                         fit="Ampliar fondo (sin recortar)",binding=True,special_pages=specials)
    img, dims, lowres = render_layout_page((items[4],), opts, page_index=1)
    try:
        assert img.size == pixel_size(148,210,150)
        assert img.getpixel((0,0)) == (246,235,220)
        assert img.getpixel((img.width-1,img.height-1)) == (246,235,220)
        palette = (246,235,220)
        assert any(img.getpixel((img.width//2,y)) != palette for y in range(img.height//4, 3*img.height//4, 15))
        assert not lowres
    finally:
        img.close()
    spec={"kind":"Página en blanco","theme":"Blanco","title":"","subtitle":""}
    blank = render_special_page(spec,(900,1200))
    assert blank.getpixel((400,600)) == (255,255,255)
    blank.close()


def test_project_roundtrip_and_export_stays_standalone(tmp_path):
    import pypdfium2
    items,specials = make_set(tmp_path)
    settings={"paper":"A5","orientation":"Vertical","fit":"Ajustar (sin recortar)",
              "dpi":150,"fmt":"PDF","binding":True,"photos_per_page":4}
    project = tmp_path / "mi_recetario.revelo"
    save_project(project,items,items,{p:p.stem for p in items},{},settings,special_pages=specials)
    for f in items:
        f.unlink()
    loaded = load_project(project,tmp_path/"unpacked")
    assert len(loaded["special_pages"])==1
    assert list(loaded["special_pages"].values())[0]["title"] == "Postres"
    assert len(page_groups(loaded['pages'],4,loaded['special_pages']))==3
    opts=ExportOptions(**settings,special_pages=loaded['special_pages'])
    pdf,low = export_pdf(loaded['pages'],opts,tmp_path/'recetario.pdf')
    assert low == 0 or low >= 0
    doc=pypdfium2.PdfDocument(str(pdf))
    try:
        assert len(doc)==3
        image=doc[1].render(scale=1).to_pil()
        assert max(abs(a-b) for a,b in zip(image.convert('RGB').getpixel((0,0)),(246,235,220))) <= 3
        image.close()
    finally:
        doc.close()
    word,_=export_word(loaded['pages'],opts,tmp_path/'recetario.docx')
    with ZipFile(word) as z:
        assert len([a for a in z.namelist() if a.startswith('word/media/')])==3
    recovered, sizes, per_page, recovered_specials = recover_sources(
        pdf,tmp_path/"from_pdf",include_specials=True)
    assert per_page==4 and len(recovered)==9 and len(recovered_specials)==1
    assert list(recovered_specials.values())[0]['title']=='Postres'
    assert len(page_groups(recovered,per_page,recovered_specials))==3


def test_one_sheet_image_export_special_is_png(tmp_path):
    items, specials = make_set(tmp_path)
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=100,fmt='Imagenes',
                       photos_per_page=1,special_pages=specials)
    folder,_=export_images(items[4:5],opts,tmp_path)
    pngs=list(folder.glob('*.png'))
    assert len(pngs)==1
    assert pngs[0].name.startswith('01_')


def test_old_project_without_specials_still_loads(tmp_path):
    pic=tmp_path/'pic.png'
    Image.new('RGB',(400,300),'red').save(pic)
    settings={'paper':'A4','orientation':'Automática','fit':'Ajustar (sin recortar)',
              'dpi':150,'fmt':'PDF','binding':False,'photos_per_page':1}
    pr=tmp_path/'old.revelo'
    save_project(pr,[pic],[pic],{}, {},settings)
    loaded=load_project(pr,tmp_path/'restored')
    assert loaded['special_pages']=={}


def test_multiple_special_pages_between_photos(tmp_path):
    photos, specials = make_set(tmp_path)
    cover=tmp_path/'portada.png'
    blank=tmp_path/'blanco.png'
    cover_spec={'kind':'Portada','title':'Mis recetas','subtitle':'Un libro de cocina','theme':'Azul noche'}
    blank_spec={'kind':'Página en blanco','title':'','subtitle':'','theme':'Blanco'}
    save_special_thumbnail(cover,cover_spec)
    save_special_thumbnail(blank,blank_spec)
    specials.update({cover:cover_spec,blank:blank_spec})
    ordered=[cover,*photos[:4],blank,*photos[4:]]
    groups=page_groups(ordered,4,specials)
    assert [len(g) for g in groups]==[1,4,1,1,4]
