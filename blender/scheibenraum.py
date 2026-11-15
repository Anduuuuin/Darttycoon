# Bullseye Boss – Scheibenraum fuer Blender (Fassung 3)
# Baut den Raum, rechnet das Licht aus ("Backen") und speichert alles als scheibenraum.glb
# Ausfuehren: Blender > oben Reiter "Scripting" > "Neu" > diesen Text einfuegen > Pfeil-Knopf "Skript ausfuehren"
import bpy, bmesh, math, os, time, traceback
from mathutils import Matrix

# ---------- Einstellungen (bei Bedarf aendern und nochmal ausfuehren) ----------
AUFLOESUNG = 2048     # Groesse des Lichtbilds. 1024 = schneller, 2048 = schaerfer
QUALITAET  = 48       # Rechenschritte pro Bildpunkt. Mehr = sauberer, aber langsamer
HELLIGKEIT = 1.3      # 1.0 = normal, 1.5 = heller, 0.7 = dunkler
ORDNER = os.path.join(os.path.expanduser('~'), 'Desktop', 'BullseyeBoss_Blender')

LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print(s)

def lin(c):  # sRGB -> linear
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def rgb(h):
    h = h.lstrip('#'); return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)

def prinzip(m):
    # liefert den Principled-Knoten eines Materials, legt ihn bei Bedarf an (Blender 2.8 bis 5.x)
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED': return n
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs[0], out.inputs[0]); return b

MATS = {}; MAT_LIST = []
def mat(name, hexcol, rough=0.85, glow=0.0):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new('BB_' + name); b = prinzip(m)
    if b:
        b.inputs['Base Color'].default_value = rgb(hexcol)
        if 'Roughness' in b.inputs: b.inputs['Roughness'].default_value = rough
        if glow > 0:
            for key in ('Emission Color', 'Emission'):
                if key in b.inputs: b.inputs[key].default_value = rgb(hexcol); break
            if 'Emission Strength' in b.inputs: b.inputs['Emission Strength'].default_value = glow * HELLIGKEIT
    MATS[name] = len(MAT_LIST); MAT_LIST.append(m); return MATS[name]

# Spiel-Koordinaten: x = nach rechts an der Rueckwand, y = hoch, z = von der Rueckwand nach vorn
# Blender: x, -z, y
bm = bmesh.new()
def setmat(verts, mi):
    seen = set()
    for v in verts:
        for f in v.link_faces:
            if f.index not in seen or True: f.material_index = mi
def box(x0, z0, x1, z1, y0, y1, mi, ry=0.0):
    M = Matrix.Translation(((x0 + x1) / 2, -(z0 + z1) / 2, (y0 + y1) / 2)) @ Matrix.Rotation(ry, 4, 'Z') @ Matrix.Diagonal((x1 - x0, z1 - z0, y1 - y0, 1.0))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=M); setmat(r['verts'], mi)
def cyl(cx, cy, cz, rad, h, mi, quer=False, seg=20):
    M = Matrix.Translation((cx, -cz, cy))
    if quer: M = M @ Matrix.Rotation(math.radians(90), 4, 'X')
    try: r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=rad, radius2=rad, depth=h, matrix=M)
    except TypeError: r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, diameter1=rad, diameter2=rad, depth=h, matrix=M)
    setmat(r['verts'], mi)
def ringstueck(cx, cy, z, r0, r1, a0, a1, mi):
    P = lambda r, a: bm.verts.new((cx + math.sin(a) * r, -z, cy + math.cos(a) * r))
    am = (a0 + a1) / 2
    vs = [P(r0, a0), P(r0, am), P(r0, a1), P(r1, a1), P(r1, am), P(r1, a0)] if r0 > 0 else [P(0, 0), P(r1, a1), P(r1, am), P(r1, a0)]
    f = bm.faces.new(vs); f.material_index = mi

RW, RD, RH = 8.0, 6.0, 3.0
SCHEIBEN = (1.0, 2.45, 3.9, 5.35)   # wie im Spiel: rechts daneben bleibt Platz fuer die Tuer zum Training
def baue():
    holz_d, holz_m, holz_h = mat('holz_d', '#4e331d'), mat('holz_m', '#6a4628'), mat('holz_h', '#8a5e34')
    # Boden aus Dielen
    dielen = [mat('d1', '#8a5a32', .6), mat('d2', '#7a4c2a', .6), mat('d3', '#946238', .6), mat('d4', '#80522e', .6)]
    n = 0
    for r in range(20):
        z0 = r * 0.3; x = -((r % 2) * 0.8)
        while x < RW:
            ln = 1.6; a, b = max(0, x), min(RW, x + ln)
            if b > a: box(a + .004, z0 + .004, b - .004, min(RD, z0 + .3) - .004, -.06, 0, dielen[(n * 7 + r) % 4])
            x += ln; n += 1
    box(-.15, -.15, RW + .15, RD + .15, -.3, -.06, mat('sockel', '#3a2616'))
    # Waende: gruen oben, Holzvertaefelung unten
    wand = mat('wand', '#2b4034'); wand2 = mat('wand2', '#253a2e')
    box(-.16, -.16, RW, 0, 0, RH, wand); box(-.16, 0, 0, RD, 0, RH, wand2)
    box(-.2, -.2, RW + .02, .04, RH, RH + .08, mat('leiste', '#c9b98c')); box(-.2, -.2, .04, RD + .02, RH, RH + .08, mat('leiste', '#c9b98c'))
    for i in range(27):
        x = i * 0.3; box(x + .01, 0, min(RW, x + .29), .035, .12, 1.05, (holz_m, holz_d, holz_h)[i % 3])
    for i in range(20):
        z = i * 0.3; box(0, z + .01, .035, min(RD, z + .29), .12, 1.05, (holz_d, holz_m, holz_h)[i % 3])
    box(0, 0, RW, .06, 1.05, 1.11, holz_h); box(0, 0, .06, RD, 1.05, 1.11, holz_h)
    box(0, 0, RW, .05, 0, .12, holz_d); box(0, 0, .05, RD, 0, .12, holz_d)
    # Vier Scheiben mit Schrank, Bahn und Strahler
    sw, cr, rt, gr = mat('schwarz', '#151515', .9), mat('creme', '#efe3c2', .9), mat('rot', '#d9333f', .9), mat('gruen', '#1f9d55', .9)
    teppich, teppich2, gold = mat('teppich', '#2b3b33', 1), mat('teppich2', '#16241d', 1), mat('gold', '#f6c64f', .4, 1.2)
    metall, lampe = mat('metall', '#2b2f33', .5), mat('lampe', '#fff2c0', .5, 14)
    for x in SCHEIBEN:
        cy, R = 1.72, .36
        box(x - .52, .035, x + .52, .075, cy - .52, cy + .52, mat('schrank', '#2a1a0e'))
        box(x - .56, .035, x - .52, .09, cy - .56, cy + .56, holz_d); box(x + .52, .035, x + .56, .09, cy - .56, cy + .56, holz_d)
        cyl(x, cy, .085, R * 1.27, .03, sw, quer=True, seg=32)
        zb = .102
        for i in range(20):
            a0 = (i - .5) * math.pi / 10; a1 = a0 + math.pi / 10; ug = i % 2
            ringstueck(x, cy, zb, R * .094, R * .57, a0, a1, cr if ug else sw)
            ringstueck(x, cy, zb, R * .57, R * .63, a0, a1, gr if ug else rt)
            ringstueck(x, cy, zb, R * .63, R * .94, a0, a1, cr if ug else sw)
            ringstueck(x, cy, zb, R * .94, R * 1.0, a0, a1, gr if ug else rt)
        cyl(x, cy, .104, R * .094, .004, gr, quer=True, seg=16); cyl(x, cy, .106, R * .04, .004, rt, quer=True, seg=12)
        box(x - .5, 0, x + .5, 2.75, 0, .012, teppich2); box(x - .44, 0, x + .44, 2.7, .012, .02, teppich)
        box(x - .44, 2.34, x + .44, 2.4, .02, .03, gold)
        box(x - .035, .04, x + .035, .86, RH - .42, RH - .35, metall); box(x - .15, .76, x + .15, .96, RH - .5, RH - .36, metall)
        box(x - .11, .8, x + .11, .92, RH - .52, RH - .5, lampe)
    # Tuer zur Theke (linke Wand) und Tuer zum Training (Rueckwand rechts)
    box(0, .31, .06, 1.39, 0, 2.16, holz_d); box(.06, .39, .1, 1.31, 0, 2.08, holz_m)
    box(.1, .47, .115, 1.23, 1.1, 1.95, holz_d); box(.1, .47, .115, 1.23, .15, .95, holz_d); cyl(.14, 1.02, 1.2, .035, .04, gold, seg=10)
    box(6.51, 0, 7.59, .06, 0, 2.16, holz_d); box(6.59, .06, 7.51, .1, 0, 2.08, holz_m)
    box(6.67, .1, 7.43, .115, 1.1, 1.95, holz_d); box(6.67, .1, 7.43, .115, .15, .95, holz_d); cyl(7.4, 1.02, .14, .035, .04, gold, quer=True, seg=10)
    # Sponsorenbanner und Fernseher an der linken Wand
    for i, c in enumerate(('#1fa55a', '#2d6cdf', '#e23d4b')):
        z = 1.95 + i * .52; box(.035, z - .2, .06, z + .2, 1.3, 2.6, mat('ban%d' % i, c, .9)); box(.03, z - .22, .07, z + .22, 2.6, 2.64, mat('stange', '#b0b4b8', .4))
        box(.06, z - .1, .066, z + .1, 2.15, 2.35, mat('weiss', '#f4f4f4', .9))
    box(.03, 4.55, .09, 5.85, 1.45, 2.35, sw); box(.09, 4.62, .1, 5.78, 1.52, 2.28, mat('tv', '#3a6ad0', .3, 2.5))
    box(.1, 4.75, .105, 5.12, 1.75, 2.05, mat('tvgelb', '#ffc340', .3, 5)); box(.1, 5.28, .105, 5.65, 1.75, 2.05, mat('tvgruen', '#7dffb0', .3, 5))
    # Bank frei im Raum, rechts hinter den Bahnen (nicht mehr unter einer Scheibe)
    box(5.7, 3.35, 7.7, 3.8, .4, .47, mat('bank', '#7a5232')); box(5.7, 3.3, 7.7, 3.38, .47, .98, holz_m)
    for x in (5.8, 6.7, 7.6): box(x - .04, 3.36, x + .04, 3.78, 0, .4, holz_d)
    # Stehtische und Pflanze
    glas, schaum = mat('bier', '#f6c64f', .2, .6), mat('schaum', '#fffbe8', .8)
    for (tx, tz) in ((4.6, 4.8), (1.9, 4.5)):
        cyl(tx, .03, tz, .28, .06, metall); cyl(tx, .56, tz, .04, 1.0, mat('chrom', '#8a8f94', .3), seg=12); cyl(tx, 1.09, tz, .4, .06, mat('bank', '#7a5232'), seg=28)
        for (dx, dz) in ((-.18, -.1), (.16, .12)):
            cyl(tx + dx, 1.19, tz + dz, .045, .14, glas, seg=12); cyl(tx + dx, 1.275, tz + dz, .048, .03, schaum, seg=12)
    cyl(7.45, .22, 5.45, .22, .44, mat('topf', '#8a5a2c'), seg=16)
    b1, b2 = mat('blatt1', '#3fa55a', .9), mat('blatt2', '#2f8a4a', .9)
    for i, (dx, y, dz, s) in enumerate(((0, .75, 0, .6), (-.16, .62, .1, .42), (.17, .6, -.1, .44), (0, 1.05, 0, .4), (.1, .9, .16, .34))):
        box(7.45 + dx - s / 2, 5.45 + dz - s / 2, 7.45 + dx + s / 2, 5.45 + dz + s / 2, y - s * .4, y + s * .4, b1 if i % 2 else b2, ry=i * .7)

def licht(name, typ, ort, energie, farbe, ziel=None, groesse=1.0, winkel=70):
    d = bpy.data.lights.new(name, typ); d.energy = energie * HELLIGKEIT; d.color = farbe
    if typ == 'SPOT': d.spot_size = math.radians(winkel); d.spot_blend = .6
    if typ == 'AREA': d.size = groesse
    o = bpy.data.objects.new(name, d); bpy.context.scene.collection.objects.link(o); o.location = (ort[0], -ort[2], ort[1])
    if ziel:
        from mathutils import Vector
        v = Vector((ziel[0], -ziel[2], ziel[1])) - o.location; o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler()
    return o

def haupt():
    t0 = time.time(); os.makedirs(ORDNER, exist_ok=True)
    log('Fassung 3 | Blender', bpy.app.version_string, '| Ordner', ORDNER)
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    except Exception: pass
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    baue()
    me = bpy.data.meshes.new('Scheibenraum'); bm.normal_update(); bm.to_mesh(me); bm.free()
    for m in MAT_LIST: me.materials.append(m)
    ob = bpy.data.objects.new('Scheibenraum', me); sc.collection.objects.link(ob)
    bpy.context.view_layer.update()
    for o in list(sc.objects):
        try:
            if o is not None and o is not ob: o.select_set(False)
        except Exception: pass
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    log('Raum gebaut:', len(me.polygons), 'Flaechen,', len(MAT_LIST), 'Farben')
    # weiche Kanten
    try:
        mod = ob.modifiers.new('Kanten', 'BEVEL'); mod.width = .011; mod.segments = 1; mod.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier='Kanten'); log('Kanten abgerundet:', len(me.polygons), 'Flaechen')
    except Exception as e: log('Kanten uebersprungen:', e)
    # Licht
    for x in SCHEIBEN: licht('Strahler', 'SPOT', (x, RH - .56, .9), 520, (1, .93, .78), ziel=(x, 1.55, .1), winkel=80)
    licht('Decke1', 'AREA', (3.2, 3.6, 3.2), 420, (1, .9, .75), ziel=(3.2, 0, 3.2), groesse=3.0)
    licht('Decke2', 'AREA', (6.4, 3.4, 4.2), 260, (1, .85, .65), ziel=(6.4, 0, 4.2), groesse=2.0)
    licht('Fuell', 'AREA', (9.5, 2.6, 8.0), 420, (.7, .8, 1), ziel=(4, 1, 3), groesse=4.0)
    licht('Wand1', 'AREA', (4.0, 2.2, 3.4), 380, (1, .92, .8), ziel=(4.0, 1.9, 0), groesse=5.0)
    licht('Wand2', 'AREA', (3.6, 2.2, 3.0), 300, (1, .92, .8), ziel=(0, 1.9, 3.0), groesse=4.0)
    w = bpy.data.worlds.new('BB_Welt'); sc.world = w
    try: w.use_nodes = True
    except Exception: pass
    try:
        bg = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
        if bg is None:
            bg = w.node_tree.nodes.new('ShaderNodeBackground'); wo = next((n for n in w.node_tree.nodes if n.type == 'OUTPUT_WORLD'), None) or w.node_tree.nodes.new('ShaderNodeOutputWorld')
            w.node_tree.links.new(bg.outputs[0], wo.inputs[0])
        bg.inputs[0].default_value = (.05, .07, .1, 1); bg.inputs[1].default_value = 1.0 * HELLIGKEIT
    except Exception as e: log('Welt-Licht uebersprungen:', e)
    # Abwicklung fuer das Lichtbild
    bpy.context.view_layer.update(); bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    try: bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.0015)
    except TypeError: bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode='OBJECT'); log('Abwicklung fertig')
    # Licht backen
    img = bpy.data.images.new('BB_Licht', AUFLOESUNG, AUFLOESUNG, alpha=False)
    for m in MAT_LIST:
        nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = img; m.node_tree.nodes.active = nd
    sc.render.engine = 'CYCLES'; sc.cycles.samples = QUALITAET
    for key, val in (('use_denoising', True), ('max_bounces', 6)):
        try: setattr(sc.cycles, key, val)
        except Exception: pass
    try: sc.render.bake.margin = 6
    except Exception: pass
    log('Licht wird ausgerechnet, Blender reagiert jetzt einige Minuten nicht ...')
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.bake(type='COMBINED')
    png = os.path.join(ORDNER, 'scheibenraum_licht.png'); img.filepath_raw = png; img.file_format = 'PNG'; img.save()
    log('Lichtbild gespeichert nach', round(time.time() - t0), 'Sekunden')
    # Ein Material mit dem fertigen Bild
    fm = bpy.data.materials.new('BB_Fertig'); b = prinzip(fm); tx = fm.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    fm.node_tree.links.new(tx.outputs['Color'], b.inputs['Base Color'])
    me.materials.clear(); me.materials.append(fm)
    me.polygons.foreach_set('material_index', [0] * len(me.polygons)); me.update()
    glb = os.path.join(ORDNER, 'scheibenraum.glb')
    ok = False
    for extra in ({'export_image_format': 'JPEG', 'export_image_quality': 84, 'export_normals': False}, {'export_image_format': 'JPEG', 'export_image_quality': 84}, {'export_image_format': 'JPEG', 'export_jpeg_quality': 84}, {'export_image_format': 'JPEG'}, {}):
        try:
            bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, **extra); ok = True; log('Export mit', extra or 'Standard'); break
        except TypeError as e: log('Export-Variante passt nicht:', e)
    if not ok: raise RuntimeError('GLB-Export fehlgeschlagen')
    try: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ORDNER, 'scheibenraum.blend'))
    except Exception as e: log('Blend-Datei nicht gespeichert:', e)
    log('FERTIG nach', round(time.time() - t0), 'Sekunden. Datei:', glb, '| Groesse', round(os.path.getsize(glb) / 1024), 'KB')
    return 'Fertig! Datei scheibenraum.glb liegt im Ordner BullseyeBoss_Blender auf dem Desktop.'

try:
    MELDUNG = haupt()
except Exception:
    LOG.append(traceback.format_exc()); MELDUNG = 'Fehler! Bitte die Datei protokoll.txt aus dem Ordner BullseyeBoss_Blender schicken.'
try:
    os.makedirs(ORDNER, exist_ok=True)
    with open(os.path.join(ORDNER, 'protokoll.txt'), 'w', encoding='utf-8') as f: f.write('\n'.join(LOG))
except Exception: pass
print(MELDUNG)
try:
    bpy.context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=MELDUNG), title='Bullseye Boss', icon='INFO')
except Exception: pass
