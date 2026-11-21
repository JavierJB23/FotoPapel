"""v1.7.5: fondo de ajuste, entrada de giro y miniatura de hoja libre."""
import os
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image, ImageTk

from processor import ExportOptions, render_layout_page, render_print_image, PAPER_BACKGROUND_PRESETS
from layout_editor import free_sheet_background
from project_io import save_project, load_project


def _sample(folder, name, color=(190,45,20), size=(420,180)):
    path=folder/name
    Image.new('RGB', size, color).save(path)
    return path


def test_custom_background_on_adjust_without_cropping(tmp_path):
    image=_sample(tmp_path, 'wide.png')
    opts=ExportOptions(paper='A4', orientation='Vertical', fit='Ajustar (sin recortar)', dpi=100,
                       paper_background='Personalizado', paper_background_color='#214F77')
    result, _, _=render_print_image(image,opts,preview_max_size=(500,700))
    try:
        assert result.getpixel((3,3))==(33,79,119)
        assert result.getpixel((result.width//2,result.height//2))==(190,45,20)
        assert result.height>result.width
    finally:result.close()
    # Sigue siendo blanco por defecto, como los proyectos antiguos.
    old,_ ,_=render_print_image(image,replace(opts,paper_background='Blanco'))
    try:assert old.getpixel((3,3))==(255,255,255)
    finally:old.close()


@pytest.mark.parametrize('palette,hexcode', list(PAPER_BACKGROUND_PRESETS.items()))
def test_named_paper_background_applies_to_multiple_photos(tmp_path,palette,hexcode):
    paths=[_sample(tmp_path,f'{i}.png') for i in range(2)]
    opts=ExportOptions(paper='A4',orientation='Horizontal',dpi=85,
                       fit='Ajustar (sin recortar)',paper_background=palette,photos_per_page=2)
    preview,_,_=render_layout_page(paths,opts,preview_max_size=(580,440))
    try: assert preview.getpixel((0,0))==tuple(bytes.fromhex(hexcode[1:]))
    finally:preview.close()


def test_background_of_free_sheet_follows_global_when_not_overridden(tmp_path):
    p=_sample(tmp_path,'sample.png')
    opts=ExportOptions(paper_background='Aguamarina',fit='Ajustar (sin recortar)')
    normal=free_sheet_background([p],opts,(350,200))
    forced=free_sheet_background([p],opts,(350,200),'Azul noche')
    try:
        assert normal.getpixel((1,1))==tuple(bytes.fromhex('DDF8EF'))
        assert forced.getpixel((1,1))==tuple(bytes.fromhex('0B1928'))
    finally:normal.close();forced.close()


def test_background_setting_persists_in_project(tmp_path):
    p=_sample(tmp_path,'stored.png')
    settings={'paper':'A4','orientation':'Vertical','fit':'Ajustar (sin recortar)',
              'dpi':100,'fmt':'PDF','binding':False,'photos_per_page':1,
              'paper_background':'Personalizado','paper_background_color':'#224466'}
    dest=tmp_path/'test.revelo'
    save_project(dest,[p],[p],{}, {}, settings)
    loaded=load_project(dest,tmp_path/'opened')
    assert loaded['settings']['paper_background']=='Personalizado'
    assert loaded['settings']['paper_background_color']=='#224466'
    opts=ExportOptions(**settings)
    opts.validate()
    with pytest.raises(ValueError):replace(opts,paper_background_color='wrong').validate()


@pytest.mark.skipif(not os.environ.get('DISPLAY'),reason='Necesita interfaz Tk')
def test_gui_main_shows_composed_sheet_and_background_controls(tmp_path):
    import tkinter as tk
    from main import ReveloApp
    from processor import source_dimensions
    p1=_sample(tmp_path,'a.png',(220,75,50))
    p2=_sample(tmp_path,'b.png',(40,170,230))
    root=tk.Tk();root.geometry('1500x900')
    app=None
    try:
        app=ReveloApp(root)
        app.paths=[p1,p2];app.pages=[p1,p2]
        app.details={p1:source_dimensions(p1),p2:source_dimensions(p2)}
        app.render_library()
        app.per_sheet.set('2');app.layout_template.set('Diseño libre')
        app.layout_items={p1:{'rect':[.28,.4,.45,.3],'background':'Azul noche','background_color':'#0B1928'},
                          p2:{'rect':[.7,.65,.4,.3]}}
        app.render_library();app.render_order();root.update()
        group_preview=app._sheet_thumbnail((p1,p2),0)
        image=ImageTk.getimage(group_preview).convert('RGB')
        # Los bordes visibles en la miniatura corresponden al papel azul noche.
        assert any(pixel[:3]==(11,25,40) for pixel in [image.getpixel((12,16)),image.getpixel((15,20)),image.getpixel((30,12))])
        image.close()
        assert str(app.paper_background_combo.cget('state'))=='readonly'
        app.fit.set('Rellenar (recortar)')
        assert str(app.paper_background_combo.cget('state'))=='disabled'
        app.fit.set('Ajustar (sin recortar)')
        app.paper_background.set('Crema');root.update()
        assert app._options().paper_background=='Crema'
    finally:root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'),reason='Necesita interfaz Tk')
def test_numeric_angle_entry_modifies_saved_free_layout(tmp_path):
    import tkinter as tk
    from layout_editor import edit_sheet
    p=_sample(tmp_path,'angle.png')
    root=tk.Tk();root.geometry('1300x900')
    saved=[]
    try:
        dialog=edit_sheet(root,[p],'Diseño libre',{},ExportOptions(paper='A4',dpi=100),saved.append)
        root.update()
        fields=[];buttons=[]
        def collect(widget):
            if isinstance(widget,tk.Entry):fields.append(widget)
            if isinstance(widget,tk.Button):buttons.append(widget)
            for child in widget.winfo_children():collect(child)
        collect(dialog)
        giro=next(field for field in fields if int(field.cget('width'))==6)
        giro.delete(0,'end');giro.insert(0,'31')
        giro.focus_force();root.update()
        giro.event_generate('<Return>');root.update()
        root.after(100,root.quit);root.mainloop()
        # El número también se aplica al terminar de escribir, sin pulsar Intro.
        giro.focus_force();giro.delete(0,'end');giro.insert(0,'-22,5')
        root.after(260,root.quit);root.mainloop()
        save=next(b for b in buttons if b.cget('text')=='Guardar composición')
        save.invoke();root.update()
        assert saved
        assert saved[0][p]['angle']==-22.5
    finally:root.destroy()


def test_pdf_and_word_have_same_colored_paper(tmp_path):
    from io import BytesIO
    from zipfile import ZipFile
    import pypdfium2
    from processor import export_pdf, export_word
    path=_sample(tmp_path, 'export.png')
    opts=ExportOptions(paper='A5',orientation='Vertical',dpi=100,
                       fit='Ajustar (sin recortar)',paper_background='Azul noche')
    pdf_path,_=export_pdf([path],opts,tmp_path/'out.pdf')
    with pypdfium2.PdfDocument(str(pdf_path)) as pdf:
        raster=pdf[0].render(scale=1).to_pil().convert('RGB')
        try:
            assert all(abs(a-b)<12 for a,b in zip(raster.getpixel((8,8)), (11,25,40)))
        finally:raster.close()
    word_path,_=export_word([path],opts,tmp_path/'out.docx')
    with ZipFile(word_path) as doc:
        media=[name for name in doc.namelist() if name.startswith('word/media/')]
        assert media
        with Image.open(BytesIO(doc.read(media[0]))) as im:
            corner=im.convert('RGB').getpixel((8,8))
            assert all(abs(a-b)<12 for a,b in zip(corner,(11,25,40)))
