# Step 1 · Tools: one tool, then a toolbox

Maya: "Love the poster. Now all the sizes, please." The main agent has two tools, `get_brand_details` and `generate_image`. Neither can resize.

A tool is a function the model may ask for. The model sees only its name, its inputs and its description; Agno builds them from the Python function, its type hints and its docstring. The model replies with a call, the harness runs the function, and the result goes back to the model. So one tool use costs two model calls.

The harness binds the approved poster, the same way Session 1 bound the workspace in `get_brand_details`. The model never names a file.

## The slot

- `launchkit/harness/picture_tools.py` · `PictureDesk.centre_crop`. Today it is marked `@todo`, so it stays out of the catalogue.
- Move 2: `detect_focal_point`, `crop`, `expand_canvas` and `scale`, in the same class. Also marked `@todo`.

## Break it first

```
uv run launchkit main harbor "Love the poster. Now all the sizes, please." --model fake:tools
```

```
reply
I cannot resize the approved poster. I only have get_brand_details and generate_image. ...
```

## Prompt card 1, for your coding agent

```
In launchkit/harness/picture_tools.py, build PictureDesk.centre_crop(width, height).
Remove its @todo. Open the approved poster with self.open(), take
centre_window(img.size, (width, height)), crop to it, resize to (width, height) and
save with self.save(img, "centre"). Return {"file": path, "size": "WxH",
"window": [left, top, right, bottom]}. Its docstring is what the model reads: say it
cuts the approved poster to a new size from its centre, and that it is plain code.
```

Run it: every size comes back. Then look at the web banner (1200×628): the bottle's base is cut off. The tool did exactly what it was told. It has one way to work.

## Prompt card 2, for your coding agent

```
In the same class, build four more tools and remove their @todo marks.
detect_focal_point(): if self.box is None, set it to find_subject(self.source,
self.model) and record trace.note("detect_focal_point asked the vision model once:
box ..."). Return {"box": self.box}. The docstring says it finds the main subject,
here the bottle, and that it asks a vision model, so it costs money.
crop(width, height, left, top, right, bottom): cut that window and resize it to
(width, height). Return {"file", "size", "window"}.
expand_canvas(width, height, colour): fit the whole poster inside (width, height)
without cutting, centred, and fill the new space with colour_of(colour, self.colours).
scale(width, height): stretch the poster to (width, height).
In entries(), drop the centre_crop line: the one tool is now split into these four.
```

## Prove it

```
uv run launchkit check tools1
```

- `centre_crop` makes every Harbor size, and cuts the bottle in the web banner only.
- `detect_focal_point` finds the bottle and asks the model once.
- `crop` cuts the window it is given; `expand_canvas` keeps everything and adds bars in the brand colour; `scale` stretches.
- The four tools join the catalogue, and `centre_crop` leaves it.

## Run it again

Ask for all the sizes again on the real model, with the four new tools, on the chat page. Start `uv run launchkit ui`, sign in as Maya at Harbor, press **New conversation** and send "Love the poster. Now all the sizes, please." Leave **Model** empty for the real model; type `fake:tools` there for the fake. The sizes show in the chat, and each tool call shows in the Trace tab. After each `git checkout`, restart `launchkit ui`: it does not reload code.

Watch the trace: the model drives them a different way on each run. It picks `scale` and squashes the bottle, crops before it finds the bottle, or adds bars where a crop was fine. Each tool did its job. Nobody told the model which one to use, in what order, or when the result is good enough.

## Stuck?

The answer is on the branch `session-02-tools-step1`.
