"""war table · meshy_optimize: a Meshy (or any one-material PBR) GLB -> the web GLBs the page loads.

run:  blender -b --factory-startup --python meshy_optimize.py -- <input.glb> <name> [options]
      writes assets/war/<name>.glb (desktop) and assets/war/<name>-m.glb (phone), and a JSON report
      (<build>/<name>-report.json, the build folder is WAR_BUILD or a temp folder)

options (all optional):
  --tris 100000        desktop triangles          --tris-m 38000     phone triangles (0: no phone file)
  --tex 2048 --nrm 2048 --orm 1024                desktop colour, normal and ORM map sizes (px)
  --tex-m 1536 --nrm-m 1024 --orm-m 512           the phone's. All maps of a cut are baked at one size
                       (its largest map, doubled when that is 1536 or less) and box-filtered down, so each
                       size must divide that bake size (2048: 2048 / 1024 / 512; 3072: 1536 / 1024 / 512)
  --margin 2 --margin-m 2   the least gap between charts in the atlas, in texels of the colour map
  --cone 120           charts: two charts merge only while their smoothed surface normals stay inside a
                       cone of this half-angle (degrees); larger: fewer, larger charts, more stretch
  --spread 1.0         charts: a chart whose texel density varies more than 2^spread between its 10th and
                       90th percentile after the unwrap (or that folds over itself) is split and unwrapped again
  --boost-top 0.26 --boost 1.6   the charts in the top 26 percent of the height (the face, the raised
                       object: where the focus goes) get 1.6 times the texel density (1 to turn off)
  --base-d 0.0416      scale: the base's diameter in metres (the scene's base, BASE_R 0.0208 x 2)
  --height 0           scale: the whole height in metres instead (wins over --base-d when set)
  --yaw 0              turn the figure about the up axis (degrees) after centring, if it does not face -Y
  --q-albedo 90,86 --q-normal 84,78 --q-orm 88,84    WebP quality per map, desktop,phone (cwebp with
                       sharp RGB->YUV when it is installed, Blender's own WebP writer otherwise)
  --coat 0.6 --coat-rough 0.12                 the lacquer clear coat (factor, roughness); the coat reads
                                               the baked normal map too (clearcoatNormalTexture)
  --tangents 1         export the MikkTSpace tangents the normal map was baked against (Draco-compressed,
                       about 300 KB on the desktop cut). Without them three.js builds a tangent frame per
                       triangle from the screen, the baked normals jump at the triangles' edges, and the
                       lacquer shows the facets (a hard triangle of light across the fan)
  --metal 0.35,0.7     the source metal's ramp to 0..1 (Meshy's metal is grey noise on non-metals)
  --lacquer 0.62,0.8   source roughness below the first value is lacquer (coat 1), above the second none
  --matte 0.72         roughness floor for the non-metal, non-lacquer paint (skin, cloth, wood)
  --ref auto           the owner's reference picture of the figure, for the colour grade: auto finds
                       _art/war-table/figures/<figure>-front.png (<figure>: the input's name before
                       "-meshy"); a path; or none (no grade)
  --grade-strength 1   how far the colour grade goes toward the reference (0: off)
  --grade-clamp 0.65,1.1   the least and largest brightness gain per hue
  --samples 16         bake samples (anti-aliasing of the bakes)
  --recolour none      site-blue (the strategist, the only blue figure): his blue armour, cloth and banner
                       moved onto the site's blue (#2745ff's hue, never purple) by hue and saturation only:
                       each blue texel keeps its own light and dark from the source, scaled so the blue's
                       median brightness is --recolour-v (0.6) and softly kept under --recolour-max (0.9),
                       at saturation --recolour-s (0.85, a little more in the darks: navy); whites (the lance
                       emblem) and gold untouched; the recoloured blue is lacquer, never metal. Measured
                       once on the desktop cut's map, used for both cuts
  --recolour-shift 0   degrees added to the recolour's hue in the map (toward cyan when negative): the page's
                       warm key (3000 K) and its tone map turn a blue toward violet; the shift sets the map
                       off so the page reads #2745ff's own hue (231.7)
  --ground-matte 0     1: the base's ground (the earth, the pebbles) matte, as the general's: no clear coat,
                       roughness at least --matte, from the base up to the ground's top (found from the mesh:
                       where the ground's band of vertices ends; --ground-top MM sets it), the plinth's own
                       wooden side untouched (the outer millimetre at each height is left as it was)
  --top-matte 0        a fraction of the height (0: off): above it, near the axis (the head and what it
                       wears), no clear coat and roughness at least --top-rough (0.5); --top-flatten 0..1
                       takes that share of the baked normal's relief away there (a faceted cap that the
                       lacquer lit like foil: the magistrate's, 0.89 / 0.5)
  --white-gain 1.0     whites and creams (saturation under about 0.4, brightness over about 0.8: a cream robe,
                       paper; skin is darker, gold more saturated) scaled by this after the grade (which barely
                       touches them): the magistrate's robe 0.87
  --keep-parts 1.0     a detached part across more than this percent of the height is never dropped as a
                       crumb, whatever its vertex count (a spear tip, a tassel, a pole)
  --renders DIR        also render the source and the exported files from four sides (Cycles) and
                       their silhouettes (Workbench), with the silhouette match in the report and the thin
                       parts' survival (the source's silhouette less its opening by a --thin-px square, 8:
                       structures under about 1.4 percent of the height across, about a millimetre on the
                       table; a WARNING when a cut keeps under 97 percent of them, the phone's 94)
  --renders-only       only the renders (with --renders) of the files already made; the report's other
                       numbers are kept from the last full run
  --report PATH        where the JSON report goes
  --out DIR            where the GLBs go (default assets/war); a name this script did not make there
                       is never overwritten (--force to override)

steps:
  1. import (vertices merged, so the UV seams are seams, not cuts); join the meshes; read the material:
     which image is base colour, roughness, metal, normal, emission, occlusion (the report says)
  2. clean: loose parts under 0.02 percent of the vertices and under --keep-parts percent of the height
     across are dropped (detached crumbs; each one is logged as a WARNING with its size and height, and
     listed in the report); every other detached part is kept and listed; degenerate faces dissolved;
     the source must be one closed piece or the report says where it is open. Each cut must come out of
     the collapse with as many pieces as the source kept (a WARNING if a part vanished or a pole broke)
  3. normalise: the bottom of the base at the origin, the base's centre on the axis, facing -Y
     (glTF +Z, three's +z: the scene's front), scaled to the scene in metres at export
  4. the web mesh: the source copied with its UVs, decimated (quadric collapse) to --tris, degenerate
     faces dissolved, smooth shaded. Then the atlas (see "the atlas" below)
  5. bake from the source onto the web mesh (selected to active, Cycles on the GPU): base colour and
     roughness / metal (emission bakes of whatever feeds the BSDF), and the tangent-space normal (the
     source's geometry and its own normal map, together). The cage is measured, not guessed: how far
     the web mesh strays from the source (each vertex to the nearest source surface), times 1.5. A
     loose cage (0.6 percent of the height) reaches through the stacked lames and the cape onto the
     layer beneath and bakes its colour and normal: 12 percent of the surface came out wrong
  6. finish the maps: metal ramped to clean 0 / 1, a lacquer mask (glossy non-metal), a matte floor
     for paint and cloth; packed as ORM (R clear-coat mask, G roughness, B metal). Metal that is not
     gold-coloured is flagged (the gold rule was tuned on the general). Then the colour grade: the
     colour map's brightness per hue matched to the reference picture's, relative to the whole figure
     (Meshy's de-lit colour runs bright and saturated in the reds; the general's came out 1.5 times
     the reference's against its gold and black)
  7. export: Principled (colour, ORM, coat from R, normal on the base and the coat), the tangents, Draco, the maps as
     WebP at their own quality; the phone file goes through 4 to 7 again from the source at its own
     budget. The report gives the focus candidates (the face, the raised hand and what it holds) for
     the scene's PIECES table

the atlas (4):
  Meshy's own charts, carried through the collapse, are the start; re-flattened as they are they fill
  39 percent of the atlas: 3,400 charts, a third of them one to three triangles, their borders cut
  through the slivers the collapse leaves (long spikes once flattened), and a quarter of the surface in
  charts that are not discs (holes, handles) which no unwrap flattens well. So: the borders are
  tidied (a sliver goes with the chart across its longest edge; a triangle with two neighbours in
  another chart joins it), every chart is made a disc (split in two from its two farthest faces until
  it is), then charts merge greedily (the longest shared border for their size first, only while the
  result stays a disc and inside --cone), then each chart is unwrapped (minimum stretch, no folds);
  a chart that still stretches or folds is split and unwrapped again. The top of the figure is
  scaled up (--boost), and the charts are packed by a skyline packer (each chart's exact shape at the
  colour map's texels, conservatively rasterised, a margin round it; turned four ways; placed where
  it wastes the least under it and stands lowest), as large as still fits. About 60 percent of the
  atlas is used at an even density (Blender's own packer, with this many charts, packs most of them
  as boxes in rows: about 40)
"""

import argparse
import heapq
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
from collections import deque

sys.dont_write_bytecode = True     # no __pycache__ beside the scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

import common as C

T0 = time.time()
WARNINGS = []


def log(*a):
    print("MESHY", f"{time.time() - T0:6.1f}s", *a, flush=True)


def warn(msg):
    WARNINGS.append(msg)
    print("MESHY", f"{time.time() - T0:6.1f}s", "WARNING:", msg, flush=True)


def parse():
    p = argparse.ArgumentParser(prog="meshy_optimize.py")
    p.add_argument("input")
    p.add_argument("name")
    p.add_argument("--tris", type=int, default=100000)
    p.add_argument("--tris-m", type=int, default=38000)
    p.add_argument("--tex", type=int, default=2048)
    p.add_argument("--nrm", type=int, default=2048)
    p.add_argument("--orm", type=int, default=1024)
    p.add_argument("--tex-m", type=int, default=1536)
    p.add_argument("--nrm-m", type=int, default=1024)
    p.add_argument("--orm-m", type=int, default=512)
    p.add_argument("--margin", type=float, default=2.0)
    p.add_argument("--margin-m", type=float, default=2.0)
    p.add_argument("--cone", type=float, default=120.0)
    p.add_argument("--spread", type=float, default=1.0)
    p.add_argument("--boost-top", type=float, default=0.26)
    p.add_argument("--boost", type=float, default=1.6)
    p.add_argument("--base-d", type=float, default=0.0416)
    p.add_argument("--height", type=float, default=0.0)
    p.add_argument("--yaw", type=float, default=0.0)
    p.add_argument("--q-albedo", default="90,86")
    p.add_argument("--q-normal", default="84,78")
    p.add_argument("--q-orm", default="88,84")
    p.add_argument("--coat", type=float, default=0.6)
    p.add_argument("--coat-rough", type=float, default=0.12)
    p.add_argument("--metal", default="0.35,0.7")
    p.add_argument("--lacquer", default="0.62,0.8")
    p.add_argument("--matte", type=float, default=0.72)
    p.add_argument("--ref", default="auto")
    p.add_argument("--grade-strength", type=float, default=1.0)
    p.add_argument("--grade-clamp", default="0.65,1.1")
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--renders", default="")
    p.add_argument("--report", default="")
    p.add_argument("--out", default=C.ASSETS)
    p.add_argument("--force", action="store_true")
    p.add_argument("--renders-only", action="store_true")
    p.add_argument("--tangents", type=int, default=1)
    p.add_argument("--keep-parts", type=float, default=1.0)
    p.add_argument("--recolour", default="none")
    p.add_argument("--recolour-shift", type=float, default=0.0)
    p.add_argument("--recolour-v", type=float, default=0.6)
    p.add_argument("--recolour-s", type=float, default=0.85)
    p.add_argument("--recolour-max", type=float, default=0.9)
    p.add_argument("--ground-matte", type=int, default=0)
    p.add_argument("--ground-top", type=float, default=0.0)
    p.add_argument("--top-matte", type=float, default=0.0)
    p.add_argument("--top-rough", type=float, default=0.5)
    p.add_argument("--top-flatten", type=float, default=0.0)
    p.add_argument("--white-gain", type=float, default=1.0)
    p.add_argument("--thin-px", type=int, default=8)
    return p.parse_args(C.args())


A = parse()
NAME = A.name
REPORT = {"name": NAME, "input": os.path.basename(A.input), "options": vars(A).copy()}
REPORT["options"].pop("input", None)


def pair(s, i):
    v = [float(x) for x in str(s).split(",")]
    return v[min(i, len(v) - 1)]


# ---------------------------------------------------------------- scene and selection

def select(active, others=()):
    for o in bpy.context.view_layer.objects:
        if o is not None:
            o.select_set(False)
    for o in others:
        o.select_set(True)
    active.select_set(True)
    bpy.context.view_layer.objects.active = active


def tri_count(ob):
    ob.data.calc_loop_triangles()
    return len(ob.data.loop_triangles)


def coords(ob):
    me = ob.data
    a = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


# ---------------------------------------------------------------- 1. import and read the material

def import_source(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, merge_vertices=True)
    meshes = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not meshes:
        raise SystemExit("no mesh in " + path)
    for o in meshes:                                   # bake the nodes' transforms into the meshes
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
    for o in [o for o in bpy.data.objects if o not in before and o.type != "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    if len(meshes) > 1:
        select(meshes[0], meshes[1:])
        bpy.ops.object.join()
    ob = meshes[0]
    ob.name = ob.data.name = NAME + "_src"
    return ob


def upstream(sock):
    """the image (and its output socket, and the channel taken from it) feeding a socket, through
    separate-colour, normal-map, mix and math nodes"""
    stack, seen = [(sock, None)], set()
    while stack:
        s, ch = stack.pop()
        for l in s.links:
            n = l.from_node
            if n.name in seen:
                continue
            seen.add(n.name)
            if n.bl_idname == "ShaderNodeTexImage":
                return {"image": n.image, "node": n.name, "socket": l.from_socket.name, "channel": ch or "RGB"}
            if n.bl_idname in ("ShaderNodeSeparateColor", "ShaderNodeSeparateRGB"):
                stack.append((n.inputs[0], l.from_socket.name))
            else:
                stack.extend((i, ch) for i in n.inputs if i.is_linked)
    return None


def read_material(ob):
    mats = [s.material for s in ob.material_slots if s.material]
    roles = {}
    if len(mats) != 1:
        warn(f"{len(mats)} materials; the first is read, every slot is baked")
    m = mats[0]
    bsdf = next((n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        raise SystemExit("no Principled BSDF in " + m.name)
    for role, inp in (("base_color", "Base Color"), ("metallic", "Metallic"), ("roughness", "Roughness"),
                      ("normal", "Normal"), ("emission", "Emission Color"), ("alpha", "Alpha")):
        u = upstream(bsdf.inputs[inp])
        if u:
            im = u["image"]
            roles[role] = {"image": im.name, "size": list(im.size), "colorspace": im.colorspace_settings.name, "channel": u["channel"]}
        elif inp in ("Metallic", "Roughness", "Alpha"):
            roles[role] = {"value": round(float(bsdf.inputs[inp].default_value), 4)}
    em = bsdf.inputs["Emission Strength"].default_value
    if "emission" in roles:
        roles["emission"]["strength"] = em
    # the importer keeps glTF occlusion in a group node beside the BSDF
    for n in m.node_tree.nodes:
        if n.bl_idname == "ShaderNodeGroup" and "Occlusion" in n.inputs:
            u = upstream(n.inputs["Occlusion"])
            if u:
                roles["occlusion"] = {"image": u["image"].name, "channel": u["channel"]}
    log("material", m.name, json.dumps(roles))
    return mats, bsdf, roles


# ---------------------------------------------------------------- 2. clean

def loose_parts(ob):
    me = ob.data
    ev = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    lab = np.arange(len(me.vertices))
    for _ in range(500):
        old = lab
        m = np.minimum(lab[ev[:, 0]], lab[ev[:, 1]])
        lab = lab.copy()
        np.minimum.at(lab, ev[:, 0], m)
        np.minimum.at(lab, ev[:, 1], m)
        lab = lab[lab[lab]]
        if np.array_equal(old, lab):
            break
    return lab


def clean_source(ob):
    T = tri_count(ob)
    lab = loose_parts(ob)
    parts, counts = np.unique(lab, return_counts=True)
    out = {"parts": int(len(parts))}
    if len(parts) > 1:
        co = coords(ob)
        z0, z1 = float(co[:, 2].min()), float(co[:, 2].max())
        h = max(z1 - z0, 1e-9)
        # the parts under 0.02 percent of the vertices (at least 12) and under --keep-parts percent of the
        # height across are crumbs: dropped, each one said. A small part that is long (a spear tip, a
        # tassel, a pole) is kept whatever its vertex count
        limit = max(12, int(0.0002 * len(lab)))
        dropped, small, detached = [], [], []
        main = int(parts[np.argmax(counts)])
        for p, n in zip(parts.tolist(), counts.tolist()):
            if p == main:
                continue
            pc = co[lab == p]
            size = float(np.linalg.norm(pc.max(0) - pc.min(0)))
            d = {"vertices": int(n), "size_pct_height": round(100 * size / h, 3),
                 "at_height_pct": round(100 * (float(pc[:, 2].mean()) - z0) / h, 1)}
            if n < limit and d["size_pct_height"] < A.keep_parts:
                dropped.append(d)
                small.append(p)
            else:
                detached.append(d)
        small = np.array(small, dtype=lab.dtype)
        out["detached_parts_kept"] = sorted(detached, key=lambda d: -d["vertices"])[:24]
        for d in out["detached_parts_kept"]:
            log(f"  kept a detached part of {d['vertices']} vertices, {d['size_pct_height']} percent of the height across, "
                f"at {d['at_height_pct']} percent up")
        for d in sorted(dropped, key=lambda d: -d["vertices"]):
            warn(f"dropped a detached part of {d['vertices']} vertices (under the {limit}-vertex limit): "
                 f"{d['size_pct_height']} percent of the height across, at {d['at_height_pct']} percent up. "
                 "Check the renders that nothing that matters went (a tassel, a horn tip)")
        if len(small):
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bm.verts.ensure_lookup_table()
            kill = [bm.verts[i] for i in np.nonzero(np.isin(lab, small))[0]]
            bmesh.ops.delete(bm, geom=kill, context="VERTS")
            bm.to_mesh(ob.data)
            bm.free()
        out["dropped_parts"] = dropped
        out["drop_limit_vertices"] = limit
        out["part_vertices"] = sorted(counts.tolist(), reverse=True)[:12]
    out["parts_kept"] = int(len(parts)) - len(out.get("dropped_parts", []))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    out["non_manifold_edges"] = sum(1 for e in bm.edges if not e.is_manifold)
    out["boundary_edges"] = sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    out["triangles"] = T
    out["vertices"] = len(ob.data.vertices)
    log("source", json.dumps(out))
    return out


def dissolve_degenerate(ob, dist):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges[:])
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()
    return n0 - len(ob.data.polygons), nm


# ---------------------------------------------------------------- 3. normalise

def normalise(ob):
    """the bottom of the base to z 0, the base's centre (its bottom ring) on the axis, turned by --yaw.
    returns the base's diameter and the height (source units)"""
    co = coords(ob)
    z0, z1 = float(co[:, 2].min()), float(co[:, 2].max())
    h = z1 - z0
    ring = co[co[:, 2] < z0 + 0.01 * h]
    cx = 0.5 * (ring[:, 0].min() + ring[:, 0].max())
    cy = 0.5 * (ring[:, 1].min() + ring[:, 1].max())
    d = float(0.5 * ((ring[:, 0].max() - ring[:, 0].min()) + (ring[:, 1].max() - ring[:, 1].min())))
    M = Matrix.Rotation(math.radians(A.yaw), 4, "Z") @ Matrix.Translation((-cx, -cy, -z0))
    ob.data.transform(M)
    ob.data.update()
    log(f"normalised: base {d:.4f} across, height {h:.4f}, moved ({-cx:.4f}, {-cy:.4f}, {-z0:.4f}), yaw {A.yaw}")
    return d, h, M


# ---------------------------------------------------------------- 4. the web mesh

def web_mesh(src, tris, name, size, margin_px):
    """decimate a copy of the source with its UVs on (the collapse carries them), then the atlas:
    charts from the source's, tidied, made discs and merged; unwrapped; packed at `size` texels"""
    me = src.data.copy()
    me.name = name
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    T = tri_count(src)
    select(ob)
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    mod = ob.modifiers.new("decimate", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = min(1.0, tris / T)
    mod.use_collapse_triangulate = True
    t = time.time()
    bpy.ops.object.modifier_apply(modifier=mod.name)
    log(f"decimated {name}: {T} -> {tri_count(ob)} triangles in {time.time() - t:.1f}s")
    h = float(coords(ob)[:, 2].max())
    removed, nm = dissolve_degenerate(ob, 1e-6 * h)
    for p in me.polygons:
        p.use_smooth = True
    log(f"  degenerate faces dissolved {removed}; non-manifold edges {nm}")
    t = time.time()
    carried = me.uv_layers[0].name if me.uv_layers else None
    if carried:
        me.uv_layers.active = me.uv_layers[carried]
        select(ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.seams_from_islands(mark_seams=True)
        bpy.ops.object.mode_set(mode="OBJECT")
    topo = Topo(ob)
    seam = np.zeros(len(me.edges), bool)
    me.edges.foreach_get("use_seam", seam)
    if not carried:                                    # a source without UVs: start from one chart per face
        seam[:] = True
    info = {"triangles": tri_count(ob), "non_manifold_edges": nm, "degenerate_dissolved": removed}
    # every detached part of the source must come through the collapse (a pole, a mallet's head, a
    # chest on the base): a part collapsed to nothing is said
    info["parts"] = int(len(np.unique(loose_parts(ob))))
    want = REPORT.get("source", {}).get("parts_kept")
    if want and info["parts"] < want:
        warn(f"{name}: {want - info['parts']} of the source's {want} detached parts did not survive the collapse: "
             "check the renders, raise the triangles")
    elif want and info["parts"] > want:
        warn(f"{name}: the collapse broke the mesh into {info['parts']} pieces (the source: {want}): check the thin parts "
             "(a pole, a handle) in the renders")
    lab, cinfo = make_charts(topo, seam)
    info.update(cinfo)
    uv = me.uv_layers.new(name="atlas")
    me.uv_layers.active = uv
    lab, rinfo = unwrap_charts(ob, topo, lab)
    info.update(rinfo)
    U = np.empty(len(me.loops) * 2, np.float64)
    me.uv_layers["atlas"].data.foreach_get("uv", U)
    U = U.reshape(-1, 3, 2)                            # (triangles: loop i of face f is 3f + i)
    boosted = boost_top(topo, lab, U, A.boost_top, A.boost) if A.boost > 1 and A.boost_top > 0 else 0.0
    U, pinfo = pack_atlas(topo, lab, U, size, margin_px)
    info.update(pinfo)
    me.uv_layers["atlas"].data.foreach_set("uv", U.astype(np.float32).ravel())
    for l in [l for l in me.uv_layers if l.name != "atlas"]:
        me.uv_layers.remove(l)
    me.update()
    seams = np.zeros(len(me.edges), bool)
    me.edges.foreach_get("use_seam", seams)
    info.update({"vertices": len(me.vertices), "seam_edges": int(seams.sum()), "boosted_surface_share": round(boosted, 4),
                 "atlas_seconds": round(time.time() - t, 1)})
    log(f"  atlas in {time.time() - t:.1f}s")
    return ob, info, lab, topo


class Topo:
    """a triangle mesh's adjacency, as arrays: each face's edges, vertices, the neighbour across each
    edge (-1 across an open or non-manifold edge), areas, normals (raw and smoothed: the shape without
    the sculpt's small bumps), each face's 3d aspect and the neighbour across its longest edge"""

    def __init__(self, ob):
        me = ob.data
        nf = len(me.polygons)
        lt = np.empty(nf, np.int32)
        me.polygons.foreach_get("loop_total", lt)
        if not (lt == 3).all():
            raise SystemExit("the web mesh must be all triangles")
        le = np.empty(len(me.loops), np.int32)
        me.loops.foreach_get("edge_index", le)
        self.nf = nf
        self.fe = le.reshape(-1, 3)
        tv = np.empty(nf * 3, np.int32)
        me.polygons.foreach_get("vertices", tv)
        self.tv = tv.reshape(-1, 3)
        ne = len(me.edges)
        ecnt = np.bincount(le, minlength=ne)
        lf = np.repeat(np.arange(nf), 3)
        o = np.argsort(le, kind="stable")
        fs = lf[o]
        st = np.concatenate([[0], np.cumsum(ecnt)[:-1]])
        self.two = np.nonzero(ecnt == 2)[0]
        self.fa, self.fb = fs[st[self.two]], fs[st[self.two] + 1]
        ef0 = np.full(ne, -1, np.int64)
        ef1 = np.full(ne, -1, np.int64)
        ef0[self.two], ef1[self.two] = self.fa, self.fb
        e = self.fe
        self.nb = np.where(ef0[e] == np.arange(nf)[:, None], ef1[e], ef0[e])
        self.nb[ecnt[e] != 2] = -1
        co = coords(ob).astype(np.float64)
        self.co = co
        ev = np.empty(ne * 2, np.int32)
        me.edges.foreach_get("vertices", ev)
        self.ev = ev.reshape(-1, 2)
        self.elen = np.linalg.norm(co[self.ev[:, 0]] - co[self.ev[:, 1]], axis=1)
        p = co[self.tv]
        cr = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        self.area = 0.5 * np.linalg.norm(cr, axis=1)
        self.fn = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-30)
        self.zc = p[:, :, 2].mean(1)
        fel = self.elen[self.fe]
        self.aspect = fel.max(1) ** 2 / np.maximum(2 * self.area, 1e-30)
        longest = self.fe[np.arange(nf), fel.argmax(1)]
        self.long_nb = np.full(nf, -1, np.int64)
        for k in range(3):
            m = self.fe[:, k] == longest
            self.long_nb[m] = self.nb[m, k]
        # smoothed normals: the mesh relaxed (30 passes at half strength) on a throwaway copy
        P = ob.copy()
        P.data = me.copy()
        bpy.context.scene.collection.objects.link(P)
        sm = P.modifiers.new("relax", "SMOOTH")
        sm.factor, sm.iterations = 0.5, 30
        select(P)
        bpy.ops.object.modifier_apply(modifier=sm.name)
        sn = np.empty(nf * 3, np.float32)
        P.data.polygons.foreach_get("normal", sn)
        self.sn = sn.reshape(-1, 3).astype(np.float64)
        d = P.data
        bpy.data.objects.remove(P, do_unlink=True)
        bpy.data.meshes.remove(d)
        select(ob)

    def components(self, lab):
        """split every label into its edge-connected pieces"""
        same = lab[self.fa] == lab[self.fb]
        a, b = self.fa[same], self.fb[same]
        l = np.arange(self.nf)
        while True:
            m = np.minimum(l[a], l[b])
            old = l.copy()
            np.minimum.at(l, a, m)
            np.minimum.at(l, b, m)
            l = l[l]
            if np.array_equal(old, l):
                break
        return np.unique(l, return_inverse=True)[1]

    def chi(self, faces):
        """the Euler characteristic of a set of faces (a disc: 1)"""
        fs = np.asarray(faces)
        return len(np.unique(self.tv[fs])) - len(np.unique(self.fe[fs])) + len(fs)

    def border(self, lab):
        return float(self.elen[self.two[lab[self.fa] != lab[self.fb]]].sum())

    def seams(self, lab, ne):
        s = np.zeros(ne, bool)
        s[self.two[lab[self.fa] != lab[self.fb]]] = True
        return s


def tidy_borders(topo, lab, iters=12):
    """a sliver (3d aspect over 6) goes with the chart across its longest edge (so a fan of slivers is
    never cut across, which flattens into spikes); a triangle whose two neighbours share a chart that
    is not its own joins it. Half the faces move per pass (by parity), so two never swap back and forth"""
    nf = topo.nf
    idx = np.arange(nf)
    for it in range(iters):
        lab = lab.copy()
        sl = (topo.aspect > 6.0) & (topo.long_nb >= 0) & ((idx + it) % 2 == 0)
        lab[sl] = lab[topo.long_nb[sl]]
        nl = np.where(topo.nb >= 0, lab[np.maximum(topo.nb, 0)], -1)
        new = lab.copy()
        for i, j in ((0, 1), (0, 2), (1, 2)):
            c = (nl[:, i] == nl[:, j]) & (nl[:, i] >= 0) & (nl[:, i] != lab)
            new[c] = nl[c, i]
        m = (new != lab) & ((idx + it) % 2 == 0)
        lab = np.where(m, new, lab)
    return topo.components(lab)


def _bfs(topo, fset, seeds):
    owner, dq, last = {}, deque(), seeds[0]
    for k, s in enumerate(seeds):
        owner[s] = k
        dq.append(s)
    while dq:
        f = dq.popleft()
        last = f
        for g in topo.nb[f]:
            g = int(g)
            if g >= 0 and g in fset and g not in owner:
                owner[g] = owner[f]
                dq.append(g)
    return owner, last


def halve(topo, faces):
    """a chart in two: grown at once from its two farthest faces (a hop apart)"""
    fset = set(faces)
    _, a = _bfs(topo, fset, [faces[0]])
    _, b = _bfs(topo, fset, [a])
    owner, _ = _bfs(topo, fset, [a, b])
    return [f for f in faces if owner.get(f, 0) == 0], [f for f in faces if owner.get(f, 0) == 1]


def make_discs(topo, lab):
    """every chart that is not a disc (holes, handles) halved until its pieces are"""
    order = np.argsort(lab, kind="stable")
    bnd = np.searchsorted(lab[order], np.arange(lab.max() + 2))
    new = lab.copy()
    nxt = lab.max() + 1
    split = 0

    def rec(faces, depth):
        if len(faces) < 4 or depth > 14 or topo.chi(faces) == 1:
            return [faces]
        p0, p1 = halve(topo, faces)
        if not p0 or not p1:
            return [faces]
        return rec(p0, depth + 1) + rec(p1, depth + 1)
    for c in range(lab.max() + 1):
        fs = order[bnd[c]:bnd[c + 1]].tolist()
        if topo.chi(fs) == 1:
            continue
        split += 1
        for part in rec(fs, 0)[1:]:
            new[np.array(part)] = nxt
            nxt += 1
    return topo.components(new), split


def _cone_union(a1, t1, a2, t2):
    phi = math.acos(max(-1.0, min(1.0, float(a1 @ a2))))
    if phi + t2 <= t1:
        return a1, t1
    if phi + t1 <= t2:
        return a2, t2
    t = 0.5 * (phi + t1 + t2)
    if t >= math.pi or phi < 1e-9:
        return a1, min(math.pi, t)
    s = (t - t1) / phi
    so = math.sin(phi)
    v = (math.sin((1 - s) * phi) / so) * a1 + (math.sin(s * phi) / so) * a2
    return v / np.linalg.norm(v), t


def merge_charts(topo, lab, cone_deg, tiny_share=3e-4):
    """greedy: the pair with the longest shared border for the smaller one's perimeter merges first,
    while the merged chart stays a disc and its smoothed normals inside the cone (a chart under
    tiny_share of the surface merges into a neighbour whatever its normals)"""
    nc = lab.max() + 1
    far, sn = topo.area, topo.sn
    Ar = np.bincount(lab, far, nc)
    N = np.stack([np.bincount(lab, far * sn[:, k], nc) for k in range(3)], 1)
    ax = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    ang = np.arccos(np.clip((sn * ax[lab]).sum(1), -1, 1))
    th = np.zeros(nc)
    np.maximum.at(th, lab, ang)
    bm = lab[topo.fa] != lab[topo.fb]
    ca, cb = lab[topo.fa][bm], lab[topo.fb][bm]
    be = topo.two[bm]
    ll = topo.elen[be]
    Pm = np.zeros(nc)
    np.add.at(Pm, ca, ll)
    np.add.at(Pm, cb, ll)
    adj = [dict() for _ in range(nc)]
    adjn = [dict() for _ in range(nc)]
    bv = [set() for _ in range(nc)]
    for x, y, w, e in zip(ca.tolist(), cb.tolist(), ll.tolist(), be.tolist()):
        adj[x][y] = adj[x].get(y, 0.0) + w
        adj[y][x] = adj[x][y]
        adjn[x][y] = adjn[x].get(y, 0) + 1
        adjn[y][x] = adjn[x][y]
        v0, v1 = int(topo.ev[e, 0]), int(topo.ev[e, 1])
        bv[x].update((v0, v1))
        bv[y].update((v0, v1))
    Fc = np.bincount(lab, minlength=nc)
    ue = np.unique(np.stack([np.repeat(lab, 3), topo.fe.reshape(-1)], 1), axis=0)
    uvv = np.unique(np.stack([np.repeat(lab, 3), topo.tv.reshape(-1)], 1), axis=0)
    chi = (np.bincount(uvv[:, 0], minlength=nc) - np.bincount(ue[:, 0], minlength=nc) + Fc).tolist()
    axl = [ax[i] for i in range(nc)]
    th, Ar, Pr = th.tolist(), Ar.tolist(), Pm.tolist()
    TH, TINY = math.radians(cone_deg), tiny_share * float(far.sum())

    def merged_chi(i, j):
        a, b = (bv[i], bv[j]) if len(bv[i]) < len(bv[j]) else (bv[j], bv[i])
        return chi[i] + chi[j] - (len(a & b) - adjn[i][j])

    def score(i, j):
        tiny = min(Ar[i], Ar[j]) < TINY
        if not tiny and _cone_union(axl[i], th[i], axl[j], th[j])[1] > TH:
            return None
        if merged_chi(i, j) != 1:
            return None
        return adj[i][j] / max(1e-12, min(Pr[i], Pr[j])) + (10.0 if tiny else 0.0)
    heap = []
    for i in range(nc):
        for j in adj[i]:
            if i < j:
                s = score(i, j)
                if s is not None:
                    heap.append((-s, i, j, 0, 0))
    heapq.heapify(heap)
    parent = list(range(nc))
    ver = [0] * nc
    alive = [True] * nc
    while heap:
        _, i, j, vi, vj = heapq.heappop(heap)
        if not (alive[i] and alive[j]) or ver[i] != vi or ver[j] != vj:
            continue
        if Ar[j] > Ar[i]:
            i, j = j, i
        a, t = _cone_union(axl[i], th[i], axl[j], th[j])
        c2 = merged_chi(i, j)
        sh = adj[i].pop(j)
        adj[j].pop(i)
        adjn[i].pop(j)
        adjn[j].pop(i)
        for k, w in adj[j].items():
            adj[k].pop(j)
            adj[i][k] = adj[i].get(k, 0.0) + w
            adj[k][i] = adj[i][k]
            n2 = adjn[k].pop(j)
            adjn[i][k] = adjn[i].get(k, 0) + n2
            adjn[k][i] = adjn[i][k]
        adj[j], adjn[j] = {}, {}
        alive[j] = False
        parent[j] = i
        bv[i] |= bv[j]
        bv[j] = set()
        axl[i], th[i] = a, t
        Ar[i] += Ar[j]
        Pr[i] = Pr[i] + Pr[j] - 2 * sh
        chi[i] = c2
        ver[i] += 1
        ver[j] += 1
        for k in adj[i]:
            s2 = score(i, k)
            if s2 is not None:
                heapq.heappush(heap, (-s2, i, k, ver[i], ver[k]))

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x
    root = np.array([find(c) for c in range(nc)])
    return np.unique(root[lab], return_inverse=True)[1]


def make_charts(topo, seam):
    """the source's charts (carried), tidied, made discs, merged, tidied and made discs again"""
    nf = topo.nf
    # the carried charts: faces joined across the edges that are not seams
    keep = ~seam[topo.two]
    a, b = topo.fa[keep], topo.fb[keep]
    l = np.arange(nf)
    while True:
        m = np.minimum(l[a], l[b])
        old = l.copy()
        np.minimum.at(l, a, m)
        np.minimum.at(l, b, m)
        l = l[l]
        if np.array_equal(old, l):
            break
    lab = np.unique(l, return_inverse=True)[1]
    out = {"charts_source": int(lab.max() + 1), "border_source": round(topo.border(lab), 3)}
    lab = tidy_borders(topo, lab)
    lab, split0 = make_discs(topo, lab)
    lab = merge_charts(topo, lab, A.cone)
    lab = tidy_borders(topo, lab)
    lab, split1 = make_discs(topo, lab)
    out.update({"charts_not_discs_split": int(split0 + split1), "charts_merged": int(lab.max() + 1),
                "border_merged": round(topo.border(lab), 3)})
    log(f"  charts: {out['charts_source']} from the source -> {out['charts_merged']} "
        f"(border {out['border_source']} -> {out['border_merged']}, {split0 + split1} split into discs)")
    return lab, out


def chart_quality(topo, lab, U):
    """per chart: the spread of its texel density (log2, 90th over 10th percentile, by area) and the
    share of its area folded over (mirrored against the rest)"""
    T = U.reshape(-1, 3, 2)
    sa = 0.5 * ((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 2, 0] - T[:, 0, 0]) * (T[:, 1, 1] - T[:, 0, 1]))
    nc = lab.max() + 1
    far = topo.area
    A3 = np.bincount(lab, far, nc)
    AU = np.bincount(lab, np.abs(sa), nc)
    r = np.abs(sa) / np.maximum(far, 1e-30) / np.maximum(AU / np.maximum(A3, 1e-30), 1e-30)[lab]
    lr = np.log2(np.maximum(r, 1e-6))
    pos = np.bincount(lab, far * (sa > 0), nc)
    neg = np.bincount(lab, far * (sa < 0), nc)
    fold = np.minimum(pos, neg) / np.maximum(A3, 1e-30)
    o = np.lexsort((lr, lab))
    lo, w = lab[o], far[o]
    cs = np.cumsum(w)
    st = np.searchsorted(lo, np.arange(nc))
    en = np.searchsorted(lo, np.arange(nc), side="right")
    base = np.where(st > 0, cs[np.maximum(st - 1, 0)], 0.0)

    def q(k):
        tgt = base + k * (cs[np.maximum(en - 1, 0)] - base)
        idx = np.clip(np.searchsorted(cs, tgt), st, np.maximum(en - 1, st))
        return lr[o][idx]
    return q(0.9) - q(0.1), fold


def unwrap_charts(ob, topo, lab, rounds=4):
    """minimum-stretch unwrap of every chart (no folds); a chart that still stretches more than
    --spread or folds is halved and the lot unwrapped again"""
    me = ob.data
    split = 0
    for rnd in range(rounds + 1):
        me.edges.foreach_set("use_seam", topo.seams(lab, len(me.edges)))
        select(ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.unwrap(method="MINIMUM_STRETCH", margin=0.001, no_flip=True, iterations=20)
        bpy.ops.object.mode_set(mode="OBJECT")
        U = np.empty(len(me.loops) * 2, np.float64)
        me.uv_layers["atlas"].data.foreach_get("uv", U)
        spread, fold = chart_quality(topo, lab, U)
        bad = np.nonzero((spread > A.spread) | (fold > 0.002))[0]
        if len(bad) == 0 or rnd == rounds:
            break
        order = np.argsort(lab, kind="stable")
        bnd = np.searchsorted(lab[order], np.arange(lab.max() + 2))
        new = lab.copy()
        nxt = lab.max() + 1
        for c in bad:
            fs = order[bnd[c]:bnd[c + 1]].tolist()
            if len(fs) < 8:
                continue
            _, p1 = halve(topo, fs)
            if p1:
                new[np.array(p1)] = nxt
                nxt += 1
                split += 1
        lab, _ = make_discs(topo, topo.components(new))
    A3 = np.bincount(lab, topo.area)
    out = {"charts": int(lab.max() + 1), "charts_split_for_stretch": split,
           "charts_still_stretched": int(len(bad)), "charts_still_stretched_area": round(float(A3[bad].sum() / A3.sum()), 4)}
    log(f"  unwrapped: {out['charts']} charts ({split} split for stretch; {len(bad)} still over, "
        f"{100 * out['charts_still_stretched_area']:.1f} percent of the surface)")
    return lab, out


def boost_top(topo, lab, U, top, k):
    """the charts in the top share of the height (the head, the raised object: where the camera's
    focus goes) scaled up k times in UV before packing, so they get k^2 the texels. returns the share
    of the surface boosted"""
    nc = lab.max() + 1
    a = np.bincount(lab, topo.area, nc)
    zc = np.bincount(lab, topo.area * topo.zc, nc) / np.maximum(a, 1e-30)
    z0, z1 = float(topo.co[:, 2].min()), float(topo.co[:, 2].max())
    up = zc >= z1 - top * (z1 - z0)
    for c in np.nonzero(up)[0]:
        f = lab == c
        cen = U[f].reshape(-1, 2).mean(0)
        U[f] = cen + (U[f] - cen) * k
    share = float(a[up].sum() / a.sum())
    log(f"  boosted the top {top:.2f} of the height: {100 * share:.1f} percent of the surface at {k}x")
    return share


# ---------------------------------------------------------------- 4b. the skyline packer

def _hull(pts):
    pts = np.unique(np.round(pts, 9), axis=0)
    if len(pts) < 3:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(tuple(p))
    for p in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(tuple(p))
    return np.array(lower[:-1] + upper[:-1])


def _min_rect(pts):
    """the turn (as a 2x2 matrix) that sets a chart's smallest bounding rectangle square to the axes"""
    h = _hull(pts)
    best, R = None, np.eye(2)
    if len(h) >= 3:
        e = np.roll(h, -1, 0) - h
        for a in np.arctan2(e[:, 1], e[:, 0]):
            c, s = math.cos(-a), math.sin(-a)
            M = np.array([[c, s], [-s, c]])
            r = h @ M
            ar = np.ptp(r[:, 0]) * np.ptp(r[:, 1])
            if best is None or ar < best:
                best, R = ar, M
    return R


def _raster(tri, w, h, conservative=True):
    """conservative: every cell a triangle touches (tri: n x 3 x 2 in cell units); otherwise the cells
    whose centre is inside"""
    m = np.zeros((h, w), bool)
    if conservative:
        v = np.clip(np.floor(tri.reshape(-1, 2)).astype(int), 0, [w - 1, h - 1])
        m[v[:, 1], v[:, 0]] = True
    mn = np.floor(tri.min(1)).astype(int)
    mx = np.floor(tri.max(1)).astype(int)
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    sgn = np.sign((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))
    E = []
    for p, q in ((a, b), (b, c), (c, a)):
        nx, ny = -(q[:, 1] - p[:, 1]) * sgn, (q[:, 0] - p[:, 0]) * sgn          # inward normals
        E.append((nx, ny, nx * p[:, 0] + ny * p[:, 1], 0.5 * (np.abs(nx) + np.abs(ny)) if conservative else 0 * nx))
    for i in range(len(tri)):
        x0, y0 = max(mn[i, 0], 0), max(mn[i, 1], 0)
        x1, y1 = min(mx[i, 0], w - 1), min(mx[i, 1], h - 1)
        if x1 < x0 or y1 < y0 or (sgn[i] == 0 and not conservative):
            continue
        if conservative and (sgn[i] == 0 or (x1 - x0 < 2 and y1 - y0 < 2)):
            m[y0:y1 + 1, x0:x1 + 1] = True
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        ins = np.ones(xs.shape, bool)
        for nx, ny, cc, sl in E:
            ins &= nx[i] * xs + ny[i] * ys - cc[i] >= -sl[i] - 1e-9
        m[y0:y1 + 1, x0:x1 + 1] |= ins
    return m


def _dilate(m, r):
    if r <= 0:
        return m
    h, w = m.shape
    o = np.zeros((h + 2 * r, w + 2 * r), bool)
    o[r:r + h, r:r + w] = m
    t = o.copy()
    for k in range(1, r + 1):
        t[:, k:] |= o[:, :-k]
        t[:, :-k] |= o[:, k:]
    out = t.copy()
    for k in range(1, r + 1):
        out[k:, :] |= t[:-k, :]
        out[:-k, :] |= t[k:, :]
    return out


def _pack_pass(charts, G, pad, scale):
    """one skyline pass at a scale (cells per UV unit). each chart's mask (with its margin) turned four
    ways; placed at the column where it rests lowest for the least waste under it. None if it overflows"""
    masks = []
    for ch in charts:
        tri = ch["r"] * scale + pad
        w = int(math.ceil(ch["ext"][0] * scale)) + 2 * pad + 1
        h = int(math.ceil(ch["ext"][1] * scale)) + 2 * pad + 1
        m = _raster(tri, w, h)
        if pad:
            m = _dilate(m, pad)[pad:pad + h, pad:pad + w]
        masks.append(m)
    order = sorted(range(len(charts)), key=lambda i: -charts[i]["area"])
    H = np.zeros(G, np.int64)
    place = [None] * len(charts)
    for i in order:
        best = None
        for k in range(4):
            m = np.rot90(masks[i], k)
            h, w = m.shape
            if w > G or h > G:
                continue
            col = m.any(0)
            rows = np.arange(h)[:, None]
            b = np.where(col, np.where(m, rows, h).min(0), 0)
            t = np.where(col, np.where(m, rows + 1, 0).max(0), 0)
            win = np.lib.stride_tricks.sliding_window_view(H, w)
            y = np.maximum(np.max(np.where(col, win - b, -(1 << 40)), axis=1), 0)
            top = y + int(t.max())
            waste = ((y[:, None] + b - win) * col).sum(1)
            score = np.where(top <= G, top * w + waste, np.iinfo(np.int64).max)
            j = int(np.argmin(score))
            if score[j] < np.iinfo(np.int64).max and (best is None or score[j] < best[0]):
                best = (score[j], k, j, int(y[j]), t, col, w, h)
        if best is None:
            return None
        _, k, x0, y0, t, col, w, h = best
        H[x0:x0 + w] = np.where(col, y0 + t, H[x0:x0 + w])
        place[i] = (k, x0, y0, masks[i].shape)
    return place


def pack_atlas(topo, lab, U, G, margin_px):
    """every chart turned square to its smallest rectangle, then packed by the skyline at G cells (the
    colour map's texels) with ceil(margin / 2) cells round each, as large as still fits"""
    t = time.time()
    pad = max(0, int(math.ceil(margin_px / 2.0)))
    nc = lab.max() + 1
    order = np.argsort(lab, kind="stable")
    bnd = np.searchsorted(lab[order], np.arange(nc + 1))
    charts, tot = [], 0.0
    for c in range(nc):
        fs = order[bnd[c]:bnd[c + 1]]
        tri = U[fs]
        pts = tri.reshape(-1, 2)
        R = _min_rect(pts)
        r = pts @ R
        lo = r.min(0)
        sa = 0.5 * ((tri[:, 1, 0] - tri[:, 0, 0]) * (tri[:, 2, 1] - tri[:, 0, 1]) - (tri[:, 2, 0] - tri[:, 0, 0]) * (tri[:, 1, 1] - tri[:, 0, 1]))
        area = float(np.abs(sa).sum())
        tot += area
        charts.append({"faces": fs, "R": R, "lo": lo, "r": (r - lo).reshape(-1, 3, 2), "ext": r.max(0) - lo, "area": area})
    scale = math.sqrt(0.72 * G * G / tot)
    ok, fail, passes = None, None, 0
    for _ in range(14):
        passes += 1
        res = _pack_pass(charts, G, pad, scale)
        if res is not None:
            ok = (scale, res)
            break
        fail = scale
        scale *= 0.96
    if ok is None:
        raise SystemExit("the atlas packer could not fit the charts")
    if fail is not None:
        lo_, hi_ = ok[0], fail
        for _ in range(3):
            passes += 1
            mid = 0.5 * (lo_ + hi_)
            res = _pack_pass(charts, G, pad, mid)
            if res is not None:
                ok, lo_ = (mid, res), mid
            else:
                hi_ = mid
    scale, place = ok
    out = U.copy()
    for ch, (k, x0, y0, (hh, ww)) in zip(charts, place):
        r = ch["r"].reshape(-1, 2) * scale + pad
        x, y = r[:, 0], r[:, 1]
        for _ in range(k):                     # np.rot90 once: (x, y) -> (y, w - x) in a w-wide mask
            x, y = y, ww - x
            ww, hh = hh, ww
        out[ch["faces"]] = np.stack([(x + x0) / G, (y + y0) / G], 1).reshape(-1, 3, 2)
    info = {"atlas_px": G, "atlas_margin_px": margin_px, "pack_scale": round(scale, 2), "pack_passes": passes,
            "pack_seconds": round(time.time() - t, 1)}
    log(f"  packed {nc} charts at {G} px in {passes} passes, {time.time() - t:.1f}s")
    return out, info


def overlap_share(ob, lab, size=1024):
    """the share of the covered texels (centre-sampled at `size`) that two charts both cover: 0 for a
    sound atlas"""
    me = ob.data
    U = np.empty(len(me.loops) * 2, np.float64)
    me.uv_layers["atlas"].data.foreach_get("uv", U)
    T = U.reshape(-1, 3, 2) * size
    cnt = np.zeros((size, size), np.int16)
    order = np.argsort(lab, kind="stable")
    bnd = np.searchsorted(lab[order], np.arange(lab.max() + 2))
    for c in range(lab.max() + 1):
        t = T[order[bnd[c]:bnd[c + 1]]]
        x0, y0 = np.floor(t.reshape(-1, 2).min(0)).astype(int)
        x1, y1 = np.ceil(t.reshape(-1, 2).max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size), min(y1, size)
        if x1 <= x0 or y1 <= y0:
            continue
        m = _raster(t - [x0, y0], x1 - x0, y1 - y0, conservative=False)
        cnt[y0:y1, x0:x1] += m
    cov = (cnt > 0).sum()
    return round(float((cnt > 1).sum() / max(1, cov)), 5)


def uv_stats(ob):
    """the atlas: how much of it the charts cover, how even the texel density is (log2 of each
    triangle's texels per area over the mean, area-weighted 5th / 50th / 95th percentile), the share
    of the surface whose UVs are mirrored (flipped), and the vertices once split at the UV seams"""
    me = ob.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    co = coords(ob)
    lt = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("loops", lt)
    vt = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", vt)
    t, p = uv[lt.reshape(-1, 3)].astype(np.float64), co[vt.reshape(-1, 3)].astype(np.float64)
    sa = 0.5 * ((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1]) - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
    a3 = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    w = a3 / a3.sum()
    r = np.abs(sa) / np.maximum(a3, 1e-20) / (np.abs(sa).sum() / a3.sum())
    lr = np.log2(np.maximum(r, 1e-9))
    o = np.argsort(lr)
    cw = np.cumsum(w[o])
    q = lambda k: round(float(lr[o][min(len(o) - 1, np.searchsorted(cw, k))]), 2)
    major = 1.0 if (sa > 0).sum() >= (sa < 0).sum() else -1.0
    lv = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    key = np.round(uv.astype(np.float64) * 65536).astype(np.int64)
    gl_verts = len(np.unique(np.stack([lv, key[:, 0], key[:, 1]], 1), axis=0))
    inside = bool((uv >= 0).all() and (uv <= 1).all())
    return {"uv_coverage": round(float(np.abs(sa).sum()), 3), "uv_density_log2_p5_p50_p95": [q(0.05), q(0.5), q(0.95)],
            "uv_flipped_share": round(float(w[np.sign(sa) != major].sum()), 5), "gl_vertices": gl_verts, "uv_inside_unit_square": inside}


# ---------------------------------------------------------------- 5. bake

def float_image(name, size, data=True):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, size, size, alpha=False, float_buffer=True)
    im.colorspace_settings.name = "Non-Color" if data else "Linear Rec.709"
    return im


def bake_material(ob, img):
    m = bpy.data.materials.get("BAKE_TARGET") or bpy.data.materials.new("BAKE_TARGET")
    m.use_nodes = True
    nt = m.node_tree
    n = nt.nodes.get("TARGET") or nt.nodes.new("ShaderNodeTexImage")
    n.name = "TARGET"
    n.image = img
    nt.nodes.active = n
    ob.data.materials.clear()
    ob.data.materials.append(m)


class Router:
    """re-points the source's material outputs: the BSDF (normal bake), or one input of the BSDF
    (whatever feeds it) through an emission (colour, roughness + metal) bake"""

    def __init__(self, mats):
        self.items = []
        for m in mats:
            nt = m.node_tree
            bsdf = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
            out = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial" and n.is_active_output)
            em = nt.nodes.new("ShaderNodeEmission")
            comb = nt.nodes.new("ShaderNodeCombineColor")
            self.items.append((nt, bsdf, out, em, comb))

    @staticmethod
    def _feed(nt, bsdf, name, to):
        i = bsdf.inputs[name]
        if i.is_linked:
            nt.links.new(i.links[0].from_socket, to)
        else:
            v = i.default_value
            to.default_value = v if not hasattr(to.default_value, "__len__") else (tuple(v)[:len(to.default_value)] if hasattr(v, "__len__") else (v,) * len(to.default_value))

    def route(self, channel):
        for nt, bsdf, out, em, comb in self.items:
            for l in list(out.inputs["Surface"].links):
                nt.links.remove(l)
            for s in (em.inputs["Color"], comb.inputs[0], comb.inputs[1], comb.inputs[2]):
                for l in list(s.links):
                    nt.links.remove(l)
            if channel == "bsdf":
                nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
                continue
            em.inputs["Strength"].default_value = 1.0
            if channel == "color":
                self._feed(nt, bsdf, "Base Color", em.inputs["Color"])
            else:                                   # roughness in G, metal in B
                comb.inputs[0].default_value = 0.0
                self._feed(nt, bsdf, "Roughness", comb.inputs[1])
                self._feed(nt, bsdf, "Metallic", comb.inputs[2])
                nt.links.new(comb.outputs[0], em.inputs["Color"])
            nt.links.new(em.outputs[0], out.inputs["Surface"])


def measure_cage(src, low, h_src):
    """how far the web mesh strays from the source: each web vertex to the nearest source surface,
    signed (+ outside). the cage covers the outside stray, the reach the inside one"""
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = BVHTree.FromObject(src, dg)
    co = coords(low)
    d = np.empty(len(co), np.float64)
    for i, p in enumerate(co):
        loc, nrm, _, dist = bvh.find_nearest(Vector(p))
        d[i] = dist if (Vector(p) - loc).dot(nrm) >= 0 else -dist
    out_ = float(np.percentile(np.maximum(d, 0), 99.9))
    in_ = float(np.percentile(np.maximum(-d, 0), 99.9))
    cage = max(1.5 * out_, 0.0003 * h_src)
    reach = cage + max(2.0 * in_, 0.0006 * h_src)
    stray = {"stray_out_p99.9_pct_height": round(100 * out_ / h_src, 4), "stray_in_p99.9_pct_height": round(100 * in_ / h_src, 4),
             "stray_max_pct_height": round(100 * float(np.abs(d).max()) / h_src, 4),
             "cage_pct_height": round(100 * cage / h_src, 4), "reach_pct_height": round(100 * reach / h_src, 4)}
    log("  cage", json.dumps(stray))
    return cage, reach, stray


def bake(low, src, img, kind, samples, cage, reach):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    bake_material(low, img)
    select(low, [src])
    t = time.time()
    bpy.ops.object.bake(type=kind, uv_layer="atlas", margin=16, margin_type="EXTEND", normal_space="TANGENT", use_clear=True,
                        use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=reach)
    log(f"  baked {img.name} {kind} {img.size[0]} px in {time.time() - t:.1f}s")
    return np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)


# ---------------------------------------------------------------- 6. finish the maps

def to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def down(a, k):
    """box filter by an integer factor k"""
    k = int(k)
    if k <= 1:
        return a
    h, w = a.shape[:2]
    return a.reshape(h // k, k, w // k, k, *a.shape[2:]).mean(axis=(1, 3))


def hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = np.maximum(mx - mn, 1e-4)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    return hue, sat, mx


def finish(srgb, rough, metal, painted_extra=None):
    """Meshy's channels -> the shipped ones. metal: its grey noise on paint ramped away, gold kept
    (a yellow, bright, saturated colour with any metal is gold leaf); a saturated colour outside the
    warm metal hues (a red, a blue, a green) is paint or lacquer over metal, so not metal. lacquer: a
    glossy non-metal. paint and cloth: never glossier than the matte floor. returns coat, rough,
    metal (0..1) and the shares (the report): gold, painted (metal Meshy marked on a saturated
    colour), and the metal that is not gold (steel, silver, copper, dark gold) with its mean colour"""
    hue, sat, mx = hsv(srgb)
    m_lo, m_hi = (float(v) for v in A.metal.split(","))
    l_lo, l_hi = (float(v) for v in A.lacquer.split(","))
    gold = smoothstep(24, 32, hue) * (1 - smoothstep(56, 64, hue)) * smoothstep(0.3, 0.42, sat) * smoothstep(0.4, 0.52, mx)
    metal1 = np.maximum(smoothstep(m_lo, m_hi, metal), gold * smoothstep(0.18, 0.42, metal))
    warm = smoothstep(10, 18, hue) * (1 - smoothstep(60, 70, hue))          # the hues of gold, brass, copper
    painted = smoothstep(0.5, 0.65, sat) * (1 - warm)
    if painted_extra is not None:                     # (--recolour: the recoloured blue is lacquer, never metal)
        painted = np.maximum(painted, painted_extra)
    metal2 = metal1 * (1 - painted)
    lac = (1 - metal2) * smoothstep(l_hi, l_lo, rough)
    paint = (1 - metal2) * (1 - lac)
    rough2 = rough * (1 - paint) + np.maximum(rough, A.matte) * paint
    rough2 = rough2 * (1 - metal2) + np.clip(rough, 0.22, 0.55) * metal2      # gold leaf: burnished, never a mirror
    n = metal2.size
    stats = {"metal_share": round(float((metal2 > 0.5).sum() / n), 4), "lacquer_share": round(float((lac > 0.5).sum() / n), 4),
             "gold_metal_share": round(float(((metal2 > 0.5) & (gold > 0.5)).sum() / n), 4),
             "metal_painted_share": round(float(((metal1 > 0.5) & (painted > 0.5)).sum() / n), 4)}
    other = (metal2 > 0.5) & (gold < 0.5)
    steel = other & (sat < 0.25)
    stats["non_gold_metal_share"] = round(float(other.sum() / n), 4)
    stats["steel_silver_metal_share"] = round(float(steel.sum() / n), 4)
    if other.any():
        stats["non_gold_metal_mean_srgb"] = [round(float(v), 3) for v in srgb[other].mean(0)]
    return np.clip(lac, 0, 1), np.clip(rough2, 0.04, 1), np.clip(metal2, 0, 1), stats


# ---------------------------------------------------------------- 6b. the colour grade

GRADE = {}


def ref_path():
    if A.ref in ("", "none", "off"):
        return None
    if A.ref != "auto":
        return A.ref if os.path.exists(A.ref) else None
    stem = os.path.basename(A.input).rsplit(".", 1)[0]
    for suffix in ("-meshy", "_meshy"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    p = os.path.join(os.environ.get("I3D_REFS") or os.path.join(C.REPO, "refs"), f"{stem}-front.png")   # (skill copy) the reference pictures folder
    return p if os.path.exists(p) else None


def load_srgb(path, maxdim=900):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[..., :3]
    # an 8-bit picture's pixels come back as stored (sRGB-encoded); a float one's are linear
    a = to_srgb(a) if im.is_float else a
    bpy.data.images.remove(im)
    k = max(1, int(math.ceil(max(w, h) / maxdim)))
    return down(a[: h - h % k, : w - w % k], k)


BANDS = np.arange(0, 360, 30)


def band_stats(rgb, mask):
    """per hue band (30 degrees, triangular weights): the median brightness (HSV value) of its
    chromatic pixels and their share; and the median of every masked pixel"""
    hue, sat, val = hsv(rgb)
    out = {"all": float(np.median(val[mask])) if mask.any() else None}
    chroma = mask & (sat > 0.35) & (val > 0.08)
    n = max(1, int(mask.sum()))
    for c in BANDS:
        d = np.abs(((hue - c + 180) % 360) - 180)
        w = np.clip(1 - d / 30.0, 0, 1) * chroma
        sel = w > 0.5
        out[int(c)] = (float(np.median(val[sel])), float(sel.sum()) / n) if sel.sum() > 50 else None
    return out


def grade_gains(albedo, cover):
    """the gain per hue band: the reference's band brightness over the colour map's, each against its
    own whole figure, clamped. bands either side holds too little of: 1"""
    path = ref_path()
    if not path or A.grade_strength <= 0:
        return None
    ref = load_srgb(path)
    bg = np.median(np.concatenate([ref[:4].reshape(-1, 3), ref[-4:].reshape(-1, 3), ref[:, :4].reshape(-1, 3), ref[:, -4:].reshape(-1, 3)]), 0)
    fig = np.abs(ref - bg).sum(-1) > 0.12
    rs, al = band_stats(ref, fig), band_stats(albedo, cover)
    lo, hi = (float(v) for v in A.grade_clamp.split(","))
    norm = (rs["all"] / al["all"]) if rs["all"] and al["all"] else 1.0
    gains, table = {}, {}
    for c in BANDS:
        c = int(c)
        if rs[c] and al[c] and rs[c][1] > 0.01 and al[c][1] > 0.01:
            g = (rs[c][0] / al[c][0]) / norm
            g = 1 + (g - 1) * A.grade_strength
            gains[c] = float(np.clip(g, lo, hi))
            table[c] = {"ref_median_v": round(rs[c][0], 3), "ref_share": round(rs[c][1], 3), "map_median_v": round(al[c][0], 3),
                        "map_share": round(al[c][1], 3), "gain": round(gains[c], 3)}
    info = {"reference": os.path.relpath(path, C.REPO), "figure_median_v_ref": round(rs["all"], 3), "figure_median_v_map": round(al["all"], 3),
            "bands": table}
    log("  colour grade", json.dumps({k: v["gain"] for k, v in table.items()}))
    return {"gains": gains, "info": info}


def apply_grade(srgb, gains):
    if not gains:
        return srgb
    hue, sat, _ = hsv(srgb)
    g = np.zeros(hue.shape, np.float32)
    wsum = np.zeros(hue.shape, np.float32)
    for c in BANDS:
        d = np.abs(((hue - c + 180) % 360) - 180)
        w = np.clip(1 - d / 30.0, 0, 1)
        g += w * gains.get(int(c), 1.0)
        wsum += w
    g = g / np.maximum(wsum, 1e-6)
    g = 1 + (g - 1) * smoothstep(0.2, 0.45, sat)        # greys, blacks and whites are left alone
    return np.clip(srgb * g[..., None], 0, 1)


# ---------------------------------------------------------------- 6b'. the recolour (one figure's own colour)

# --recolour site-blue (the strategist, the only blue figure): his blue armour, cloth and banner moved
# onto the site's blue family by hue and saturation only: every blue texel at one hue (that of #2745ff,
# 231.7 degrees, so never purple), its own light and dark from the source kept (the blue's brightness
# scaled so its median is --recolour-v, the top softly kept under --recolour-max: nothing at full
# brightness), its saturation --recolour-s (a little more in the darks: navy). The first version mapped
# the median onto #2745ff itself (brightness 1.0): the blue came out 3.6 times the source's, a quarter of
# it clipped at full brightness, and read periwinkle and loud on the page beside the other five.
# Greys, whites (the lance emblem on the banner) and golds are outside the hue band or under the
# saturation floor and keep their colour
SITE_BLUE = {"hue": 231.67, "band": (186, 198, 262, 274), "sat": (0.16, 0.3)}
RECOLOUR = {}
GROUND = {}


def _hue_rgb(hue, s, v):
    """sRGB of a hue in the blue sextant (180 to 240 degrees: blue the largest channel, red the
    smallest) at a saturation and value (arrays or numbers; the hue one number)"""
    s = np.asarray(s, np.float32)
    v = np.asarray(v, np.float32)
    b = v
    r = v * (1 - s)
    g = r + (b - r) * (4 - hue / 60.0)
    return np.stack([r, g, b], -1)


def blue_weight(srgb):
    hue, sat, val = hsv(srgb)
    a0, a1, b0, b1 = SITE_BLUE["band"]
    return (smoothstep(a0, a1, hue) * (1 - smoothstep(b0, b1, hue)) * smoothstep(*SITE_BLUE["sat"], sat)
            * smoothstep(0.03, 0.08, val)), hue, sat, val


def recolour_levels(srgb, cover):
    """the blue's brightness (5th, 50th, 97th percentile of HSV value) and its median saturation, measured
    once on the desktop cut's map and used for both cuts"""
    w, hue, sat, val = blue_weight(srgb)
    sel = cover & (w > 0.5)
    if sel.sum() < 200:
        warn("--recolour site-blue: almost no blue found in the colour map; nothing recoloured")
        return None
    v = val[sel]
    lv = [float(np.percentile(v, k)) for k in (5, 50, 97)]
    s_med = float(np.median(sat[sel]))
    H = SITE_BLUE["hue"] + A.recolour_shift
    gain = A.recolour_v / max(lv[1], 1e-3)
    mid = [int(round(255 * c)) for c in _hue_rgb(H, A.recolour_s, A.recolour_v)]
    info = {"kind": "site-blue", "hue_deg": SITE_BLUE["hue"], "shift_deg": A.recolour_shift, "map_hue_deg": round(H, 2),
            "map_median_v": A.recolour_v, "map_sat": A.recolour_s, "map_max_v": A.recolour_max, "value_gain": round(gain, 3),
            "map_mid_srgb_hex": "#%02x%02x%02x" % tuple(mid), "site_srgb_hex": "#2745ff",
            "blue_share_of_figure": round(float(sel.sum() / max(1, cover.sum())), 4),
            "source_blue_hue_p5_p50_p95": [round(float(np.percentile(hue[sel], k)), 1) for k in (5, 50, 95)],
            "source_blue_sat_median": round(s_med, 3),
            "source_blue_value_p5_p50_p97": [round(x, 3) for x in lv]}
    return {"levels": lv + [s_med], "info": info}


def recolour_value(val, mid):
    """the source's brightness scaled (median -> --recolour-v), the top kept softly under --recolour-max"""
    v = val * (A.recolour_v / max(mid, 1e-3))
    top = A.recolour_max
    knee = top - 0.12
    return np.where(v <= knee, v, knee + (top - knee) * (1 - np.exp(-(v - knee) / (top - knee))))


def apply_recolour(src_srgb, graded, levels):
    """the blue (weighted by hue band, saturation and a floor on brightness) set to one hue at the
    saturation asked, its brightness the source's own scaled; blended over the graded map by that weight"""
    lo, mid, hi, s_med = levels
    w, _, sat, val = blue_weight(src_srgb)
    H = SITE_BLUE["hue"] + A.recolour_shift            # (--recolour-shift: the map's hue set off so the page shows #2745ff's)
    v2 = recolour_value(val, mid)
    # the saturation: the one asked, following the source's own a little, and deeper in the darks (navy)
    s2 = A.recolour_s + 0.35 * (sat - s_med) + 0.06 * (1 - np.clip(v2 / max(A.recolour_v, 1e-3), 0, 1))
    s2 = np.clip(s2, A.recolour_s - 0.12, min(0.95, A.recolour_s + 0.08))
    rec = _hue_rgb(H, s2, v2)
    out = graded * (1 - w[..., None]) + rec * w[..., None]
    return np.clip(out, 0, 1), w


def purple_share(srgb, region):
    """of a region, the share that reads purple (hue 248 to 300, saturated, not black)"""
    hue, sat, val = hsv(srgb)
    p = region & (hue > 248) & (hue < 300) & (sat > 0.3) & (val > 0.08)
    return round(float(p.sum() / max(1, region.sum())), 4)


# ---------------------------------------------------------------- 6b''. the finishes that go by place

def bake_position(low, size, h):
    """the web mesh's own surface position at each texel (an emission bake of the mesh itself, not from
    the source), in source units: x, y about the axis, z up from the base's bottom"""
    img = float_image(f"{low.name}-pos-raw", size)
    m = bpy.data.materials.get("POS_BAKE") or bpy.data.materials.new("POS_BAKE")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    ma = nt.nodes.new("ShaderNodeVectorMath")
    ma.operation = "MULTIPLY_ADD"                     # (x / 2h + 0.5, y / 2h + 0.5, z / h): all inside 0..1
    ma.inputs[1].default_value = (0.5 / h, 0.5 / h, 1.0 / h)
    ma.inputs[2].default_value = (0.5, 0.5, 0.0)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(geo.outputs["Position"], ma.inputs[0])
    nt.links.new(ma.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.nodes.active = t
    low.data.materials.clear()
    low.data.materials.append(m)
    select(low)
    sc = bpy.context.scene
    keep = sc.cycles.samples
    sc.cycles.samples = 1
    t0 = time.time()
    bpy.ops.object.bake(type="EMIT", uv_layer="atlas", margin=16, margin_type="EXTEND", use_clear=True, use_selected_to_active=False)
    sc.cycles.samples = keep
    px = np.array(img.pixels[:], dtype=np.float32).reshape(size, size, 4)
    bpy.data.images.remove(img)
    log(f"  baked the surface position {size} px in {time.time() - t0:.1f}s")
    return np.stack([(px[..., 0] - 0.5) * 2 * h, (px[..., 1] - 0.5) * 2 * h, px[..., 2] * h], -1)


def ground_profile(low, scale):
    """the base's ground, from the web mesh: its top (mm; the end of the band of vertices the earth and
    pebbles make between 55 and 93 percent of the base's radius: the first half millimetre past its
    peak holding under 15 percent of the peak), and the outer radius at each height (the plinth's side)"""
    co = coords(low).astype(np.float64) * scale * 1000.0
    r = np.hypot(co[:, 0], co[:, 1])
    z = co[:, 2]
    H = float(z.max())
    R = float(r[z < 0.03 * H].max())
    inner = (r > 0.55 * R) & (r < 0.93 * R) & (z < 0.35 * H)
    edges = np.arange(0.0, 0.35 * H + 0.5, 0.5)
    hist = np.histogram(z[inner], bins=edges)[0]
    pk = int(hist.argmax())
    top = float(edges[-1])
    for i in range(pk, len(hist)):
        if hist[i] < 0.15 * hist[pk]:
            top = float(edges[i])
            break
    if A.ground_top > 0:
        top = A.ground_top
    zb = np.arange(0.0, top + 3.0, 0.25)
    rz = np.zeros(len(zb))
    for i, z0 in enumerate(zb):
        sel = (z >= z0 - 0.375) & (z < z0 + 0.375)
        rz[i] = r[sel].max() if sel.any() else 0.0
    return {"top_mm": round(top, 2), "base_r_mm": round(R, 2), "z_mm": zb, "r_mm": rz, "peak_mm": float(edges[pk])}


def place_weights(pos, scale, prof, h_src):
    """per texel: ground (the base's earth and pebbles, the plinth's side left out) and top (--top-matte:
    the head and what it wears), 0..1"""
    mm = pos * scale * 1000.0
    r = np.hypot(mm[..., 0], mm[..., 1])
    z = mm[..., 2]
    out = {}
    if A.ground_matte and prof:
        rz = np.interp(z, prof["z_mm"], prof["r_mm"])
        t = prof["top_mm"]
        out["ground"] = (1 - smoothstep(t - 0.25, t + 0.75, z)) * (1 - smoothstep(rz - 1.0, rz - 0.4, r))
    if A.top_matte > 0:
        Hm = h_src * scale * 1000.0
        f = z / Hm
        out["top"] = smoothstep(A.top_matte - 0.006, A.top_matte + 0.006, f) * (1 - smoothstep(0.10 * Hm, 0.14 * Hm, r))
    return out


def coverage_mask(ob, size):
    """the texels the charts cover, at `size` (conservative)"""
    me = ob.data
    U = np.empty(len(me.loops) * 2, np.float64)
    me.uv_layers["atlas"].data.foreach_get("uv", U)
    T = U.reshape(-1, 3, 2) * size
    return _raster(T, size, size)


# ---------------------------------------------------------------- 6c. the focus candidates

def focus_points(ob, albedo, scale):
    """where the scene's focus goes, from the colour map: skin in the top of the figure. The face: the
    skin near the axis in the top 30 percent (its front-most third); the raised hand: the highest
    skin away from the head; the raised object: what is above that hand within reach. In three's axes
    (x, y up, z toward the viewer), metres. Candidates for PIECES in table.js; check them"""
    me = ob.data
    nf = len(me.polygons)
    U = np.empty(len(me.loops) * 2, np.float64)
    me.uv_layers["atlas"].data.foreach_get("uv", U)
    uvc = U.reshape(-1, 3, 2).mean(1)
    S = albedo.shape[0]
    px = albedo[np.clip((uvc[:, 1] * S).astype(int), 0, S - 1), np.clip((uvc[:, 0] * S).astype(int), 0, S - 1)]
    hue, sat, val = hsv(px)
    skin = (hue > 8) & (hue < 40) & (sat > 0.18) & (sat < 0.62) & (val > 0.3) & (val < 0.9)
    co = coords(ob).astype(np.float64)
    tv = np.empty(nf * 3, np.int32)
    me.polygons.foreach_get("vertices", tv)
    p = co[tv.reshape(-1, 3)]
    cen = p.mean(1)
    ar = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    H = float(co[:, 2].max())
    rad = np.hypot(cen[:, 0], cen[:, 1])
    three = lambda v: [round(float(v[0]) * scale, 4), round(float(v[2]) * scale, 4), round(float(-v[1]) * scale, 4)]
    out = {}
    head = skin & (cen[:, 2] > 0.7 * H) & (rad < 0.14 * H)
    if head.sum() > 10:
        fy = cen[head, 1]
        front = head.copy()
        front[head] = fy <= np.percentile(fy, 33)          # the front-most third (blender -y is the front)
        out["face"] = three(np.average(cen[front], axis=0, weights=ar[front]))
    hands = skin & (rad >= 0.14 * H) & (cen[:, 2] > 0.55 * H)
    if hands.sum() > 10:
        z = cen[hands, 2]
        top = hands.copy()
        top[hands] = z >= np.percentile(z, 70)
        hand = np.average(cen[top], axis=0, weights=ar[top])
        out["raised_hand"] = three(hand)
        reach = 0.16 * H
        above = (cen[:, 2] > hand[2] + 0.01 * H) & (np.hypot(cen[:, 0] - hand[0], cen[:, 1] - hand[1]) < reach) & ~skin
        if out.get("face"):
            fc = np.array([out["face"][0], -out["face"][2], out["face"][1]]) / scale
            above &= np.linalg.norm(cen - fc, axis=1) > 0.12 * H      # not the helmet
        if above.sum() > 10:
            out["raised_object"] = three(np.average(cen[above], axis=0, weights=ar[above]))
    out["note"] = "candidates from the colour map (skin in the top of the figure): check them against a render before using them in PIECES"
    return out


# ---------------------------------------------------------------- the WebP files

CWEBP = shutil.which("cwebp") or next((p for p in ("/opt/homebrew/bin/cwebp", "/usr/local/bin/cwebp") if os.path.exists(p)), None)


def save_image(name, rgb, path, quality=None):
    """rgb rows bottom first (blender's order), 0..1 as stored; PNG for the record, WebP for the GLB
    (cwebp with sharp RGB->YUV when it is there: the reds and golds keep their edges)"""
    h, w = rgb.shape[:2]
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, w, h, alpha=False)
    im.colorspace_settings.name = "Non-Color"
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., :3] = rgb
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    webp = None
    if quality:
        webp = os.path.splitext(path)[0] + ".webp"
        if CWEBP:
            subprocess.run([CWEBP, "-quiet", "-q", str(int(quality)), "-m", "6", "-sharp_yuv", "-metadata", "none", path, "-o", webp], check=True)
        else:
            im.file_format = "WEBP"
            im.filepath_raw = webp
            im.save(quality=int(quality))
            im.file_format = "PNG"
            im.filepath_raw = path
    return im, webp


# ---------------------------------------------------------------- 7. export

def export_material(ob, imgs, name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(p.outputs[0], out.inputs["Surface"])
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "atlas"

    def tex(img):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = img
        nt.links.new(uv.outputs[0], n.inputs["Vector"])
        return n
    nt.links.new(tex(imgs["albedo"]).outputs["Color"], p.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex(imgs["orm"]).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], p.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], p.inputs["Metallic"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "atlas"
    nt.links.new(tex(imgs["normal"]).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    if A.coat > 0:
        # the coat's weight is the map's R times the factor (the exporter writes clearcoatFactor), and the
        # coat follows the baked normal too (clearcoatNormalTexture: the same map), so the lacquer's
        # highlights break on the plates' edges and the fan's ribs instead of lying broad on the facets
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = A.coat
        nt.links.new(sep.outputs["Red"], mul.inputs[0])
        nt.links.new(mul.outputs[0], p.inputs["Coat Weight"])
        p.inputs["Coat Roughness"].default_value = A.coat_rough
        p.inputs["Coat IOR"].default_value = 1.5
        nt.links.new(nm.outputs["Normal"], p.inputs["Coat Normal"])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return m


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    jlen = struct.unpack("<I", data[12:16])[0]
    js = json.loads(data[20:20 + jlen])
    b0 = 20 + jlen
    blen = struct.unpack("<I", data[b0:b0 + 4])[0]
    return js, data[b0 + 8:b0 + 8 + blen]


def write_glb(path, js, bin_):
    jb = json.dumps(js, separators=(",", ":")).encode()
    jb += b" " * (-len(jb) % 4)
    bin_ = bytes(bin_) + b"\0" * (-len(bin_) % 4)
    total = 12 + 8 + len(jb) + 8 + len(bin_)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(jb), b"JSON") + jb)
        f.write(struct.pack("<I4s", len(bin_), b"BIN\0") + bin_)


def replace_images(path, repl):
    """the exporter encodes every map at one quality; put each map's own WebP in its place"""
    js, bin_ = read_glb(path)
    by_view = {im["bufferView"]: im for im in js.get("images", []) if "bufferView" in im}
    out = bytearray()
    for i, v in enumerate(js["bufferViews"]):
        o = v.get("byteOffset", 0)
        chunk = bin_[o:o + v["byteLength"]]
        im = by_view.get(i)
        if im is not None and im.get("name") in repl:
            with open(repl[im["name"]], "rb") as f:
                chunk = f.read()
            im["mimeType"] = "image/webp"
        out += b"\0" * (-len(out) % 4)
        v["byteOffset"] = len(out)
        v["byteLength"] = len(chunk)
        out += chunk
    js["buffers"][0]["byteLength"] = len(out) + (-len(out) % 4)
    js.setdefault("asset", {}).setdefault("extras", {})["madeBy"] = MARK
    write_glb(path, js, out)


MARK = "scripts/blender/war-table/meshy_optimize.py"


def guard(path):
    """never overwrite a file this script did not make (general.glb, the oak maps)"""
    if os.path.exists(path) and not A.force:
        try:
            js, _ = read_glb(path)
            ok = js.get("asset", {}).get("extras", {}).get("madeBy") == MARK
        except Exception:
            ok = False
        if not ok:
            raise SystemExit(f"{path} exists and was not made by meshy_optimize.py: pick another name (or --force)")


def glb_summary(path):
    js, _ = read_glb(path)
    imgs = []
    for im in js.get("images", []):
        bv = js["bufferViews"][im["bufferView"]]
        imgs.append({"name": im.get("name"), "kb": round(bv["byteLength"] / 1024, 1)})
    mesh_kb = sum(v["byteLength"] for i, v in enumerate(js["bufferViews"]) if i not in {im["bufferView"] for im in js.get("images", [])}) / 1024
    return {"bytes": os.path.getsize(path), "kb": round(os.path.getsize(path) / 1024, 1), "mesh_kb": round(mesh_kb, 1), "images": imgs,
            "extensionsUsed": js.get("extensionsUsed"), "extensionsRequired": js.get("extensionsRequired"),
            "material": js.get("materials", [{}])[0]}


def export(ob, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
        export_texcoords=True, export_normals=True, export_tangents=bool(A.tangents), export_materials="EXPORT",
        export_image_format="WEBP", export_image_quality=90,
        export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
        export_draco_position_quantization=14, export_draco_normal_quantization=10, export_draco_texcoord_quantization=12,
    )


# ---------------------------------------------------------------- a variant, start to end

def variant(src, router, tag, tris, sizes, scale, h_src, margin_px, qi):
    name = NAME if tag == "" else f"{NAME}{tag}"
    tex, nrm_px, orm_px = sizes
    top = max(sizes)
    bake_px = top * 2 if top <= 1536 else top           # the small maps: baked at twice and box-filtered down
    for s in sizes:
        if bake_px % s:
            raise SystemExit(f"{name}: map size {s} does not divide the bake size {bake_px}")
    low, info, lab, topo = web_mesh(src, tris, name, tex, margin_px)
    info.update(uv_stats(low))
    info["uv_overlap_share"] = overlap_share(low, lab)
    cage, reach, stray = measure_cage(src, low, h_src)
    info.update(stray)
    router.route("color")
    alb = bake(low, src, float_image(f"{name}-albedo-raw", bake_px, data=False), "EMIT", A.samples, cage, reach)
    router.route("mr")
    mr = bake(low, src, float_image(f"{name}-mr-raw", bake_px), "EMIT", max(4, A.samples // 2), cage, reach)
    router.route("bsdf")
    nrm = bake(low, src, float_image(f"{name}-normal-raw", bake_px), "NORMAL", A.samples, cage, reach)
    srgb_full = to_srgb(alb[..., :3])
    coat, rough, metal, fin = finish(srgb_full, mr[..., 1], mr[..., 2],
                                     blue_weight(srgb_full)[0] if A.recolour == "site-blue" else None)
    # the finishes that go by place: the base's ground matte (--ground-matte), the top dulled (--top-matte)
    place = {}
    if A.ground_matte or A.top_matte > 0:
        if "ground" not in REPORT and A.ground_matte:
            prof = ground_profile(low, scale)
            REPORT["ground"] = {k: prof[k] for k in ("top_mm", "base_r_mm", "peak_mm")}
            REPORT["ground"]["note"] = "the base's ground (earth, pebbles) matte below top_mm, the plinth's side left as it was"
            GROUND["prof"] = prof
            log("  ground", json.dumps(REPORT["ground"]))
        place = place_weights(bake_position(low, bake_px, h_src), scale, GROUND.get("prof"), h_src)
        floor_ = (1 - metal)
        if "ground" in place:
            wg = place["ground"] * floor_
            coat = coat * (1 - wg)
            rough = rough * (1 - wg) + np.maximum(rough, A.matte) * wg
            info["ground_matte_share"] = round(float((wg > 0.5).mean()), 4)
        if "top" in place:
            wt = place["top"] * floor_
            coat = coat * (1 - wt)
            rough = rough * (1 - wt) + np.maximum(rough, A.top_rough) * wt
            info["top_matte_share"] = round(float((wt > 0.5).mean()), 4)
    srgb = down(srgb_full, bake_px // tex)
    orm = down(np.stack([coat, rough, metal], -1), bake_px // orm_px)
    # the colour grade: measured once on the desktop cut's map, used for both
    if "gains" not in GRADE:
        cov = coverage_mask(low, 512)
        g = grade_gains(down(srgb, tex // 512) if tex % 512 == 0 else srgb[:: max(1, tex // 512), :: max(1, tex // 512)], cov)
        GRADE["gains"] = g["gains"] if g else None
        REPORT["colour_grade"] = g["info"] if g else {"reference": None, "note": "no reference picture: no grade"}
    srgb_graded = apply_grade(srgb, GRADE["gains"])
    if A.white_gain != 1.0:
        # whites and creams toned (the grade barely touches them): saturation under about 0.4 (a cream robe
        # is 0.33), brightness over about 0.8 (skin stays under it, gold is more saturated)
        _, s_w, v_w = hsv(srgb_graded)
        ww = (1 - smoothstep(0.38, 0.5, s_w)) * smoothstep(0.74, 0.86, v_w)
        srgb_graded = np.clip(srgb_graded * (1 - (1 - A.white_gain) * ww)[..., None], 0, 1)
        info["white_toned_share"] = round(float((ww > 0.5).mean()), 4)
    if A.recolour == "site-blue" and tag == "":
        # (the colour before the recolour, for trying the recolour's settings on the page without a bake)
        save_image(f"{name}-albedo-src", srgb, os.path.join(C.BUILD, f"{name}-albedo-src.png"))
        save_image(f"{name}-albedo-graded", srgb_graded, os.path.join(C.BUILD, f"{name}-albedo-graded.png"))
    if A.recolour == "site-blue":
        if "levels" not in RECOLOUR:
            k = max(1, tex // 512)
            r = recolour_levels(down(srgb, k) if tex % 512 == 0 else srgb[::k, ::k], coverage_mask(low, srgb[::k, ::k].shape[0]))
            RECOLOUR["levels"] = r["levels"] if r else None
            REPORT["recolour"] = r["info"] if r else {"kind": "site-blue", "note": "no blue found"}
        if RECOLOUR["levels"]:
            region = blue_weight(srgb)[0] > 0.5
            before = purple_share(srgb_graded, region)
            srgb_graded, wb = apply_recolour(srgb, srgb_graded, RECOLOUR["levels"])
            hue2, sat2, val2 = hsv(srgb_graded)
            info["recolour"] = {"purple_share_before_after": [before, purple_share(srgb_graded, region)],
                                "blue_hue_after_p5_p50_p95": [round(float(np.percentile(hue2[region], k)), 1) for k in (5, 50, 95)],
                                "blue_median_srgb_after": [round(float(np.median(srgb_graded[region][:, c])), 3) for c in range(3)]}
            log("  recolour site-blue", json.dumps(info["recolour"]))
    elif A.recolour not in ("", "none"):
        raise SystemExit("--recolour: none or site-blue")
    if GRADE["gains"]:
        hue, sat, val = hsv(srgb)
        _, _, val2 = hsv(srgb_graded)
        red = (sat > 0.45) & ((hue < 20) | (hue > 340)) & (val > 0.1)
        if red.any():
            info["grade_red_median_v"] = [round(float(np.median(val[red])), 3), round(float(np.median(val2[red])), 3)]
    n3 = down(nrm[..., :3], bake_px // nrm_px)
    n3 = n3 * 2 - 1
    if "top" in place and A.top_flatten > 0:
        # the top's relief eased toward the web mesh's own smooth normal (tangent space: straight up)
        k = down(place["top"], bake_px // nrm_px)[..., None] * float(np.clip(A.top_flatten, 0, 1))
        n3 = n3 * (1 - k) + np.array([0.0, 0.0, 1.0], np.float32) * k
    n3 /= np.maximum(np.linalg.norm(n3, axis=-1, keepdims=True), 1e-6)
    n3 = n3 * 0.5 + 0.5
    B = C.BUILD
    imgs, webps = {}, {}
    imgs["albedo"], webps[f"{name}-albedo"] = save_image(f"{name}-albedo", srgb_graded, os.path.join(B, f"{name}-albedo.png"), pair(A.q_albedo, qi))
    imgs["albedo"].colorspace_settings.name = "sRGB"
    imgs["orm"], webps[f"{name}-orm"] = save_image(f"{name}-orm", orm, os.path.join(B, f"{name}-orm.png"), pair(A.q_orm, qi))
    imgs["normal"], webps[f"{name}-normal"] = save_image(f"{name}-normal", n3, os.path.join(B, f"{name}-normal.png"), pair(A.q_normal, qi))
    export_material(low, imgs, name)
    if tag == "":
        REPORT["focus_candidates"] = focus_points(low, down(srgb_graded, max(1, tex // 512)), scale)
        log("  focus candidates", json.dumps(REPORT["focus_candidates"]))
    # metres, and the export
    low.data.transform(Matrix.Diagonal((scale, scale, scale, 1.0)))
    low.data.update()
    path = os.path.join(A.out, f"{name}.glb")
    guard(path)
    export(low, path)
    replace_images(path, webps)
    co = coords(low)
    mn, mx = co.min(0), co.max(0)
    info.update(fin)
    log(f"  metal: {100 * fin['metal_share']:.1f} percent of the map (gold {100 * fin['gold_metal_share']:.1f}, not gold "
        f"{100 * fin['non_gold_metal_share']:.1f}, of it steel or silver {100 * fin['steel_silver_metal_share']:.1f}); "
        f"{100 * fin['metal_painted_share']:.1f} percent marked metal by Meshy on a saturated colour, taken as lacquer or paint")
    if tag == "" and fin["steel_silver_metal_share"] > 0.005:
        warn(f"{name}: {100 * fin['steel_silver_metal_share']:.1f} percent of the colour map is grey metal (steel, silver). "
             "The gold rule was tuned on the general's gold; check the steel's roughness and colour in the renders "
             "(--metal moves the ramp)")
    if tag == "" and fin["non_gold_metal_share"] > 0.08:
        warn(f"{name}: {100 * fin['non_gold_metal_share']:.1f} percent of the colour map is metal that is not gold "
             f"(mean sRGB {fin.get('non_gold_metal_mean_srgb')}): check it is meant to be metal")
    info["textures"] = {"albedo": tex, "normal": nrm_px, "orm": orm_px, "bake": bake_px}
    info["glb"] = glb_summary(path)
    info["path"] = os.path.relpath(path, C.REPO)
    # three's axes: x, y up (blender z), z toward the viewer (blender -y)
    info["bounds_m"] = {"min": [round(float(mn[0]), 5), round(float(mn[2]), 5), round(float(-mx[1]), 5)],
                        "max": [round(float(mx[0]), 5), round(float(mx[2]), 5), round(float(-mn[1]), 5)]}
    log(name, json.dumps({k: info[k] for k in ("triangles", "gl_vertices", "charts", "uv_coverage", "uv_density_log2_p5_p50_p95", "textures", "bounds_m")}),
        f"{info['glb']['kb']} KB")
    low.data.transform(Matrix.Diagonal((1 / scale, 1 / scale, 1 / scale, 1.0)))
    low.data.update()
    return low, info


# ---------------------------------------------------------------- comparison renders

def renders(out_dir, src_path, files, M, scale):
    """the source and the exported files from four sides on a grey studio (Cycles), and their
    silhouettes (Workbench, orthographic, flat) with how much of the source's outline each keeps"""
    os.makedirs(out_dir, exist_ok=True)
    sc = C.reset()
    srcs = {}
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=src_path)
    so = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    for o in so:
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Diagonal((scale, scale, scale, 1.0)) @ M
    srcs["src"] = so
    for tag, path in files.items():
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=path)
        srcs[tag] = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    allz = np.concatenate([np.array([(o.matrix_world @ Vector(c)) for c in o.bound_box]) for o in so])
    H = float(allz[:, 2].max())
    tgt = Vector((0, 0, H * 0.5))
    w = bpy.data.worlds.new("grey")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.42, 0.44, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sc.world = w

    def area(n, loc, power, size, color):
        L = bpy.data.lights.new(n, "AREA")
        L.energy, L.size, L.color = power, size, color
        o = bpy.data.objects.new(n, L)
        sc.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (tgt - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    area("key", (-0.12 * H / 0.08, -0.16 * H / 0.08, 0.2 * H / 0.08), 5 * (H / 0.08) ** 2, 0.12 * H / 0.08, (1.0, 0.9, 0.78))
    area("rim", (0.14 * H / 0.08, 0.16 * H / 0.08, 0.12 * H / 0.08), 2.5 * (H / 0.08) ** 2, 0.08 * H / 0.08, (0.78, 0.85, 1.0))
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    views = [("front", 0), ("left", 90), ("back", 180), ("three-quarter", -35)]

    def aim(az, el, dist):
        a, e = math.radians(az), math.radians(el)
        cam.location = tgt + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()

    def only(tag):
        for t, obs in srcs.items():
            for o in obs:
                o.hide_render = t != tag
    shots = {}
    C.cycles(sc, samples=48, denoise=True)
    sc.render.resolution_x, sc.render.resolution_y = 560, 800
    sc.view_settings.view_transform = "AgX"
    cd.lens = 85
    cd.clip_start, cd.clip_end = H * 0.05, H * 40
    for tag in srcs:
        only(tag)
        for v, az in views:
            aim(az, 8, H * 3.6)
            p = os.path.join(out_dir, f"{NAME}-{tag}-{v}.png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            shots.setdefault(tag, {})[v] = p
        log("rendered", tag)
    # silhouettes
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.background_type = "WORLD"
    w.color = (0, 0, 0)
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    cd.type = "ORTHO"
    cd.ortho_scale = H * 1.12
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1400
    sil = {}
    for tag in srcs:
        only(tag)
        for v, az in views[:3] + [("top", None)]:
            if az is None:
                cam.location = tgt + Vector((0, 0, H * 3))
                cam.rotation_euler = (0, 0, 0)
            else:
                aim(az, 0, H * 3)
            p = os.path.join(out_dir, f"{NAME}-{tag}-sil-{v}.png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(p)
            a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
            im.pixels.foreach_get(a)
            sil.setdefault(tag, {})[v] = a.reshape(im.size[1], im.size[0], 4)[..., 0] > 0.5
            bpy.data.images.remove(im)
    match = {}
    # the thin parts (a pole, a spear, a handle, a rope, a scroll's edge): the source's silhouette less its
    # opening by a --thin-px square (structures under about 2 x thin-px + 1 pixels across, at 1250 pixels
    # to the height: 1.4 percent of it, about a millimetre on the table, with the default 8); a thin
    # pixel is kept when the cut covers it within a pixel
    r = max(1, A.thin_px)

    def opened(m):
        h_, w_ = m.shape
        er = ~_dilate(~m, r)[r:r + h_, r:r + w_]
        return _dilate(er, r)[r:r + h_, r:r + w_]
    thin = {v: sil["src"][v] & ~opened(sil["src"][v]) for v in sil["src"]}
    for tag in files:
        match[tag] = {}
        for v in sil["src"]:
            s, t = sil["src"][v], sil[tag][v]
            iou = (s & t).sum() / max(1, (s | t).sum())
            t1 = _dilate(t, 1)[1:1 + t.shape[0], 1:1 + t.shape[1]]
            th = thin[v]
            kept = float((th & t1).sum() / th.sum()) if th.any() else 1.0      # (no thin part seen from this side)
            match[tag][v] = {"iou": round(float(iou), 4), "lost_px": int((s & ~t).sum()), "added_px": int((t & ~s).sum()),
                             "thin_px": int(th.sum()), "thin_kept": round(kept, 4), "thin_lost_px": int((th & ~t1).sum())}
            # the difference as a picture: lost (in the source, not the web mesh) red, added blue, a thin
            # part's pixel lost yellow
            img = np.zeros(s.shape + (4,), np.float32)
            img[..., 3] = 1
            img[..., :3] = s[..., None] * 0.35
            img[th] = (0.55, 0.55, 0.55, 1)
            img[s & ~t] = (1, 0.1, 0.1, 1)
            img[t & ~s] = (0.2, 0.4, 1, 1)
            img[th & ~t1] = (1, 0.9, 0.1, 1)
            dim = bpy.data.images.new(f"diff-{tag}-{v}", s.shape[1], s.shape[0])
            dim.pixels.foreach_set(img.ravel())
            dim.filepath_raw = os.path.join(out_dir, f"{NAME}-{tag}-sildiff-{v}.png")
            dim.file_format = "PNG"
            dim.save()
    for tag in match:
        worst = min(match[tag].items(), key=lambda kv: kv[1]["thin_kept"])
        lim = 0.97 if tag == "desktop" else 0.94
        if worst[1]["thin_kept"] < lim:
            warn(f"{NAME} {tag}: the thin parts kept {100 * worst[1]['thin_kept']:.1f} percent from the {worst[0]} "
                 f"({worst[1]['thin_lost_px']} pixels lost, yellow in {NAME}-{tag}-sildiff-{worst[0]}.png): check the poles and handles")
    return {"renders": shots, "silhouette": match}


# ---------------------------------------------------------------- main

def renders_only():
    """the comparison renders of the files already exported (the source normalised the same way)"""
    C.reset()
    src = import_source(A.input)
    base_d, h_src, M = normalise(src)
    scale = A.height / h_src if A.height > 0 else A.base_d / base_d
    files = {"desktop": os.path.join(A.out, f"{NAME}.glb")}
    if A.tris_m > 0:
        files["phone"] = os.path.join(A.out, f"{NAME}-m.glb")
    path = A.report or os.path.join(C.BUILD, f"{NAME}-report.json")
    rep = json.load(open(path)) if os.path.exists(path) else dict(REPORT)
    rep.update(renders(A.renders, A.input, files, M, scale))
    rep["warnings"] = [w for w in rep.get("warnings", []) if "thin parts kept" not in w] + WARNINGS
    with open(path, "w") as f:
        json.dump(rep, f, indent=1)
    log("renders", A.renders, "report", path)


def main():
    if A.renders_only:
        if not A.renders:
            raise SystemExit("--renders-only needs --renders DIR")
        return renders_only()
    for tag in ("", "-m") if A.tris_m > 0 else ("",):      # before any work: the names are free or ours
        guard(os.path.join(A.out, f"{NAME}{tag}.glb"))
    os.makedirs(C.BUILD, exist_ok=True)
    REPORT["webp_encoder"] = "cwebp -sharp_yuv" if CWEBP else "blender"
    sc = C.reset()
    C.cycles(sc, samples=A.samples, denoise=False)
    sc.render.bake.margin = 16
    src = import_source(A.input)
    mats, bsdf, roles = read_material(src)
    REPORT["material_roles"] = roles
    REPORT["source"] = clean_source(src)
    base_d, h_src, M = normalise(src)
    scale = A.height / h_src if A.height > 0 else A.base_d / base_d
    REPORT["scale"] = {"source_base_diameter": round(base_d, 4), "source_height": round(h_src, 4), "metres_per_unit": round(scale, 6),
                       "base_diameter_m": round(base_d * scale, 5), "height_m": round(h_src * scale, 5)}
    log("scale", json.dumps(REPORT["scale"]))
    router = Router(mats)
    REPORT["variants"] = {}
    files = {}
    low, info = variant(src, router, "", A.tris, (A.tex, A.nrm, A.orm), scale, h_src, A.margin, 0)
    REPORT["variants"]["desktop"] = info
    files["desktop"] = os.path.join(C.REPO, info["path"])
    low.hide_render = True
    if A.tris_m > 0:
        low_m, info_m = variant(src, router, "-m", A.tris_m, (A.tex_m, A.nrm_m, A.orm_m), scale, h_src, A.margin_m, 1)
        REPORT["variants"]["phone"] = info_m
        files["phone"] = os.path.join(C.REPO, info_m["path"])
    REPORT["seconds_build"] = round(time.time() - T0, 1)
    if A.renders:
        REPORT.update(renders(A.renders, A.input, files, M, scale))
    REPORT["warnings"] = WARNINGS
    REPORT["seconds"] = round(time.time() - T0, 1)
    path = A.report or os.path.join(C.BUILD, f"{NAME}-report.json")
    with open(path, "w") as f:
        json.dump(REPORT, f, indent=1)
    log("report", path)
    for k, v in REPORT["variants"].items():
        log(f"{k}: {v['triangles']} triangles, {v['glb']['kb']} KB ({v['glb']['mesh_kb']} KB mesh, " +
            ", ".join(f"{i['name']} {i['kb']} KB" for i in v["glb"]["images"]) + ")")
    for w_ in WARNINGS:
        log("WARNING:", w_)


main()
