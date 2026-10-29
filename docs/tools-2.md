# Step 2 · Skills: write the know-how down

Maya: "All the sizes" again. The four tools work, but the results change from run to run: a squashed bottle, a stretched crop, bars where none were needed. The tools know how to act. They do not know which one to use, in what order, or when to stop.

A skill is a how-to file the agent reads only when it needs it. It bundles tools with a plan: which tools, in what order, what to do in each case, and how to judge the result. The prompt lists each skill in one line; `run_skill` loads the whole file.

Ready-made, with its moment: `check_copy`, a tool the agent can call while it works ("Shorter headline, please"), and the `on_brand_copy` skill, which moves the copy rules out of the prompt into a file.

## The slot

- `launchkit/skills/resize_image/skill.md`. It does not exist yet.
- `launchkit/harness/picture_tools.py` · `window_around`, the bottle-box fit rule. Today it is marked `@todo` and returns None, so `crop` still needs a window.

## Break it first

```
uv run launchkit main harbor "Love the poster. Now all the sizes, please." --model fake:tools
```

```
  tool      scale(1080, 1080) → file data/sizes/tidal-poster-scaled-1080x1080.png
  ...
```

The fake picks `scale` every time and squashes the bottle. On the real model the pick changes from run to run.

## Prompt card, for your coding agent

```
Create launchkit/skills/resize_image/skill.md, in plain words, no code.
First line "# resize_image". Then:
"Pick me when: the approved poster must go out in other sizes, e.g. all the sizes."
"Uses: detect_focal_point, crop, expand_canvas"
"Hides: crop, expand_canvas, scale, detect_focal_point (prefer_over)"
Then numbered steps: take the sizes from the brand's placements; call
detect_focal_point once; for each size call crop with only width and height, so it
cuts around the product; if crop says the product does not fit, call expand_canvas
with that size and the brand's main colour; check every result says the product is
whole. Never call scale to change the shape.

In launchkit/harness/picture_tools.py, build window_around(box, size, target, margin)
and remove its @todo. Take the biggest window of the target's shape that fits in the
picture, centre it on the box, and push it back inside the picture. Return it as
(left, top, right, bottom) if it holds the whole box plus the margin on every side,
else None. Plain code, no model: it gives the same answer every time.
```

## Prove it

```
uv run launchkit check tools2
```

- The skill says when to pick it, names its tools, never scales, and hides the raw tools.
- The fit rule keeps the bottle whole in every Harbor size, and says no when a shape is too thin.
- `crop` with no window cuts around the bottle.
- Asked for all the sizes, the main agent loads `resize_image`, finds the bottle once, and every size keeps it whole.
- Ready-made: `check_copy` catches long words and banned claims.

## Run it again

The same ask on the real model. Every size, bottle whole, the brand's sizes only. On this poster the bottle fits every Harbor size, so every size is a crop around it; the bars are the safety net for a shape the bottle cannot fit. The tools are the same as in step 1. What is new is the skill file and the fit rule.

## Stuck?

The answer is on the branch `session-02-tools-step2`.
