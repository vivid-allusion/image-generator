# UI Assets — square SVG icons for Helmer

Audience: a future cold agent asked to make a UI icon or graphic for Helmer.
Commands below were run on this box on 2026-10-12 against the dev clone;
anything not exercised is marked **(documented, not run here)**.

## What this is

The **Image Generator** (this repo) is a markdown → provider pipeline. Pointed
at a **Recraft V4.1 text-to-vector** profile it returns **square SVG** icons and
graphics — exactly what the Helmer UI (Theia) needs for gutter marks, toolbar
glyphs, and small design assets.

- Canonical repo: `vivid-allusion/image-generator`
- Dev path (this box): `/home/admin/GENERATORS/image-generator`
- Pipeline: *a `.md` prompt file + a profile YAML → Engine (`engine-fal`) → fal
  Recraft endpoint → an SVG in a timestamped output folder.*
- Model: `fal-ai/recraft/v4.1/text-to-vector` (fal.ai). Cost **$0.08/image**.

The Owner's commission (2026-10-12): *"it creates square SVG images … for icons
and other graphics for the Helmer UI … a red version of the broken link emoji
for the gutter to show broken links."*

## Setup (exact)

1. **Bootstrap the venv + deps.** `run.py` creates `venv/`, installs
   `requirements.txt`, then launches the Generator:
   ```bash
   python3 run.py --dry-run
   ```
   (`--dry-run` is a no-API-call preflight; use it to bootstrap.) The engine's
   own SDK dependency lands as `fal_client` (1.0.3) in the venv.

2. **API key in `.env`.** The key is `FAL_KEY` (get one at https://fal.ai).
   The repo-root `.env` is gitignored — **never commit or print the key**.
   In automation there is **no TTY**, so the interactive key wizard cannot run;
   the key **must** already be in `.env`:
   ```
   FAL_KEY=<your-key>
   ```
   Verify only that a key exists: `grep -q FAL_KEY .env && echo ok`.

3. **Install the `fal` Engine.** The Engine is a git clone into `ENGINES/`.
   In non-TTY automation the auto-install flag installs the engine as a side
   effect but the *first* invocation still exits 1 (see Gotchas) — expect to run
   it twice:
   ```bash
   python3 run.py --dry-run --install-default-engine=fal   # clones ENGINES/engine-fal, exits 1
   python3 run.py --dry-run                                # now detects fal, exits 0
   ```
   A manual equivalent, if the flag path ever breaks **(documented, not run
   here** — the flag did this clone):
   ```bash
   git clone https://github.com/vivid-allusion/engine-fal.git ENGINES/engine-fal
   ```

4. **Place the profile** at
   `USER-FILES/03.PROFILES/recraft-v4.1-text-to-vector_1x1.yaml`
   (both `03.PROFILES/` and `02.STANDBY/` are gitignored; only the file matters
   at runtime). The `02.STANDBY/` shelf is engine-owned and seeded on engine
   install.

## The icon recipe (the heart)

### The profile (verbatim, active)

```yaml
# Recraft V4.1 Text to Vector — 1:1 Square HD
platform: fal
endpoint: fal-ai/recraft/v4.1/text-to-vector
media_type: image
parameters:
  image_size: "square_hd"
pricing:
  base_cost: 0.08
  currency: USD
```

`square_hd` yields a square canvas — observed as `viewBox="0 0 2048 2048"`,
`width/height="1024"`. Only valid endpoint params for this model are
`prompt`, `image_size`, `colors`, `background_color`, `enable_safety_checker`
(verified against the live fal OpenAPI schema).

### The prompt `.md`

One `.md` file in `USER-FILES/04.INPUT/` = one generation job. The prompt is the
first non-image line; extra markdown-image lines would be reference URLs (not
needed for text-to-vector). Example (`USER-FILES/04.INPUT/demo-broken-link.md`):

```markdown
A single flat vector glyph of a broken chain link, bold and simple, solid red (#e5484d), centered on a plain background, minimal geometric style, no text, no shadows, no gradients — a small editor gutter warning symbol, square canvas.
```

### Style rules that worked

- **Flat vector, single glyph.** State it explicitly: "a single flat vector
  glyph", "minimal geometric style". Recraft's vector model honours it.
- **Solid colour, named.** "solid red (#e5484d)" steers the hue but only
  approximately — one run came back `rgb(241,27,56)`. To **pin the exact hue**,
  add a `colors` list (verified: produced exactly `rgb(229,72,77)` = `#e5484d`):
  ```yaml
  parameters:
    image_size: "square_hd"
    colors:
      - {r: 229, g: 72, b: 77}
  ```
  RGB values are 0–255. `background_color` accepts the same `{r,g,b}` shape.
- **Centered, square, no text/shadows/gradients.** Say each one — negative
  constraints are respected.
- **State the use.** "a small editor gutter warning symbol" nudges the weight
  and framing toward a tiny UI mark.
- **What did not work / gotchas:** see below — chiefly that the SVG is saved
  with a `.png` extension.

### Commands

```bash
python3 run.py --cost-estimation --verbose   # price the batch, no API calls
python3 run.py --dry-run                     # validate inputs, no API calls
python3 run.py --verbose                     # the real generation (spends money)
```

Add `--verbose` for INFO output, `-l/--logs` to also write per-file run logs
(off by default; standalone mode only).

### Outputs

A real run writes a timestamped folder:

```
USER-FILES/05.OUTPUT/261012_162513_IMG/
└── 261012_162525-demo-broken-link-0.png   # ← an SVG file, misnamed .png (see Gotchas)
```

After renaming (see Gotchas) the same file is `…-0.svg`.

- **File name pattern:** `<YYMMDD_HHMMSS>-<input-stem>-<idx>.<ext>`.
- The output folder is `<YYMMDD_HHMMSS>_IMG/`; nested input dirs are mirrored.
- **Run log** (`-l/--logs`): `<name>.log` beside the media **(documented, not
  run here** — the demo used the default, no logs, to stay within the
  three-generation budget).
- **Embedded payload metadata:** the Generator embeds the recipe JSON (prompt,
  endpoint, parameters) as XMP into PNG/JPEG/WebP. **Not for SVG** — the SVG's
  bytes are not PNG/JPEG/WebP, so embedding logs a non-fatal error and the file
  is left unchanged (the run still exits 0). Capture the recipe from your input
  `.md` / the console instead.

### Costs

- `$0.08` per image (profile `pricing.base_cost`; the endpoint is flat-rate).
- `--cost-estimation` prints `N files x $0.080 = $…` without spending.
- The demo below spent **$0.24** (3 generations).

## The worked example — the red broken-link icon

- **Prompt:** the `.md` above (verbatim).
- **Profile:** the verbatim profile above **plus** the `colors:
  [{r: 229, g: 72, b: 77}]` block to pin `#e5484d`.
- **Command:** `python3 run.py --verbose`
- **Raw result:** `USER-FILES/05.OUTPUT/261012_162513_IMG/261012_162525-demo-broken-link-0.png`
  (an SVG misnamed `.png`); renamed to `…-0.svg` for use.
- **Content:** a flat `rgb(229,72,77)` glyph on an off-white ground; square viewBox.
- **Tracked example in the repo:** [`docs/ui-assets/examples/broken-link-red.svg`](ui-assets/examples/broken-link-red.svg)
- Render a preview without an image viewer:
  ```bash
  rsvg-convert -w 256 -h 256 <file.svg> -o /tmp/preview.png
  ```

## Gotchas / troubleshooting

- **The SVG is saved as `.png`.** The Recraft endpoint returns a URL ending in
  the vector file; the fal Engine's URL path names image outputs `.png`
  regardless. Recraft is always vector, so **rename the output to `.svg`**:
  ```bash
  mv 'USER-FILES/05.OUTPUT/<ts>_IMG/<ts>-<stem>-0.png' '…/<ts>-<stem>-0.svg'
  ```
  Adding `output_format: "svg"` to the profile is **accepted by the API but does
  not rename the file** (verified) — don't rely on it.
- **Payload embed error for SVG** (`Failed to embed payload … unsupported image
  format: .png`): expected and non-fatal for vector output. Ignore it (exit is
  still 0).
- **Engine missing** (`No Engine found for platform '…'`): install the `fal`
  engine (Setup step 3). On the *first* non-TTY run the flag clones the engine
  but detection still reports the default platform (`replicate`) and exits 1 —
  **re-run**; the second run detects `fal`.
- **Empty `02.STANDBY/`**: it is seeded by `copy_standby_profiles()` after the
  engine loads. If it's empty, the engine isn't installed yet.
- **No-TTY key wizard**: the interactive wizard needs a TTY. In automation the
  key must already be in `.env` (Setup step 2).
- **A failed generation**: a mixed run writes red error-placeholder images so the
  output serial stays intact; an all-failed run exits 1. Per-file logs (with
  `-l`) and the fallback `image_generator_<ts>.log` carry the error detail.

## Where the assets go in the product

Generated SVGs are **candidates**, not shipped art. They reach **Helmer** (the
`theia-platform` repo) **through the owning workstream, through the design
gate** — the W16 comparison, and the Owner's look wherever the asset is
user-visible. The editor gutter's red broken-link mark is the **A70** item's;
this icon lands with that item. Do not copy a generated SVG straight into
`theia-platform` from here.

## Rules

- **Square / 1:1** (`image_size: "square_hd"`); **vector (SVG)** output.
- **Never commit or print the key** (`FAL_KEY` lives only in the gitignored
  `.env`).
- **USER-FILES is protected** — read from `04.INPUT/`, write to `05.OUTPUT/`;
  one prompt file per generation; no auto-cleanup/archiving.
- This repo's own `AGENTS.md` rules still apply (incl. the `04.INPUT/`
  read-only rule).
- Generated assets land via workstreams + the design gate (above) — never
  straight into the product repo.
