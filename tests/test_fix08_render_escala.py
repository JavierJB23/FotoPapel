"""FIX08: tests del zoom, la transparencia y la actualización real de la hoja.

Se incluyen en el repositorio para ejecutarse con el código auténtico en CI.
"""
from dataclasses import replace
from pathlib import Path
import tkinter as tk
import pytest
from PIL import Image, ImageChops

from revelo_free_layers import visible_photo_patch, editing_alpha
from revelo_button_skin import style_button


def test_render_recortado_no_crea_imagen_gigante():
    source=Image.new('RGB',(150,100),'#BD1D29')
    result=visible_photo_patch(source,None,(0,0,300,260),(150,130),(2400,1600),25)
    assert result is not None
    patch,(x,y)=result
    try:
        assert patch.width<=300 and patch.height<=260
        assert patch.getpixel((patch.width//2,patch.height//2))[0]>100
    finally: patch.close();source.close()


def test_rotacion_transparente_respeta_el_papel():
    original=Image.new('RGB',(120,70),'#DD3220')
    layer=Image.new('RGB',(260,240),'#DDF8EF')
    result=visible_photo_patch(original,None,(0,0,260,240),(130,120),(160,100),32)
    assert result is not None
    patch,at=result
    try:
        layer.paste(patch,at,patch.getchannel('A'))
        assert layer.getpixel((0,0))==(221,248,239)
        assert layer.getpixel((130,120))[0]>150
        assert not any(all(v>250 for v in rgb) for rgb in layer.getdata())
    finally: patch.close();original.close();layer.close()


def test_huecos_de_enderezado_usan_mascara_real(tmp_path):
    edits=pytest.importorskip('photo_edits')
    path=tmp_path/'rojo.png'
    Image.new('RGB',(150,90),'#B52632').save(path)
    setup={'straighten':14.0}
    with Image.open(path) as original:
        prepared=edits.apply_edits(original,setup)
    try:
        mask=editing_alpha(path,setup,prepared.size)
        assert mask is not None
        assert mask.getpixel((0,0))<30
        canvas=Image.new('RGB',(330,330),'#DDF8EF')
        layer=visible_photo_patch(prepared,mask,(0,0,330,330),(165,165),(270,270),0)
        assert layer is not None
        patch,pos=layer
        canvas.paste(patch,pos,patch.getchannel('A'))
        assert not any(all(v>250 for v in rgb) for rgb in canvas.getdata())
        patch.close();canvas.close();mask.close()
    finally: prepared.close()


def test_ampliacion_mas_del_150_por_ciento_es_valida():
    from photo_edits import validate_edits
    assert validate_edits({'print_scale': 4.5})['print_scale']==4.5
    assert validate_edits({'print_scale': 8.0})['print_scale']==8.0
    with pytest.raises(ValueError):validate_edits({'print_scale': 100000.0})


def test_posicion_de_pie_en_hoja_conserva_compatibilidad():
    from advanced_layout import validate_caption
    old=validate_caption({'title':'Leyenda','placement':'Personalizado','title_x':.2,'title_y':.8})
    assert 'position_space' not in old
    new=validate_caption({'title':'Leyenda','placement':'Personalizado','title_x':.97,'title_y':.96,'position_space':'page'})
    assert new['position_space']=='page'


def test_cambio_de_diseno_muestra_miniatura_actualizada(tmp_path):
    from main import ReveloApp
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('El runner no tiene escritorio Tk')
    photo=tmp_path/'a.png';Image.new('RGB',(320,160),'#B82120').save(photo)
    try:
        app=ReveloApp(root)
        app.paths=[photo];app.pages=[photo]
        app.details[photo]=(320,160)
        app.path_labels[photo]=photo.name
        app.layout_items[photo]={'rect':[.3,.3,.28,.24]}
        app.per_sheet.set('1'); app.layout_template.set('Diseño libre')
        app._thumbnail(photo)
        group=(photo,)
        before=app._sheet_thumbnail(group,0)
        from PIL import ImageTk
        free_rgb=ImageTk.getimage(before).convert('RGB').copy()
        app.layout_template.set('Cuadrícula')
        root.update()
        after=app._sheet_thumbnail(group,0)
        grid_rgb=ImageTk.getimage(after).convert('RGB').copy()
        assert ImageChops.difference(free_rgb,grid_rgb).getbbox() is not None
        assert len(app.sheet_thumbnails)>=1
        free_rgb.close();grid_rgb.close()
    finally:root.destroy()


def test_texto_personalizado_usa_todo_el_papel(tmp_path):
    from processor import ExportOptions,render_layout_page
    p=tmp_path/'foto.png';Image.new('RGB',(160,100),'#B82426').save(p)
    opts=ExportOptions(paper='A6',dpi=100,layout_template='Diseño libre',
        photos_per_page=1,fit='Ajustar (sin recortar)',paper_background='Aguamarina',
        layout_items={p:{'rect':[.25,.25,.3,.2]}})
    caption={'title':'Prueba','placement':'Personalizado','position_space':'page',
             'title_color':'#111111','title_size':18,'title_x':.95,'title_y':.95}
    blank,_,_=render_layout_page((p,),opts,preview_max_size=(400,400))
    printed,_,_=render_layout_page((p,),replace(opts,captions={p:caption}),
                                    preview_max_size=(400,400))
    try:
        diff=ImageChops.difference(blank,printed)
        rect=diff.getbbox()
        assert rect is not None
        # El título está en el extremo inferior derecho, no en su foto arriba a la izquierda.
        assert rect[0]>printed.width*.50
        assert rect[1]>printed.height*.70
    finally:blank.close();printed.close()


def test_disabled_hover_no_expone_tramado_tk():
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('No hay pantalla')
    try:
        panel=tk.Frame(root,bg='#103044');panel.pack()
        btn=tk.Button(panel,text='Elegir foto…',bg='#4CE8D4');btn.pack()
        style_button(btn)
        btn.configure(state='disabled')
        root.update()
        from PIL import ImageTk
        disabled=ImageTk.getimage(btn._editorial_assets[2]).convert('RGB')
        assert disabled.getpixel((0,0))==(16,48,68)
        assert btn._editorial_disabled_overlay.winfo_ismapped()
        btn.event_generate('<Enter>');root.update()
        assert btn.cget('state')=='disabled'
        assert btn._editorial_disabled_overlay.winfo_ismapped()
    finally:root.destroy()


def test_alpha_nativa_de_png_transparente_no_pinta_papel_blanco(tmp_path):
    path=tmp_path/'png_con_transparencia.png'
    original=Image.new('RGBA',(120,90),(225,30,40,255))
    original.putpixel((0,0),(0,0,0,0))
    original.save(path);original.close()
    mask=editing_alpha(path,None,(120,90))
    assert mask is not None and mask.getpixel((0,0))==0
    with Image.open(path) as im:
        source=im.convert('RGB')
    canvas=Image.new('RGB',(240,180),'#DDF8EF')
    result=visible_photo_patch(source,mask,(0,0,240,180),(120,90),(120,90),0)
    assert result is not None
    layer,origin=result
    try:
        canvas.paste(layer,origin,layer.getchannel('A'))
        assert canvas.getpixel((60,45))==(221,248,239)
    finally:
        canvas.close();layer.close();source.close();mask.close()


def test_zoom_800_en_hoja_sin_diseno_libre_no_desborda_memoria(tmp_path):
    from processor import ExportOptions, render_print_image
    p=tmp_path/'alta_escala.png'
    Image.new('RGB',(200,120),'#B5242C').save(p)
    opts=ExportOptions(paper='A6',dpi=150,photos_per_page=1,
                       photo_edits={p:{'print_scale':8.0}})
    im,_,_=render_print_image(p,opts,preview_max_size=(330,350))
    try:
        assert im.width<=330 and im.height<=350
        assert im.getpixel((im.width//2,im.height//2))[0]>100
    finally: im.close()


def test_zona_libre_con_tres_fotos_y_pie_en_esquina(tmp_path):
    from processor import ExportOptions,render_layout_page
    paths=[]
    for i,color in enumerate(('#DF292C','#275EB7','#2E9A47')):
        p=tmp_path/f'{i}.png';Image.new('RGB',(180,110),color).save(p)
        paths.append(p)
    layouts={p:{'rect':[.21+i*.28,.24,.22,.23], 'angle': 19 if i==0 else 0}
             for i,p in enumerate(paths)}
    base=ExportOptions(paper='A6',dpi=100,layout_template='Diseño libre',
                      photos_per_page=3,fit='Ajustar (sin recortar)',
                      layout_items=layouts,paper_background='Aguamarina')
    cap={'title':'Pie libre','placement':'Personalizado','position_space':'page',
         'title_x':.93,'title_y':.93,'title_color':'#172637','title_size':18}
    orig,_,_=render_layout_page(tuple(paths),base,preview_max_size=(400,400))
    edited,_,_=render_layout_page(tuple(paths),replace(base,captions={paths[0]:cap}),
                                   preview_max_size=(400,400))
    try:
        bounds=ImageChops.difference(orig,edited).getbbox()
        assert bounds is not None
        assert bounds[0]>edited.width*.50
        assert bounds[1]>edited.height*.70
    finally:orig.close();edited.close()
