# Where the workspace files come from

Harbor's and Ember's files are written by hand in this repo so the build has something to read.
For a real brand they are drafted at onboarding, from the brand pack, and a human owns them from then on.

## How it works

1. A marketer uploads the brand pack as a PDF. The file is stored under `workspaces/<id>/assets/`.
2. The harness pulls the text out of the PDF and hands it to the model with a form to fill: `BrandProfile`
   (brand name, voice, rules, banned claims, colours, facts). Same pattern as the poster: the model fills a form, code checks and writes.
3. Code renders `SOUL.md`, `AGENTS.md`, `rules.yaml` and `facts.md` from the form, and `brand-book.md` from the text.
4. The marketer reads and edits the files. Nothing in Python changed. A new brand is a new folder.

The workspace id must match the allow-list (`[a-z0-9-]`, up to 32 characters), the same rule step 4 enforces on every request.

## Try it

In the chat page press "Onboard a brand", give an id and a PDF. Or in the terminal:

```
uv run launchkit onboard moss samples/harbor-brand-pack.pdf --model fake:profile
uv run launchkit onboard harbor-2 samples/harbor-brand-pack.pdf        # real model, needs a key
uv run launchkit check onboard
```

With `fake:profile` the files are drafted from a fixed form, so you can see the shape without a key.
