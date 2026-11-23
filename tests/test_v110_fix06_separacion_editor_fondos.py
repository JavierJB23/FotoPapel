"""FIX06: sólo el editor 'Fondos por foto · opacidad' modifica los fondos.

No desactivar las pruebas heredadas; esta batería añade comprobaciones reales
con el motor de impresión y el mismo renderizador de Diseño libre.
"""
from pathlib import Path
from dataclasses import replace
from PIL import Image, ImageChops


def _fixture(tmp_path):
    paths=[]
    for i,color in enumerate(((230, 30, 50),(30, 210, 70),(80, 80, 230))):
        path=tmp_path / f'photo{i}.png'
        Image.new('RGB',(280,180),color).save(path)
        paths.append(path)
    return paths


def test_editor_options_never_modify_global_or_individual_backgrounds(tmp_path):
    from processor import ExportOptions
    from revelo_shared_layout import editor_options
    photos=_fixture(tmp_path)
    layout={photos[0]:{'rect':[.25,.5,.25,.3]},
            photos[1]:{'rect':[.75,.5,.25,.3]}}
    individual={
        photos[0]:{'mode':'Color','color':'#D0A122','opacity':28},
        photos[1]:{'mode':'Color','color':'#4E25E0','opacity':72},
        photos[2]:{'mode':'Color','color':'#113355','opacity':90},
    }
    global_bg={'mode':'Color','color':'#171717','opacity':100}
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=90,
        fit='Ajustar (sin recortar)',photos_per_page=2,
        layout_template='Diseño libre',layout_items=layout,
        paper_background='Crema',background_global=global_bg,
        background_overrides=individual)
    for pretend_kind, pretend_color, dirty in [
        ('Difuminado','#00FF00',True),
        ('Personalizado','#0000FF',True),
        ('Blanco','#FF11FF',False),
    ]:
        changed=editor_options(opts,photos[:2],'Diseño libre',layout,{},
                               {photos[0]:1.0,photos[1]:1.0},
                               pretend_kind,pretend_color,dirty)
        assert changed.paper_background==opts.paper_background
        assert changed.paper_background_color==opts.paper_background_color
        assert changed.background_global==global_bg
        assert changed.background_overrides==individual
        assert changed.background_overrides[photos[2]]==individual[photos[2]]
        assert 'background' not in changed.layout_items[photos[0]]
    assert opts.background_overrides==individual


def test_free_editor_is_pixel_identical_to_exported_page_with_individual_layers(tmp_path):
    """Dos fondos diferentes/opacidades, sin fondo artificial del editor."""
    from processor import ExportOptions, render_layout_page
    from revelo_shared_layout import render_editor_sheet
    photos=_fixture(tmp_path)
    layout={photos[0]:{'rect':[.25,.5,.25,.3]},
            photos[1]:{'rect':[.75,.5,.25,.3]}}
    individual={
        photos[0]:{'mode':'Color','color':'#FFB222','opacity':40},
        photos[1]:{'mode':'Color','color':'#1144B5','opacity':100},
        photos[2]:{'mode':'Color','color':'#AA0000','opacity':70},
    }
    opts=ExportOptions(paper='A5',orientation='Horizontal',dpi=90,
        fit='Ajustar (sin recortar)',photos_per_page=2,
        layout_template='Diseño libre',layout_items=layout,
        paper_background='Azul noche',background_overrides=individual)
    original,_,_=render_layout_page(photos[:2],opts,
                                   preview_max_size=(280,330),page_index=0)
    edited,_,_=render_editor_sheet(photos[:2],opts,'Diseño libre',layout,{},
        {photos[0]:1,photos[1]:1},'Difuminado','#EE00EE',(280,330),
        page_index=0,background_dirty=True)
    try:
        assert original.size==edited.size
        assert ImageChops.difference(original,edited).getbbox() is None
        assert opts.background_overrides[photos[2]]==individual[photos[2]]
    finally:
        original.close();edited.close()
