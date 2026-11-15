# Tauscht das Bild in einer GLB (beliebige Lage im Puffer) und schreibt die Datei neu
import struct,json,io
from PIL import Image,ImageEnhance
def load(p):
    d=open(p,'rb').read();n=struct.unpack('<I',d[12:16])[0];j=json.loads(d[20:20+n]);o=20+n;bl=struct.unpack('<I',d[o:o+4])[0];return j,bytes(d[o+8:o+8+bl])
def image(j,b):
    bv=j['bufferViews'][j['images'][0]['bufferView']];o=bv.get('byteOffset',0);return Image.open(io.BytesIO(b[o:o+bv['byteLength']])).convert('RGB')
def save(p,j,b,im,q=84):
    buf=io.BytesIO();im.save(buf,'JPEG',quality=q,optimize=True);jb=buf.getvalue();iv=j['images'][0]['bufferView'];nb=bytearray()
    for k,bv in enumerate(j['bufferViews']):
        o=bv.get('byteOffset',0);data=jb if k==iv else b[o:o+bv['byteLength']]
        while len(nb)%4:nb.append(0)
        bv['byteOffset']=len(nb);bv['byteLength']=len(data);nb+=data
    while len(nb)%4:nb.append(0)
    j['buffers'][0]['byteLength']=len(nb);j['images'][0]['mimeType']='image/jpeg'
    js=json.dumps(j,separators=(',',':')).encode();js+=b' '*((4-len(js)%4)%4)
    open(p,'wb').write(struct.pack('<III',0x46546C67,2,28+len(js)+len(nb))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(nb),0x004E4942)+bytes(nb));return 28+len(js)+len(nb)
def ton(im,gamma=1.0,satt=1.0,hell=1.0):
    if gamma!=1.0:im=im.point([int(255*((i/255)**gamma)*hell+.5) if 255*((i/255)**gamma)*hell<255 else 255 for i in range(256)]*3)
    if satt!=1.0:im=ImageEnhance.Color(im).enhance(satt)
    return im
