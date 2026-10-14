# Words we use

| Word | Meaning |
| --- | --- |
| Copy | The words on an ad. Poster copy is the headline, the subheadline and the body text. The picture is separate. A copywriter writes copy. |
| Model | The language model. You send text, it returns text. It knows nothing about Harbor and remembers nothing between calls. |
| Harness | The code around the model. It decides what the model reads, what it may do, when it stops, and whether its answer is good enough. The model proposes. The harness decides. |
| Agno | The Python library that gives us the engine: the loop, tool calling, sessions. Product rules stay in our own code. |
| Workspace | One folder per customer. Harbor has one, Ember has one. Plain text files in it tell the agent who it is and what the rules are. |
| Spec | Our name for the form the model must fill: headline, subheadline, body, image prompt, format. The general idea is structured output: code can check a form, not prose. Agno does it with `output_schema`. |
| Tool | A function the model may ask the harness to run. The harness runs it and gives the result back to the model. |
| Step | One turn of the loop: the model answers, or asks for a tool. A run is many steps until the model says it is done, or the harness stops it. |
| Budget | A cap the harness enforces. A step cap. An image budget. A size per section of the prompt. |
| Trace | The list of what happened in one run: files read, model calls, tool calls, refusals, checks, the stop reason. Every check reads it. |
| Context | Everything the model sees on one turn. We build it in a fixed order with a size per part. |
| Token | The unit the model bills in. About three quarters of a word. Cost is tokens times a price. |
| Fake model | A stand-in for the real model that returns a scripted answer. Free, instant, and it lets a check prove the harness without a key. |

## The story

**LaunchKit** is a marketing assistant. Brands are its customers. A marketer types a request, and LaunchKit answers with the poster's words (the copy) and the poster's picture, both following that brand's rules.

**Harbor** sells outdoor drinkware. **Tidal** is Harbor's new insulated bottle, and "the Tidal launch" is the campaign for it. **Ember Coffee Co.** is the second customer: same software, different voice and rules.
