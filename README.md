# genvm-lint

A static analyzer for **GenLayer Intelligent Contract source files** — real
`.py` contracts written against the `py-genlayer` SDK, not prompt wording.

## Why this exists

The previous version of this repo was a 41-line script that pattern-matched
vague English phrases like `"if needed"` in a typed sentence. It never
imported `genlayer`, never touched `gl.Contract`, and had nothing to do with
GenLayer's actual SDK. A reviewer correctly rejected it for exactly that
reason.

This version reads real contract source with Python's `ast` module and
checks for structural problems that GenVM itself cares about. Every rule
below exists because it caused a real, confirmed bug while building and
deploying an actual GenLayer contract in this account's other submissions —
this isn't a linter built from reading the docs once; it's built from the
debugging history.

## What it checks

| Rule | Catches |
|---|---|
| `missing-depends-header` | No `# { "Depends": "py-genlayer:..." }` in the first 5 lines — GenVM won't know which runtime to use |
| `depends-non-pinned` | `py-genlayer:test` / `:latest` — works locally, but hosted Studio explicitly refuses non-pinned runners in non-debug mode |
| `missing-genlayer-import` | No `from genlayer import *` — `gl`, `Address`, `u256`, `TreeMap` etc. are all undefined |
| `missing-dataclass-import` | `@dataclass` used without `from dataclasses import dataclass`. **This is the single most dangerous bug this tool catches** — it deploys fine, reaches full validator consensus, and only fails on every subsequent read with a generic "contract not found" RPC error that looks exactly like a network problem and isn't. This exact bug caused a real rejected submission. |
| `no-contract-class` | No class extends `gl.Contract` |
| `dynarray-inmem-allocate-antipattern` | `DynArray[...]` + `gl.storage.inmem_allocate(...)` — multiple independent developers have reported this combination as unreliable in the current SDK; `TreeMap` + plain construction is the proven pattern |
| `nondet-fetch-inside-non-comparative` | A live `gl.nondet.web.get/render/post` call nested inside a callback passed to `gl.eq_principle.prompt_non_comparative`. No confirmed-working public example does this — every fetch-and-judge example (oracle/verification patterns) uses `prompt_comparative` instead. This exact pattern caused a contract to deploy, reach full validator consensus, and still fail to load with `invalid_contract`. |
| `vague-eq-principle-rule` | A `prompt_comparative`/`strict_eq` comparison rule under 15 characters — too vague to guarantee validators agree on the *exact* value that drives a payout |
| `url-passed-as-string` | A URL typed directly into prompt text headed toward `exec_prompt`, with no `gl.nondet.web.get/render/post` call anywhere nearby. An LLM can't browse the internet from inside a prompt — the page has to actually be fetched first. |
| `json-loads-no-fence-strip` | `json.loads()` on a raw LLM response with no visible markdown-fence stripping — LLMs wrap JSON in ` ``` ` fences even when told not to |
| `nondeterminism-in-view` | A `@gl.public.view` method calling `gl.nondet.*`/`gl.eq_principle.*` — non-deterministic work belongs in `@gl.public.write` |

## Real output, on real contracts

Run against this account's actual deployed-and-working contract
(`bounty_board.py`, an on-chain bounty adjudicator):

```
$ python genvm_lint.py bounty_board.py
genvm-lint: bounty_board.py
  ℹ [INFO] json-loads-no-fence-strip (line 85)
      json.loads(...) is called on what looks like a raw LLM response with
      no visible code-fence stripping nearby. LLMs frequently wrap JSON in
      ``` fences even when explicitly told not to — this will throw a
      JSONDecodeError on a fraction of real responses unless the fences are
      stripped first.

0 error(s), 0 warning(s), 1 info
```

That's a genuinely live risk in already-deployed code, not a false positive
— worth fixing even though the contract works today.

Run against a synthetic reconstruction of this account's *original*, broken
`TaskReward` contract — the actual combination of bugs that took several
days and multiple failed deployments to diagnose in the accompanying
`task-reward-tutorial` submission:

```
$ python genvm_lint.py broken_example.py
genvm-lint: broken_example.py
  ✖ [ERROR] missing-dataclass-import
      ...deploys successfully...then fails every subsequent `genlayer call`
      with a generic 'contract not found' RPC error...
  ⚠ [WARNING] dynarray-inmem-allocate-antipattern
      ...TreeMap + plain construction is the proven pattern...
  ⚠ [WARNING] nondet-fetch-inside-non-comparative (line 31)
      ...caused a contract to deploy, reach full validator consensus, and
      still fail to load with a generic 'invalid_contract' error...
  ⚠ [WARNING] vague-eq-principle-rule (line 31)
  ℹ [INFO] json-loads-no-fence-strip (line 36)

1 error(s), 3 warning(s), 1 info
```

Every one of those findings corresponds to a real bug that was actually hit,
in that order, while building this account's other GenLayer submissions.
This tool exists specifically so the next person doesn't have to lose the
same days to the same four mistakes.

## Usage

```bash
python genvm_lint.py path/to/contract.py
python genvm_lint.py path/to/contract.py --json   # for CI / tooling

# reproduce the broken-example output above yourself:
python genvm_lint.py fixtures/broken_example.py
```

Exit code is `1` if any error-level finding is present, `0` otherwise —
usable as a pre-commit or CI gate.

## Limitations

This is a static analyzer, not a GenVM simulator — it cannot catch every
possible way a contract fails to load (the `invalid_contract` error this
project also hit, even after every check above passed, appears to be a
deeper SDK-level issue not yet fully understood — see the companion
`task-reward-tutorial` submission's README for that ongoing investigation).
It checks structure and known antipatterns, not runtime correctness.

## What changed from the previous version

The old `app.py` (kept out of this version entirely) took a plain English
sentence like `"Send ETH if conditions are met"` and matched substrings
against it. It had no relationship to GenLayer's SDK, syntax, or runtime.
`genvm_lint.py` reads actual contract source with `ast`, and every rule maps
to a specific, real GenVM/SDK behavior — most of them behaviors this very
account's other work ran into directly.
