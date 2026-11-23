"""FIX04: ventana única, fondos independientes y compatibilidad con navegación vieja."""
from pathlib import Path
import tkinter as tk
import pytest
from PIL import Image

from revelo_navigation_seamless import with_page_background


def _root():
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip('Sin escritorio Tk disponible')


def _walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _walk(child)


def _button(dialog, caption):
    buttons = [w for w in _walk(dialog) if isinstance(w, tk.Button)
               and w.cget('text') == caption]
    assert len(buttons) == 1, (caption, len(buttons))
    return buttons[0]


def _photos(folder, count):
    out = []
    for i in range(count):
        p = folder / f'foto{i + 1}.png'
        Image.new('RGB', (200, 140), (75+i*25, 90, 140)).save(p)
        out.append(p)
    return out


def test_only_active_sheet_backgrounds_change_and_no_mutation():
    paths=[Path(f'{i}.png') for i in range(6)]
    overrides = {
        paths[0]: {'mode': 'Color', 'color': '#FF2200', 'opacity': 70},
        paths[1]: {'mode': 'Imagen', 'image': 'foto.png', 'opacity': 30},
        paths[2]: {'mode': 'Color', 'color': '#11AA22', 'opacity': 20},
        paths[4]: {'mode': 'Difuminado', 'opacity': 60},
    }
    original={p:dict(s) for p,s in overrides.items()}
    first=with_page_background(overrides, paths[:2], 'Crema', '#FFFFFF')
    assert first[paths[0]]['color']=='#F6EBDC'
    assert first[paths[1]]['color']=='#F6EBDC'
    assert first[paths[0]]['opacity']==100
    assert first[paths[2]]==original[paths[2]]
    assert first[paths[4]]==original[paths[4]]
    assert overrides == original
    restored=with_page_background(first, paths[:2], 'Según encaje', '#FFFFFF')
    assert paths[0] not in restored and paths[1] not in restored
    assert restored[paths[2]]==original[paths[2]]
    assert restored[paths[4]]==original[paths[4]]


def test_custom_background_applies_to_one_sheet_only():
    a,b,c,d=(Path(f'{i}.png') for i in range(4))
    source={c:{'mode':'Color','color':'#0088FF','opacity':30}}
    updated=with_page_background(source, (a,b), 'Personalizado', '#ABCDEF')
    assert updated[a]['color']==updated[b]['color']=='#ABCDEF'
    assert updated[c]==source[c]
    assert d not in updated
    with pytest.raises(ValueError):
        with_page_background(source,(a,b),'Personalizado','not-a-color')


def test_same_window_switches_multiple_sheets_and_preserves_individual_backgrounds(tmp_path, monkeypatch):
    """Ejecución real en Windows: no se destruye el Toplevel en cada clic."""
    from processor import source_dimensions
    from main import ReveloApp
    root=_root()
    dialog=None
    try:
        app=ReveloApp(root)
        paths=_photos(tmp_path,5)
        app.paths=list(paths)
        app.pages=list(paths)
        app.details={p:source_dimensions(p) for p in paths}
        app.path_labels={p:p.name for p in paths}
        app.background_overrides={
            paths[0]: {'mode':'Color','color':'#EF5533','opacity':35},
            paths[1]: {'mode':'Color','color':'#2255EF','opacity':85},
            paths[2]: {'mode':'Color','color':'#55AA22','opacity':25},
            paths[3]: {'mode':'Color','color':'#DD1188','opacity':65},
        }
        frozen={p:dict(s) for p,s in app.background_overrides.items()}
        monkeypatch.setattr(app,'render_library',lambda:None)
        monkeypatch.setattr(app,'render_order',lambda:None)
        app.per_sheet.set('2')
        app.layout_template.set('Diseño libre')
        app.edit_page_layout()
        root.update()
        windows=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)
                 and 'Diseño libre' in w.title()]
        assert len(windows)==1
        dialog=windows[0]
        widget_path=str(dialog)
        original_size=dialog.geometry()
        _button(dialog, 'Siguiente').invoke()
        root.update()
        assert dialog.winfo_exists() and str(dialog)==widget_path
        assert app.order_selected==paths[2]
        assert app.background_overrides==frozen, 'Navegar no debe reescribir fondos'
        _button(dialog, 'Siguiente').invoke()
        root.update()
        assert dialog.winfo_exists() and str(dialog)==widget_path
        assert app.order_selected==paths[4]
        assert _button(dialog,'Siguiente').cget('state')=='disabled'
        _button(dialog,'Anterior').invoke()
        root.update()
        assert app.order_selected==paths[2]
        assert app.background_overrides==frozen
        assert dialog.winfo_exists() and str(dialog)==widget_path
        assert dialog.winfo_width()>0 and dialog.winfo_height()>0
    finally:
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        root.destroy()


def test_new_palette_on_one_sheet_does_not_change_other_sheet_or_global(tmp_path, monkeypatch):
    """Probar el guardado REAL del control de la hoja, sin cambiar el menú general."""
    from processor import source_dimensions
    from main import ReveloApp
    root=_root()
    dialog=None
    try:
        app=ReveloApp(root)
        paths=_photos(tmp_path,4)
        app.paths=list(paths); app.pages=list(paths)
        app.details={p:source_dimensions(p) for p in paths}
        app.path_labels={p:p.name for p in paths}
        app.background_overrides={paths[2]:{
            'mode':'Color','color':'#CC4488','opacity':35}}
        monkeypatch.setattr(app,'render_library',lambda:None)
        monkeypatch.setattr(app,'render_order',lambda:None)
        app.per_sheet.set('2');app.layout_template.set('Diseño libre')
        before_global=app.paper_background.get()
        app.edit_page_layout();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel)
                    and 'Diseño libre' in w.title())
        # Seleccionar el desplegable de fondo del editor libre (no el de la raíz).
        from tkinter import ttk
        candidates=[w for w in _walk(dialog) if isinstance(w,ttk.Combobox)
                    and 'Crema' in w.cget('values')]
        assert len(candidates)==1
        candidates[0].set('Aguamarina')
        _button(dialog,'Siguiente').invoke();root.update()
        assert app.background_overrides[paths[0]]['color']=='#DDF8EF'
        assert app.background_overrides[paths[1]]['color']=='#DDF8EF'
        assert app.background_overrides[paths[2]]['color']=='#CC4488'
        assert paths[3] not in app.background_overrides
        assert app.paper_background.get()==before_global
        _button(dialog,'Anterior').invoke();root.update()
        assert app.background_overrides[paths[0]]['color']=='#DDF8EF'
        assert app.background_overrides[paths[2]]['color']=='#CC4488'
    finally:
        if dialog is not None and dialog.winfo_exists():dialog.destroy()
        root.destroy()


def test_render_page_2_identical_before_and_after_editing_page_1(tmp_path):
    """El motor real de vista previa/exportación solo altera la hoja editada."""
    from dataclasses import replace
    from PIL import ImageChops
    from processor import ExportOptions, render_layout_page
    paths=_photos(tmp_path,4)
    common={p:{'rect':[.25 if i%2==0 else .75,.5,.23,.22]}
            for i,p in enumerate(paths)}
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=90,
        photos_per_page=2,layout_template='Diseño libre',
        background_overrides={paths[2]:{
            'mode':'Color','color':'#CC4488','opacity':35}},
        layout_items=common)
    before,_,_=render_layout_page(paths[2:],opts,preview_max_size=(270,330))
    edited=with_page_background(opts.background_overrides,paths[:2],
                                'Personalizado','#214F77')
    modified=replace(opts,background_overrides=edited)
    after,_,_=render_layout_page(paths[2:],modified,preview_max_size=(270,330))
    first,_,_=render_layout_page(paths[:2],modified,preview_max_size=(270,330))
    try:
        assert ImageChops.difference(before,after).getbbox() is None
        assert first.getpixel((5,5))==(33,79,119)
        assert edited[paths[2]]==opts.background_overrides[paths[2]]
    finally:
        before.close();after.close();first.close()
