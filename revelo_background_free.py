"""Zonas no solapadas para fondos de fotografías en el diseño libre.

Una foto libre puede cubrir al 100 % su propio rectángulo; pintar el fondo
solamente en ese rectángulo lo oculta. Se utiliza una partición geométrica de
la página por proximidad a los centros de foto. La máscara NO afecta a los
píxeles de las fotos ni a las leyendas, solo al papel visible.
"""
from __future__ import annotations

from PIL import Image, ImageDraw


def _clip_polygon(poly, ax, ay, bound):
    """Conserva ax*x+ay*y <= bound (semiplano de Voronoi)."""
    if not poly:
        return []
    out=[]
    old=poly[-1]
    old_value=ax*old[0]+ay*old[1]-bound
    for point in poly:
        value=ax*point[0]+ay*point[1]-bound
        old_in=old_value<=0
        point_in=value<=0
        if old_in != point_in:
            denom=old_value-value
            if abs(denom)>1e-12:
                t=old_value/denom
                out.append((old[0]+t*(point[0]-old[0]),
                            old[1]+t*(point[1]-old[1])))
        if point_in:
            out.append(point)
        old=point
        old_value=value
    return out


def free_background_area(paths, current, opts, size, physical, page_index=0):
    """Devuelve (rectángulo mínimo, máscara L) del territorio de una foto.

    Siempre recorta al tamaño del papel; admite posiciones fuera de la zona
    imprimible, superposiciones y una única foto libre. La máscara devuelta
    pertenece al llamante y debe cerrarla.
    """
    from layout_editor import validate_layout_item, free_default
    from processor import printable_box
    w,h=size
    w_mm,h_mm=physical
    if opts.binding:
        x0,y0,x1,y1=printable_box(size,physical,binding=True,page_index=page_index)
    else:
        mx=max(1,round(w*3/w_mm));my=max(1,round(h*3/h_mm))
        x0,y0,x1,y1=mx,my,w-mx,h-my
    zw,zh=x1-x0,y1-y0
    positions=[]
    for i,p in enumerate(paths):
        spec=validate_layout_item(opts.layout_items.get(p))
        cx,cy,*_=spec.get('rect',free_default(i,len(paths))['rect'])
        positions.append((x0+zw*cx,y0+zh*cy))
    idx=paths.index(current)
    x,y=positions[idx]
    polygon=[(0.,0.),(float(w),0.),(float(w),float(h)),(0.,float(h))]
    for other, (ox,oy) in enumerate(positions):
        if other==idx:
            continue
        dx,dy=ox-x,oy-y
        if abs(dx)+abs(dy)<1e-9:
            # Centro idéntico: priorizar el más reciente sin generar errores.
            if idx>other:
                continue
            return None
        polygon=_clip_polygon(polygon,2*dx,2*dy,ox*ox+oy*oy-x*x-y*y)
        if len(polygon)<3:
            return None
    mask=Image.new('L',(w,h),0)
    draw=ImageDraw.Draw(mask)
    draw.polygon(polygon,fill=255)
    del draw
    bbox=mask.getbbox()
    if bbox is None:
        mask.close()
        return None
    crop=mask.crop(bbox)
    mask.close()
    return bbox,crop
