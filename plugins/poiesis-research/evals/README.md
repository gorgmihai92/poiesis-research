# Eval cases

Six cases for `claude plugin eval`, each a mistake this plugin's rules exist to prevent. Three come from the two
recorded runs of 2026-11-17: a share with different document types on its two sides, a verdict that drifted when it
was retyped, and a step that was improvised.

| Case | Passes when |
|---|---|
| `share-same-types` | a share of articles over all works is refused, and the same-type share is given |
| `not-found-is-not-new` | an empty search with one database refusing is not written up as novelty |
| `rows-copied-not-retyped` | an agent's rows and verdict come back unchanged |
| `no-silent-improvisation` | a step with no playbook or script is named as missing, with the choices |
| `signal-is-an-observation` | a signal note records what was seen and no reading of it |
| `read-level-is-stated` | a note from an abstract says "abstract only" and gives no page |

Run from the plugin's folder. **Each run is a real model call**, and each `llm` grader calls a judge model:

```
claude plugin eval . --no-publish --max-cost-usd 5
claude plugin eval . --case share-same-types --no-publish
```

Without `--no-publish` the command publishes its report to claude.ai when your account allows it; with it the
report stays in `evals/results/`. `--max-cost-usd` stops the run at a ceiling.

Every case asks for one run (`runs: 1`), so a first pass is six runs with the plugin and six without, plus the
judges. `--runs 3` gives a steadier score. The cases need only the read-only tools they list; the prompt carries
everything the task needs, because each run starts in an empty folder.

Before the first run, sign the Claude command line in once with `claude auth login`. It uses your Claude
subscription unless you pass `--console`. The runs are separate `claude` sessions, so a sign-in in the desktop app
does not reach them. The cost the command prints is an estimate at list price.

The format follows the blank case that `claude plugin eval init --bare` writes and the reference in the Claude
Code documentation ("Test plugins with evals"), read on 2026-11-21. No case has been run yet. One attempt on
2026-11-21 stopped at sign-in, before any run; the case it tried, `share-same-types`, loaded with its four graders.
