# Lesson reporter (opt-in prototype)

**[← Back to the overview](../../README.md)** · Off by default · Status: prototype

**Off by default** (`defaultEnabled: false`) and **local only**: it writes a redacted package to an outbox in its
own data folder and never sends anything. Full design, including what a future transport would look like:
`docs/lesson-reporter/SPEC.md` (repo root).

What it packages: structured lesson entries, diffs of the engine's own tools (`tools/`, `checks/`, `review/`)
and method notes - nothing else. It refuses pictures, meshes, scenes, arrays, binaries, anything from `cases/` or
`eval/`, secrets (never echoed), invisible characters, quoted conversation, text aimed at an AI, markup and
embedded data; it redacts paths, the user's names, machine name, git identity, e-mail and case names; then it
checks the finished package for leaks again.

Switching reporting on for an engine and approving a package both need the person at their own console: the
script shows a one-time code on the console device and reads the keystrokes from it, never from stdin, so an
agent's shell cannot do either (SPEC section 14, finding F1: the first version trusted `isatty()`, which an
agent's shell passed on Windows).

| Path | What |
|---|---|
| `skills/lesson-reporter/SKILL.md` | instructions for the agent (`disable-model-invocation: true`: only the user starts it) |
| `scripts/lesson_reporter.py` | the prototype, Python stdlib only, no network or process modules |
| `schema/lesson.schema.json` | the lesson schema (JSON Schema 2020-12) |
| `examples/lessons.example.json` | two example lessons (a judgment lesson and a check) |
| `tests/test_lesson_reporter.py` | 49 tests: consent, redaction, refusals, outbox, approval, no-network |

```bash
python -m unittest discover -s plugins/lesson-reporter/tests
```

## Install

```
/plugin install lesson-reporter --marketplace dirtcodevet/self-improving-engines
```

It installs switched off. Reporting is turned on per engine, at your own console.
