# Muse body study (from the real .mdl files)

Date: 2026-11-14. Everything below was read from the body mod's own `.mdl` files with `tools/mdl_study.py` (read-only). Nothing here was tested in game. Raw output for all 47 files: `builds/study/muse_body_mdl_raw.txt` (re-run command at the end).

Plain words for SloppyMods: Penumbra's "Export to glTF" fails on the Muse body, so this project never asks Penumbra to export it. It reads the `.mdl` files straight from the Penumbra library and builds the `.glb` itself (`tools/mdl_to_glb.py`, checked against real exports, see section 6).

## 1. Where the Muse body is

| item | value |
|---|---|
| Mod folder | `/mnt/STORAGE/Penumbra/[HS] Muse+ (YAS)/` (read-only for this project) |
| Name / version / author (`meta.json`) | `[HS] Muse+ (YAS)`, version 3.2.2, by kydeimos |
| `.mdl` files | 47, all under `files/<group>/<variant>/chara/...`. Nothing else in the mod has geometry. |
| Enabled in | Penumbra collection `SGE` (`~/.xlcore/pluginConfigs/Penumbra/collections/eca2e486-...json`): Muse+ enabled, priority 1 |
| SGE choices for the body | Smallclothes Chest = option 0 `Defined - Bare`; Smallclothes Legs = option 9 `Defined - Barbie`; Hands and Feet = option 1 `Dyeable Nails` (hands and feet were not needed for the pilot) |

How the body reaches the game: the option files are swapped in by path. The chest option `Defined - Bare` maps the game path `chara/equipment/e0000/model/c0201e0000_top.mdl` (the "no gear" top, race c0201 = female Midlander) to `files/smallclothes chest/defined - bare/chara/equipment/e0000/model/c0201e0000_top.mdl`. The legs option `Defined - Barbie` maps `.../c0201e0000_dwn.mdl` to `files/smallclothes legs/defined - barbie/.../c0201e0000_dwn.mdl`. So an outfit that covers the top slot replaces that model, exactly as for Dionys and Doll Body 2: the outfit has to carry the body's skin itself.

Slots and variants found (c0201 slot / variant paths):

| slot | game path | variants in the mod | files |
|---|---|---|---|
| top | `chara/equipment/e0000/model/c0201e0000_top.mdl` | Defined - Bare, Defined - Barbie, Defined - Binder, Soft - Bare, Soft - Barbie, Soft - Binder | 6 |
| dwn | `chara/equipment/e0000/model/c0201e0000_dwn.mdl` | 20 (Defined and Soft, each with SFW Bulge, SFW Flat, Flaccid, Erect, Gen A, Gen B, Gen C, Transmasc, Intersex, Barbie; the `Soft - Erect` and `Defined - Erect` etc. share the same game path) | 20 |
| glv | `.../c0201e0000_glv.mdl` | Default Nails, dyeable nails | 2 |
| sho | `.../c0201e0000_sho.mdl` | Default Nails, dyeable nails (note: material path is `c0101b0001`, the male-race body path) | 2 |
| Emperor's New (robe, breeches, gloves, boots) | `chara/equipment/e0279/model/c0201e0279_{top,dwn,glv,sho}.mdl` | binder / SFW bulge / SFW flat / dyeable nails | 8 |
| body connectors | `chara/human/c0201/obj/body/b0002/model/c0201b0002_top.mdl` (and b0005, and the same for c0401 ... c1801) | one `install` option | 9 |

## 2. The fit target

**Chest: `Defined - Bare`** (`files/smallclothes chest/defined - bare/...`). Reason: the SGE collection uses it (read from the Penumbra collection file, see section 1). Check against the other chest options with `tools/skin_compare.py`:

- `Defined - Barbie` skin: every vertex is also in `Defined - Bare` (0.00 mm median and p95); it only has fewer vertices (9664 against 10530). Same chest geometry.
- `Soft - Bare` skin: median 0.00 mm, p95 2.17 mm, max 17.24 mm (belly area), chest max 1.84 mm. Same chest within 2 mm.
- Binder variants flatten the chest with a cloth piece (mesh 3, `top_b.mtrl`); they are not a skin target.

So a top fitted to `Defined - Bare` also sits right on the other bare/barbie chests to within a few mm. **Legs (later jobs): `Defined - Barbie`**, per the SGE collection. Not done in this job.

## 3. What the Muse top is made of (Defined - Bare, the target)

`files/smallclothes chest/defined - bare/chara/equipment/e0000/model/c0201e0000_top.mdl`: 21 bones in the file, 3 meshes.

| mesh | material | vertices | triangles | submeshes | attributes (`atr_`) | bones with weight |
|---|---|---|---|---|---|---|
| 0 | `/mt_c0201b0001_bibo.mtrl` (the **body skin**) | 10530 | 19724 | 5 | atr_hij (elbow/forearm piece), atr_nek (neck), atr_ude (upper arm) | 21 |
| 1 | `/mt_c0201b0001_piercingsa.mtrl` (navel piercing options) | 5569 | 9924 | 3 | none | 6 |
| 2 | `/mt_c0201b0001_betterpits.mtrl` (armpit detail) | 394 | 668 | 1 | none | 9 |

- Mesh 0 submeshes become `mesh 0.0` to `mesh 0.4`: torso 8378 vertices, wrists/forearms (atr_hij) 462, neck (atr_nek) 108, upper arms (atr_ude) 1558, neck connector 24.
- Bones (21): `iv_nitoukin_l/r` (upper-arm physics), `j_kosi`, `j_kubi`, `j_sako_l/r`, `j_sebo_a/b/c`, `j_te_l/r`, `j_ude_a_l/r`, `j_ude_b_l/r`, `n_hhiji_l/r`, `n_hkata_l/r`, `n_hte_l/r`. **No** `iv_fukubu_phys` belly physics bone in the Bare/Barbie/Binder Defined options; the `Soft - ...` options add `iv_fukubu_phys` and `ya_fukubu_phys` (23 bones). No chest bones at all (no `j_mune`, no `iv_c_mune`): the Muse chest is driven by the spine and shoulder bones.
- Vertex layout (every mesh of every file): stream 0 = POSITION float3, BLENDWEIGHT ubyte8 (raw 0..255, the 8 influences sum to 255), BLENDINDICES ubyte8; stream 1 = NORMAL float3, TANGENT ubyte4n, COLOR0 ubyte4n, UV0 float4 (two texture sets in one element), UV1 float2. In a Penumbra glTF export: UV0 -> TEXCOORD_0 and TEXCOORD_1, UV1 -> TEXCOORD_2, COLOR0 -> `_FFXIV_COLOR`.
- Body size: bbox x -0.47..0.47, y 1.001..1.452 (arm span and neck), front-most point z 0.101. The chest front reaches z 0.099.

Other variants used or compared (full detail in the raw file):

| file | skin mesh 0 vertices | bones with weight | other meshes |
|---|---|---|---|
| top Defined - Barbie | 9664 | 21 | piercingsa 1277, betterpits 394, barbie 974 (`/mt_c0201b0001_barbie.mtrl`) |
| top Soft - Bare | 10530 | 23 (adds iv_fukubu_phys, ya_fukubu_phys) | piercingsa 5569, betterpits 394 |
| top Defined - Binder | 7646 | 21 | piercingsa 1277, betterpits 394, mesh 3 `/mt_c0201e0000_top_b.mtrl` 2665 (the binder cloth) |
| dwn Defined - Barbie (legs target) | 9399 (atr_hiz, atr_sne), 3 submeshes | 18 (iv_daitai_phys, iv_shiri, j_asi_a..d, j_kosi, j_sebo; ya_* physics) | bibopube 132, betterpube 1408, barbie 336; 19 bones in the file |
| glv Default Nails | 8168 (atr_gv_a/b/c), 4 submeshes | 32 (finger bones plus iv_*_c finger physics) | none |
| sho Default Nails | 6266 (`heels_offset_n_a_abj`), 2 submeshes | 26 (toe bones iv_asi_*) | none; material `/mt_c0101b0001_bibo.mtrl` |

Materials: the body skin is always the `bibo` material (`/mt_c0201b0001_bibo.mtrl`), the same name Dionys uses. The extra meshes (piercingsa, betterpits, barbie, bibopube, betterpube) are body-mod options with their own materials. The outfit fit keeps **only the `bibo` mesh** as the skin (the transplant step also treats any `/mt_c0201b0001_b...` material as skin, so the other extras must not be handed to it; `mdl_to_glb.py` writes only the chosen mesh).

## 4. How Muse differs from Dionys and Doll Body 2

Dionys numbers are from the same kind of `.mdl` read (Dionys V1.4.0 top `Dionys/Models/Top/Chest/...`) and from XIVAutoFit `builds/_dionys/dionys_study_findings.md`. Doll Body 2 numbers are from `[Cry] Doll Body 2 [Body][Gen3] v2.1.8/Smallclothes Body/S - Soft/...` and from XIVAutoFit `tools/FITTING_PROCESS.md` and `tools/SKILL.md`. Distances are from `tools/skin_compare.py` (`builds/study/skin_compare_output.txt`), vertex to nearest vertex, in mm.

| | Muse+ (YAS) 3.2.2, Defined - Bare | Dionys V1.4.0 | Doll Body 2 v2.1.8 |
|---|---|---|---|
| Body skin material | `/mt_c0201b0001_bibo.mtrl` | `/mt_c0201b0001_bibo.mtrl` | `/mt_c0201b0001_b.mtrl` |
| Top skin vertices / submeshes | 10530 / 5 (torso 8378) | 3866 / 5 (torso 2944) | 5467 / 3 |
| Attributes on the skin | atr_hij, atr_nek, atr_ude | atr_hij, atr_nek, atr_ude | atr_hij, atr_ude |
| Extra body meshes in the top model | piercingsa, betterpits (options) | piercing meshes `/dy_diomtbody1_piercing_*` | metallic joints `/mt_c0201b0001_DOLL.mtrl` and `DOLLC` (separate meshes, an empty placeholder mesh 1) |
| Joints (metal) | none | none | yes, must be re-added to every outfit (`JOINTMAT=DOLL`) |
| Bones with weight, top | 21 (Soft: 23) | 22 (adds iv_fukubu_phys; 26 in the file) | 21 (has `j_mune_l/r` chest bones) |
| Physics bones on the top skin | `iv_nitoukin_l/r` (arms) | `iv_nitoukin_l/r`, `iv_fukubu_phys` | none in the top file (file bones: j_*, n_h*, `n_root`) |
| Chest distance to Muse | (itself) | median 3.25, p95 7.37, max 11.16 mm | median 13.25, p95 21.63, max 22.51 mm |
| Whole top distance to Muse | (itself) | median 2.42, p95 7.64, max 15.33 mm | median 7.22, p95 21.04, max 22.51 mm |
| Chest front-most z (m) | 0.099 | 0.099 | 0.117 |
| YAB (the body the Track Suit was made for), chest | median 11.90, p95 34.52, max 47.14 mm; front-most z 0.132 | chest p95 34 mm (XIVAutoFit's Track Suit recipe) | |
| Practical effect | Flat-ish chest, almost the Dionys chest. Dionys chest steps (cup removal, fold lift) carry over. | chest flatter than YAB | chest between the two; Doll needs a separate chest-flatten step |

Read the table this way: a top made for a big-bust body (YAB) sits 12 mm (median) off the Muse chest, and the Muse chest is within about 3 mm (median) of the Dionys chest. That is why the pilot reuses the Dionys recipe unchanged (parameters in `docs/MUSE_FITTING_PROCESS.md`) and why the numbers it reached on Muse match the Dionys ones.

## 5. Not determined

- How the Muse skin looks in game with the outfit on (the pilot is untested in game).
- Which `.mdl` the SGE collection really loads for the Track Suit (mod `OH - Track Suit`, enabled or not there, which option): not checked. Check it before importing, as the hard rules say (XIVAutoFit's recipe checked this for the DNC collection only).
- Whether the Muse `Soft - ...` or `Defined - Binder` variants matter for outfits: only measured (section 2), not tried.
- Hands, feet and legs fitting: outside this job. The dwn, glv and sho models are only summarised.
- The `UNKNOWN` material of Techie's original extra mesh (see `docs/TECHIE_METHOD.md`) was not identified.

## 6. How this was checked

- `tools/mdl_study.py` re-run on all 47 `.mdl` files gave the same text as job 009's output, line for line (only the file order differs): `builds/study/muse_body_mdl_raw.txt`.
- `tools/mdl_to_glb.py` (the `.mdl` to `.glb` writer) was tested against two real Penumbra exports of the same models. Track Suit `.mdl` mesh 1 against `~/Downloads/APDoll-full-r2/c0201e6116_top_a.glb`: positions, normals, UV sets, colours and triangles identical (0.00 difference), bones and weights equal per vertex, 2 meshes (`builds/skins/proof_compare_output.txt`). Dionys top mesh 0 against XIVAutoFit's in-game Dionys skin `ingame_top_skin.glb`: all five submeshes identical including the `atr_hij`, `atr_nek` and `atr_ude` tags (`builds/skins/proof_compare_dionys_output.txt`). So the Muse skin made the same way can be trusted; it carries no TANGENT (the rule) and a Penumbra export would only add one.
- Re-run:

```
python3 -I -B tools/mdl_study.py "/mnt/STORAGE/Penumbra/[HS] Muse+ (YAS)/files/Smallclothes Chest/defined - bare/chara/equipment/e0000/model/c0201e0000_top.mdl"
python3 -I -B tools/skin_compare.py <muse .mdl> "Dionys=<dionys .mdl>" "YAB=<track suit .mdl>:1"
```
