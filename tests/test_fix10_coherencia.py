"""FIX10 — regressions across editor, thumbnail, paper, and export.

Tests deliberately exercise the actual application modules, not screenshots
or hard-coded flags claiming a fix was applied.
"""
from dataclasses import replace
from pathlib import Path
import tkinter as tk
import pytest
from PIL import Image, ImageChops


def image(tmp_path, name, color, size=(280,140)):
    p=tmp_path/name
    Image.new('RGB',size,color).save(p)
    return p


def test_shared_editor_options_preserve_one_scale_without_double_multiplication(tmp_path):
    from processor import ExportOptions
    from revelo_shared_layout import editor_options
    p=image(tmp_path,'a.png','#CC4422')
    original=ExportOptions(paper='A5',dpi=90,fit='Ajustar (sin recortar)',
        photos_per_page=1,layout_template='Diseño libre',
        photo_edits={p:{'print_scale':.8}},
        captions={p:{'title':'Leyenda','placement':'Personalizado',
                     'photo_scale':.75}},
        layout_items={p:{'rect':[.45,.45,.5,.4]}})
    expected=.8*.75
    state={p:{'rect':[.5,.4,.6,.3], 'angle':17.0}}
    opts=editor_options(original,[p],'Diseño libre',state,{},
                        {p:expected},'Aguamarina','#123456')
    assert opts.photo_edits[p]['print_scale']==pytest.approx(expected)
    assert opts.captions[p]['photo_scale']==1.0
    assert opts.layout_items[p]['angle']==17.0
    assert opts.layout_items[p]['background']=='Aguamarina'
    assert original.photo_edits[p]['print_scale']==.8
    assert original.captions[p]['photo_scale']==.75


@pytest.mark.parametrize('layout', ['Diseño libre','Grande arriba + 2 abajo'])
def test_editor_preview_and_final_export_share_same_pixels_for_three_photos(tmp_path,layout):
    from processor import ExportOptions,render_layout_page
    from revelo_shared_layout import editor_options,render_editor_sheet
    files=[image(tmp_path,f'p{i}.png',color) for i,color in enumerate(
        ('#CC2222','#22B244','#3654BC'))]
    positions={p:{'rect':[.20+.28*i,.25,.30,.25],
                  'angle':22.0 if i==0 else 0.0} for i,p in enumerate(files)}
    scales={p: .8 if i==0 else 1.1 for i,p in enumerate(files)}
    opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',
        photos_per_page=3,fit='Ajustar (sin recortar)',
        paper_background='Azul noche',layout_template=layout)
    editor,_,_=render_editor_sheet(files,opts,layout,positions,
        {'split_main':.58,'split_small':.45},scales,'Azul noche','#102030',
        (390,540),page_index=0)
    updated=editor_options(opts,files,layout,positions,
        {'split_main':.58,'split_small':.45},scales,'Azul noche','#102030')
    exported,_,_=render_layout_page(files,updated,preview_max_size=(390,540))
    try:
        assert editor.size==exported.size
        assert ImageChops.difference(editor,exported).getbbox() is None
    finally:editor.close();exported.close()


def test_background_from_straighten_is_not_white_in_single_photo_or_thumbnail(tmp_path):
    from processor import ExportOptions,render_print_image
    from thumbnail_preview import render_photo_thumbnail
    p=image(tmp_path,'inclined.png','#DB2024',(320,110))
    opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',
        fit='Ajustar (sin recortar)',paper_background='Aguamarina',
        photo_edits={p:{'straighten':12.0}})
    image_full,_,_=render_print_image(p,opts,preview_max_size=(320,430))
    tiny=render_photo_thumbnail(p,opts,max_size=(180,250))
    try:
        assert image_full.getpixel((0,0))==(221,248,239)
        assert tiny.getpixel((0,0))==(221,248,239)
        assert image_full.getpixel((image_full.width//2,image_full.height//2))[0]>100
        assert not any(pixel[:3]==(255,255,255) for pixel in tiny.getdata())
    finally:image_full.close();tiny.close()


def test_three_photo_template_preserves_paper_behind_straightened_photo(tmp_path):
    from processor import ExportOptions,render_layout_page
    a=image(tmp_path,'a.png','#CC2628',(250,130))
    b=image(tmp_path,'b.png','#28B13A')
    c=image(tmp_path,'c.png','#2461BA')
    opts=ExportOptions(paper='A5',dpi=100,orientation='Vertical',
        photos_per_page=3,layout_template='Grande arriba + 2 abajo',
        fit='Ajustar (sin recortar)',paper_background='Azul noche',
        photo_edits={a:{'straighten':14.0}})
    paper,_,_=render_layout_page((a,b,c),opts,preview_max_size=(360,480))
    try:
        assert paper.getpixel((0,0))==(11,25,40)
        assert not any(p==(255,255,255) for p in paper.getdata())
    finally:paper.close()


def test_caption_can_reach_near_paper_bottom_independently_of_small_photo(tmp_path):
    from processor import ExportOptions,render_layout_page
    p=image(tmp_path,'small.png','#BD2525')
    base=ExportOptions(paper='A5',dpi=100,photos_per_page=1,
        layout_template='Diseño libre',fit='Ajustar (sin recortar)',
        paper_background='Aguamarina',
        layout_items={p:{'rect':[.15,.15,.18,.14]}})
    caption={'title':'ESQUINA','placement':'Personalizado',
             'position_space':'page','title_x':.97,'title_y':.98,
             'title_color':'#142635','title_size':16}
    blank,_,_=render_layout_page((p,),base,preview_max_size=(360,440))
    text,_,_=render_layout_page((p,),replace(base,captions={p:caption}),
                                preview_max_size=(360,440))
    try:
        diff=ImageChops.difference(blank,text)
        region=diff.getbbox()
        assert region is not None
        assert region[0]>text.width*.60
        assert region[1]>text.height*.82,region
        assert region[3]>text.height*.88,region
    finally:blank.close();text.close()


def test_cover_photo_zoom_supports_8x_and_keeps_original(tmp_path):
    from special_pages import validate_special_spec,render_special_page,CUSTOM_THEME
    img=image(tmp_path,'cover.png','#A12B30',(360,180))
    before=img.read_bytes()
    base=dict(kind='Portada',theme=CUSTOM_THEME,title='',subtitle='',
              background_type='imagen',background_image=str(img),
              image_mode='Libre',background_color='#F6EBDC',
              image_zoom_x=8.0,image_zoom_y=8.0)
    spec=validate_special_spec(base)
    assert spec['image_zoom_x']==8.0
    out=render_special_page(spec,(380,280))
    try:
        assert out.size==(380,280)
    finally:out.close()
    assert img.read_bytes()==before


def test_disabled_button_hover_uses_independent_sibling_overlay():
    from revelo_button_skin import style_button
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('No hay escritorio Tk')
    root.geometry('330x160')
    counter=[]
    try:
        frame=tk.Frame(root,bg='#103044');frame.pack(fill='both',expand=True)
        b=tk.Button(frame,text='Elegir foto…',bg='#4CE8D4',command=lambda:counter.append(True))
        b.pack(pady=20)
        style_button(b)
        b.configure(state='disabled')
        root.update()
        overlay=b._editorial_disabled_overlay
        assert overlay.master is frame, 'No debe ser hijo del Button nativo'
        assert overlay.winfo_ismapped()
        b.event_generate('<Enter>');overlay.event_generate('<Enter>');root.update()
        assert overlay.winfo_ismapped()
        assert b.cget('state')=='disabled'
        b.invoke();assert not counter
        b.configure(state='normal');root.update()
        assert not overlay.winfo_ismapped()
        b.invoke();assert counter==[True]
    finally:root.destroy()


def test_8_handles_on_custom_cover_image_editor(tmp_path):
    from special_pages import CUSTOM_THEME
    from custom_editor import edit_custom_page
    try:root=tk.Tk()
    except tk.TclError:pytest.skip('No hay escritorio Tk')
    bg=image(tmp_path,'portrait.png','#702B36',(320,190))
    root.geometry('1360x900')
    win=None
    try:
        win=edit_custom_page(root,initial=dict(kind='Portada',theme=CUSTOM_THEME,
            background_type='imagen',background_image=str(bg),
            image_mode='Libre',image_zoom_x=.75,image_zoom_y=.75),
            image_dir=tmp_path,landscape=False,binding=False,on_save=lambda _:None)
        root.update()
        def walk(w):
            yield w
            for child in w.winfo_children():yield from walk(child)
        # Hay DOS controles «Fotografía»: el de fondo y el del editor.
        radios=[w for w in walk(win) if isinstance(w,tk.Radiobutton)
                and w.cget('text')=='Fotografía' and str(w.cget('value'))=='image']
        assert len(radios)==1, 'No se encuentra el selector de foto del editor libre'
        radios[0].invoke()
        root.update();win.after(220,win.quit);win.mainloop()
        canvases=[w for w in walk(win) if isinstance(w,tk.Canvas)]
        # La barra izquierda usa también un Canvas para el desplazamiento. En
        # los runners de Windows puede ocupar MÁS píxeles que la hoja, de
        # modo que max(width*height) seleccionaba un lienzo equivocado.
        previews=[c for c in canvases if str(c.cget('cursor'))=='fleur']
        assert len(previews)==1, f'Lienzos del editor inesperados: {[(str(c.cget("cursor")), c.winfo_width(), c.winfo_height()) for c in canvases]}'
        preview=previews[0]
        def read_handles():
            return [i for i in preview.find_all() if preview.type(i)=='rectangle'
                and preview.itemcget(i,'fill').upper()=='#4CE8D4']
        # Esperar a que termine el repintado real (la imagen se carga de forma
        # diferida). Si falla, informar del Canvas elegido y sus elementos.
        import time
        deadline=time.monotonic()+2.0
        while True:
            root.update()
            items=read_handles()
            if len(items)==8 or time.monotonic()>=deadline:
                break
            time.sleep(.025)
        assert len(items)==8, (f'Esperados 8 tiradores en el Canvas de la foto; '
                              f'encontrados {len(items)}. Elementos: '
                              f'{[(i,preview.type(i),preview.itemcget(i,"fill") if preview.type(i)=="rectangle" else "") for i in preview.find_all()]}')
        # El borde central derecho es un verdadero tirador interactivo.
        centers=[((preview.coords(i)[0]+preview.coords(i)[2])/2,
                  (preview.coords(i)[1]+preview.coords(i)[3])/2) for i in items]
        mx=max(p[0] for p in centers)
        mx,my=min((p for p in centers if abs(p[0]-mx)<3),
                   key=lambda p:abs(p[1]-sum(z[1] for z in centers)/8))
        before_scalars=[w.get() for w in walk(win) if isinstance(w,tk.Scale)
                        and str(w.cget('to')) in ('8.0','8')]
        preview.event_generate('<ButtonPress-1>',x=int(mx),y=int(my))
        preview.event_generate('<B1-Motion>',x=int(mx+35),y=int(my))
        preview.event_generate('<ButtonRelease-1>',x=int(mx+35),y=int(my))
        root.update()
        after_scalars=[w.get() for w in walk(win) if isinstance(w,tk.Scale)
                       and str(w.cget('to')) in ('8.0','8')]
        assert len(before_scalars)==len(after_scalars)==2
        assert after_scalars[0]>before_scalars[0],(before_scalars,after_scalars)
        assert after_scalars[1]==pytest.approx(before_scalars[1],abs=.055), (before_scalars,after_scalars)
    finally:
        if win is not None and win.winfo_exists():win.destroy()
        root.destroy()
