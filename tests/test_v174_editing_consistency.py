"""Regresiones v1.7.4: recorte irreversible visualmente, edición no destructiva."""
import os
from pathlib import Path
from PIL import Image, ImageChops
import pytest

from photo_edits import (DEFAULT, legacy_to_operations, apply_edits,
                         validate_edits, transformed_dimensions)
from layout_editor import validate_layout_item
from processor import ExportOptions,render_layout_page,export_pdf
from project_io import save_project,load_project


def test_committed_crop_is_new_basis_for_all_subsequent_transforms():
    # Una banda azul intensa rodea el área interior roja. Después de recortar,
    # ningún giro debe volver a mostrar los píxeles azules descartados.
    source=Image.new('RGB',(500,300),(0,0,250))
    for y in range(70,230):
        for x in range(120,380):source.putpixel((x,y),(235,45,26))
    edited=legacy_to_operations({'crop':[.24,70/300,.76,230/300]})
    assert edited['crop'] is None
    assert edited['ops'][-1]['kind']=='crop'
    for extra in ({'turns':1},{'turns':3},{'straighten':15},{'straighten':-15},
                  {'flip_h':True},{'turns':1,'straighten':8}):
        out=apply_edits(source,{**edited,**extra})
        assert out.size[0]>20
        # La rotación puede crear esquinas blancas, pero NO píxeles azules originales.
        blue=sum(1 for p in out.getdata() if p[2]>180 and p[0]<50)
        assert blue==0
        out.close()
    source.close()


def test_two_committed_crops_act_in_order_and_source_remains_intact():
    source=Image.new('RGB',(720,450))
    for y in range(450):
        for x in range(720):source.putpixel((x,y),(x%255,y%255,55))
    spec=validate_edits({'ops':[{'kind':'crop','value':[.1,.1,.8,.9]},
                               {'kind':'turn','value':1},
                               {'kind':'crop','value':[.2,.2,.7,.7]}],
                         'straighten':10})
    img=apply_edits(source,spec)
    assert img.width < source.width and img.height < source.height
    w,h=transformed_dimensions(source.size,spec)
    assert abs(img.width-w)<5 and abs(img.height-h)<5
    img.close();source.close()


def test_invalid_operation_histories_are_rejected():
    for spec in ({'ops':[{'kind':'code','value':'eval(1)'}]},
                 {'ops':[{'kind':'crop','value':[0,0,1,5]}]},
                 {'ops':[{'kind':'turn','value':900}]},
                 {'ops':[{'kind':'crop','value':[0,0,1,1]}]*60}):
        with pytest.raises(ValueError):validate_edits(spec)


def test_new_stretched_free_layout_renders_true_width_and_height(tmp_path):
    p=tmp_path/'photo.png';Image.new('RGB',(800,300),(20,120,200)).save(p)
    base={'rect':[.5,.5,.40,.22],'angle':0.,'stretch':True}
    opt=ExportOptions(paper='A4',orientation='Horizontal',dpi=90,
                     photos_per_page=1,layout_template='Diseño libre',layout_items={p:base})
    first,_,_=render_layout_page([p],opt,preview_max_size=(600,450))
    taller={**base,'rect':[.5,.5,.40,.50]}
    second,_,_=render_layout_page([p],ExportOptions(paper='A4',orientation='Horizontal',dpi=90,
                     photos_per_page=1,layout_template='Diseño libre',layout_items={p:taller}),preview_max_size=(600,450))
    try:
        assert ImageChops.difference(first,second).getbbox() is not None
        assert validate_layout_item(taller)['stretch'] is True
    finally:first.close();second.close()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Necesita interfaz Tk')
def test_confirmed_crop_and_reopen_uses_result_view_and_scroll_no_changes(tmp_path):
    import tkinter as tk
    from photo_editor_ui import PhotoEditor
    photo=tmp_path/'source.png';Image.new('RGB',(900,550),(64,80,105)).save(photo)
    original=photo.read_bytes()
    root=tk.Tk();root.geometry('1440x900')
    saved=[];editor=None;reopened=None
    try:
        editor=PhotoEditor(root,photo,None,saved.append)
        root.update()
        editor.spec['crop']=[.2,.25,.8,.78]
        editor._refresh_crop_button();editor.crop_btn.invoke()
        root.update()
        assert editor.spec['crop'] is None
        assert editor.spec['ops'][-1]['kind']=='crop'
        initial=apply_edits(Image.open(photo),editor.spec)
        editor._slider_vars['straighten'].set(15.0)
        root.update();root.after(60,root.quit);root.mainloop()
        rotated=apply_edits(Image.open(photo),editor.spec)
        assert rotated.width < 900 and rotated.height < 550
        assert rotated.size != initial.size
        editor.save();root.update()
        reopened=PhotoEditor(root,photo,saved[0],lambda _:None)
        root.update()
        assert reopened._result is True
        assert reopened.spec['crop'] is None
        assert reopened.result_btn.cget('text') == 'Modificar recorte'
        scale=reopened._slider_vars['print_scale']
        current=scale.get()
        # Rueda sobre escala: desplaza el panel, no cambia la escala.
        tk_scales=[]
        def walk(w):
            if isinstance(w,tk.Scale):tk_scales.append(w)
            for child in w.winfo_children():walk(child)
        walk(reopened)
        tk_scales[-1].event_generate('<MouseWheel>',delta=-120)
        root.update()
        assert scale.get() == current
        assert photo.read_bytes()==original
        initial.close();rotated.close()
    finally:
        if editor and editor.winfo_exists():editor.close()
        if reopened and reopened.winfo_exists():reopened.close()
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Necesita interfaz Tk')
def test_free_layout_eight_handles_resize_separate_axes(tmp_path):
    import tkinter as tk
    from layout_editor import edit_sheet
    p=tmp_path/'sample.png';Image.new('RGB',(600,220),(33,145,80)).save(p)
    opts=ExportOptions(paper='A4',orientation='Horizontal',dpi=90,
                       photos_per_page=1,layout_template='Diseño libre')
    root=tk.Tk();root.geometry('1200x850')
    saved=[];dialog=None
    try:
        dialog=edit_sheet(root,[p],'Diseño libre',{},opts,saved.append)
        root.update();root.after(180,root.quit);root.mainloop()
        canvases=[]
        def walk(w):
            if isinstance(w,tk.Canvas):canvases.append(w)
            for ch in w.winfo_children():walk(ch)
        walk(dialog)
        canvas=canvases[0]
        def handles():
            return [(iid,tuple(map(float,canvas.coords(iid)))) for iid in canvas.find_all()
                    if canvas.type(iid)=='rectangle' and canvas.itemcget(iid,'fill').lower()=='#4fd9bc']
        values=handles();assert len(values)==8
        pts=[((c[0]+c[2])/2,(c[1]+c[3])/2) for _,c in values]
        # Derecha central -> solo ancho, no alto.
        mx=max(x for x,y in pts);rx,ry=min((xy for xy in pts if abs(xy[0]-mx)<4),key=lambda xy:abs(xy[1]-sum(y for x,y in pts)/8))
        canvas.event_generate('<ButtonPress-1>',x=int(rx),y=int(ry))
        canvas.event_generate('<B1-Motion>',x=int(rx+40),y=int(ry))
        canvas.event_generate('<ButtonRelease-1>',x=int(rx+40),y=int(ry))
        root.update()
        values=handles();pts=[((c[0]+c[2])/2,(c[1]+c[3])/2) for _,c in values]
        my=max(y for x,y in pts);sx,sy=min((xy for xy in pts if abs(xy[1]-my)<4),key=lambda xy:abs(xy[0]-sum(x for x,y in pts)/8))
        canvas.event_generate('<ButtonPress-1>',x=int(sx),y=int(sy))
        canvas.event_generate('<B1-Motion>',x=int(sx),y=int(sy+28))
        canvas.event_generate('<ButtonRelease-1>',x=int(sx),y=int(sy+28))
        root.update()
        buttons=[]
        def btnwalk(w):
            if isinstance(w,tk.Button):buttons.append(w)
            for ch in w.winfo_children():btnwalk(ch)
        btnwalk(dialog)
        next(b for b in buttons if b.cget('text')=='Guardar composición').invoke()
        assert saved and saved[0][p]['stretch'] is True
        assert saved[0][p]['rect'][2]>0 and saved[0][p]['rect'][3]>0
    finally:
        if dialog and dialog.winfo_exists():dialog.destroy()
        root.destroy()


def test_committed_crop_and_horizontal_stretch_survive_project_and_pdf(tmp_path):
    from pdf_sources import recover_sources
    path=tmp_path/'mosaico.png'
    Image.new('RGB',(700,400),(150,85,40)).save(path)
    spec={'ops':[{'kind':'crop','value':[.2,.1,.85,.9]},
                 {'kind':'turn','value':1},
                 {'kind':'straighten','value':-11.0}],
          'print_scale':.80}
    layout={'rect':[.5,.5,.65,.40],'stretch':True,'angle':13.0,'z':2,
            'background':'Crema'}
    settings={'paper':'A5','orientation':'Horizontal','dpi':100,
              'fmt':'PDF','fit':'Ajustar (sin recortar)','binding':False,'photos_per_page':1,
              'layout_template':'Diseño libre'}
    project=tmp_path/'contenido.revelo'
    save_project(project,[path],[path],{}, {},settings,photo_edits={path:spec},
                 layout_items={path:layout})
    loaded=load_project(project,tmp_path/'recuperado')
    recovered=loaded['pages'][0]
    assert loaded['photo_edits'][recovered]['ops']==validate_edits(spec)['ops']
    assert loaded['layout_items'][recovered]['stretch'] is True
    opts=ExportOptions(**settings,photo_edits={path:spec},layout_items={path:layout})
    output=tmp_path/'resultado.pdf'
    export_pdf([path],opts,output)
    restored=recover_sources(output,tmp_path/'pdf_sources',include_edits=True,
                             include_layout=True,include_captions=True,include_specials=True)
    assert restored is not None
    # Las fuentes incrustadas conservan el historial y las geometrías libres.
    _, _, _, _, pdf_edits, _, pdf_layout, _ = restored
    assert pdf_edits and list(pdf_edits.values())[0]['ops']==validate_edits(spec)['ops']
    assert pdf_layout and list(pdf_layout.values())[0]['stretch'] is True
