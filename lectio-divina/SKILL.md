---
name: lectio-divina
description: >
  Generate a 30-minute lectio divina guide with somatic grounding, a scripture passage,
  phase-specific spiritual questions, a sharing invitation, and a closing prayer.
  Accepts optional passage criteria and Bible translation — defaults to lectio divina-appropriate
  passages and NRSVue. Output is a markdown code block ready to copy/paste.
---

# /lectio-divina

Generate a complete 30-minute lectio divina guide as a single markdown code block.

## Arguments

Parse from `$ARGS` (freeform text after the skill name). Extract:
- **passage** — what kind of passage to select. Default: `passages that are good for lectio divinas`
- **translation** — Bible translation to use. Default: `NRSVue`

Examples:
- `/lectio-divina` — uses all defaults
- `/lectio-divina passage="a jesus narrative appropriate to maundy thursday"  translation="First Nations Version"`
- `/lectio-divina passage="a psalm of lament" translation="The Message"`
- `/lectio-divina passage="beatitudes"`

---

## What lectio divina is

Lectio divina ("divine reading") is a contemplative Christian practice of slow, prayerful scripture reading. It has four phases:

1. **Lectio** (Read) — Read the passage slowly, 2–3 times aloud. Listen for a word, phrase, or image that shimmers or catches attention.
2. **Meditatio** (Meditate) — Sit with that word or phrase. Let it interact with your thoughts, memories, questions, longings.
3. **Oratio** (Pray) — Respond to what arose. What do you want to say to God? Move from reflection into prayer.
4. **Contemplatio** (Contemplate) — Release words. Rest in God's presence. Simply be.

Good passages for lectio divina are:
- Narrative scenes with emotional texture (encounters, healings, calls, meals)
- Short enough to hold in mind (roughly 10–20 verses max)
- Rich in imagery and detail
- Open enough to invite personal resonance without being abstractly doctrinal

---

## Bible.com version IDs

Use these to construct passage links (`https://www.bible.com/bible/{id}/{book}.{chapter}.{verse}`):

| Translation | ID |
|---|---|
| NRSVue | 2016 |
| First Nations Version (FNV) | 1660 |
| NRSV | 37 |
| ESV | 59 |
| NIV | 111 |
| The Message | 97 |
| CEB | 37 |
| NKJV | 114 |
| KJV | 1 |
| NLT | 116 |

If the translation is unknown, use NRSVue (2016) and note the link may need adjustment.

Book abbreviations for bible.com URLs use standard abbreviations (e.g., `JHN`, `LUK`, `MRK`, `MAT`, `ROM`, `PSA`).

---

## Steps

### 1. Select a passage

Choose a passage that fits the **passage criteria** from the args (or the default).

If the criteria references a liturgical occasion (e.g., Maundy Thursday, Advent, Lent), pick a passage traditionally associated with that moment. For Maundy Thursday specifically: consider John 13 (foot washing), Luke 22:14–30 (last supper), or John 17 (high priestly prayer).

**Passage length:** Target 3–6 verses (roughly 50–150 words) — short enough to read aloud in under a minute, so it can be repeated 2–3 times without crowding out reflection. A brief scene, parable, or saying from the Gospels is ideal. Avoid passages over 200 words; longer passages shift the practice toward study rather than contemplation.

### 2. Craft phase-specific spiritual questions

Write 2–3 questions for each lectio divina phase that are:
- Specific to the **content and texture** of the chosen passage (not generic)
- Appropriate to the **depth and tone** of that phase
- Open and inviting, not leading or theological-lecture-y

**Lectio questions** — help participants notice what's alive in the text:
> "What word, image, or moment caught your attention as you listened?"

**Meditatio questions** — help them sit with it personally:
> "Where does this scene touch something in your own life right now?"

**Oratio questions** — invite honest response to God:
> "What do you want to say to God in response to what you've received?"

**Contemplatio** — no questions; this phase is silent rest.

### 3. Generate the guide

Output the complete guide as a single fenced markdown code block (` ```markdown ... ``` `). Include:

- **Title** — "Lectio Divina: [Passage Reference]"
- **Occasion / Theme** (if relevant)
- **Somatic grounding exercise** — 2–3 minutes; feet on floor, breath, body scan, releasing the noise of the day into God's hands. Gentle and non-clinical in tone.
- **Invitation to presence** — a brief spoken invitation (2–3 sentences) to open the heart and quiet the mind.
- **The passage** — the full passage text in the chosen translation, formatted clearly.
- **Lectio phase** (~5 min) — instructions + phase-specific questions
- **Meditatio phase** (~8 min) — instructions + phase-specific questions
- **Oratio phase** (~7 min) — instructions + phase-specific questions
- **Contemplatio phase** (~5 min) — instructions, no questions; invite silence
- **Bible.com link** — link to the passage in the chosen translation on bible.com
- **Sharing invitation** — gentle invitation to share if they wish; name one specific person to go first (use "the person to your left" or a placeholder like [Name] if no names are known)
- **Closing prayer** — written out in full; 3–5 sentences; warm, grounded, not overwrought

### 4. Timing

The full arc should fit 30 minutes:
- Grounding + opening: ~3 min
- Reading aloud (3 passes): ~4 min
- Lectio reflection: ~3 min
- Meditatio: ~8 min
- Oratio: ~5 min
- Contemplatio: ~4 min
- Sharing + closing: ~3 min

Include approximate timing markers in the guide (e.g., `*(~5 minutes)*`).

---

## Output format

Output a single fenced markdown code block. The content inside should be clean, copy-paste-ready markdown — no meta-commentary before or after. Just the block.
