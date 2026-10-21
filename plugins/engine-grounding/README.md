# Engine grounding

**[← Back to the overview](../../README.md)** · Companion to [recursive improvement](../recursive-improvement/) · Status: on trial

Keeps an engine's output grounded in evidence. It supplements `recursive-improvement` and an engine's own skill,
and never replaces either: where they disagree, they win.

| | Items |
|---|---|
| **Where values come from** | G1 concepts before the first example · G2 one record, every value with its source · G3 ranked evidence for what the input doesn't show · G4 propose, pick, check · G5 references are evidence, not authority · G14 case values live in the case's files, never in engine code |
| **Proving a change** | G6 a baseline before changing working code · G7 tuned values carry their case · G8 contamination audit · G9 an AI critic supports, it never decides · G10 cheap before expensive · G13 approved work is protected |
| **The person's input** | G11 account for every note · G12 a person's input is evidence, not authority |

Each item is switchable in `flags.json`. `SKILL.original.md` and `flags.original.json` keep the text before G13
and G14 were added, and `references/source-map.md` records where each item came from and what was left out.

## Use it when

- an engine fills in what its inputs don't show;
- it uses reference or AI-made material;
- it is about to change code that already works;
- or it receives a person's review.

## Install

```
/plugin install engine-grounding --marketplace dirtcodevet/self-improving-engines
```

On Claude Code older than 2.1.275, add the marketplace first (`/plugin marketplace add dirtcodevet/self-improving-engines`), then `/plugin install engine-grounding@self-improving-engines`.

It declares a dependency on `recursive-improvement`.
