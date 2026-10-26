# Step 3 · A tool and a leash

Now the agent can make the picture. A tool is a function the model may ask for. The harness runs it.
A model that can call a tool can call it forever: one more try for a better sky. Every image costs money.
So the harness holds a leash: 3 images per request, 6 tool calls per run.

Agno has a `tool_call_limit`. Read its source: it skips the tool and tells the model not to try again, then keeps looping.
If the model does not listen, the loop never ends. So our hook stops the run itself. The harness owns the stop.

The picture phase only gets the image prompt. The headline never reaches the image model, so words never get drawn.

## The slot

- `launchkit/harness/tools.py` · `generate_image`. Today it returns "not built".
- `launchkit/harness/limits.py` · `make_leash`. Today the hook just passes the call through.
- `launchkit/harness/agent.py` · `build_picture_agent`. Today it returns None, so the picture phase is skipped.

## Break it first

Before you paste the card, run this and keep the output:

```
LAUNCHKIT_IMAGE_PROVIDER=placeholder uv run launchkit run harbor "Poster for the Tidal bottle on a misty lakeshore at dawn." --model fake:endless
```

```
  picture   skipped, the image tool is step 3
```

No picture at all yet. The leash only matters once there is a tool to call, so this step breaks it after the build (below).

## Prompt card, for your coding agent

```
In launchkit/harness/tools.py, make generate_image(image_prompt) call
images.generate(image_prompt, colours) and return {"file": str(path)}.
The docstring is what the model reads: it says the picture contains no words.

In launchkit/harness/limits.py, implement make_leash(limits, trace). It returns an Agno
tool hook with the signature (function_name, function_call, arguments). Count every call.
When the count passes limits.step_cap, record trace.stop(...) and raise
agno.exceptions.StopAgentRun. When generate_image is asked more than limits.image_budget
times, do not call it; record trace.refused(...) and return
{"status": "refused", "reason": "image budget of 3 spent"}. Otherwise call the function,
record trace.tool(name, arguments, result), and return the result.

In launchkit/harness/agent.py, build_picture_agent returns an Agent with
system_message=PICTURE_TASK, tools=[make_generate_image(images, colours, trace)] and
tool_hooks=[make_leash(settings.limits, trace)].
```

## Prove it

```
uv run launchkit check 3
```

- The endless fake stops at the step cap.
- A 4th image call against a budget of 3 is refused.
- The image prompt sent to the adapter never contains the headline.

## Run it again

The same command after the build:

```
  tool      generate_image("the same lakeshore, better sky, try 1") → file data/outputs/poster-…-1.png
  tool      generate_image("the same lakeshore, better sky, try 2") → file data/outputs/poster-…-2.png
  tool      generate_image("the same lakeshore, better sky, try 3") → file data/outputs/poster-…-3.png
  refused   generate_image: image budget of 3 spent
  refused   generate_image: image budget of 3 spent
  refused   generate_image: image budget of 3 spent
  stop      step cap of 6 tool calls reached, run ended
```

Now take the leash off. In `agent.py`, comment out the `tool_hooks=[make_leash(...)]` line in `build_picture_agent` and run the same command. It never stops: hundreds of placeholder pictures in seconds, until Ctrl-C. With a real image model, each one is paid. Put the line back and delete `data/outputs`.

## Why it matters

Spend has a ceiling the model cannot talk its way past. The harness owns the stop, because Agno's `tool_call_limit` does not end the loop.

## See it

Send a Harbor request with the real model. A picture appears in the poster panel after a few seconds.
To see the leash fire, in the terminal: `LAUNCHKIT_IMAGE_PROVIDER=placeholder uv run launchkit run harbor "Poster for the Tidal bottle" --model fake:endless`: three pictures, three refusals, then "stop".

## Stuck?

The answer is on the branch `session-01-harness-step3`.
