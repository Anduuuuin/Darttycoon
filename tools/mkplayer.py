# Baut eigene Dart-Spieler auf das freie KayKit-Skelett (CC0): Körper aus runden Formen, Animationen bleiben
import struct,json,numpy as np
SRC='models/skelett_quelle.glb';DST='models/spieler.glb'
d=open(SRC,'rb').read();n=struct.unpack('<I',d[12:16])[0];J=json.loads(d[20:20+n]);o=20+n;bl=struct.unpack('<I',d[o:o+4])[0];BIN=bytearray(d[o+8:o+8+bl])
JN={J['nodes'][ji]['name']:k for k,ji in enumerate(J['skins'][0]['joints'])}
def ell(c,r,seg=18,rings=12,keep=None):
    V=[];N=[];I=[]
    for a in range(rings+1):
        th=np.pi*a/rings
        for b in range(seg+1):
            ph=2*np.pi*b/seg;u=np.array([np.sin(th)*np.cos(ph),np.cos(th),np.sin(th)*np.sin(ph)])
            V.append(np.array(c)+u*np.array(r));nn=u/np.array(r);N.append(nn/np.linalg.norm(nn))
    for a in range(rings):
        for b in range(seg):
            p=a*(seg+1)+b;q=p+seg+1
            for t in ((p,p+1,q),(p+1,q+1,q)):
                if keep is None or keep(sum(V[i] for i in t)/3): I.append(t)
    return np.array(V),np.array(N),np.array(I).reshape(-1,3)
PARTS={}   # Material -> Liste (V,N,I,joints,weights)
def add(mat,geo,bone,bone2=None,wf=None):
    V,N,I=geo;j=np.zeros((len(V),4),np.uint8);w=np.zeros((len(V),4),np.float32);j[:,0]=JN[bone];w[:,0]=1
    if bone2:
        k=np.clip(np.array([wf(v) for v in V]),0,1);j[:,1]=JN[bone2];w[:,0]=1-k;w[:,1]=k
    PARTS.setdefault(mat,[]).append((V,N,I,j,w))
# Kopf, Gesicht, Haare
add('skin',ell((0,1.70,0),(.5,.5,.47),24,16),'head')
for s in (-1,1):
    add('skin',ell((s*.5,1.66,0),(.06,.1,.08),10,8),'head');add('eyes',ell((s*.17,1.70,.435),(.055,.08,.04),10,8),'head')
add('eyes',ell((0,1.47,.44),(.1,.022,.03),10,6),'head')
add('hair',ell((0,1.76,-.03),(.535,.5,.53),24,16,lambda p:p[1]>1.88+max(0,p[2])*.35 or (p[2]<-.1 and p[1]>1.45)),'head')
add('hair_long',ell((0,1.52,-.1),(.56,.5,.42),20,12,lambda p:p[2]<.12 and p[1]<1.9),'head')
add('beard',ell((0,1.44,.16),(.36,.2,.34),16,10,lambda p:p[1]<1.5 and p[2]>.05),'head')
add('cap',ell((0,1.82,0),(.545,.46,.535),24,14,lambda p:p[1]>1.9),'head');add('cap',ell((0,1.93,.5),(.3,.035,.26),14,6),'head')
# Rumpf
add('shirt',ell((0,.95,0),(.33,.37,.25),20,14),'spine','chest',lambda v:(v[1]-.72)/.36)
add('trim',ell((0,1.27,.0),(.2,.06,.17),16,6),'chest')
add('pants',ell((0,.52,0),(.31,.2,.24),18,10),'hips')
for s,sd in ((1,'l'),(-1,'r')):
    add('shirt',ell((s*.33,1.107,0),(.15,.115,.115),14,10),'upperarm.'+sd)
    add('skin',ell((s*.585,1.107,-.005),(.155,.085,.085),12,8),'lowerarm.'+sd)
    add('skin',ell((s*.80,1.10,0),(.105,.09,.1),12,8),'hand.'+sd)
    add('pants',ell((s*.171,.40,0),(.125,.155,.13),12,8),'upperleg.'+sd)
    add('pants',ell((s*.171,.22,0),(.115,.115,.115),12,8),'lowerleg.'+sd)
    add('shoes',ell((s*.171,.07,.05),(.115,.075,.19),12,8),'foot.'+sd)
COL={'skin':'#f2c49b','hair':'#2b1d14','hair_long':'#2b1d14','beard':'#2b1d14','cap':'#d9333f','eyes':'#1a1a1a','shirt':'#1fa55a','trim':'#f4f4f4','pants':'#2b2f3a','shoes':'#151515'}
lin=lambda c:c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
rgb=lambda h:[lin(int(h[i:i+2],16)/255) for i in (1,3,5)]+[1]
# altes Aussehen entfernen
for nd in J['nodes']:
    if 'mesh' in nd: nd.pop('mesh');nd.pop('skin',None)
J['meshes']=[];J['materials']=[];J.pop('textures',None);J.pop('images',None);J.pop('samplers',None)
def view(data,target=None):
    while len(BIN)%4:BIN.append(0)
    bv={'buffer':0,'byteOffset':len(BIN),'byteLength':len(data)}
    if target:bv['target']=target
    BIN.extend(data);J['bufferViews'].append(bv);return len(J['bufferViews'])-1
def acc(arr,ctype,typ,target=None,mm=False):
    a={'bufferView':view(arr.tobytes(),target),'componentType':ctype,'count':len(arr),'type':typ}
    if mm:a['min']=arr.min(axis=0).tolist();a['max']=arr.max(axis=0).tolist()
    J['accessors'].append(a);return len(J['accessors'])-1
prims=[];tri=0
for mat,lst in PARTS.items():
    V=np.concatenate([p[0] for p in lst]).astype(np.float32);Nn=np.concatenate([p[1] for p in lst]).astype(np.float32);jj=np.concatenate([p[3] for p in lst]);ww=np.concatenate([p[4] for p in lst]).astype(np.float32)
    off=0;II=[]
    for p in lst:II.append(p[2]+off);off+=len(p[0])
    II=np.concatenate(II).astype(np.uint16).reshape(-1);tri+=len(II)//3
    J['materials'].append({'name':mat,'pbrMetallicRoughness':{'baseColorFactor':rgb(COL[mat]),'metallicFactor':0,'roughnessFactor':.75}})
    prims.append({'attributes':{'POSITION':acc(V,5126,'VEC3',34962,True),'NORMAL':acc(Nn,5126,'VEC3',34962),'JOINTS_0':acc(jj,5121,'VEC4',34962),'WEIGHTS_0':acc(ww,5126,'VEC4',34962)},'indices':acc(II,5123,'SCALAR',34963),'material':len(J['materials'])-1})
J['meshes']=[{'name':'Spieler','primitives':prims}]
J['nodes'].append({'name':'Spieler','mesh':0,'skin':0});rig=J['scenes'][0]['nodes'][0];J['nodes'][rig].setdefault('children',[]).append(len(J['nodes'])-1)
# unbenutzte Daten wegräumen
used=set()
for p in prims:used.update(p['attributes'].values());used.add(p['indices'])
for s in J['skins']:used.add(s['inverseBindMatrices'])
for a in J['animations']:
    for s in a['samplers']:used.add(s['input']);used.add(s['output'])
al=sorted(used);am={a:i for i,a in enumerate(al)};vl=sorted({J['accessors'][a]['bufferView'] for a in al});vm={};nb=bytearray()
for v in vl:
    bv=J['bufferViews'][v];data=BIN[bv['byteOffset']:bv['byteOffset']+bv['byteLength']]
    while len(nb)%4:nb.append(0)
    vm[v]=len(vm);bv['byteOffset']=len(nb);nb+=data
J['bufferViews']=[J['bufferViews'][v] for v in vl];na=[]
for a in al:
    A=J['accessors'][a];A['bufferView']=vm[A['bufferView']];na.append(A)
J['accessors']=na
for p in prims:
    p['attributes']={k:am[v] for k,v in p['attributes'].items()};p['indices']=am[p['indices']]
for s in J['skins']:s['inverseBindMatrices']=am[s['inverseBindMatrices']]
for a in J['animations']:
    for s in a['samplers']:s['input']=am[s['input']];s['output']=am[s['output']]
while len(nb)%4:nb.append(0)
J['buffers']=[{'byteLength':len(nb)}];js=json.dumps(J,separators=(',',':')).encode();js+=b' '*((4-len(js)%4)%4)
open(DST,'wb').write(struct.pack('<III',0x46546C67,2,28+len(js)+len(nb))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(nb),0x004E4942)+bytes(nb))
print('spieler.glb',(28+len(js)+len(nb))//1024,'KB',tri,'Dreiecke',list(PARTS))
