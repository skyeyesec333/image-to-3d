"""war table · shared helpers for the Blender scripts (Blender 5.2 LTS, run headless).

units: carving units while modelling (the base is 1.95 units in radius, the general 6.6 units tall);
the export scales by EXPORT_SCALE to metres, so the general stands 7.0 cm on the table. the piece
faces -Y (glTF +Z), stands on z = 0.

contents:
  paths        where the build writes (WAR_BUILD, default a temp folder) and the repo's assets/war
  scene        reset, Cycles on the GPU
  NB           a small node-tree builder, so a shader reads as a formula
  geometry     lathe, tube, box, slab (an extruded outline), finish (solidify, bevel, smooth, jitter)
"""

import math
import os
import sys
import tempfile

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
# (skill copy) the project is the folder you run from, or I3D_ROOT; the GLBs go to I3D_OUT (default
# <project>/assets/3d); working files to I3D_BUILD (default a temp folder)
REPO = os.path.abspath(os.environ.get("I3D_ROOT") or os.getcwd())
ASSETS = os.path.abspath(os.environ.get("I3D_OUT") or os.path.join(REPO, "assets", "3d"))
BUILD = os.environ.get("I3D_BUILD") or os.environ.get("WAR_BUILD") or os.path.join(tempfile.gettempdir(), "image-to-3d-build")
os.makedirs(BUILD, exist_ok=True)
os.makedirs(ASSETS, exist_ok=True)

TAU = math.tau
EXPORT_SCALE = 0.0106          # metres per carving unit (every piece uses the same)
DEG = math.pi / 180


def args():
    """the script's own arguments (after the -- on the blender command line)"""
    a = sys.argv
    return a[a.index("--") + 1:] if "--" in a else []


# ---------------------------------------------------------------- scene

def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def cycles(sc, samples=128, gpu=True, denoise=True):
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    if gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        try:
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = d.type == "METAL"
            cy.device = "GPU"
        except Exception:
            cy.device = "CPU"
    cy.samples = samples
    cy.use_denoising = denoise
    cy.use_adaptive_sampling = True
    return cy


# ---------------------------------------------------------------- node builder

def _is_sock(v):
    return isinstance(v, bpy.types.NodeSocket)


class NB:
    """build a node tree as formulas: every helper takes floats, tuples or sockets and returns a socket"""

    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        n.location = (self.x, 0)
        self.x += 40
        return n

    def put(self, sock, v):
        if _is_sock(v):
            self.nt.links.new(v, sock)
        elif v is not None:
            if sock.type in ("RGBA",) and not isinstance(v, (tuple, list)):
                v = (v, v, v, 1.0)
            elif sock.type == "RGBA" and len(v) == 3:
                v = (*v, 1.0)
            elif sock.type == "VECTOR" and not isinstance(v, (tuple, list)):
                v = (v, v, v)
            sock.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if c is not None:
            self.put(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def div(self, a, b): return self.math("DIVIDE", a, b)
    def pow(self, a, b): return self.math("POWER", a, b)
    def mn(self, a, b): return self.math("MINIMUM", a, b)
    def mx(self, a, b): return self.math("MAXIMUM", a, b)
    def sin(self, a): return self.math("SINE", a)
    def abs(self, a): return self.math("ABSOLUTE", a)
    def fract(self, a): return self.math("FRACT", a)
    def sat(self, a): return self.math("ADD", a, 0.0, clamp=True)
    def madd(self, a, b, c): return self.math("MULTIPLY_ADD", a, b, c)
    def one_minus(self, a): return self.math("SUBTRACT", 1.0, a)

    def smooth(self, e0, e1, x):
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP", clamp=True)
        self.put(n.inputs[0], x)
        self.put(n.inputs[1], e0)
        self.put(n.inputs[2], e1)
        n.inputs[3].default_value = 0.0
        n.inputs[4].default_value = 1.0
        return n.outputs[0]

    def remap(self, x, a0, a1, b0, b1, clamp=True):
        n = self.node("ShaderNodeMapRange", interpolation_type="LINEAR", clamp=clamp)
        for i, v in enumerate((x, a0, a1, b0, b1)):
            self.put(n.inputs[i], v)
        return n.outputs[0]

    def mix(self, f, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self.put(n.inputs[0], f)
        self.put(n.inputs[2], a)
        self.put(n.inputs[3], b)
        return n.outputs[0]

    def mixc(self, f, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=True)
        self.put(n.inputs[0], f)
        self.put(n.inputs[6], a)
        self.put(n.inputs[7], b)
        return n.outputs[2]

    def sep(self, v):
        n = self.node("ShaderNodeSeparateXYZ")
        self.put(n.inputs[0], v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def vec(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self.put(n.inputs[i], v)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self.put(n.inputs[0], a)
        if b is not None:
            self.put(n.inputs[1], b)
        if scale is not None:
            self.put(n.inputs[3], scale)
        out = n.outputs[1] if op in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else n.outputs[0]
        return out

    def obj(self):
        return self.node("ShaderNodeTexCoord").outputs["Object"]

    def uv(self, name):
        n = self.node("ShaderNodeUVMap")
        n.uv_map = name
        return n.outputs[0]

    def geo(self):
        return self.node("ShaderNodeNewGeometry")

    def noise(self, v, scale, detail=2.0, rough=0.5, dist=0.0, dims="3D"):
        n = self.node("ShaderNodeTexNoise", noise_dimensions=dims)
        self.put(n.inputs["Vector"], v)
        self.put(n.inputs["Scale"], scale)
        self.put(n.inputs["Detail"], detail)
        self.put(n.inputs["Roughness"], rough)
        self.put(n.inputs["Distortion"], dist)
        return n.outputs["Factor"]

    def voronoi(self, v, scale, rand=1.0, feature="F1", out="Distance"):
        n = self.node("ShaderNodeTexVoronoi", feature=feature, voronoi_dimensions="3D")
        self.put(n.inputs["Vector"], v)
        self.put(n.inputs["Scale"], scale)
        self.put(n.inputs["Randomness"], rand)
        return n.outputs[out]

    def ao(self, dist, inside=False, only_local=True, samples=16):
        n = self.node("ShaderNodeAmbientOcclusion", samples=samples, inside=inside, only_local=only_local)
        self.put(n.inputs["Distance"], dist)
        return n.outputs["AO"]

    def bevel_normal(self, radius, samples=8):
        n = self.node("ShaderNodeBevel", samples=samples)
        self.put(n.inputs["Radius"], radius)
        return n.outputs[0]

    def bump(self, height, distance, strength=1.0):
        n = self.node("ShaderNodeBump")
        self.put(n.inputs["Height"], height)
        self.put(n.inputs["Distance"], distance)
        self.put(n.inputs["Strength"], strength)
        return n.outputs[0]

    def const(self, v):
        if isinstance(v, (tuple, list)):
            n = self.node("ShaderNodeRGB")
            n.outputs[0].default_value = (*v[:3], 1.0)
        else:
            n = self.node("ShaderNodeValue")
            n.outputs[0].default_value = float(v)
        return n.outputs[0]

    def reroute(self, name, sock):
        if not _is_sock(sock):
            sock = self.const(sock)
        n = self.node("NodeReroute")
        n.name = name
        n.label = name
        self.nt.links.new(sock, n.inputs[0])
        return n.outputs[0]


# ---------------------------------------------------------------- geometry

def _new_obj(name, bm, mat=None, uv=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def lathe(name, prof, segs, a0=0.0, a1=TAU, mat=None, ysc=1.0, rfun=None, xform=None, cap=True, uref=None):
    """revolve a profile [(r, z), ...] about z. theta = 0 at the front (-Y), growing toward +X.
    a full turn wraps; a part turn is an open shell (for plates). rfun(theta, z, r) -> r shapes
    the cross-section (folds, flats). the 'param' uv: u = theta * uref (cm along the turn),
    v = cm down the profile"""
    full = abs((a1 - a0) - TAU) < 1e-6
    cols = segs if full else segs + 1
    rows = len(prof)
    if uref is None:
        uref = sum(p[0] for p in prof) / max(1, rows)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("param")
    vlen = [0.0]
    for i in range(1, rows):
        vlen.append(vlen[-1] + math.hypot(prof[i][0] - prof[i - 1][0], prof[i][1] - prof[i - 1][1]))
    grid = []
    poles = {}
    for i, (r, z) in enumerate(prof):
        if r <= 1e-6 and full:
            poles[i] = bm.verts.new((0.0, 0.0, z))
            grid.append(None)
            continue
        row = []
        for j in range(cols):
            t = a0 + (a1 - a0) * j / segs
            rr = rfun(t, z, r) if rfun else r
            row.append(bm.verts.new((rr * math.sin(t), -rr * math.cos(t) * ysc, z)))
        grid.append(row)
    th = lambda j: a0 + (a1 - a0) * j / segs
    for i in range(rows - 1):
        for j in range(segs):
            j1 = (j + 1) % cols if full else j + 1
            uj, uj1 = th(j) * uref, th(j + 1) * uref
            a, b = grid[i], grid[i + 1]
            if a is None and b is None:
                continue
            if a is None:
                f = bm.faces.new((poles[i], b[j1], b[j]))
                uvs = [((uj + uj1) / 2, vlen[i]), (uj1, vlen[i + 1]), (uj, vlen[i + 1])]
            elif b is None:
                f = bm.faces.new((a[j], a[j1], poles[i + 1]))
                uvs = [(uj, vlen[i]), (uj1, vlen[i]), ((uj + uj1) / 2, vlen[i + 1])]
            else:
                f = bm.faces.new((a[j], a[j1], b[j1], b[j]))
                uvs = [(uj, vlen[i]), (uj1, vlen[i]), (uj1, vlen[i + 1]), (uj, vlen[i + 1])]
            for l, u in zip(f.loops, uvs):
                l[uvl].uv = u
    if full and cap:
        for i in (0, rows - 1):
            if grid[i] is not None:
                f = bm.faces.new(grid[i] if i == rows - 1 else list(reversed(grid[i])))
                for l in f.loops:
                    co = l.vert.co
                    l[uvl].uv = (co.x, co.y)
    bm.normal_update()
    if full:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    else:
        # a plate: its normals point away from the axis
        bm.faces.ensure_lookup_table()
        f = bm.faces[len(bm.faces) // 2]
        c = f.calc_center_median()
        if f.normal.dot(Vector((c.x, c.y / max(ysc, 1e-3), 0.0))) < 0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
    if xform is not None:
        bmesh.ops.transform(bm, matrix=xform, verts=bm.verts)
    return _new_obj(name, bm, mat)


def _frames(pts):
    """parallel-transport frames along a polyline"""
    tans = []
    n = len(pts)
    for i in range(n):
        a = pts[max(0, i - 1)]
        b = pts[min(n - 1, i + 1)]
        tans.append((b - a).normalized())
    up = Vector((0, 0, 1)) if abs(tans[0].z) < 0.9 else Vector((1, 0, 0))
    nrm = tans[0].cross(up).normalized()
    out = []
    for i in range(n):
        t = tans[i]
        if i:
            nrm = (nrm - t * nrm.dot(t)).normalized()
        out.append((t, nrm, t.cross(nrm).normalized()))
    return out


def tube(name, pts, radii, segs=8, mat=None, squash=1.0, twist=0.0, cap=True):
    """a faceted tube along a polyline: pts [(x,y,z)], radii per point. squash flattens the
    cross-section (carved forearms are not round)"""
    pts = [Vector(p) for p in pts]
    fr = _frames(pts)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("param")
    rings = []
    vlen = [0.0]
    for i in range(1, len(pts)):
        vlen.append(vlen[-1] + (pts[i] - pts[i - 1]).length)
    for i, p in enumerate(pts):
        t, n, b = fr[i]
        ring = []
        for j in range(segs):
            a = TAU * j / segs + twist
            d = n * math.cos(a) * radii[i] + b * math.sin(a) * radii[i] * squash
            ring.append(bm.verts.new(p + d))
        rings.append(ring)
    rmean = sum(radii) / len(radii)
    for i in range(len(pts) - 1):
        for j in range(segs):
            j1 = (j + 1) % segs
            f = bm.faces.new((rings[i][j], rings[i][j1], rings[i + 1][j1], rings[i + 1][j]))
            u0, u1 = TAU * j / segs * rmean, TAU * (j + 1) / segs * rmean
            for l, uv in zip(f.loops, [(u0, vlen[i]), (u1, vlen[i]), (u1, vlen[i + 1]), (u0, vlen[i + 1])]):
                l[uvl].uv = uv
    if cap:
        for k, ring in ((0, rings[0]), (-1, rings[-1])):
            c = bm.verts.new(pts[k])
            for j in range(segs):
                j1 = (j + 1) % segs
                f = bm.faces.new((ring[j], ring[j1], c))
                for l in f.loops:
                    l[uvl].uv = (l.vert.co.x, l.vert.co.y)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _new_obj(name, bm, mat)


def box(name, size, mat=None, xform=None, subdiv=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if subdiv:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=subdiv, use_grid_fill=True)
    uvl = bm.loops.layers.uv.new("param")
    for f in bm.faces:
        ax = max(range(3), key=lambda k: abs(f.normal[k]))
        o = [k for k in range(3) if k != ax]
        for l in f.loops:
            l[uvl].uv = (l.vert.co[o[0]], l.vert.co[o[1]])
    if xform is not None:
        bmesh.ops.transform(bm, matrix=xform, verts=bm.verts)
    return _new_obj(name, bm, mat)


def slab(name, outline, thick, mat=None, xform=None):
    """an outline [(x, z)] in the XZ plane, extruded along Y (centred), as a flat carved plate"""
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("param")
    vs = [bm.verts.new((x, -thick / 2, z)) for x, z in outline]
    f = bm.faces.new(vs)
    bm.normal_update()
    if f.normal.y > 0:
        f.normal_flip()
    ext = bmesh.ops.extrude_face_region(bm, geom=[f])
    nv = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, thick, 0), verts=nv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for fc in bm.faces:
        for l in fc.loops:
            l[uvl].uv = (l.vert.co.x, l.vert.co.z)
    # the big faces as triangles (a concave outline as one ngon would not export cleanly)
    big = [fc for fc in bm.faces if len(fc.verts) > 4]
    bmesh.ops.triangulate(bm, faces=big, quad_method="BEAUTY", ngon_method="BEAUTY")
    if xform is not None:
        bmesh.ops.transform(bm, matrix=xform, verts=bm.verts)
    return _new_obj(name, bm, mat)


def finish(ob, solidify=None, bevel=0.018, segs=2, angle=32.0, smooth=38.0, offset=-1.0):
    """the carving's edges: a solid plate, then small softened bevels on every crisp edge; smooth
    shading inside a facet, sharp between facets"""
    if solidify:
        m = ob.modifiers.new("solid", "SOLIDIFY")
        m.thickness = solidify
        m.offset = offset
        m.use_even_offset = True
        m.use_quality_normals = True
    if bevel:
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = segs
        m.limit_method = "ANGLE"
        m.angle_limit = angle * DEG
        m.use_clamp_overlap = True
        m.harden_normals = False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    me.shade_smooth()
    me.set_sharp_from_angle(angle=smooth * DEG)
    return ob


def jitter(objs, amp=0.012, scale=0.55, seed=3.7):
    """the hand-made wobble: every vertex moved by one smooth field in world space, so parts that
    touch move together and no seam opens"""
    off = Vector((seed, seed * 1.7, seed * 0.3))
    for ob in objs:
        me = ob.data
        mw = ob.matrix_world
        inv = mw.inverted()
        for v in me.vertices:
            w = mw @ v.co
            d = noise.noise_vector(w * scale + off)
            v.co = inv @ (w + Vector(d) * amp)
        me.update()


def M(t=(0, 0, 0), r=(0, 0, 0), s=None, order="XYZ"):
    """a transform: translate @ rotate (degrees, Euler) @ scale"""
    from mathutils import Euler
    m = Matrix.Translation(Vector(t)) @ Euler([a * DEG for a in r], order).to_matrix().to_4x4()
    if s is not None:
        if isinstance(s, (int, float)):
            s = (s, s, s)
        m = m @ Matrix.Diagonal((*s, 1.0))
    return m


def apply_matrix(ob, m):
    ob.data.transform(m)
    ob.data.update()
    if m.determinant() < 0:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(ob.data)
        bm.free()


def blade(name, spine, widths, thicks, across, mat=None):
    """a carved blade: a diamond cross-section (a ridge down the middle of each face) along a spine,
    `widths` to each side along `across`, `thicks` front and back; a width of 0 closes to a point"""
    pts = [Vector(p) for p in spine]
    A = Vector(across).normalized()
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("param")
    rings = []
    vlen = [0.0]
    for i in range(1, len(pts)):
        vlen.append(vlen[-1] + (pts[i] - pts[i - 1]).length)
    n = len(pts)
    for i, p in enumerate(pts):
        t = (pts[min(n - 1, i + 1)] - pts[max(0, i - 1)]).normalized()
        a = (A - t * A.dot(t)).normalized()
        d = t.cross(a).normalized()
        w, th = widths[i], thicks[i]
        rings.append([bm.verts.new(p + a * w), bm.verts.new(p + d * th), bm.verts.new(p - a * w), bm.verts.new(p - d * th)])
    for i in range(n - 1):
        for j in range(4):
            j1 = (j + 1) % 4
            f = bm.faces.new((rings[i][j], rings[i][j1], rings[i + 1][j1], rings[i + 1][j]))
            for l, uv in zip(f.loops, [(j, vlen[i]), (j + 1, vlen[i]), (j + 1, vlen[i + 1]), (j, vlen[i + 1])]):
                l[uvl].uv = (uv[0] * 0.1, uv[1])
    for ring in (rings[0], rings[-1]):
        f = bm.faces.new(ring)
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x, l.vert.co.z)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _new_obj(name, bm, mat)


def band(name, outline, inset, thick, mat=None, xform=None):
    """a flat band along a closed or open outline [(x, z)] in the XZ plane (inset toward the outline's
    middle), `thick` deep along Y: the gold leaf laid round a fan's rim"""
    cx = sum(p[0] for p in outline) / len(outline)
    cz = sum(p[1] for p in outline) / len(outline)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("param")
    outer, inner = [], []
    for x, z in outline:
        dx, dz = cx - x, cz - z
        L = math.hypot(dx, dz) or 1.0
        outer.append((x, z))
        inner.append((x + dx / L * inset, z + dz / L * inset))
    layers = []
    for y in (-thick / 2, thick / 2):
        layers.append(([bm.verts.new((x, y, z)) for x, z in outer], [bm.verts.new((x, y, z)) for x, z in inner]))
    n = len(outline)
    quads = []
    for k in range(n):
        k1 = (k + 1) % n
        (o0, i0), (o1, i1) = layers
        quads += [(o0[k], o0[k1], i0[k1], i0[k]), (o1[k], i1[k], i1[k1], o1[k1]),
                  (o0[k], o1[k], o1[k1], o0[k1]), (i0[k], i0[k1], i1[k1], i1[k])]
    for q in quads:
        f = bm.faces.new(q)
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x, l.vert.co.z)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if xform is not None:
        bmesh.ops.transform(bm, matrix=xform, verts=bm.verts)
    return _new_obj(name, bm, mat)
