# How the original creator moved Techie from the original body to Muse

Date: 2026-11-14. Method reference only: Techie is not fitted again by this project. Nothing here was tested in game.

## What was compared

Four of SloppyMods's Penumbra exports in `~/Downloads/APDoll-full-r2/Muse Body/` (read-only, not copied; 30-35 MB each):

| file | sha256 | what it is |
|---|---|---|
| `c0201e6164_top_orig.glb` | `027cd18c1051493e3c291ecb8924ee49b9b061bb191675c68729815c75fc85e3` | original `{Miette} » Techie` top |
| `c0201e6164_top_muse.glb` | `a54fa0c9f550a30834cb54d8cdf3952e7c06ef38f1caaaf5e92b3fbe10554467` | the Muse remake `[IVCS2] Techie - Muse+` top |
| `c0201e6164_dwn_orig.glb` | `eea09a892d5c0225f1bdb869ab83736e2978cacb923090fcf2c6ffc4cc00bdd9` | original bottoms |
| `c0201e6164_dwn_muse.glb` | `bf0da52e761c054fe2f358c70ca43e7a552d4077a06c1d6f796cb19848a07a2f` | Muse remake bottoms (shorts) |

Scripts: `tools/techie_compare.py` (per pair; output in `builds/study/techie_top_compare.txt` and `techie_dwn_compare.txt`) and `tools/compare_study.py` (against the mod `.mdl` files; `builds/study/compare_top_output.txt`). Heights are the `.glb` y axis in metres (chest band y 1.16-1.32); front is +z. "Moved" is the distance between a vertex of the original and its counterpart in the remake: same vertex index when both files have the same vertex count, otherwise the nearest remake vertex.

Which files these are, from the mod `.mdl` files: the "orig" top export equals the `{Miette} » Techie` option `[ yab - sayonara ]` (0.00 mm median and p95 over every vertex), so the original is the YAB-body version. The "muse" top export equals the installed `[IVCS2] Techie - Muse+/Top/Install/.../c0201e6164_top.mdl` (0.00 mm). The mod `[IVCS2] Techie - Muse+ (2)` is a different, older version (median 0.42, p95 5.30 mm) and was not used.

## What the creator changed, as numbers

### Skin (the body under the outfit)

| | original top | Muse remake top |
|---|---|---|
| skin meshes (`/mt_c0201b0001_bibo.mtrl`) | 5 (0.0-0.4), 12709 vertices | 5 (0.0-0.4), **4122 vertices** |
| `atr_` tags on the skin | atr_nek, atr_tv_a, atr_tv_a + atr_ude, atr_hij + atr_tv_a, atr_tv_b | the same tag kinds: atr_tv_a, atr_hij + atr_tv_a, atr_nek, atr_tv_a + atr_ude, atr_tv_b |
| skin bones with weight | 26, including `j_mune_l/r` (chest), `j_kao`, `j_asi_a_l/r` | 25, with `iv_kyokin_phys_l/r` and `iv_nitoukin_l/r` instead (physics bones) |

- The remake skin is the Muse body, cut down to the pieces the outfit leaves visible: remake skin to the Muse `Defined - Bare` / `Defined - Barbie` `.mdl` skin is 2.70 mm median, 8.72 mm p95 (`compare_top_output.txt`; `Soft - Bare` 3.02 / 10.24). The original skin is not the Muse body: original-to-remake nearest distance is 10.6 mm median, 66.7 p95 (parts missing in the remake), remake-to-original 4.6 median, 11.4 p95.
- The outfit's own `atr_tv_a` / `atr_tv_b` tags (they hide body parts under the outfit) were kept on the matching skin pieces; the body-part split stayed the same (5 meshes).
- Bottoms: skin 3098 vertices -> 2456; the original skin used 11 bones, the remake 17: new `iv_daitai_phys_l/r`, `iv_koumon_l/r`, `iv_shiri_l/r` (leg and butt physics). Original-to-remake skin distance 7.5 mm median, 15.7 p95.

### Cloth shape (vertex movement)

- **Top mesh 1.0** (2737 vertices, the same count; a chest-sized piece, x within 0.116 m of the middle and y 1.158-1.392, that stood out to z 0.150 while the rest of the garment ends at z 0.100): moved **6.80 mm median, 45.59 p95, 55.30 max**. Front/back change: median **-4.50 mm**, p5 -44.05, p95 -0.12 (the cloth went back toward the body). The front-most point went from z 0.150 to z 0.100, which is the Muse chest depth (0.099, `docs/MUSE_BODY_STUDY.md`). In the chest band (2114 vertices) the median move is 9.48 mm; in the waist band 6.02 mm; neck/shoulder 2.28 mm.
- **Top mesh 1.1** (the large garment: 29070 -> 29769 vertices, 699 added): moved only **0.54 mm median, 5.95 p95, 12.44 max**; chest band median 0.69, p95 7.14 mm; waist band 0.01 mm. In short, the creator re-shaped the bust piece and left the rest of the cloth alone.
- **Bottoms mesh 1.0** (7002 -> 7003): 0.86 mm median, 10.80 p95, 16.48 max. **Bottoms mesh 1.1** (1402, same count): 6.17 mm median, 10.70 p95; front/back median -2.86 mm (z max 0.110 -> 0.104).
- UVs are identical on the same-count meshes (max difference 0.00) and vertex colours differ on 0 of 2737 and 0 of 1402 vertices: the texture side did not change.
- Materials: cloth stays `/mt_c0201e6164_top_c.mtrl` (top) and `/mt_c0101e6164_dwn_b.mtrl` (bottoms) and the skin stays `bibo`. The only material change: the original top's extra mesh 2.0 had material `UNKNOWN` (1923 vertices, 1397 triangles, 3 bones); the remake's mesh 2.0 is the body mod's `/mt_c0201b0001_piercingsa.mtrl` (885 vertices, 1504 triangles, 3 bones). What the original `UNKNOWN` mesh was is not determined.
- Mesh/attribute changes: mesh count is the same (the remake top has 5 skin meshes + 2 cloth + 1 extra, like the original); no new `atr_` kinds on the cloth; vertex-count changes only as above.

### Weights and bones

- Top cloth bones: original 23, remake 24. Dropped: `j_mune_l/r` (chest), `j_oya_a_r`. Added: `iv_kyokin_phys_l/r` (chest physics), `iv_nitoukin_l/r` (arm physics).
- Bottoms cloth bones: original 4, remake 8; added `iv_daitai_phys_l/r`, `iv_shiri_l/r`.
- Weights were re-made, not kept: on the same-count top mesh 1.0 only 733 of 2737 vertices keep the same bone set (weight change mean 0.14, p95 0.42); on mesh 1.1 the nearest-vertex weight change is mean 0.084, p95 0.24. Bottoms: mesh 1.0 mean 0.090, p95 0.31; mesh 1.1 same bone set on 59 of 1402 vertices, mean 0.053.
- The new weights follow the Muse skin: cloth within 12 mm of its own skin has a weight difference to the skin under it (0 = identical, 1 = no bone in common) of **0.029 mean, 0.067 p95 in the remake top** (original 0.037 / 0.126), and **0.023 mean in the remake bottoms** (original 0.017). That is the same near-copy of the skin weights that the Dionys-made outfits show in XIVAutoFit's study (0.003-0.02), including the physics bones.

## What that means: the steps the process reuses

1. **Replace the skin with the body's own skin**, keeping the outfit's skin-piece split and its `atr_` tags. (Our process: `mdl_to_glb.py` + `transplant_body.py`.)
2. **Reshape only the cloth that the body difference touches**, chiefly the bust: pull the front cloth back so its front-most point equals the Muse chest depth, and leave the rest of the garment where the original author put it. (Our process: wrap, fit, cup removal and fold lift, which for the Track Suit moved cloth by up to 30 mm; the large cloth stays within a few mm.) Test: front-most chest z of cloth equals Muse's 0.099-0.100.
3. **Re-derive cloth weights from the Muse skin weights** where the cloth is close to the skin (within about 12 mm), drop bones Muse does not have (`j_mune_*`) and add the physics bones Muse has (`iv_*`). (Our process: `skin_weights.py`, then the crease smoothing `wsmooth.py`. `skin_weights.py` copies only onto close cloth, so it does **not** drop the creator's own chest bones everywhere: the Track Suit torso still carries 0.76% of its weight on `iv_c_mune_l/r` (449 vertices over 1%, at most 0.32 on one vertex; the source had 5.20%), bones the Muse top does not have. A step that removes or re-maps them is still missing.) Target: weight difference to the skin about 0.03 mean for close cloth.
4. **Keep the cloth's materials, UVs and vertex colours and its vertex count nearly unchanged**; swap only body-mod extras for the Muse mod's own (piercingsa).
5. Compare orig and remake of any outfit with `tools/techie_compare.py` before trusting a recipe on a new outfit.

Not copied: the creator removed most of the original skin (12709 -> 4122 vertices). Our process keeps the whole Muse skin pieces (`mesh 0.0`-`0.4`, 10530 vertices) so nothing the Muse body shows is missing; that choice is cheaper and was not compared in game. The creator's chest physics bones (`iv_kyokin_phys_l/r`) are not on the Muse `Defined - Bare` top; where they come from is not determined.

## Notes on the earlier job 009 run

Job 009's first cloth comparison printed nothing for "cloth material top_c": it filtered on `top_c`, which the bottoms do not use (`dwn_b`). `tools/techie_compare.py` and `compare_study.py` now filter on the outfit id `e6164`, which covers tops and bottoms; both were re-run for this note.
