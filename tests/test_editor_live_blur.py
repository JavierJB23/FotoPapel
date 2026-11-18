"""FIX03: editor libre, fondo difuminado, refresco continuo y compatibilidad."""
from pathlib import Path
import os
import pytest
from PIL import Image, ImageChops, ImageDraw

from special_pages import CUSTOM_THEME, validate_special_spec, render_special_page
from custom_editor import PREVIEW_FRAME_MS
from project_io import save_project, load_project
from pdf_sources import recover_sources
from processor import ExportOptions, export_pdf


def image_file(tmp_path):
    photo = tmp_path / 'foto_de_portada.png'
    im = Image.new('RGB', (1400, 700), (17, 72, 150))
    d = ImageDraw.Draw(im)
    d.rectangle((400, 120, 980, 580), fill=(230, 176, 26))
    d.ellipse((630, 270, 760, 400), fill=(240, 255, 240))
    im.save(photo)
    im.close()
    return photo


def spec_for(photo, **changes):
    spec = {'kind':'Portada', 'theme':CUSTOM_THEME, 'title':'ÁLBUM',
            'background_type':'imagen', 'background_image':str(photo),
            'background_fill':'blurred', 'image_mode':'Encajar',
            'background_color':'#F6EBDC', 'show_title':False,
            'show_subtitle':False}
    spec.update(changes)
    return validate_special_spec(spec)


def test_background_blur_extends_original_without_solid_white_bands(tmp_path):
    source = image_file(tmp_path)
    normal = render_special_page(spec_for(source, background_fill='color'), (720, 520))
    blended = render_special_page(spec_for(source), (720, 520))
    try:
        # Encajar: el fondo liso aún existe y debe diferenciarse claramente.
        assert normal.getpixel((10, 10)) == (246, 235, 220)
        assert blended.getpixel((10, 10)) != normal.getpixel((10, 10))
        assert blended.getpixel((10, 10))[2] > blended.getpixel((10, 10))[0]
        assert blended.getpixel((360, 260)) == normal.getpixel((360, 260))
        assert ImageChops.difference(normal, blended).getbbox() is not None
        # La foto central conserva detalles sin blur.
        assert blended.getpixel((360, 260))[1] > 150
    finally:
        normal.close()
        blended.close()


def test_blur_is_optional_and_old_specs_keep_solid_background(tmp_path):
    photo = image_file(tmp_path)
    legacy = validate_special_spec({'kind':'Separador','theme':CUSTOM_THEME,
                                    'background_type':'imagen','background_image':str(photo)})
    assert legacy['background_fill'] == 'color'
    assert validate_special_spec({**legacy,'background_fill':'blurred'})['background_fill'] == 'blurred'
    with pytest.raises(ValueError):
        validate_special_spec({**legacy,'background_fill':'extraño'})
    # El fondo difuminado también debe poder utilizarse con zoom libre.
    img = render_special_page(spec_for(photo,image_mode='Libre',image_zoom_x=.60,
                                       image_zoom_y=.70, image_x=.25), (600, 840))
    assert img.getpixel((590, 20)) != (246, 235, 220)
    img.close()


def test_blur_survives_portable_project_and_reversible_pdf(tmp_path):
    photo=image_file(tmp_path)
    cover=tmp_path/'cover.png'
    clean=spec_for(photo, title='PORTADA')
    from special_pages import save_special_thumbnail
    save_special_thumbnail(cover, clean)
    settings={'paper':'A5','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1}
    saved=tmp_path/'album.revelo'
    source_pdf=tmp_path/'album.pdf'
    save_project(saved,[cover],[cover],{}, {},settings,special_pages={cover:clean})
    export_pdf([cover], ExportOptions(**settings,special_pages={cover:clean}),source_pdf)
    photo.unlink()
    restored=load_project(saved,tmp_path/'restored')
    back=next(iter(restored['special_pages'].values()))
    assert back['background_fill']=='blurred'
    assert Path(back['background_image']).exists()
    recovered_paths,_,_,recovered_specs=recover_sources(source_pdf,tmp_path/'pdf_import',include_specials=True)
    assert len(recovered_paths)==1
    assert recovered_specs[recovered_paths[0]]['background_fill']=='blurred'


def test_repaint_throttled_to_target_refresh_interval():
    assert 0 < PREVIEW_FRAME_MS <= 17


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Requiere una sesión gráfica X11')
def test_editor_is_modeless_and_updates_paper_without_reopening(tmp_path):
    import tkinter as tk
    from main import ReveloApp
    try:
        root=tk.Tk()
    except tk.TclError:
        pytest.skip('No hay servidor gráfico accesible')
    root.geometry('1250x820+0+0')
    app=None
    try:
        app=ReveloApp(root)
        app.paper.set('A4')
        app.orientation.set('Vertical')
        root.update()
        editor=app._custom_page_dialog()
        # _custom_page_dialog no devuelve el editor; hallarlo por el título.
        child=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel)
                   and 'Personalizar' in w.title())
        root.update()
        assert root.grab_current() is None
        assert child.revelo_page_mm==(210,297)
        app.orientation.set('Horizontal')
        app.paper.set('A5')
        app.binding.set('Sí')
        root.update()
        assert child.revelo_page_mm==(210,148)
        app.orientation.set('Vertical')
        root.update()
        assert child.revelo_page_mm==(148,210)
        assert child.winfo_exists()
        child.destroy()
        # Eliminación de los rastreos de los ajustes tras cerrar el editor.
        app.orientation.set('Horizontal')
        root.update()
    finally:
        if app:
            app._close_preview()
            app._close_mobile_import()
            for attr in ('pdf_temp','special_temp','mobile_temp','project_temp'):
                obj=getattr(app,attr,None)
                if obj:obj.cleanup()
        root.destroy()
