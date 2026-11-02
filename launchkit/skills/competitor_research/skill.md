# competitor_research

Pick me when: the job is to find out how competitors are launching, selling or advertising their products.

1. List every competitor the request names.
2. Call run_tool once with name "research_many" and inputs {"briefs": ["How is <competitor> launching bottles this season (<month year>)? ...", ...]}: one brief per competitor, each a plain sentence, not an object, all in one call. Each brief stands alone, because the research agent sees nothing else and has no clock: put this month and year from today's date in it. "How is <competitor> launching bottles this season (<month year>)? Give their message (the launch line), their channels and what to avoid copying. Never repeat these claims: eco-friendly, sustainable, unbreakable, lifetime guarantee, cold forever, fully dishwasher-safe, or anything about recycling, carbon or certifications."
3. For each competitor, write one paragraph from its report, with the addresses it used.
4. Never repeat a claim from a report that our never-say list bans.
5. Answer as a reply with the paragraphs, never as a poster.
