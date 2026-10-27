# Stage 1: the turnaround sheet prompt

## The shape that worked

Every prompt that produced a good Meshy model had the same parts, in this order:

1. **What it is, as one sentence:** "A three-view turnaround sheet (front, left side, back) of a single [object] [made as / carved as] [the medium]".
2. **The design, concretely:** silhouette-defining parts first (hat, cloak, roof, wheels), then what it holds or carries, then the base.
3. **House style, repeated word for word across a set:** the material and finish, where accents go ("small gold-leaf accents only on the hat rim"), and the anti-goals ("Sculpture, not a toy or CG character", "Bold simple silhouette that reads at thumbnail size").
4. **The views, precisely:** same scale and height; a *true* side profile; identical design in every view.
5. **The sheet hygiene:** backdrop, light, shadows, no text, nothing cropped, space between views.
6. **Fixes for known failures:** faces, crests, anything the model tends to get wrong.

## Template

```
A three-view turnaround sheet (front, left side, back, side by side) of a single [OBJECT]
[carved as / made as] [MEDIUM]: [DESIGN: silhouette parts, what it holds or carries, details],
standing on [BASE].

[HOUSE STYLE: material and finish, e.g. "Carved boxwood with visible knife facets"; accents and
where they go, e.g. "small gold-leaf accents only on the roof ridge ends"]. Sculpture, not a toy or
CG model. Bold simple silhouette that reads at thumbnail size.

Three full views side by side at the same scale and height: 1) straight front view, 2) true left
side profile (camera at 90 degrees to its left; it faces the right edge of the image), 3) straight
back view. Identical design in every view; only the camera angle changes. Orthographic views.

Plain light-grey background, soft even studio light, no shadows on the background (a soft contact
shadow under the base at most), no text, no labels, nothing cropped (the top of [the tallest part]
inside the frame), clear space between the three views.

[FIXES: e.g. "The faces should have a lacquered red-brown menpo half mask, eyes as one dark
shadow under the hat brim." / "Replace any family crest with a simple abstract geometric mark."
/ "No people." for props]
```

When a piece must match an existing design (a lineup image, an earlier render), attach that image in ChatGPT and say so: "Make a character turnaround sheet of [NAME] exactly as designed in the lineup: [its key features]".

Then, separately, ask for a **single front view** of the same object, square, high resolution, same backdrop and light. It becomes `refs/<name>-front.png`, the colour reference for the grade in stage 4. (The front panel cut from the sheet works too.)

## Examples that shipped

A figure:

> A three-view turnaround sheet (front, left side, back) of a single small Sengoku ashigaru foot-soldier game piece carved in boxwood: a simple compact figure in a conical jingasa hat and lacquered do armour, holding a long yari spear upright, with a small blank sashimono banner pole on the back, standing on a lathe-turned black lacquered base. Bold simple silhouette that reads at thumbnail size, visible knife facets, small gold-leaf accents only on the hat rim. Sculpture, not a toy or CG character. Plain light-grey background, soft studio light, no text. The faces should have a lacquered red-brown menpo half mask, eyes as one dark shadow under the hat brim.

A prop:

> A three-view turnaround sheet (front, left side, back, side by side on a plain light-grey background) of a single miniature Sengoku siege battering ram carved as a tabletop game piece: a heavy log ram with a bronze-capped head, slung by ropes under a low gabled shelter roof of black lacquered planks, on four solid wooden wheels, the shelter's frame of dark timber with rope lashings and small gold-leaf accents only on the roof ridge ends. Carved boxwood with visible knife facets; sculpture, not a toy or CG model. Bold simple silhouette that reads at thumbnail size. Orthographic views, soft even studio light, no people, no text, soft contact shadow only.

A figure matched to an existing lineup (the most precise about views):

> Make a character turnaround sheet of THE ENVOY exactly as designed in the lineup: wide conical straw hat, grey-green travelling cloak, a sealed letter with a red seal held out in both hands, a white banner on a pole behind him. Three full-body views side by side at the same scale and height, each on his round wooden base: 1) straight front view, 2) true left side profile (camera at 90 degrees to his left; his body faces the right edge of the image), 3) straight back view. Identical design in every view; only the camera angle changes. Plain light grey background, even studio light, no shadows on the background, no text, no labels, nothing cropped (the top of the banner pole inside the frame), clear space between the three views. Replace any family crest with a simple abstract geometric mark.

## What each phrase is for

- **"true left side profile (camera at 90 degrees…; faces the right edge)":** without it the side view drifts to three-quarter, and Meshy gets contradictory views.
- **"Identical design in every view; only the camera angle changes":** stops details (straps, crests, what is held) changing between views.
- **"same scale and height", "clear space between the three views":** the cutter needs empty columns, and Meshy needs matching proportions.
- **"nothing cropped (the top of the banner pole inside the frame)":** name the tallest part; it is the one that gets cut off.
- **"Plain light-grey background… no shadows on the background", "soft contact shadow only":** cast shadows become geometry.
- **"Bold simple silhouette that reads at thumbnail size", "Sculpture, not a toy or CG":** keeps the forms chunky enough for Meshy and for small on-screen sizes.
- **"accents only on…":** without "only", accents spread everywhere.
- **Face and crest fixes:** image models default to realistic faces and to real heraldry; say what to do instead.

## Checks before cutting

- Three views, in front / left / back order, same height and pose; the side is a true profile.
- Clear backdrop gaps between views.
- The base fully visible and flat-bottomed in all three; the tallest part inside the frame.
- Thin parts (spears, poles, crests, banners) present and continuous, and thick enough to survive: Meshy fuses or drops very thin geometry, and the optimiser keeps only what Meshy made.
- No cast shadow or reflection touching the outline.
- The back view is designed, not a guess: if the back matters, say what is on it.

## Iterating

Change one thing at a time and keep the house style fixed. When making a set, generate the hardest piece first and lock the house style from it.
