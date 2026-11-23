"""Portabilidad y seguridad de los fondos de imagen de proyectos .revelo.

Los archivos se embeben con rutas internas predecibles, hash SHA256 y límites
de tamaño. No se extraen nombres de archivo suministrados por un tercero.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
from PIL import Image

from revelo_backgrounds import validate_background_spec

EXTENSIONS={'.jpg','.jpeg','.png','.webp','.bmp','.tif','.tiff','.heic','.heif'}
MAX_FILE=300*1024*1024
MAX_TOTAL=3*1024*1024*1024
ARC_RE=re.compile(r'layer_backdrops/(global|[0-9]{5})\.(jpg|jpeg|png|webp|bmp|tif|tiff|heic|heif)')


def _sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as fd:
        for block in iter(lambda:fd.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def _copy_spec(spec, label):
    from project_io import ProjectError
    spec=validate_background_spec(spec)
    if not spec:
        return None,None,None
    clean=dict(spec)
    if spec['mode']!='Imagen':
        return clean,None,None
    path=Path(spec['image'])
    if path.suffix.lower() not in EXTENSIONS or not path.is_file():
        raise ProjectError('La imagen de fondo no existe o tiene un formato no compatible')
    size=path.stat().st_size
    if size<=0 or size>MAX_FILE:
        raise ProjectError('Una imagen de fondo supera el tamaño máximo permitido')
    arc=f'layer_backdrops/{label}{path.suffix.lower()}'
    clean['image']=arc
    return clean,{'name':arc,'size':size,'sha256':_sha(path)},(path,arc)


def pack_layers(paths, global_spec, overrides, bytes_used):
    """Devuelve especificaciones, adjuntos ZIP y tamaño verificado acumulado."""
    from project_io import ProjectError
    glob,gmeta,gasset=_copy_spec(global_spec,'global')
    individual=[];assets=[]
    if gasset:assets.append(gasset);bytes_used+=gmeta['size']
    for idx,p in enumerate(paths,1):
        spec,meta,asset=_copy_spec((overrides or {}).get(p),f'{idx:05d}')
        individual.append((spec,meta))
        if asset:assets.append(asset);bytes_used+=meta['size']
        if bytes_used>MAX_TOTAL:
            raise ProjectError('Los fondos superan el tamaño máximo del proyecto')
    if bytes_used>MAX_TOTAL:
        raise ProjectError('El proyecto supera el tamaño máximo permitido')
    return glob,gmeta,individual,assets


def unpack_layer(archive, entries, spec, metadata, directory, label):
    """Valida metadata y reconstruye la ruta dentro del directorio temporal."""
    from project_io import ProjectError
    if spec is None:
        if metadata is not None:
            raise ProjectError('El proyecto contiene un fondo no declarado')
        return {},0
    try:
        checked=validate_background_spec(spec)
    except (ValueError,TypeError) as exc:
        raise ProjectError('Configuración de fondo del proyecto inválida') from exc
    if not checked:
        if metadata is not None:
            raise ProjectError('Imagen de fondo inesperada')
        return {},0
    if checked['mode']!='Imagen':
        if metadata is not None:
            raise ProjectError('Archivo inesperado asociado al fondo')
        return checked,0
    arc=checked['image']
    if (not isinstance(arc,str) or not ARC_RE.fullmatch(arc)
            or arc.rsplit('/',1)[-1].split('.')[0] != label
            or not isinstance(metadata,dict)
            or set(metadata)!={'name','size','sha256'}
            or metadata['name']!=arc or arc not in entries
            or entries[arc].is_dir()):
        raise ProjectError('Ruta de fondo no válida dentro del proyecto')
    size=metadata['size'];sha=metadata['sha256']
    if (type(size) is not int or size<=0 or size>MAX_FILE
            or size!=entries[arc].file_size
            or not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha)):
        raise ProjectError('Imagen de fondo demasiado grande o no verificada')
    path=Path(directory)/f'capa_{label}{Path(arc).suffix}'
    actual=hashlib.sha256()
    with archive.open(entries[arc]) as source, path.open('wb') as target:
        for block in iter(lambda:source.read(1024*1024),b''):
            actual.update(block);target.write(block)
    if actual.hexdigest()!=sha:
        path.unlink(missing_ok=True)
        raise ProjectError('La imagen de fondo del proyecto está dañada')
    try:
        with Image.open(path) as photo:
            if photo.width * photo.height>220_000_000:
                raise ValueError('Imagen de fondo demasiado grande')
            photo.verify()
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        path.unlink(missing_ok=True)
        raise ProjectError('Imagen de fondo corrupta') from exc
    checked['image']=str(path)
    return checked,size
