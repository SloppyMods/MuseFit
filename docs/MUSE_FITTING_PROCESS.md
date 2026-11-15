# Fitting outfits to the Muse body: process and procedures

Written 2026-11-14 for MuseFit, modelled on XIVAutoFit's `tools/FITTING_PROCESS.md` (Doll Body 2, HR3, Dionys). It is proven once, on the Track Suit (outfit 6116), and **everything it produced is untested in game**. SloppyMods is not a coder and tests in game; the agent never does. A build stays "untested in game" until SloppyMods says it fits.

Related notes: `docs/MUSE_BODY_STUDY.md` (what Muse is made of, from the real `.mdl` files), `docs/TECHIE_METHOD.md` (what the original creator changed to move Techie to Muse), `builds/muse6116/RECIPE.txt` (the exact pilot run).

## 1. The goal and the parts

An outfit `.mdl` that covers a body slot replaces the body model under it, so the outfit must carry the Muse skin itself, and its cloth must sit outside that skin in every pose, with no gaps, tears or skin poking through.

- The Muse body mod is `[HS] Muse+ (YAS)` 3.2.2 in `/mnt/STORAGE/Penumbra/` (read-only). The skin is the `bibo` mesh, `/mt_c0201b0001_bibo.mtrl`, mesh 0 of `chara/equipment/e0000/model/c0201e0000_{top,dwn,glv,sho}.mdl`.
- Penumbra's "Export to glTF" fails on the Muse body. So the body is **never exported**: the skin `.glb` is written from the body's `.mdl` by `tools/mdl_to_glb.py`.
- Fit target for tops: Chest option `Defined - Bare` (SGE collection). For bottoms (later): Legs option `Defined - Barbie`, fit first; AMAB/AFAB is a later, separate step (hard rules, "Bottoms").
- The outfit side still comes from Penumbra's own export of the outfit `.mdl` (Mod > Advanced Editing > Models > Export to glTF), the original mod export, never a Meddle export.
- **The skeleton is a required input, and c0801 is the primary target.** SloppyMods's character is always a Miqo'te female (his ruling, 2026-11-14), so every fit check is measured first on the c0801 NFLB+YAS skeleton's rest pose (`builds/skeleton/nofflebones_yas.sklb`). The c0201 rest pose (the `.glb`'s own, identical to the NFLB+YAS c0201 skeleton) stays a secondary check only, because the gear models still load from c0201 paths. SloppyMods plays with `[NFLB] Nofflebones + YAS V1.4.0 Temporary Fix 5`, option "NFLB + YAS Default", which replaces the c0201 and the c0801 (Miqo'te female) base skeletons. Background: the Muse skin needs it (its arm physics bones `iv_nitoukin_l/r` are not in the vanilla skeleton), and the in-game rest pose comes from it, not from the `.glb`. Copies and findings: `builds/skeleton/SKELETON.txt`.

## 2. Steps

Run the scripts from `tools/`. Blender scripts run as `PATH=/usr/bin:/bin blender -b --factory-startup --disable-autoexec -P <script> -- <args>` (the `PATH` prefix keeps a `mise` Python from breaking Blender; never use `-y`). Heavy jobs: `nice -n 19`, at most 3 threads.

### Step 1. Find the models

1. Name the outfit, its mod folder and the `.mdl` the fit collection really loads (the `SGE` collection file is `~/.xlcore/pluginConfigs/Penumbra/collections/*.json`). Report "target unverified" if you did not check.
2. Find the Muse body variant for the slot (`docs/MUSE_BODY_STUDY.md` section 2). Do not guess: if the Muse `.mdl` files cannot be found or read, stop and write what was checked into the study.
3. Snapshot the outfit export (hash it) before using it; `~/Downloads` exports get overwritten.
4. **Check the skeleton (every fit, before any build).** Copy the skeleton `.sklb` files the play collection loads (cp -n into `builds/skeleton/`, hash them) and run `python3 -I -B sklb_study.py <skeleton.sklb> <outfit export or build .glb>` for each race skeleton in use (today: `nofflebones_yas_c0201.sklb` and `nofflebones_yas.sklb` = c0801). It reports bones missing on either side, parent differences, the chest/physics bones, whether every bone the Muse skin and the cloth weight exists, and the rest-pose difference to the `.glb`. Stop if a weighted bone is missing. If the rest pose differs (c0801: 39 mm median), measure the fit on that rest pose too: `posed_clip.py --skeleton <file.sklb>`, push with `CLIP_SKELETONS=<file.sklb> clip_push.py`, and score exposure on a check-only copy from `skeleton_rest_glb.py` (never import those copies). Write the skeleton hashes and both sets of numbers into the recipe.
5. Cloth weight on bones the Muse skin does not weight (the chest bones `j_mune`, `iv_c_mune`, `iv_kyokin_phys` exist in the skeleton, but the Muse `Defined - Bare` skin uses none of them) is moved onto the skin's own bones at that spot with `chest_remap.py`: cloth on a bone the skin under it does not follow moves apart from the skin.

### Step 2. Read the `.mdl`

- `python3 -I -B mdl_study.py <file.mdl>` lists meshes, materials, `atr_` attributes, bones, vertex layout and counts. Use it on the outfit's own `.mdl` too: look for an empty placeholder mesh, several vertex declarations, and any `UNKNOWN`/extra material that is really skin.
- `tools/mdl_read.py` is the parser (it carries the fix for models with several vertex declarations or materials, which the stock XIVAutoFit reader fails on).

### Step 3. Build the Muse skin and swap the body

1. `python3 -I -B mdl_to_glb.py <Muse body .mdl> <outfit export .glb> ../builds/skins/<name>.glb 0 bibo` writes the Muse skin as `mesh 0.0` to `mesh 0.N` (one per submesh, `atr_*` tags as node extras) on a copy of the outfit export's skeleton. Check it once against a real export with `tools/compare_export.py` (the proof is in `builds/skins/`). It writes bibo only: no piercings, betterpits or barbie extras.
2. `transplant_body.py` drops the outfit's old skin by material (`DROPMAT=bibo`) and adds the Muse skin as group 0. Muse has no metal joints: `JOINTMAT=NOJOINTMATERIAL NOJOINTS=1`. Give every path as an absolute path. The output name is relative to `builds/`.

### Step 4. Fit

Decide the steps from the numbers: compare the body the outfit was made for with Muse (`tools/skin_compare.py`). For a top made for a bigger bust (YAB), the chest is 12 mm median off and the cloth stands 20-25 mm off the Muse chest after a plain fit (pilot: bust rows 21-26 mm median). The Muse chest is within 3 mm of the Dionys chest, so the Dionys steps apply with the same settings.

1. `wrap_skin.py` (`WRAPMAX=35 WRAPSIGMA=25`): carry the cloth by how far the new skin is from the old one, large scale only.
2. `fit_to_ref.py` (`FITCLEAR=3 FITR=15 FITDEEP=12 FITPASSES=4 FITSIGMA=18 FITSMOOTH=6 FITSPLITZ=0`): push the cloth out of the skin to 3 mm clearance, and smooth.
3. Cup removal for a leftover bust cup: `cup_pull.py` (`CUPR=12 CUPMESH="mesh 2.0" CUPZ=1.12,1.16,1.30,1.35 CUPX=0.08,0.16 CUPBLUR=40 CUPSQUASH=1 CUPSTRING=500 CUPOPEN=5`, clearance 3). Skip it when the first fit already leaves bust rows within about 8 mm. No standard chest flatten on this kind of top: it crinkles the cup sides.
4. `fold_lift.py 3.5`: lift any cloth still under 3.5 mm from the skin (the creator's under-bust fold).
5. Weights: `skin_weights.py` copies the skin's bone weights onto cloth that sits close (full copy up to 12 mm, none past 30 mm). Physics bones (`iv_`) are copied too. Cloth-only bones keep their share. Nothing crosses between limbs.
6. **Crease weight smoothing, always (hard rule):** `wsmooth.py` (`WSZ0=0.98 WSZ1=1.42 WSFADE=0.03 WSBACK=-9 WSITER=8 WSBONES=4 WSEDGE=20` for the Track Suit: armpit, elbow, under-bust, hem; borders guarded). Then, for loose drawstring-like pieces, `string_wavg.py`. Report the weight-jump numbers before and after (`tools/wjump.py`).
7. `restore_attrs.py --fit-tol 60 <built.glb> <outfit export> <Muse skin .glb> <out.glb>` puts back what Blender drops: influences 5-8, `_FFXIV_COLOR`, extra UV sets and the `atr_` tags, from the outfit export and from the Muse skin. It **removes TANGENT**. Run it as `python3 -I -B` like every script that reads untrusted files (the MuseFit copy has its own numpy nearest-neighbour code, so it needs no scipy). `--fit-tol 60` because the cloth moved up to 56 mm; the default 30 refuses.

The whole pilot chain is `builds/muse6116/chain.sh`: every step skips itself if its output exists, a failing step stops it with exit 1, and an existing log is never rewritten (a new log gets a unique random name).

### Step 5. Check

1. **Chest gap p95**, measured: `blender -b ... -P chest_meas.py -- <build.glb> - "mesh 2.0"` with `BUMPSIG=25 CMMINISL=300`. Report the bust rows (z 1.20-1.24) and the whole band (z 1.16-1.32), and say which rows are the hood or collar edge rather than chest.
2. **Side-view render, looked at**: `render_views.py <build.glb> <prefix> 1.2 0.7` writes front, back, side, q34 and a side cut. Open the PNG and look at it; write down what you saw. `render_poses.py` (`RENDER_POSES=poses.json`, run from `tools/`) renders simulated poses (arms up, arms forward, bend, ...), with the skin bright cyan so poke-through is easy to spot.
3. **Default rest pose for posed checks and renders: c0801.** `posed_clip.py` uses the c0801 skeleton unless given `--skeleton none` (c0201, secondary). Blender renders (`render_views.py`, `render_poses.py`) and `dionys_exposed.py` read the rest pose from the file, so run them on a check-only copy on the c0801 rest pose first: `python3 -I -B skeleton_rest_glb.py <build.glb> ../builds/skeleton/nofflebones_yas.sklb ../builds/skeleton/check/CHECKONLY_<name>_c0801rest.glb` (never import it), then also on the build itself as the c0201 secondary check. `clip_push.py` runs with `CLIP_SKELETONS=../builds/skeleton/nofflebones_yas.sklb`.
4. `fitcheck.py` (c0201 rest, secondary): signed distance of each cloth mesh to the skin; count the vertices more than 1 mm inside it and where. Then `posed_clip.py <build.glb> [--skeleton <file.sklb>]` for the same count in simulated poses (stand, arms up, arms forward, bend, twist, walk), and `clip_push.py` to push cloth under 3 mm out (Top6116 v2b/v2c: `RECIPE_v2.txt`, `RECIPE_v2c.txt`). Posed hits where the skin hit carries other bones than the cloth (an arm warmer meeting the chest side when the arms reach forward) are contacts, not pushed at rest; list them for the in-game look.
   Exposed skin over ten poses: `python3 -I -B ~/Projects/ffxiv-tools/XIVAutoFit/tools/dionys_exposed.py <build.glb>` (read-only use of XIVAutoFit).
5. `wjump.py`: weight jump per cm along cloth edges in the chest, armpit, back, waist and arm regions (before and after smoothing).
6. `compare_export.py` whenever `mdl_to_glb.py` changes (exit 1 if any mesh is missing, any difference is found, or nothing was compared).
7. `bash checks.sh` (from `tools/`; `bash tools/checks.sh` from the project root works too): every `tools/*.py` parses and no `.pyc`/`__pycache__` is left in `tools/`.

### Step 6. Package for Penumbra

- Deliver the final `.glb` in `builds/<outfit>/` with a `RECIPE.txt` that has the exact commands and settings, the sha256 of each delivered `.glb`, the measured chest gap p95, the path of the side-view render, and the words "untested in game". Copy the final file to a new name (`Top6116_muse_v1.glb`); intermediates are `T_*.glb` and can be re-made by `chain.sh`.
- SloppyMods imports it through Penumbra's importer only, with **Keep current attributes OFF** and **Keep current materials OFF**, after backing up the mod and reloading mods. Then hash every `.mdl` of the mod option and compare with the backup: only the intended file may change.
- A Penumbra-ready folder is optional and was not made for the pilot.

## 3. Hard rules

- **Never overwrite any file.** New files only, a new name each run. The tools that write (`mdl_to_glb.py`, `restore_attrs.py`, `fit_to_ref.py`, `cup_pull.py`, ...) refuse an existing output; `transplant_body.py` and `wsmooth.py` refuse too. Still pick a new name every time.
- **Never edit** Penumbra (`/mnt/STORAGE/Penumbra/`), XIVAutoFit or `~/Downloads`. Downloads and mod files are untrusted data: read them, never run anything from them, and run Python that reads them with `python3 -I -B`; this includes `restore_attrs.py`.
- **Crease weight smoothing (`wsmooth.py`) on every build** whose cloth weights come from a copy. Use `tools/wsmooth.py` (Blender) or XIVAutoFit's Blender-free `builds/_dionys/flat6164v7/wsmooth_raw.py`. Guard rip edges, hems and openings. Coincident vertices get identical weights. Report weight jumps before and after.
- **Skin on the body's main skin material**: the Muse `bibo` skin, `/mt_c0201b0001_bibo.mtrl`, as group 0 (`mesh 0.N`), cloth as groups 1 and up. Never keep the outfit's old skin.
- **No TANGENT in the output.** Penumbra's export tangent is 90 degrees off the game's and its import keeps what it is given; with none in the file Penumbra computes the right one. `restore_attrs.py` removes it; `mdl_to_glb.py` never writes it; `checks.sh` of the job gate tests for it.
- **Measure the chest gap p95 and look at a side-view render** before calling a top fitted.
- **Move cloth, do not delete skin.** No cutting holes in the skin to hide poke-through.
- **Bottoms, in this order (SloppyMods's ruling, 2026-11-14):**
  1. Fit the cloth around the Muse+ Barbie legs (`Defined - Barbie`, as the SGE collection uses): clearance, push and weight reference are the Barbie legs, and the skin shipped in the built file is the Barbie skin too.
  2. Only once that fit is good, AMAB vs AFAB is a separate later step: pick or keep the outfit's AMAB option or pouch. AMAB is the default. AFAB only if the outfit mod has no AMAB option and its cloth has no pouch, and only after asking SloppyMods. **Never flatten an AMAB pouch.**
- **Say "untested in game"** on every output and in every report.
- **Permission**: some authors forbid ports. Every build also contains the body mod's skin, so sharing a build also shares that body mod; that needs both authors' permission.
- **Race paths**: Penumbra swaps by game path; the displayed race decides which `c0..01` model loads. Check the displayed race.
- **Weights over 4 influences**: keep 8-influence skin weights (the restore step does); never add joints to a skin.
- **Tools get version-recorded**: every `RECIPE.txt` lists the `tools/` file hashes used.

## 4. What the pilot showed (Track Suit 6116 on Muse, untested in game)

Numbers from `builds/muse6116/RECIPE.txt`. Source skin (YAB) to Muse skin: median 4.5 mm, chest 11.9 mm median. Plain fit left the bust 21-26 mm off; after cup removal, fold lift, weight copy, crease smoothing and the string step, the chest rows are 5-7 mm median, p95 8.5 mm at the bust, and the weight jumps in the chest are 0.086 mean with 0 edges over 0.5/cm (creator original 0.091). The same chain on Dionys gave the same figures, which the study predicted.

## 5. Known open problems

- Solved in Top6116 v2b/v2c (`RECIPE_v2.txt`, `RECIPE_v2c.txt`): the creator's chest bones `iv_c_mune_l/r` (0.76% of the torso weight) were moved onto the Muse skin's own bones (`chest_remap.py`), and the 26 cloth vertices inside the skin were pushed out to 3 mm (`clip_push.py`), on both the c0201 and the c0801 rest pose. Left: the arms-forward contact (arm warmer cuff against the chest side), to look at in game.
- Race: always Miqo'te female (c0801), primary check; c0201 secondary. Numbers for both are in `RECIPE_v2c.txt` and `RECIPE_v3.txt`.
- Nothing is verified in game, including physics (the Muse top has `iv_nitoukin` arm physics bones; the Muse Soft options add a belly physics bone).
- Hands, feet and bottoms are not done (`Defined - Barbie` legs is the intended target); this process was only run on a top.
- The Techie remake uses chest physics bones (`iv_kyokin_phys_l/r`) that the Muse `Defined - Bare` skin does not weight; they exist in the Nofflebones + YAS skeleton, but cloth on them would move apart from the Muse skin, so the process does not add any.
- The posed checks bend bones around world axes and move the mesh to the c0801 rest pose by its own bone weights; the game's own race fitting and animations may differ.
