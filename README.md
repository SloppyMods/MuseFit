# MuseFit

A repeatable, written process for fitting FFXIV outfits onto the **Muse** body (the `[HS] Muse+ (YAS)` body mod, version 3.2.2), the way XIVAutoFit does it for Doll Body 2 and Dionys.

Plain words: Penumbra cannot export the Muse body to glTF, so MuseFit reads the Muse body straight from its `.mdl` files, builds the skin itself (`tools/mdl_to_glb.py`, checked against real Penumbra exports), swaps it into an outfit, fits the cloth onto it, and writes a `.glb` you import back into Penumbra.

Everything here is **untested in game**. SloppyMods, who uses this process, is not a coder and tests in game; an output counts as working only after he says so.

## Read in this order

1. `docs/MUSE_FITTING_PROCESS.md`: the steps, the hard rules, the checks.
2. `docs/MUSE_BODY_STUDY.md`: what Muse is made of (meshes, materials, attributes, bones, vertex layout), the fit target, and how it compares with Dionys and Doll Body 2.
3. `docs/TECHIE_METHOD.md`: what the original creator of the Techie outfit changed to move it from the original body to Muse (numbers from the files), turned into steps.
4. `builds/PILOT_STATUS.md`: the first job, the Track Suit (outfit 6116), and how far it got. Its files are `builds/muse6116/Top6116_muse_v1.glb` and `builds/muse6116/RECIPE.txt`.

## Folders

- `tools/` scripts (copies adapted from XIVAutoFit, plus new ones) and `tools/checks.sh`
- `docs/` the study, the method note, the process
- `builds/` generated files; nothing in it is ever overwritten

See `AGENTS.md` for the agent-facing summary (layout, commands, checks).
