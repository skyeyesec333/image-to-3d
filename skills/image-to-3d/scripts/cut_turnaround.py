"""Cut a three-view turnaround sheet (front, left side, back, side by side on a plain background)
into three square images for Meshy's multi-image upload.

    python3 cut_turnaround.py "<sheet.png>" <name> <out_dir> [<out_dir> ...]

writes <name>-front.png, <name>-left.png, <name>-back.png (1024 x 1024, the figure centred on the
sheet's own background grey, 5% margin) into each out_dir. Needs only Pillow.

How the cut is found: every pixel is compared with the background at its own row (sampled at the
sheet's left and right edges, so a vertical gradient on the backdrop does not count as figure), the
figure pixels are counted per column, and the two emptiest bands (one in the left half of the middle,
one in the right) are the cuts. Each panel is then cropped to its own figure box."""

import sys
from pathlib import Path
from PIL import Image, ImageChops

THRESH = 30          # difference from the backdrop (0..255, luma) that counts as figure
PAD = 0.05           # margin round the figure, of the square's side


def cut(sheet_path, name, out_dirs):
    im = Image.open(sheet_path).convert("RGB")
    W, H = im.size
    # the backdrop at each row: the mean of a thin strip at each side edge
    left = im.crop((0, 0, 6, H)).resize((1, H), Image.BOX)
    right = im.crop((W - 6, 0, W, H)).resize((1, H), Image.BOX)
    edge = Image.blend(left, right, 0.5)
    mask = ImageChops.difference(im, edge.resize((W, H), Image.NEAREST)).convert("L").point(
        lambda v: 255 if v > THRESH else 0)

    # figure pixels per column (the lowest tenth left out: floor shading sits there)
    body = mask.crop((0, 0, W, int(H * 0.9)))
    counts = [body.crop((x, 0, x + 1, body.height)).histogram()[255] for x in range(W)]

    def band(x):
        return sum(counts[max(0, x - 6):x + 7])

    c1 = min(range(int(W * 0.22), int(W * 0.46)), key=band)
    c2 = min(range(int(W * 0.54), int(W * 0.78)), key=band)
    cuts = [0, c1, c2, W]

    bg = im.crop((0, 0, W, 10)).resize((1, 1), Image.BOX).getpixel((0, 0))
    written = []
    for i, view in enumerate(("front", "left", "back")):
        x0, x1 = cuts[i], cuts[i + 1]
        box = mask.crop((x0, 0, x1, H)).getbbox()
        if not box:
            raise SystemExit(f"{name}: no figure found in the {view} panel")
        crop = im.crop((x0 + box[0], box[1], x0 + box[2], box[3]))
        w, h = crop.size
        side = int(max(w, h) / (1 - 2 * PAD))
        sq = Image.new("RGB", (side, side), bg)
        sq.paste(crop, ((side - w) // 2, (side - h) // 2))
        sq = sq.resize((1024, 1024), Image.LANCZOS)
        for d in out_dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
            p = Path(d) / f"{name}-{view}.png"
            sq.save(p)
            written.append(str(p))
        print(f"{name} {view}: panel x {x0}-{x1}, figure box {box}, crowded columns at cut {band(cuts[i + 1]) if i < 2 else '-'}")
    return written


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    cut(sys.argv[1], sys.argv[2], sys.argv[3:])
