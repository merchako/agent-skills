---
name: scriptura-profile
description: Scriptura staff identity kit for a Google Workspace (scriptura.org) account — a profile photo with the Scriptura spiral-S mark badged into the photo's negative space (light or dark backgrounds), and the standard Scriptura Gmail signature. Use when someone wants a Scriptura profile picture, avatar, or headshot with the logo, or wants to set up their Scriptura email signature.
---

# Scriptura profile

Two independent deliverables; do whichever the person asks for:

- **Profile photo** — steps below.
- **Email signature** — read [`references/email-signature.md`](references/email-signature.md) and follow it.

## Profile photo

The look: a square portrait with the face **off-center** (left of center by default) and the Scriptura mark sitting in the **negative space**: the biggest calm (low-contrast, unbusy) stretch of background beside the head that **contrasts** with the badge. The badge is the brand red disc with a cream spiral-S when red stands out; on backgrounds where it doesn't (dark, or mid-tone warm), it goes **monochrome** — a cream disc on dark backgrounds, an ink disc on light-to-mid ones — with the spiral knocked out to the background. Google shows avatars as circles, so the badge must also sit fully inside the circle crop.

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

Writes `OUTDIR/profile-scriptura.jpg` (1024×1024) and `OUTDIR/preview.png` (square beside the circle crop). Placement and color are automatic. For each badge color the script marks background that is calm in grayscale and has ≥3:1 contrast with the disc, excludes the head and shoulders and anything the circle mask would clip, and centers the badge in the biggest such area (shrinking it to fit, down to 16% of the frame). Red wins whenever it fits; otherwise the monochrome color with the biggest area. It prints every color's area radius and contrast — read them when a result surprises you.

Knobs (sizes and positions are fractions of the frame):

| Flag       | Default | Effect                                                              |
| ---------- | ------- | ------------------------------------------------------------------- |
| `--face-x` | `0.38`  | Head center across; lower pushes the face further left              |
| `--head`   | `0.38`  | Head width; higher zooms in                                         |
| `--badge`  | `0.25`  | Max badge diameter                                                  |
| `--color`  | auto    | Force `red`, `light`, or `dark`                                     |
| `--calm`   | `12`    | Grayscale std-dev still counted as calm; raise for textured backdrops |
| `--at`     | auto    | Force badge center, e.g. `--at 0.74,0.53`                           |

If the head faces or leans left, the negative space is probably on the left: use `--face-x 0.62`.

### 4. Review

Read `preview.png` and judge it against the look above. The badge sits in plain background that makes it pop — clear of shoulder, collar, hair, and busy patches — and shows whole in the circle. Brand red is the default to aim for; accept monochrome only when red would blend in. Adjust knobs and recompose until it does, then show the person the preview and iterate on their feedback.

### 5. Set it on the account

Hand this step to the person — Google's photo picker opens a native file dialog, and there's no API for a non-admin to set their own photo:

1. Open <https://myaccount.google.com/personal-info> signed in as the scriptura.org account (check the avatar menu — personal Gmail is a common wrong account).
2. _Profile picture_ → _Upload from device_ → choose `profile-scriptura.jpg`.
3. In the crop step keep the full circle so the badge isn't cut, then _Save as profile picture_.

It propagates to Gmail, Chat, Meet, and Calendar within minutes.
