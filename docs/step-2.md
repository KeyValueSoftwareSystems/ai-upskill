# Step 2 · Check the form, fix it once, then stop

The model proposes. The harness checks. A model can return nine words in a headline, or a banned claim.
Code catches both. We send the errors back once. If the spec is still wrong, we stop with a clear error.
We never ship bad copy, and the picture phase never starts.

You did this once already, in the opener, for a single model call. Now the harness owns it, for every brand and every turn.

The banned claim lives in two files on purpose. The sentence in `AGENTS.md` is for the model: a request.
The list in `rules.yaml` is for the code: a guarantee.

## The slot

- `launchkit/harness/spec.py` · `validate_spec`. Today it returns no errors.
- `launchkit/harness/run.py` · after the copy agent returns. Today errors are ignored.

## Prompt card, for your coding agent

```
In launchkit/harness/spec.py, implement validate_spec(spec, rules) -> list[str].
Return one readable error per problem: headline over 6 words, subheadline over 12,
body over 25, any banned claim from rules["banned_claims"] appearing in the copy,
and the headline or subheadline text appearing inside image_prompt.

In launchkit/harness/run.py, after the copy agent returns a spec: validate it.
If there are errors, record them on the trace with trace.validation(errors, attempt=1),
run the agent once more with repair_message(errors) as the message, and validate again.
Record attempt 2. If errors remain, raise SpecError(errors).
Never start the picture phase with an invalid spec.
```

## Prove it

```
uv run launchkit check 2
```

- The spec validates: headline up to 6 words, subheadline up to 12, body up to 25, no banned claims.
- A malformed spec gets one repair, then a typed error.
- The copy never reaches the image prompt: no image call, and the leaked headline is caught.

## See it

In the chat page pick the model `fake: malformed`. The trace shows check, repair, check, then a red SpecError card. No poster.

## Stuck?

The answer is on the branch `session-01-harness-step2`.
