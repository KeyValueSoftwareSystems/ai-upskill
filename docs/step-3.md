# Step 3 · A tool and a leash

Now the agent can make the picture. A tool is a function the model may ask for. The harness runs it.
A model that can call a tool can call it forever: one more try for a better sky. Every image costs money.
So the harness holds a leash: 3 images per request, 6 tool calls per run.

Agno has a `tool_call_limit`. Read its source: it skips the tool and tells the model not to try again, then keeps looping.
If the model does not listen, the loop never ends. So our hook stops the run itself. The harness owns the stop.

The picture phase only gets the image prompt. The headline never reaches the image model, so words never get drawn.

## The slot

- `launchkit/harness/tools.py` · `render_image`. Today it returns "not built".
- `launchkit/harness/limits.py` · `make_leash`. Today the hook just passes the call through.
- `launchkit/harness/agent.py` · `build_picture_agent`. Today it returns None, so the picture phase is skipped.

## Prompt card, for your coding agent

```
In launchkit/harness/tools.py, make render_image(image_prompt) call
images.generate(image_prompt, colours) and return {"file": str(path)}.
The docstring is what the model reads: it says the picture contains no words.

In launchkit/harness/limits.py, implement make_leash(limits, trace). It returns an Agno
tool hook with the signature (function_name, function_call, arguments). Count every call.
When the count passes limits.step_cap, record trace.stop(...) and raise
agno.exceptions.StopAgentRun. When render_image is asked more than limits.image_budget
times, do not call it; record trace.refused(...) and return
{"status": "refused", "reason": "image budget of 3 spent"}. Otherwise call the function,
record trace.tool(name, arguments, result), and return the result.

In launchkit/harness/agent.py, build_picture_agent returns an Agent with
system_message=PICTURE_TASK, tools=[make_render_image(images, colours, trace)] and
tool_hooks=[make_leash(settings.limits, trace)].
```

## Prove it

```
uv run launchkit check 3
```

- The endless fake stops at the step cap.
- A 4th image call against a budget of 3 is refused.
- The image prompt sent to the adapter never contains the headline.

## See it

Send a Harbor request with the real model. A picture appears in the poster panel after a few seconds.
Then pick the model `fake: endless`: three fake pictures, three refusals in red, then "stop".

## Stuck?

The answer is on the branch `session-01-harness-step3`.
