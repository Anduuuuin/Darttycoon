# Bullseye Boss – alle Raeume des Vereinsheims fuer Blender (Fassung 6)
# Baut Scheibenraum, Theke, Training und Buero, rechnet das Licht aus und speichert je Raum eine .glb-Datei.
# Jeder Raum besteht aus einer Huelle und einzelnen Teilen (Scheiben, Tresen-Stufen, Moebel),
# damit das Spiel genau das zeigt, was du schon gebaut hast.
# Ausfuehren: Blender > Reiter "Scripting" > Text > Oeffnen > diese Datei > Pfeil-Knopf "Skript ausfuehren"
import math, os, sys, time, traceback, json, struct
try:
    import bpy, bmesh
    from mathutils import Matrix, Vector
    BLENDER = True
except ImportError:
    BLENDER = False

# ---------- Einstellungen ----------
AUFLOESUNG = 2048     # Groesse des Lichtbilds je Raum
QUALITAET  = 32       # Rechenschritte pro Bildpunkt
HELLIGKEIT = 0.45
RAEUME = ['theke']     # zuerst nur die Theke komplett; moeglich sind: 'scheiben', 'theke', 'training', 'buero'
ORDNER = os.path.join(os.path.expanduser('~'), 'Desktop', 'BullseyeBoss_Blender')

LOG = []
def log(*a):
    s = ' '.join(str(x) for x in a); LOG.append(s); print(s)
    if not BLENDER: return
    try:
        os.makedirs(ORDNER, exist_ok=True)
        with open(os.path.join(ORDNER, 'protokoll.txt'), 'w', encoding='utf-8') as f: f.write('\n'.join(LOG))
    except Exception: pass

# =====================================================================
# Teil 1: Beschreibung der Raeume (unabhaengig von Blender)
# Spiel-Koordinaten: x = nach rechts an der Rueckwand, y = hoch, z = von der Rueckwand nach vorn
# =====================================================================
RW, RD, RH = 8.0, 6.0, 3.0
PR = []; LI = []; TE = {}; CUR = ['huelle']
def neu():
    PR.clear(); LI.clear(); TE.clear(); teil('huelle')
def teil(name, grp=None, var=None):
    CUR[0] = name; TE.setdefault(name, (grp, var))
def box(x0, z0, x1, z1, y0, y1, col, ry=0.0, glow=0.0, rough=.85, art=None, metal=0.0):
    PR.append(('box', CUR[0], (col, rough, glow, art, metal), (min(x0, x1), min(z0, z1), max(x0, x1), max(z0, z1), min(y0, y1), max(y0, y1), ry)))
def bc(cx, cy, cz, w, h, d, col, **k): box(cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2, cy - h / 2, cy + h / 2, col, **k)
def cyl(cx, cy, cz, rad, h, col, achse='y', seg=16, glow=0.0, rough=.85, art=None, metal=0.0):
    PR.append(('cyl', CUR[0], (col, rough, glow, art, metal), (cx, cy, cz, rad, h, achse, seg)))
def ring(cx, cy, z, r0, r1, a0, a1, col):
    PR.append(('ring', CUR[0], (col, .9, 0.0, None, 0.0), (cx, cy, z, r0, r1, a0, a1)))
def netz(V, F, col, glatt=True, glow=0.0, rough=.85, art=None, metal=0.0):
    PR.append(('netz', CUR[0], (col, rough, glow, art, metal), (V, F, glatt)))
def dreh(cx, cz, profil, col, seg=14, sx=1.0, sz=1.0, zu=True, **k):
    # Drehkoerper um die senkrechte Achse; profil = Liste (Radius, Hoehe) von unten nach oben
    V = []; R = []
    for r, y in profil:
        if r < 1e-6: R.append([len(V)]); V.append((cx, y, cz))
        else:
            R.append(list(range(len(V), len(V) + seg)))
            for j in range(seg):
                a = 2 * math.pi * j / seg; V.append((cx + r * math.cos(a) * sx, y, cz + r * math.sin(a) * sz))
    F = []; n = len(profil); paare = [(i, i + 1) for i in range(n - 1)] + ([] if zu else [(n - 1, 0)])
    for i, i2 in paare:
        A, B = R[i], R[i2]
        if len(A) == 1 and len(B) == 1: continue
        for j in range(seg):
            j2 = (j + 1) % seg
            if len(A) == 1: F.append((A[0], B[j], B[j2]))
            elif len(B) == 1: F.append((A[j], B[0], A[j2]))
            else: F.append((A[j], B[j], B[j2], A[j2]))
    if zu:
        if len(R[0]) > 1: F.append(tuple(R[0]))
        if len(R[-1]) > 1: F.append(tuple(reversed(R[-1])))
    netz(V, F, col, **k)
def kugel(cx, cy, cz, rx, ry, rz, col, seg=12, ringe=8, **k):
    dreh(cx, cz, [(math.sin(math.pi * i / ringe), cy - math.cos(math.pi * i / ringe) * ry) for i in range(ringe + 1)], col, seg=seg, sx=rx, sz=rz, **k)
def torus(cx, cy, cz, R, r, col, seg=18, rs=8, **k):
    dreh(cx, cz, [(R + r * math.cos(-math.pi / 2 + 2 * math.pi * i / rs), cy + r * math.sin(-math.pi / 2 + 2 * math.pi * i / rs)) for i in range(rs)], col, seg=seg, zu=False, **k)
def stab(p0, p1, r, col, seg=8, **k):
    # runder Stab zwischen zwei Punkten
    d = [b - a for a, b in zip(p0, p1)]; ln = math.sqrt(sum(a * a for a in d)) or 1; d = [a / ln for a in d]
    h = (1, 0, 0) if abs(d[0]) < .9 else (0, 1, 0)
    u = [h[1] * d[2] - h[2] * d[1], h[2] * d[0] - h[0] * d[2], h[0] * d[1] - h[1] * d[0]]; lu = math.sqrt(sum(a * a for a in u)); u = [a / lu for a in u]
    v = [u[1] * d[2] - u[2] * d[1], u[2] * d[0] - u[0] * d[2], u[0] * d[1] - u[1] * d[0]]
    V = []
    for P in (p0, p1):
        for j in range(seg):
            a = 2 * math.pi * j / seg; c, s_ = math.cos(a) * r, math.sin(a) * r; V.append(tuple(P[i] + u[i] * c + v[i] * s_ for i in range(3)))
    F = [(j, seg + j, seg + (j + 1) % seg, (j + 1) % seg) for j in range(seg)] + [tuple(range(seg)), tuple(reversed(range(seg, 2 * seg)))]
    netz(V, F, col, **k)
def linie(punkte, r, col, **k):
    for a, b in zip(punkte, punkte[1:]): stab(a, b, r, col, **k)
def prisma(punkte, y0, y1, col, **k):
    # Grundriss (x, z) in Drehrichtung wie bei dreh, senkrecht hochgezogen
    n = len(punkte); V = [(x, y0, z) for x, z in punkte] + [(x, y1, z) for x, z in punkte]
    F = [(j, n + j, n + (j + 1) % n, (j + 1) % n) for j in range(n)] + [tuple(range(n)), tuple(reversed(range(n, 2 * n)))]
    netz(V, F, col, glatt=False, **k)
def rundeck(x0, z0, x1, z1, rad, seg=5, ecken=(1, 1, 1, 1)):
    # Rechteck mit runden Ecken; ecken = (vorn rechts, vorn links, hinten links, hinten rechts)
    P = []
    for q, (cx, cz, a0) in enumerate(((x1, z1, 0), (x0, z1, 90), (x0, z0, 180), (x1, z0, 270))):
        if not ecken[q]: P.append((cx, cz)); continue
        mx = cx - rad if q in (0, 3) else cx + rad; mz = cz - rad if q in (0, 1) else cz + rad
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg); P.append((mx + rad * math.cos(a), mz + rad * math.sin(a)))
    return P
def licht(typ, ort, energie, farbe, ziel, groesse=1.0, winkel=70):
    LI.append((CUR[0], typ, ort, energie, farbe, ziel, groesse, winkel))
def onB(x, y, w, h, col, d=0.0, **k): bc(x, y, .035 + d, w, h, .05, col, **k)      # flach an der Rueckwand
def onL(z, y, w, h, col, d=0.0, **k): bc(.035 + d, y, z, .05, h, w, col, **k)      # flach an der linken Wand

HOLZ_D, HOLZ_M, HOLZ_H, METALL, CHROM, GOLD = '#4e331d', '#6a4628', '#8a5e34', '#2b2f33', '#8a8f94', '#f6c64f'

def huelle(dielen, wand, wand2, leiste, sockel, paneel=None, fliesen=False):
    n = 0
    if fliesen:
        for i in range(10):
            for j in range(8):
                box(i * .8 + .006, j * .75 + .006, i * .8 + .794, j * .75 + .744, -.06, 0, dielen[(i + j) % len(dielen)], rough=.7)
    else:
        for r in range(20):
            z0 = r * 0.3; x = -((r % 2) * 0.8)
            while x < RW:
                a, b = max(0, x), min(RW, x + 1.6)
                if b > a: box(a + .004, z0 + .004, b - .004, min(RD, z0 + .3) - .004, -.06, 0, dielen[(n * 7 + r) % len(dielen)], rough=.5, art='holzx')
                x += 1.6; n += 1
    box(-.15, -.15, RW + .15, RD + .15, -.3, -.06, '#3a2616')
    box(-.16, -.16, RW, 0, 0, RH, wand, art='putz'); box(-.16, 0, 0, RD, 0, RH, wand2, art='putz')
    box(-.2, -.2, RW + .02, .04, RH, RH + .08, leiste); box(-.2, -.2, .04, RD + .02, RH, RH + .08, leiste)
    if paneel:
        for i in range(27):
            x = i * 0.3; box(x + .01, 0, min(RW, x + .29), .035, .12, 1.05, paneel[i % 3], art='holzy')
        for i in range(20):
            z = i * 0.3; box(0, z + .01, .035, min(RD, z + .29), .12, 1.05, paneel[(i + 1) % 3], art='holzy')
        box(0, 0, RW, .06, 1.05, 1.11, paneel[2]); box(0, 0, .06, RD, 1.05, 1.11, paneel[2])
    box(0, 0, RW, .05, 0, .12, sockel); box(0, 0, .05, RD, 0, .12, sockel)

def tuer(seite, c):
    if seite == 'L':
        box(0, c - .54, .06, c + .54, 0, 2.16, HOLZ_D); box(.06, c - .46, .1, c + .46, 0, 2.08, HOLZ_M)
        box(.1, c - .38, .115, c + .38, 1.1, 1.95, HOLZ_D); box(.1, c - .38, .115, c + .38, .15, .95, HOLZ_D); cyl(.14, 1.02, c + .35, .035, .04, GOLD, 'x', 10, glow=.8, rough=.4)
    else:
        box(c - .54, 0, c + .54, .06, 0, 2.16, HOLZ_D); box(c - .46, .06, c + .46, .1, 0, 2.08, HOLZ_M)
        box(c - .38, .1, c + .38, .115, 1.1, 1.95, HOLZ_D); box(c - .38, .1, c + .38, .115, .15, .95, HOLZ_D); cyl(c + .35, 1.02, .14, .035, .04, GOLD, 'z', 10, glow=.8, rough=.4)

def scheibe(x, cy, R, z=.035):
    box(x - R * 1.45, z, x + R * 1.45, z + .04, cy - R * 1.45, cy + R * 1.45, '#2a1a0e')
    box(x - R * 1.56, z, x - R * 1.45, z + .055, cy - R * 1.56, cy + R * 1.56, HOLZ_D); box(x + R * 1.45, z, x + R * 1.56, z + .055, cy - R * 1.56, cy + R * 1.56, HOLZ_D)
    cyl(x, cy, z + .05, R * 1.27, .03, '#151515', 'z', 32, rough=.9)
    zb = z + .067
    for i in range(20):
        a0 = (i - .5) * math.pi / 10; a1 = a0 + math.pi / 10; ug = i % 2
        ring(x, cy, zb, R * .094, R * .57, a0, a1, '#efe3c2' if ug else '#151515')
        ring(x, cy, zb, R * .57, R * .63, a0, a1, '#1f9d55' if ug else '#d9333f')
        ring(x, cy, zb, R * .63, R * .94, a0, a1, '#efe3c2' if ug else '#151515')
        ring(x, cy, zb, R * .94, R * 1.0, a0, a1, '#1f9d55' if ug else '#d9333f')
    cyl(x, cy, zb + .002, R * .094, .004, '#1f9d55', 'z', 16); cyl(x, cy, zb + .004, R * .04, .004, '#d9333f', 'z', 12)
def strahler(x, cy):
    box(x - .035, .04, x + .035, .86, RH - .42, RH - .35, METALL, rough=.5); box(x - .15, .76, x + .15, .96, RH - .5, RH - .36, METALL, rough=.5)
    box(x - .11, .8, x + .11, .92, RH - .52, RH - .5, '#fff2c0', glow=14)
    licht('SPOT', (x, RH - .56, .9), 520, (1, .93, .78), (x, cy - .15, .1), winkel=80)
def bahn(x, z1=2.37):
    box(x - .5, 0, x + .5, z1 + .38, 0, .012, '#16241d', rough=1); box(x - .44, 0, x + .44, z1 + .33, .012, .02, '#2b3b33', rough=1)
    box(x - .44, z1 - .03, x + .44, z1 + .03, .02, .03, GOLD, glow=1.2, rough=.4)
def stehtisch_einfach(x, z):
    cyl(x, .03, z, .28, .06, METALL, rough=.5); cyl(x, .56, z, .04, 1.0, CHROM, seg=12, rough=.3); cyl(x, 1.09, z, .4, .06, '#7a5232', seg=28)
    for dx, dz in ((-.18, -.1), (.16, .12)):
        cyl(x + dx, 1.19, z + dz, .045, .14, GOLD, seg=12, glow=.6, rough=.2); cyl(x + dx, 1.275, z + dz, .048, .03, '#fffbe8', seg=12)
def pflanze_einfach(x, z):
    cyl(x, .22, z, .22, .44, '#8a5a2c')
    for i, (dx, y, dz, s) in enumerate(((0, .75, 0, .6), (-.16, .62, .1, .42), (.17, .6, -.1, .44), (0, 1.05, 0, .4), (.1, .9, .16, .34))):
        box(x + dx - s / 2, z + dz - s / 2, x + dx + s / 2, z + dz + s / 2, y - s * .4, y + s * .4, '#2f8a4a' if i % 2 else '#3fa55a', ry=i * .7, rough=.9)
def flasche_einfach(x, y, z, c):
    cyl(x, y + .14, z, .06, .28, c, seg=10, glow=.25, rough=.3); cyl(x, y + .34, z, .025, .12, c, seg=8, rough=.3); cyl(x, y + .41, z, .03, .03, '#1a1a1a', seg=8)
def hocker_einfach(x, z, edel):
    cyl(x, .02, z, .16, .04, '#c0c4c8' if edel else '#3a2a1a', rough=.4); cyl(x, .37, z, .03, .66, '#c0c4c8' if edel else '#3a2a1a', seg=8, rough=.4); cyl(x, .74, z, .19, .08, '#a32020' if edel else '#7a4a24', seg=18)
def deckenlicht(x, z, e=420, g=3.0, f=(1, .9, .75)): licht('AREA', (x, 3.6, z), e, f, (x, 0, z), groesse=g)
def grundlicht():
    licht('AREA', (9.5, 2.6, 8.0), 420, (.7, .8, 1), (4, 1, 3), groesse=4.0)
    licht('AREA', (4.0, 2.2, 3.4), 380, (1, .92, .8), (4.0, 1.9, 0), groesse=5.0); licht('AREA', (3.6, 2.2, 3.0), 300, (1, .92, .8), (0, 1.9, 3.0), groesse=4.0)

# ---------------- Scheibenraum ----------------
def raum_scheiben():
    huelle(('#8a5a32', '#7a4c2a', '#946238', '#80522e'), '#2b4034', '#253a2e', '#c9b98c', HOLZ_D, paneel=(HOLZ_M, HOLZ_D, HOLZ_H))
    tuer('L', .85); tuer('B', 7.05); stehtisch_einfach(4.6, 4.75)
    deckenlicht(3.2, 3.2); deckenlicht(6.4, 4.2, 260, 2.0, (1, .85, .65)); grundlicht()
    cx = lambda c: 1.0 + c * 1.45
    for i in range(4):                                   # e0..e3: eine Reihe, grosse Scheiben
        teil('e%d' % i, 'reihe', 'einzel'); scheibe(cx(i), 1.72, .36); strahler(cx(i), 1.72); bahn(cx(i))
    for i in range(8):                                   # d0..d7: zwei Reihen, etwas kleinere Scheiben
        teil('d%d' % i, 'reihe', 'doppel'); scheibe(cx(i % 4), 2.12 if i < 4 else 1.22, .3)
        if i < 4: strahler(cx(i), 1.7); bahn(cx(i))
    teil('sprahmen', 'sponsor', 'leer')
    box(.02, 1.7, .06, 4.3, 1.3, 1.34, '#3a4a42'); box(.02, 1.7, .06, 4.3, 2.56, 2.6, '#3a4a42'); box(.02, 1.7, .06, 1.74, 1.3, 2.6, '#3a4a42'); box(.02, 4.26, .06, 4.3, 1.3, 2.6, '#3a4a42')
    BAN = ('#1fa55a', '#2d6cdf', '#e23d4b', '#f6c64f', '#7d3cc8')
    for i, c in enumerate(BAN):
        teil('sp%d' % i, 'sponsor', 'voll'); z = 1.95 + i * .52
        box(.035, z - .2, .06, z + .2, 1.3, 2.6, c, rough=.9); box(.03, z - .22, .07, z + .22, 2.6, 2.64, '#b0b4b8', rough=.4); box(.06, z - .1, .066, z + .1, 2.15, 2.35, '#f4f4f4'); box(.06, z - .13, .066, z + .13, 1.5, 1.56, '#f4f4f4')
    teil('tv'); box(.03, 4.55, .09, 5.85, 1.45, 2.35, '#151515'); box(.09, 4.62, .1, 5.78, 1.52, 2.28, '#3a6ad0', glow=2.5, rough=.3)
    box(.1, 4.75, .105, 5.12, 1.75, 2.05, '#ffc340', glow=5, rough=.3); box(.1, 5.28, .105, 5.65, 1.75, 2.05, '#7dffb0', glow=5, rough=.3)
    teil('wappen'); onB(6.05, 2.55, .5, .62, '#c9a227', glow=.4, rough=.4); onB(6.05, 2.58, .4, .46, '#1f9d55', d=.02); onB(6.05, 2.58, .16, .16, '#f4f4f4', d=.04); onB(6.05, 2.27, .3, .06, '#c9a227', d=.02, glow=.4)
    teil('bank'); box(5.6, 3.3, 7.7, 3.75, .38, .46, '#7a5232'); box(5.6, 3.3, 7.7, 3.38, .46, .95, HOLZ_M)
    for x in (5.75, 6.65, 7.55): box(x - .04, 3.34, x + .04, 3.72, 0, .38, HOLZ_D)

# ---------------- Theke (komplett ausgearbeitet) ----------------
MESSING = dict(rough=.3, metal=.7); STAHL = dict(rough=.25, metal=.7)
def bierglas(x, y, z, voll=True):
    dreh(x, z, [(0, y), (.034, y), (.046, y + .15), (0, y + .15)], '#e8a020' if voll else '#dfe8ee', seg=10, glow=.6 if voll else .2, rough=.15)
    if voll: dreh(x, z, [(0, y + .15), (.048, y + .15), (.05, y + .175), (.03, y + .19), (0, y + .19)], '#fffbe8', seg=10)
FLASCHEN = ([(0, 0), (.055, 0), (.055, .2), (.02, .3), (.02, .4), (.026, .4), (.026, .43), (0, .43)],
            [(0, 0), (.065, 0), (.065, .17), (.045, .24), (.02, .27), (.02, .36), (0, .36)],
            [(0, 0), (.045, 0), (.05, .24), (.018, .32), (.018, .42), (0, .42)])
def flasche(x, y, z, c, typ=0):
    dreh(x, z, [(r, y + h) for r, h in FLASCHEN[typ % 3]], c, seg=10, glow=.3, rough=.15)
    hh = FLASCHEN[typ % 3][-1][1]; cyl(x, y + hh + .012, z, .022, .024, '#1a1a1a' if typ % 2 else '#c9a227', seg=8)
    cyl(x, y + .1, z, FLASCHEN[typ % 3][1][0] + .003, .08, '#f4f0e0', seg=10)
def hocker(x, z, edel):
    if edel:
        dreh(x, z, [(0, 0), (.17, 0), (.16, .025), (.045, .05), (0, .05)], '#c0c4c8', seg=16, **STAHL); stab((x, .05, z), (x, .68, z), .028, '#c0c4c8', **STAHL)
        torus(x, .3, z, .13, .012, '#c0c4c8', **STAHL)
        for a in (0, 2.09, 4.19): stab((x, .3, z), (x + math.cos(a) * .13, .3, z + math.sin(a) * .13), .01, '#c0c4c8', **STAHL)
        dreh(x, z, [(0, .68), (.17, .68), (.195, .71), (.195, .75), (.16, .79), (0, .8)], '#a32020', seg=16, rough=.6, art='stoff')
    else:
        for a in (.79, 2.36, 3.93, 5.5): stab((x + math.cos(a) * .17, 0, z + math.sin(a) * .17), (x + math.cos(a) * .1, .72, z + math.sin(a) * .1), .022, '#5a3a22')
        torus(x, .28, z, .135, .012, '#5a3a22'); dreh(x, z, [(0, .72), (.18, .72), (.19, .75), (.18, .78), (0, .78)], '#8a5a32', seg=14, art='holzx')
def stehtisch(x, z):
    dreh(x, z, [(0, 0), (.28, 0), (.27, .03), (.06, .07), (0, .07)], METALL, seg=18, rough=.4, metal=.5); stab((x, .07, z), (x, 1.05, z), .035, CHROM, **STAHL)
    dreh(x, z, [(0, 1.05), (.38, 1.05), (.41, 1.075), (.41, 1.1), (.38, 1.12), (0, 1.12)], '#7a5232', seg=24, rough=.35, art='holzx')
    bierglas(x - .18, 1.12, z - .1); bierglas(x + .16, 1.12, z + .12); cyl(x + .02, 1.124, z - .2, .055, .008, '#d9333f', seg=10)
def haengelampe(x, z, staerke=140, farbe='#2a3a30'):
    stab((x, RH + .05, z), (x, 2.32, z), .008, '#151515', seg=5)
    dreh(x, z, [(.2, 2.08), (.19, 2.1), (.07, 2.28), (.04, 2.32), (0, 2.32)], farbe, seg=16, rough=.4); dreh(x, z, [(0, 2.09), (.185, 2.09), (.06, 2.27), (0, 2.27)], '#fff2c0', seg=16, glow=3)
    kugel(x, 2.12, z, .05, .06, .05, '#fff6d8', seg=8, ringe=6, glow=20); licht('SPOT', (x, 2.05, z), staerke, (1, .86, .62), (x, 0, z), winkel=110)
def pflanze(x, z):
    dreh(x, z, [(0, 0), (.17, 0), (.24, .42), (.25, .46), (.21, .46), (.2, .43), (0, .43)], '#a0562c', seg=14); cyl(x, .425, z, .2, .02, '#3a2a1a', seg=14)
    for i in range(11):
        a = i * 2.4; h = .75 + (i * 37 % 10) * .05; r = .1 + (i * 53 % 10) * .022
        stab((x, .43, z), (x + math.cos(a) * r, h, z + math.sin(a) * r), .012, '#2f6a3a', seg=5)
        kugel(x + math.cos(a) * (r + .06), h + .03, z + math.sin(a) * (r + .06), .15, .045, .1, '#3fa55a' if i % 2 else '#2f8a4a', seg=8, ringe=5, rough=.6)
    kugel(x, .95, z, .2, .22, .2, '#2f8a4a', seg=10, ringe=6, rough=.7)
def bild(z, y, w, h, farben):
    onL(z, y, w, h, HOLZ_D, art='holzy'); onL(z, y, w - .1, h - .1, '#efe6cf', d=.01)
    for k, c in enumerate(farben): onL(z - w * .22 + k * w * .22, y - h * .08 + (k % 2) * h * .16, w * .2, h * .3, c, d=.02)

def tresen(lv):
    x0 = .9; LEN = (2.6, 3.0, 3.6, 4.2, 4.8, 5.2); x1 = x0 + LEN[lv]
    if lv == 0:                                          # Stufe 0: Campingtisch, Bierkasten, Kuehlbox
        box(x0, 1.5, x1, 2.2, .92, .96, '#c8b48a', rough=.5)
        for x, z, dx, dz in ((x0 + .1, 1.58, -.08, -.06), (x1 - .1, 1.58, .08, -.06), (x0 + .1, 2.12, -.08, .06), (x1 - .1, 2.12, .08, .06)): stab((x + dx, 0, z + dz), (x, .92, z), .02, '#9aa0a8', **STAHL)
        stab((x0 + .06, .45, 1.55), (x0 + .06, .45, 2.15), .012, '#9aa0a8', **STAHL); stab((x1 - .06, .45, 1.55), (x1 - .06, .45, 2.15), .012, '#9aa0a8', **STAHL)
        for i in range(3): bierglas(x0 + .5 + i * .7, .96, 1.9, i < 2)
        prisma(rundeck(1.1, 2.7, 1.8, 3.2, .04), 0, .34, '#2a6a3a'); prisma(rundeck(1.1, 2.7, 1.8, 3.2, .04), .38, .72, '#2f7a44')
        for i in range(12): cyl(1.2 + (i % 4) * .166, .75, 2.8 + (i // 4) * .15, .028, .12, '#5a3a1a', seg=8, rough=.2); cyl(1.2 + (i % 4) * .166, .815, 2.8 + (i // 4) * .15, .016, .02, '#c9a227', seg=6)
        prisma(rundeck(2.2, 2.8, 2.95, 3.3, .06), 0, .46, '#e8eef4', rough=.4); prisma(rundeck(2.18, 2.78, 2.97, 3.32, .07), .46, .56, '#2d6cdf', rough=.4); linie([(2.3, .56, 3.05), (2.3, .68, 3.05), (2.85, .68, 3.05), (2.85, .56, 3.05)], .014, '#f4f4f4', seg=6)
        return
    front = (None, '#9a6a3a', '#7a4524', '#4a2614', '#5a1e14', '#3a1410')[lv]; top = '#2a1408' if lv >= 3 else '#5a3218'
    prisma(rundeck(x0, 1.5, x1, 2.2, .3, 6, (1, 0, 0, 0)), .1, 1.0, front, art='holzy', rough=.6)          # Korpus mit runder Ecke
    prisma(rundeck(x0 + .03, 1.53, x1 - .03, 2.17, .27, 6, (1, 0, 0, 0)), 0, .1, '#1a100a')                # Sockel
    prisma(rundeck(x0 - .07, 1.42, x1 + .08, 2.29, .36, 7, (1, 0, 0, 0)), 1.0, 1.035, top, art='holzx', rough=.25)
    prisma(rundeck(x0 - .05, 1.44, x1 + .06, 2.27, .34, 7, (1, 0, 0, 0)), 1.035, 1.07, top, art='holzx', rough=.25)
    if lv >= 2:                                          # Kassetten an der Front
        n = int((x1 - .35 - x0) / .6)
        for k in range(n):
            xa = x0 + .12 + k * .6; box(xa, 2.2, xa + .5, 2.215, .2, .9, front, rough=.5); box(xa + .05, 2.215, xa + .45, 2.225, .26, .84, '#2a160d' if lv < 4 else '#22100c', art='holzy')
    stab((x0 + .1, .2, 2.38), (x1 - .32, .2, 2.38), .022, '#c9a227' if lv >= 3 else '#8a8f94', **MESSING)   # Fussstange
    x = x0 + .2
    while x < x1 - .3: stab((x, .2, 2.38), (x, .2, 2.2), .014, '#c9a227' if lv >= 3 else '#8a8f94', **MESSING); stab((x, .2, 2.38), (x, 0, 2.38), .014, '#c9a227' if lv >= 3 else '#8a8f94', **MESSING); x += .85
    if lv >= 3: bc((x0 + x1 - .3) / 2, .97, 2.212, LEN[lv] - .5, .03, .02, '#f4c430', glow=1.2, rough=.3, metal=.6)
    if lv >= 4:
        bc((x0 + x1 - .3) / 2, .14, 2.21, LEN[lv] - .5, .03, .02, '#7af0ff', glow=10)
        licht('AREA', ((x0 + x1) / 2, .2, 2.45), 70, (.45, .95, 1), ((x0 + x1) / 2, 0, 2.9), groesse=LEN[lv] * .8)
    if lv >= 5:                                          # goldene Zapfsaeule
        xs = x0 + 1.5; dreh(xs, 1.68, [(0, 1.07), (.1, 1.07), (.09, 1.1), (.045, 1.13), (.04, 1.5), (.06, 1.53), (0, 1.55)], '#c9a227', seg=14, glow=.3, **MESSING)
        stab((xs - .3, 1.45, 1.68), (xs + .3, 1.45, 1.68), .03, '#c9a227', glow=.3, **MESSING)
        for dx in (-.26, 0, .26): stab((xs + dx, 1.45, 1.68), (xs + dx, 1.36, 1.8), .014, '#f4d060', **MESSING); stab((xs + dx, 1.47, 1.68), (xs + dx, 1.62, 1.63), .016, '#151515', seg=6); kugel(xs + dx, 1.63, 1.63, .025, .03, .025, ('#d9333f', '#f4f4f4', '#1f9d55')[int(dx * 4) + 1], seg=6, ringe=4)
        box(xs - .34, 1.7, xs + .34, 1.92, 1.07, 1.085, '#8a8f98', **STAHL)
    else:
        for i in range(lv):                              # einzelne Zapfhaehne mit Tropfblech
            x = x0 + .5 + i * .55; stab((x, 1.07, 1.68), (x, 1.36, 1.68), .022, '#d0d4d8', **STAHL); stab((x, 1.33, 1.68), (x, 1.28, 1.82), .014, '#d0d4d8', **STAHL)
            stab((x, 1.36, 1.68), (x, 1.5, 1.63), .016, '#151515', seg=6); kugel(x, 1.51, 1.63, .024, .028, .024, ('#d9333f', '#f4c430', '#1f9d55', '#2d6cdf')[i % 4], seg=6, ringe=4)
            box(x - .1, 1.72, x + .1, 1.92, 1.07, 1.082, '#8a8f98', **STAHL)
    for i in range(min(4, lv + 1)):                      # Glaeser und Bierdeckel
        x = x0 + .75 + i * .85
        if x < x1 - .35: cyl(x, 1.074, 2.02, .06, .008, '#f4f0e0' if i % 2 else '#d9333f', seg=10); bierglas(x, 1.078, 2.02)
    if lv >= 2:                                          # Kasse und Glaeserstapel
        box(x0 + .08, 1.56, x0 + .42, 1.86, 1.07, 1.2, '#2a2a2e', rough=.4); box(x0 + .1, 1.58, x0 + .4, 1.66, 1.2, 1.34, '#2a2a2e', rough=.4); bc(x0 + .25, 1.27, 1.665, .24, .1, .01, '#7dffb0', glow=4)
        for k in range(3): bierglas(x1 - .55 - k * .11, 1.07, 1.62, False)
    n = 1 + lv // 2                                       # Haengelampen ueber dem Tresen
    for k in range(n): haengelampe(x0 + LEN[lv] * (k + .5) / n, 1.86, 150, '#2a3a30' if lv < 3 else '#7a1a1e')

def raum_theke():
    huelle(('#6a3f24', '#5c351d', '#73462a', '#633a20'), '#5a3028', '#4e2a23', '#c9a66a', '#3a2010', paneel=('#5a3620', '#47290f', '#6e4428'))
    tuer('L', 1.15); tuer('B', 7.05)
    dreh(3.4, 4.3, [(0, 0), (1.05, 0), (1.05, .012), (0, .012)], '#7a1a1e', seg=28, rough=1, art='stoff'); dreh(3.4, 4.3, [(0, .012), (.85, .012), (.85, .018), (0, .018)], '#a3262f', seg=28, rough=1, art='stoff'); dreh(3.4, 4.3, [(0, .018), (.5, .018), (.5, .022), (0, .022)], '#c9a227', seg=24, rough=1, art='stoff')
    stehtisch(3.4, 4.3); haengelampe(3.4, 4.3, 130, '#7a1a1e')
    # Flaschenregal hinter dem Tresen
    for y in (1.5, 2.05): box(.6, .02, 5.6, .32, y, y + .06, '#8a5a32', art='holzx')
    for x in (.6, 2.24, 3.88, 5.52): box(x, .02, x + .08, .3, 1.36, 2.62, '#2a160d', art='holzy')
    box(.54, .02, 5.66, .34, 2.62, 2.7, '#3a2010', art='holzx'); box(.6, .02, 5.6, .3, 1.3, 1.36, '#3a2010', art='holzx')
    box(.3, 0, 5.9, .5, 0, .9, '#3a2010', art='holzy'); box(.28, 0, 5.92, .54, .9, .95, '#2a1408', art='holzx', rough=.3)        # Unterschrank
    for k in range(7): box(.4 + k * .78, .5, 1.08 + k * .78, .515, .12, .8, '#4a2a16', art='holzy'); kugel(.74 + k * .78, .62, .53, .02, .02, .02, '#c9a227', seg=6, ringe=4, **MESSING)
    for k in range(5): bierglas(4.3 + k * .13, .95, .3, False)
    # Kreidetafel neben dem Regal
    onB(6.07, 1.8, .74, 1.06, HOLZ_D, art='holzy'); onB(6.07, 1.8, .64, .96, '#1c2420', d=.01)
    for k in range(5): onB(6.0 + (k % 2) * .06, 2.12 - k * .16, .36 + (k * 7 % 3) * .08, .03, '#e8e8e0', d=.02)
    onB(6.07, 1.42, .3, .1, '#f4c430', d=.02)
    # Fanshop-Regal an der linken Wand
    box(.02, 2.3, .3, 4.35, .5, 2.0, '#4a3420', art='holzy'); box(.02, 2.3, .34, 4.35, .5, .56, '#6a4a2a', art='holzx'); box(.02, 2.3, .34, 4.35, 1.94, 2.0, '#6a4a2a', art='holzx')
    stab((.32, 1.74, 2.34), (.32, 1.74, 4.31), .012, '#b0b4b8', seg=6, **STAHL)
    bild(5.75, 1.25, .34, .42, ('#2d6cdf', '#f4c430')); bild(4.75, 2.45, .5, .36, ('#d9333f', '#1f9d55', '#f4c430'))
    deckenlicht(2.2, 1.9, 200, 2.4, (1, .86, .62)); deckenlicht(4.4, 1.9, 200, 2.4, (1, .86, .62)); deckenlicht(6.5, 4.4, 220, 2.0, (1, .84, .66)); grundlicht()
    for lv in range(6): teil('bar%d' % lv, 'bar', lv); tresen(lv)
    teil('regalwand')                                    # Spiegelrueckwand mit Licht
    onB(3.1, 2.0, 4.86, 1.2, '#d8c8a8', glow=.7, rough=.15); licht('AREA', (3.1, 2.0, .5), 45, (1, .85, .6), (3.1, 2.0, 0), groesse=3.0)
    for y in (1.47, 2.02): bc(3.1, y, .3, 4.8, .015, .015, '#ffd890', glow=8)
    teil('neon'); onB(3.1, 2.86, 1.1, .4, '#1a0a14')
    z = .078; B = lambda ox, pts: [(ox + a * .26, 2.74 + b * .26, z) for a, b in pts]
    for ox, striche in ((2.68, ([(0, 0), (0, 1), (.55, 1), (.65, .8), (.55, .52), (0, .52)], [(.55, .52), (.7, .28), (.55, 0), (0, 0)])),
                        (2.98, ([(0, 0), (.35, 1), (.7, 0)], [(.15, .42), (.55, .42)])), (3.28, ([(0, 0), (0, 1), (.55, 1), (.65, .76), (.55, .52), (0, .52)], [(.3, .52), (.7, 0)]))):
        for st in striche: linie(B(ox, st), .014, '#ff4fa3', seg=6, glow=12)
    licht('AREA', (3.1, 2.86, .4), 18, (1, .3, .65), (3.1, 2.4, 1.2), groesse=.8)
    COLS = ('#2fd673', '#d9333f', '#f4c430', '#9fd3ff', '#7a4a24', '#e8e8e8', '#3a8a3a', '#c06030')
    for i in range(22):                                  # fl0..fl5: je Ausbaustufe vier Flaschen mehr
        teil('fl%d' % (i // 4)); x = .9 + (i // 2) * .42; y = 2.11 if i % 2 else 1.56
        if x <= 5.4 and not any(abs(x - q - .04) < .1 for q in (.6, 2.24, 3.88, 5.52)): flasche(x, y, .16, COLS[(i * 3) % 8], i)
        elif x <= 5.4: flasche(x + .16, y, .16, COLS[(i * 3) % 8], i)
    for edel in (0, 1):
        for i in range(6): teil('ho%s%d' % ('b' if edel else 'a', i), 'hocker', edel); hocker(.9 + .3 + i * .8, 2.75, edel)
    for i in range(5):                                   # Trikots auf Buegeln
        teil('fs%d' % i); z = 2.6 + i * .38; c = '#d9333f' if i % 2 else '#1f9d55'
        stab((.32, 1.74, z), (.32, 1.68, z), .008, '#b0b4b8', seg=5); box(.3, z - .15, .345, z + .15, 1.18, 1.68, c, art='stoff'); box(.3, z - .25, .345, z - .15, 1.46, 1.68, c, art='stoff'); box(.3, z + .15, .345, z + .25, 1.46, 1.68, c, art='stoff')
        box(.345, z - .06, .352, z + .06, 1.38, 1.52, '#ffffff'); box(.3, z - .05, .35, z + .05, 1.66, 1.7, '#f4f4f4'); box(.345, z - .15, .35, z + .15, 1.2, 1.24, '#f4f4f4')
    teil('fsschals')
    for i in range(5):
        z = 2.55 + i * .38; cyl(.2, .64, z, .075, .26, '#f4f4f4' if i % 2 else '#d9333f', 'x', 12, art='stoff'); cyl(.2, .64, z, .078, .08, '#1f9d55', 'x', 12, art='stoff')
        kugel(.19, 2.04, z + .02, .1, .07, .1, '#1f9d55' if i % 2 else '#d9333f', seg=10, ringe=6, art='stoff'); cyl(.28, 2.01, z + .02, .08, .012, '#151515', seg=10)
    teil('foto'); bild(5.2, 1.95, 1.0, .75, ('#1f9d55', '#f4c430', '#d9333f'))
    teil('kicker')
    for x, z, dx, dz in ((5.72, 3.97, -.05, -.05), (7.48, 3.97, .05, -.05), (5.72, 4.73, -.05, .05), (7.48, 4.73, .05, .05)): stab((x + dx, 0, z + dz), (x, .62, z), .04, '#2a2a2e', seg=8); cyl(x + dx, .015, z + dz, .06, .03, '#151515', seg=8)
    prisma(rundeck(5.6, 3.85, 7.6, 4.85, .08), .6, .92, '#5a3a22', art='holzx', rough=.5); box(5.68, 3.93, 7.52, 4.77, .92, .925, '#2f8a4a', rough=1, art='stoff')
    box(6.595, 3.93, 6.605, 4.77, .925, .928, '#f4f4f4'); cyl(6.6, .926, 4.35, .14, .004, '#f4f4f4', seg=16); cyl(6.6, .928, 4.35, .125, .004, '#2f8a4a', seg=16)
    for sx in (5.6, 7.52): box(sx, 3.85, sx + .08, 4.85, .92, 1.02, '#5a3a22', art='holzx')
    for sz in (3.85, 4.77): box(5.6, sz, 7.6, sz + .08, .92, 1.02, '#5a3a22', art='holzx')
    for i in range(4):
        x = 5.92 + i * .45; c = '#d9333f' if i % 2 else '#2d6cdf'; stab((x, 1.0, 3.62), (x, 1.0, 5.08), .014, '#c0c4c8', seg=6, **STAHL)
        stab((x, 1.0, 3.6 if i % 2 else 4.98), (x, 1.0, 3.72 if i % 2 else 5.1), .03, '#151515', seg=8)
        for k in range(3): box(x - .03, 4.07 + k * .28, x + .03, 4.11 + k * .28, .93, 1.06, c); kugel(x, 1.09, 4.09 + k * .28, .03, .03, .03, '#f2c49b', seg=6, ringe=4)
    kugel(6.3, .945, 4.5, .02, .02, .02, '#f4f4f4', seg=6, ringe=4)
    teil('jukebox')
    prisma(rundeck(.12, 3.98, .76, 4.57, .05), 0, 1.45, '#7a1a3a', rough=.35); cyl(.44, 1.45, 4.275, .295, .64, '#7a1a3a', 'x', 20, rough=.35)
    bc(.765, .5, 4.275, .012, .5, .44, '#2a1420'); bc(.765, 1.1, 4.275, .012, .4, .44, '#ffe9a8', glow=5)
    for k in range(6): bc(.772, .3 + k * .08, 4.275, .01, .025, .4, '#c9a227', **MESSING)
    for k in range(4): bc(.774, 1.0 + k * .07, 4.275, .008, .03, .34, '#7a4a24')
    linie([(.77, 1.45 + math.sin(math.pi * k / 10) * .25, 4.275 - math.cos(math.pi * k / 10) * .25) for k in range(11)], .02, '#ff4fa3', seg=6, glow=10)
    linie([(.77, .08, 4.025), (.77, 1.45, 4.025)], .02, '#7af0ff', seg=6, glow=10); linie([(.77, .08, 4.525), (.77, 1.45, 4.525)], .02, '#7af0ff', seg=6, glow=10)
    licht('AREA', (.95, 1.0, 4.275), 30, (1, .5, .75), (2, .6, 4.275), groesse=.6)
    teil('pflanze'); pflanze(7.45, 5.45)

# ---------------- Trainingsraum ----------------
def raum_training():
    huelle(('#4a4f55', '#42474d', '#52575e'), '#3a4a44', '#33423c', '#9aa0a8', '#1a1c20', fliesen=True)
    tuer('L', .85)
    deckenlicht(3.6, 3.4, 460, 3.2, (1, .97, .92)); deckenlicht(5.6, 4.6, 300, 2.4, (1, .97, .92)); grundlicht()
    teil('bau', 'stufe', 'bau')                          # Stufe 0: Baustelle
    box(2.4, 1.2, 3.6, 2.4, 0, 1.0, '#a07a4a'); box(3.8, 1.6, 4.8, 2.6, 0, .8, '#8a6a3a'); box(2.6, 1.4, 3.4, 2.2, 1.0, 1.7, '#b08a5a')
    for i in range(18): onB(.6 + i * .4, 2.05, .4, .16, '#f4c430' if i % 2 else '#111111')
    teil('basis', 'stufe', 'fertig')                     # ab Stufe 1: Scheibe, Bahn, Taktiktafel
    scheibe(2.0, 1.72, .36); strahler(2.0, 1.72); bahn(2.0)
    onL(3.85, 1.9, 1.7, 1.05, '#b0b4b8', rough=.4); onL(3.85, 1.9, 1.6, .95, '#f4f4f4', d=.01)
    for k, c in enumerate(('#d9333f', '#2d6cdf', '#1f9d55')): onL(3.35 + k * .45, 2.05 - k * .14, .34, .04, c, d=.02)
    onL(3.85, 1.38, 1.7, .05, '#8a8f94', d=.03)
    teil('lv2')                                          # Hantelbank
    box(4.0, 4.35, 6.2, 4.8, 0, .5, '#4a4f58'); box(4.0, 4.35, 6.2, 4.8, .5, .56, '#2a2d34')
    for x in (4.3, 4.9, 5.5): cyl(x, .63, 4.575, .03, .4, '#c0c4c8', 'x', 8, rough=.3); cyl(x - .21, .63, 4.575, .11, .06, '#17191b', 'x', 14); cyl(x + .21, .63, 4.575, .11, .06, '#17191b', 'x', 14)
    teil('lv3')                                          # zweite Scheibe und blaue Matte
    scheibe(5.0, 1.72, .36); strahler(5.0, 1.72); bahn(5.0); box(.8, 3.3, 3.4, 5.25, 0, .014, '#2a5aa0', rough=1); box(.9, 3.4, 3.3, 5.15, .014, .02, '#1f4a8a', rough=1)
    teil('lv4')                                          # Spiegel und Kamera
    onL(5.4, 1.4, 1.0, 2.3, '#9aa0a8', rough=.3); onL(5.4, 1.4, .9, 2.2, '#bfd8e8', d=.01, glow=.5, rough=.1)
    cyl(6.53, .6, .88, .03, 1.2, '#3a3a3a', seg=8); box(6.36, .78, 6.7, .98, 1.2, 1.42, '#18181c'); cyl(6.53, 1.31, 1.0, .06, .06, '#3a6ad0', 'z', 12, glow=1.5)
    teil('lv5')                                          # Auswertung und Pokalsaeule
    onB(7.0, 1.95, 1.5, 1.1, '#0e1420')
    for k, h in enumerate((.3, .5, .42, .7, .62)): onB(6.5 + k * .25, 1.55 + h / 2, .16, h, '#3aff8c' if k % 2 else '#7af0ff', d=.02, glow=5)
    box(7.2, .2, 7.6, .6, 0, .9, '#2a2a2a'); cyl(7.4, 1.0, .4, .06, .2, '#f4c430', seg=10, glow=.8, rough=.3); cyl(7.4, 1.2, .4, .14, .22, '#f4c430', seg=14, glow=.8, rough=.3)
    teil('poster'); onB(3.5, 1.9, .7, 1.05, '#f4f4f4'); onB(3.5, 2.0, .58, .6, '#d9333f', d=.01); onB(3.5, 2.0, .3, .3, '#f4c430', d=.02); onB(3.5, 1.5, .5, .08, '#151515', d=.01)
    teil('wasser'); box(7.0, 4.8, 7.45, 5.25, 0, .9, '#e8eef4'); cyl(7.225, 1.2, 5.025, .17, .6, '#7ac8ff', seg=14, glow=.8, rough=.15)

# ---------------- Buero ----------------
def raum_buero():
    huelle(('#a37a4a', '#96703f', '#ad8450', '#9c7545'), '#33435a', '#2c3a4f', '#5a4a3a', '#3a2a1a')
    tuer('L', 5.2); pflanze_einfach(7.45, 2.2)
    onL(1.6, 1.85, 1.65, 1.3, '#efe6cf'); onL(1.6, 1.85, 1.5, 1.15, '#bfe4ff', d=.01, glow=6, rough=.2); onL(1.6, 1.85, .05, 1.15, '#efe6cf', d=.02); onL(1.6, 1.85, 1.5, .05, '#efe6cf', d=.02)   # Fenster
    box(.02, .7, .2, 2.5, 1.14, 1.2, '#8a7a6a'); licht('AREA', (.4, 1.9, 1.6), 260, (.8, .9, 1), (4, .8, 2.6), groesse=1.3)
    for x, pins in ((1.5, ('#d9333f', '#2d6cdf', '#f4c430')), (4.0, ('#f4c430', '#1f9d55', '#d9333f'))):                       # Pinnwaende Liga und Pokal
        onB(x, 1.85, 2.1, 1.2, HOLZ_D); onB(x, 1.85, 1.96, 1.06, '#b98a52', d=.01)
        for k in range(6):
            px, py = x - .7 + (k % 3) * .7, 2.1 - (k // 3) * .5; onB(px, py, .46, .34, '#f4f0e0', d=.02); onB(px, py + .17, .05, .05, pins[k % 3], d=.035)
    deckenlicht(3.4, 2.9, 420, 3.0); deckenlicht(6.2, 1.6, 280, 2.2); deckenlicht(6.4, 4.6, 240, 2.0); grundlicht()
    for nm, cw in (('schrank_k', 1.5), ('schrank_g', 2.1)):                                                                  # Pokalschrank klein / gross
        teil(nm, 'schrank', nm); c0 = 5.6
        box(c0, .08, c0 + cw, .16, 0, 2.5, '#2a3a4c'); box(c0, .08, c0 + .07, .74, 0, 2.5, '#4a3020'); box(c0 + cw - .07, .08, c0 + cw, .74, 0, 2.5, '#4a3020')   # offener Schrank, die Pokale stellt das Spiel hinein
        box(c0, .08, c0 + cw, .76, 2.5, 2.58, '#4a3020'); box(c0, .08, c0 + cw, .74, 0, .5, '#4a3020'); bc(c0 + cw / 2, 2.46, .45, cw - .3, .03, .3, '#fff2c0', glow=6)
        licht('AREA', (c0 + cw / 2, 2.4, .45), 30, (1, .9, .7), (c0 + cw / 2, 0, .5), groesse=cw * .6)
        for s in range(4): box(c0 + .06, .1, c0 + cw - .06, .74, .5 + s * .55, .54 + s * .55, '#7a5a3a')
    teil('teppich'); box(1.2, 1.65, 5.8, 4.2, 0, .012, '#c9a227', rough=1); box(1.4, 1.85, 5.6, 4.0, .012, .02, '#a3262f', rough=1)
    teil('aquarium'); box(.1, 2.7, .75, 3.9, 0, .75, '#3a2a1a'); bc(.425, 1.1, 3.3, .6, .66, 1.14, '#3a8ad0', glow=2.5, rough=.1); box(.1, 2.7, .75, 3.9, 1.43, 1.48, '#3a2a1a')
    for z, y, c in ((3.0, 1.0, '#f4c430'), (3.4, 1.2, '#ff6040'), (3.7, .95, '#f4c430')): bc(.74, y, z, .03, .07, .14, c, glow=4)
    licht('AREA', (.95, 1.1, 3.3), 30, (.4, .7, 1), (2.2, .6, 3.3), groesse=.8)
    teil('stuhl', 'sitz', 'stuhl'); cyl(3.4, .22, 1.8, .04, .45, '#555555', seg=8); cyl(3.4, .03, 1.8, .26, .05, '#333333', seg=14); box(3.05, 1.5, 3.75, 2.15, .45, .55, '#3a3d44'); box(3.05, 1.42, 3.75, 1.54, .55, 1.2, '#3a3d44')
    teil('sessel', 'sitz', 'sessel'); box(2.95, 1.45, 3.85, 2.2, 0, .6, '#7a1a1e'); box(2.95, 1.3, 3.85, 1.52, .6, 1.75, '#a3262f'); box(2.87, 1.45, 2.97, 2.15, .3, .85, '#7a1a1e'); box(3.83, 1.45, 3.93, 2.15, .3, .85, '#7a1a1e')
    for chef in (0, 1):
        d0, d1, dz1, th = (1.5, 5.3, 3.4, .86) if chef else (1.9, 4.9, 3.25, .76)
        teil('tisch_c' if chef else 'tisch_n', 'tisch', chef)
        if chef:
            box(d0, 2.3, d1, dz1, 0, th, '#5a1e14'); box(d0 - .06, 2.24, d1 + .06, dz1 + .06, th, th + .07, '#3a120c', rough=.3)
            x = d0 + .45
            while x < d1: box(x - .03, dz1, x + .03, dz1 + .02, .06, th - .06, '#c9a227', glow=.5, rough=.3); x += .9
            cyl(d1 - .5, th + .11, 2.9, .12, .08, '#5a3a22', seg=12); cyl(d1 - .5, th + .3, 2.9, .07, .3, '#f4c430', seg=12, glow=.8, rough=.3)
        else:
            box(d0, 2.3, d1, dz1, th - .08, th, '#c08a50')
            for x, z in ((d0 + .08, 2.38), (d1 - .08, 2.38), (d0 + .08, dz1 - .08), (d1 - .08, dz1 - .08)): box(x - .05, z - .05, x + .05, z + .05, 0, th - .08, '#6a4220')
            box(d0 + .1, 2.34, d1 - .1, 2.4, .2, th - .08, '#8a5a30')
        top = th + (.07 if chef else 0)
        bc(2.4, top + .015, 2.95, .5, .03, .36, '#efe6cf')
        for dual in (0, 1):                              # Bildschirm einfach / doppelt, passend zur Tischhoehe
            teil('mon%d%s' % (2 if dual else 1, 'c' if chef else 'n'), 'mon' + ('c' if chef else 'n'), dual)
            mw, mh = (1.5, .58) if dual else (.9, .52); my = top + .12 + mh / 2
            cyl(3.4, top + .06, 2.56, .04, .12, '#18181c', seg=8); cyl(3.4, top + .01, 2.56, .14, .02, '#18181c', seg=12)
            bc(3.4, my, 2.58, mw, mh, .05, '#18181c'); bc(3.4, my, 2.55, mw - .08, mh - .08, .012, '#3a7ad8', glow=3.5, rough=.2)
            for k in range(3): bc(3.4 - mw * .25 + k * mw * .25, my + .08 - k * .08, 2.542, mw * .18, .05, .008, '#bfe4ff', glow=5)
    teil('kaffee'); box(6.6, 4.7, 7.6, 5.5, 0, .9, '#5a3a22'); box(6.85, 4.9, 7.3, 5.3, .9, 1.45, '#2a2a2e'); bc(7.075, 1.1, 5.31, .3, .12, .02, '#c0c4c8', glow=.8, rough=.3); cyl(7.45, .96, 5.2, .05, .12, '#ffffff', seg=10)

BAU = {'scheiben': raum_scheiben, 'theke': raum_theke, 'training': raum_training, 'buero': raum_buero}

def lin(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def rgb(h):
    h = h.lstrip('#'); return tuple(lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)) + (1.0,)
def gruppen_letzte():
    g = {}
    for name, (grp, var) in TE.items():
        if grp: g[grp] = var
    return g
def sichtbar(p, q, letzte):
    # Ist Teil q zu sehen, waehrend das Licht fuer Teil p ausgerechnet wird?
    if q == 'huelle': return True
    if p == 'huelle': return False
    gp, vp = TE[p]; gq, vq = TE[q]
    if not gq: return True
    if gq == gp: return vq == vp
    return vq == letzte[gq]

# =====================================================================
# Teil 2: Blender – bauen, Licht backen, speichern
# =====================================================================
def prinzip(m):
    try: m.use_nodes = True
    except Exception: pass
    nt = m.node_tree
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED': return n
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(b.outputs[0], out.inputs[0]); return b

MUSTER_FEHLER = []
def muster(m, b, col, art):
    # Maserung fuer Holz, Wolken fuer Putz, feines Korn fuer Stoff: hell-dunkel-Mischung der Grundfarbe
    nt = m.node_tree; tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); nz = nt.nodes.new('ShaderNodeTexNoise')
    mass, a, h = {'holzx': ((1.2, 26, 26), .62, 1.22), 'holzz': ((26, 1.2, 26), .62, 1.22), 'holzy': ((26, 26, 1.2), .62, 1.22), 'putz': ((2.2, 2.2, 2.2), .8, 1.12), 'stoff': ((70, 70, 70), .78, 1.15)}[art]
    mp.inputs['Scale'].default_value = mass
    for nm, val in (('Scale', 1.0), ('Detail', 4.0)):
        if nm in nz.inputs: nz.inputs[nm].default_value = val
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    c = rgb(col); dunkel = (c[0] * a, c[1] * a, c[2] * a, 1); hell = (min(1, c[0] * h), min(1, c[1] * h), min(1, c[2] * h), 1)
    try:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        A = [i for i in mx.inputs if i.name == 'A' and i.type == 'RGBA'][0]; B = [i for i in mx.inputs if i.name == 'B' and i.type == 'RGBA'][0]
        F = [i for i in mx.inputs if i.type == 'VALUE'][0]; O = [o for o in mx.outputs if o.type == 'RGBA'][0]
    except Exception:
        mx = nt.nodes.new('ShaderNodeMixRGB'); A, B, F, O = mx.inputs[1], mx.inputs[2], mx.inputs[0], mx.outputs[0]
    A.default_value = dunkel; B.default_value = hell
    nt.links.new(nz.outputs[0], F); nt.links.new(O, b.inputs['Base Color'])

def aufraeumen():
    try:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
    except Exception: pass
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for sammlung in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.images):
        for d in list(sammlung):
            try:
                if d.name.startswith('BB_'): sammlung.remove(d)
            except Exception: pass

def waehle(ob):
    bpy.context.view_layer.update()
    for o in list(bpy.context.scene.objects):
        try:
            if o is not None: o.select_set(o is ob)
        except Exception: pass
    bpy.context.view_layer.objects.active = ob

def blender_raum(rid):
    t0 = time.time(); sc = bpy.context.scene
    aufraeumen(); neu(); BAU[rid]()
    teile = list(TE.keys()); letzte = gruppen_letzte()
    MATS = {}; MAT_LIST = []; MAT_TEIL = []
    def mat(t, key):
        k = (t, key)
        if k in MATS: return MATS[k]
        col, rough, glow, art, metal = key; m = bpy.data.materials.new('BB_m'); b = prinzip(m)
        b.inputs['Base Color'].default_value = rgb(col)
        if 'Roughness' in b.inputs: b.inputs['Roughness'].default_value = rough
        if metal and 'Metallic' in b.inputs: b.inputs['Metallic'].default_value = metal
        if art:
            try: muster(m, b, col, art)
            except Exception as e:
                if not MUSTER_FEHLER: MUSTER_FEHLER.append(1); log('Muster uebersprungen (Farben bleiben glatt):', e)
        if glow > 0:
            for nm in ('Emission Color', 'Emission'):
                if nm in b.inputs: b.inputs[nm].default_value = rgb(col); break
            if 'Emission Strength' in b.inputs: b.inputs['Emission Strength'].default_value = glow * HELLIGKEIT
        MATS[k] = len(MAT_LIST); MAT_LIST.append(m); MAT_TEIL.append(t); return MATS[k]
    bm = bmesh.new()
    def setmat(verts, mi):
        for v in verts:
            for f in v.link_faces: f.material_index = mi
    for art, t, key, p in PR:
        mi = mat(t, key)
        if art == 'box':
            x0, z0, x1, z1, y0, y1, ry = p
            M = Matrix.Translation(((x0 + x1) / 2, -(z0 + z1) / 2, (y0 + y1) / 2)) @ Matrix.Rotation(ry, 4, 'Z') @ Matrix.Diagonal((max(x1 - x0, .002), max(z1 - z0, .002), max(y1 - y0, .002), 1.0))
            setmat(bmesh.ops.create_cube(bm, size=1.0, matrix=M)['verts'], mi)
        elif art == 'cyl':
            cx, cy, cz, rad, h, achse, seg = p; M = Matrix.Translation((cx, -cz, cy))
            if achse == 'z': M = M @ Matrix.Rotation(math.radians(90), 4, 'X')
            elif achse == 'x': M = M @ Matrix.Rotation(math.radians(90), 4, 'Y')
            try: r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=rad, radius2=rad, depth=h, matrix=M)
            except TypeError: r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, diameter1=rad, diameter2=rad, depth=h, matrix=M)
            setmat(r['verts'], mi)
        elif art == 'netz':
            V, F, glatt = p; vs = [bm.verts.new((x, -z, y)) for x, y, z in V]
            for fl in F:
                try: f = bm.faces.new([vs[i] for i in fl])
                except ValueError: continue
                f.material_index = mi; f.smooth = bool(glatt) and len(fl) <= 4
        else:
            cx, cy, z, r0, r1, a0, a1 = p; am = (a0 + a1) / 2
            P = lambda r, a: bm.verts.new((cx + math.sin(a) * r, -z, cy + math.cos(a) * r))
            vs = [P(r0, a0), P(r0, am), P(r0, a1), P(r1, a1), P(r1, am), P(r1, a0)]
            f = bm.faces.new(vs); f.material_index = mi
    me = bpy.data.meshes.new('BB_' + rid); bm.normal_update(); bm.to_mesh(me); bm.free()
    for m in MAT_LIST: me.materials.append(m)
    ob = bpy.data.objects.new('BB_' + rid, me); sc.collection.objects.link(ob); waehle(ob)
    log(rid, '| gebaut:', len(me.polygons), 'Flaechen,', len(teile), 'Teile,', len(MAT_LIST), 'Farben')
    try:
        mod = ob.modifiers.new('Kanten', 'BEVEL'); mod.width = .011; mod.segments = 1; mod.limit_method = 'ANGLE'
        bpy.ops.object.modifier_apply(modifier='Kanten')
    except Exception as e: log('Kanten uebersprungen:', e)
    waehle(ob)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    try: bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003)
    except TypeError: bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode='OBJECT'); log(rid, '| Abwicklung fertig,', len(me.polygons), 'Flaechen')
    # in einzelne Teile zerlegen (die Abwicklung bleibt erhalten)
    OBJ = {}
    for t in teile:
        idx = set(i for i, tt in enumerate(MAT_TEIL) if tt == t)
        m2 = me.copy(); m2.name = 'BB_' + t; b2 = bmesh.new(); b2.from_mesh(m2)
        weg = [f for f in b2.faces if f.material_index not in idx]
        if len(weg) == len(b2.faces): b2.free(); bpy.data.meshes.remove(m2); continue
        if weg: bmesh.ops.delete(b2, geom=weg, context='FACES')
        b2.to_mesh(m2); b2.free(); o2 = bpy.data.objects.new(t, m2); sc.collection.objects.link(o2); OBJ[t] = o2
    bpy.data.objects.remove(ob, do_unlink=True)
    # Licht
    LICHT = []
    for n, (t, typ, ort, energie, farbe, ziel, groesse, winkel) in enumerate(LI):
        d = bpy.data.lights.new('BB_L%d' % n, typ); d.energy = energie * HELLIGKEIT; d.color = farbe
        if typ == 'SPOT': d.spot_size = math.radians(winkel); d.spot_blend = .6
        if typ == 'AREA': d.size = groesse
        o = bpy.data.objects.new('BB_L%d' % n, d); sc.collection.objects.link(o); o.location = (ort[0], -ort[2], ort[1])
        v = Vector((ziel[0], -ziel[2], ziel[1])) - o.location; o.rotation_euler = v.to_track_quat('-Z', 'Y').to_euler(); LICHT.append((o, t))
    w = bpy.data.worlds.get('BB_Welt') or bpy.data.worlds.new('BB_Welt'); sc.world = w
    try: w.use_nodes = True
    except Exception: pass
    try:
        bg = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
        if bg is None:
            bg = w.node_tree.nodes.new('ShaderNodeBackground'); wo = next((n for n in w.node_tree.nodes if n.type == 'OUTPUT_WORLD'), None) or w.node_tree.nodes.new('ShaderNodeOutputWorld')
            w.node_tree.links.new(bg.outputs[0], wo.inputs[0])
        bg.inputs[0].default_value = (.05, .07, .1, 1); bg.inputs[1].default_value = 1.0 * HELLIGKEIT
    except Exception as e: log('Welt-Licht uebersprungen:', e)
    # Licht backen: jedes Teil einzeln, damit ausgeblendete Teile keine Schatten hinterlassen
    img = bpy.data.images.new('BB_Licht_' + rid, AUFLOESUNG, AUFLOESUNG, alpha=False)
    for m in MAT_LIST:
        nd = m.node_tree.nodes.new('ShaderNodeTexImage'); nd.image = img; m.node_tree.nodes.active = nd
    sc.render.engine = 'CYCLES'; sc.cycles.samples = QUALITAET
    for key, val in (('use_denoising', True), ('max_bounces', 6)):
        try: setattr(sc.cycles, key, val)
        except Exception: pass
    for key, val in (('margin', 3), ('use_clear', False)):
        try: setattr(sc.render.bake, key, val)
        except Exception: pass
    for n, (t, o) in enumerate(OBJ.items()):
        for q, oq in OBJ.items(): oq.hide_render = not sichtbar(t, q, letzte)
        for ol, tl in LICHT: ol.hide_render = not sichtbar(t, tl, letzte)
        waehle(o)
        try: bpy.ops.object.bake(type='COMBINED', use_clear=False)
        except TypeError: bpy.ops.object.bake(type='COMBINED')
        log(rid, '| Licht', n + 1, 'von', len(OBJ), '(' + t + ')', round(time.time() - t0), 's')
    for o in OBJ.values(): o.hide_render = False
    png = os.path.join(ORDNER, 'raum_%s_licht.png' % rid); img.filepath_raw = png; img.file_format = 'PNG'; img.save()
    fm = bpy.data.materials.new('BB_Fertig_' + rid); b = prinzip(fm); tx = fm.node_tree.nodes.new('ShaderNodeTexImage'); tx.image = img
    fm.node_tree.links.new(tx.outputs['Color'], b.inputs['Base Color'])
    for o in OBJ.values():
        m2 = o.data; m2.materials.clear(); m2.materials.append(fm); m2.polygons.foreach_set('material_index', [0] * len(m2.polygons)); m2.update()
    bpy.context.view_layer.update()
    for o in list(sc.objects):
        try: o.select_set(o.name in OBJ)
        except Exception: pass
    bpy.context.view_layer.objects.active = OBJ['huelle']
    glb = os.path.join(ORDNER, 'raum_%s.glb' % rid); ok = False
    for extra in ({'export_image_format': 'JPEG', 'export_image_quality': 86, 'export_normals': False}, {'export_image_format': 'JPEG', 'export_image_quality': 86}, {'export_image_format': 'JPEG', 'export_jpeg_quality': 86}, {'export_image_format': 'JPEG'}, {}):
        try:
            bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_apply=True, **extra); ok = True; break
        except TypeError as e: log('Export-Variante passt nicht:', e)
    if not ok: raise RuntimeError('GLB-Export fehlgeschlagen')
    log(rid, '| FERTIG nach', round(time.time() - t0), 'Sekunden |', round(os.path.getsize(glb) / 1024), 'KB')

def blender_haupt():
    t0 = time.time(); os.makedirs(ORDNER, exist_ok=True); fertig = []
    log('Fassung 6 | Blender', bpy.app.version_string, '| Ordner', ORDNER)
    for rid in RAEUME:
        try: blender_raum(rid); fertig.append(rid)
        except Exception: log('FEHLER in', rid); log(traceback.format_exc())
    log('Gesamt:', round((time.time() - t0) / 60, 1), 'Minuten | fertig:', ', '.join(fertig) or 'nichts')
    if len(fertig) == len(RAEUME): return 'Fertig! %d Raeume liegen im Ordner BullseyeBoss_Blender auf dem Desktop.' % len(fertig)
    return 'Nur %d von %d Raeumen fertig. Bitte die Datei protokoll.txt schicken.' % (len(fertig), len(RAEUME))

# =====================================================================
# Teil 3: Vorschau ohne Blender (einfache Farben, kein gebackenes Licht) – nur zum Pruefen der Teile
# =====================================================================
def vorschau(rid, ziel):
    neu(); BAU[rid]()
    L = (0.35, 0.8, 0.5); ln = math.sqrt(sum(a * a for a in L)); L = tuple(a / ln for a in L)
    T = {}
    def quad(t, col, glow, P, n):
        d = T.setdefault(t, ([], [], []))
        k = min(1.6, (.5 + .5 * max(0, sum(a * b for a, b in zip(n, L)))) * (1 + glow * .12)); c = [v * k for v in rgb(col)[:3]]
        b = len(d[0]) // 3
        for q in P: d[0].extend(q); d[1].extend(c)
        for i in range(1, len(P) - 1): d[2].extend((b, b + i, b + i + 1))
    for art, t, key, p in PR:
        col, rough, glow = key[:3]
        if art == 'netz':
            V, F, glatt = p
            for fl in F:
                P = [V[i] for i in fl]; a = [P[1][i] - P[0][i] for i in range(3)]; b = [P[-1][i] - P[0][i] for i in range(3)]
                n = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]); ln = math.sqrt(sum(q * q for q in n)) or 1
                quad(t, col, glow, P, tuple(q / ln for q in n))
        elif art == 'box':
            x0, z0, x1, z1, y0, y1, ry = p; cx, cz = (x0 + x1) / 2, (z0 + z1) / 2; c, s = math.cos(ry), math.sin(ry)
            def R(x, y, z): dx, dz = x - cx, z - cz; return (cx + dx * c - dz * s, y, cz + dx * s + dz * c)
            for P, n in (([(x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)], (0, 1, 0)), ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
                         ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)), ([(x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)], (0, 0, -1)),
                         ([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], (1, 0, 0)), ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0))):
                quad(t, col, glow, [R(*q) for q in P], n)
        elif art == 'cyl':
            cx, cy, cz, rad, h, achse, seg = p
            def A(u, v, w):      # u,v im Kreis, w entlang der Achse
                return (cx + u, cy + w, cz + v) if achse == 'y' else ((cx + u, cy + v, cz + w) if achse == 'z' else (cx + w, cy + u, cz + v))
            ring_o = []; ring_u = []
            for i in range(seg):
                a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg; am = (a0 + a1) / 2
                quad(t, col, glow, [A(math.cos(a0) * rad, math.sin(a0) * rad, -h / 2), A(math.cos(a0) * rad, math.sin(a0) * rad, h / 2), A(math.cos(a1) * rad, math.sin(a1) * rad, h / 2), A(math.cos(a1) * rad, math.sin(a1) * rad, -h / 2)], tuple(b - a for a, b in zip((cx, cy, cz), A(math.cos(am), math.sin(am), 0))))
                ring_o.append(A(math.cos(a0) * rad, math.sin(a0) * rad, h / 2)); ring_u.append(A(math.cos(a0) * rad, math.sin(a0) * rad, -h / 2))
            na = tuple(b - a for a, b in zip((cx, cy, cz), A(0, 0, 1))); quad(t, col, glow, ring_o, na); quad(t, col, glow, ring_u, tuple(-a for a in na))
        else:
            cx, cy, z, r0, r1, a0, a1 = p; am = (a0 + a1) / 2; P = lambda r, a: (cx + math.sin(a) * r, cy + math.cos(a) * r, z)
            quad(t, col, glow, [P(r0, a0), P(r0, am), P(r0, a1), P(r1, a1), P(r1, am), P(r1, a0)], (0, 0, 1))
    J = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [], 'materials': [{'name': 'vorschau', 'doubleSided': False, 'pbrMetallicRoughness': {'metallicFactor': 0, 'roughnessFactor': 1}}], 'accessors': [], 'bufferViews': [], 'buffers': [{}]}
    B = bytearray()
    def acc(fmt, data, typ, ct, target, mm=None):
        while len(B) % 4: B.append(0)
        raw = struct.pack('<%d%s' % (len(data), fmt), *data); J['bufferViews'].append({'buffer': 0, 'byteOffset': len(B), 'byteLength': len(raw), 'target': target}); B.extend(raw)
        n = {'SCALAR': 1, 'VEC3': 3}[typ]; a = {'bufferView': len(J['bufferViews']) - 1, 'componentType': ct, 'count': len(data) // n, 'type': typ}
        if mm: a['min'] = [min(data[i::3]) for i in range(3)]; a['max'] = [max(data[i::3]) for i in range(3)]
        J['accessors'].append(a); return len(J['accessors']) - 1
    for t, (pos, colr, idx) in T.items():
        J['meshes'].append({'name': t, 'primitives': [{'attributes': {'POSITION': acc('f', pos, 'VEC3', 5126, 34962, True), 'COLOR_0': acc('f', colr, 'VEC3', 5126, 34962)}, 'indices': acc('I', idx, 'SCALAR', 5125, 34963), 'material': 0}]})
        J['nodes'].append({'name': t, 'mesh': len(J['meshes']) - 1}); J['scenes'][0]['nodes'].append(len(J['nodes']) - 1)
    while len(B) % 4: B.append(0)
    J['buffers'][0]['byteLength'] = len(B); js = json.dumps(J, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
    with open(ziel, 'wb') as f: f.write(struct.pack('<III', 0x46546C67, 2, 28 + len(js) + len(B)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(B), 0x004E4942) + bytes(B))
    return len(T), sum(len(v[2]) for v in T.values()) // 3

if BLENDER:
    try: MELDUNG = blender_haupt()
    except Exception:
        log(traceback.format_exc()); MELDUNG = 'Fehler! Bitte die Datei protokoll.txt aus dem Ordner BullseyeBoss_Blender schicken.'
    print(MELDUNG)
    try: bpy.context.window_manager.popup_menu(lambda self, ctx: self.layout.label(text=MELDUNG), title='Bullseye Boss', icon='INFO')
    except Exception: pass
elif __name__ == '__main__':
    ziel = sys.argv[1] if len(sys.argv) > 1 else '.'
    for rid in RAEUME: print(rid, vorschau(rid, os.path.join(ziel, 'raum_%s.glb' % rid)))
