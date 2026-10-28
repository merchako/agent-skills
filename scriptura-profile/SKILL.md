---
name: scriptura-profile
description: Scriptura staff identity kit for a Google Workspace (scriptura.org) account — a profile photo with the Scriptura spiral-S mark badged into the photo's light negative space, and the standard Scriptura Gmail signature. Use when someone wants a Scriptura profile picture, avatar, or headshot with the logo, or wants to set up their Scriptura email signature.
---

# Scriptura profile

Two independent deliverables; do whichever the person asks for:

- **Profile photo** — steps below.
- **Email signature** — read [`references/email-signature.md`](references/email-signature.md) and follow it.

## Profile photo

The look: a square portrait with the face **off-center** (left of center by default) and the Scriptura mark — red disc, cream spiral-S — sitting in the **negative space**: the lightest, calmest stretch of background beside the head. Google shows avatars as circles, so the badge must also sit fully inside the circle crop.

Needs Python 3 with Pillow and numpy (`pip install pillow numpy`). Script: `scripts/profile_photo.py` (paths below are relative to this skill's folder).

### 1. Get the source

Ask for the **uncropped original** (full-resolution, with background on all sides of the head). An already-tight crop leaves no room to move the face off-center. Done when you have a file path to a photo with background visible beside the head.

### 2. Locate the head

```bash
python3 scripts/profile_photo.py grid SRC grid.png
```

Read `grid.png` (it prints the source size; red lines every 10%). Estimate the head box — ear to ear, crown to chin — and convert to **source pixels** `X,Y,W,H`. Done when the box hugs the head on all four sides; zoom (re-run `grid` on a crop) if unsure.

### 3. Compose

```bash
python3 scripts/profile_photo.py compose SRC OUTDIR --face X,Y,W,H
```

Writes `OUTDIR/profile-scriptura.jpg` (1024×1024) and `OUTDIR/preview.png` (square beside the circle crop). Placement is automatic: the script scores candidate spots in grayscale for lightness and calm, excluding the face and anything the circle mask would clip.

Knobs, all fractions of the frame:

| Flag       | Default | Effect                                                              |
| ---------- | ------- | ------------------------------------------------------------------- |
| `--face-x` | `0.38`  | Head center across; lower pushes the face further left              |
| `--head`   | `0.38`  | Head width; higher zooms in                                         |
| `--badge`  | `0.25`  | Badge diameter                                                      |
| `--at`     | auto    | Force badge center, e.g. `--at 0.74,0.53`                           |

If the head faces or leans left, the negative space is probably on the left: use `--face-x 0.62`.

### 4. Review

Read `preview.png` and judge it against the look above. The badge sits in light, plain background — never over shoulder, collar, hair, or a busy/dark patch — and shows whole in the circle. Adjust knobs and recompose until it does, then show the person the preview and iterate on their feedback.

### 5. Set it on the account

Hand this step to the person — Google's photo picker opens a native file dialog, and there's no API for a non-admin to set their own photo:

1. Open <https://myaccount.google.com/personal-info> signed in as the scriptura.org account (check the avatar menu — personal Gmail is a common wrong account).
2. _Profile picture_ → _Upload from device_ → choose `profile-scriptura.jpg`.
3. In the crop step keep the full circle so the badge isn't cut, then _Save as profile picture_.

It propagates to Gmail, Chat, Meet, and Calendar within minutes.
