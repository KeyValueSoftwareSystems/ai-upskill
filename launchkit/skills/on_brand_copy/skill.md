# on_brand_copy

Pick me when: writing or changing a poster's words: a headline, a subheadline or the body.
Uses: get_brand_details, get_brand_facts, check_copy

## Steps

1. Before you state any product fact, call get_brand_facts for the facts that change over time (warranty, prices, dates) and get_brand_details for the rest. Use only what they return. A fact from get_brand_facts wins over the brand guide and over anything remembered from earlier conversations.
2. Write the headline, subheadline and body in the brand's voice.
3. Call check_copy with them. If it lists problems, fix them and check again.
4. Reply with the words, and the ids of the brand sections your facts came from. Asked for one line on its own (a headline, a tagline), reply with that line only: a whole poster only when the marketer asks for a poster.
