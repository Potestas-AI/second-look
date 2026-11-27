# Proofs

The scripted stand-ins and configurations behind FINDINGS.md. Each returns fixed, harmless replies, so you can
watch how a tool grades a reply without any AI model being tested.

| File | What it is |
|---|---|
| `scripted_target2.js`, `promptfoo_contract_proof.yaml` | One sentence, wrapped six ways. Run with `promptfoo eval -c promptfoo_contract_proof.yaml`. |
| `promptfoo_make_twelve_checks.py` | Writes the provider, the replies and the config for the twelve-check run, the tool-call cases and the planted rule. |
| `garak_scripted_replies_1.py`, `garak_scripted_replies_2.py` | Functions for garak's `function` generator, for example `--target_type function --target_name "garak_scripted_replies_2#r_no"`. |
| `garak_scripted_replies_3.py` | Ordinary words that contain a phrase from garak's lists: `p_has_any`, `p_was_an`, `m_no_ethics`. Use `--probes phrasing.PastTense` for the first two. |
| `promptfoo_real_pressure_run.py`, `promptfoo_real_wider_run.py` | Real models with a real money tool. The second is the nine-model run behind `samples/promptfoo_real_answers.json`. |
| `giskard_controlled_proof.py` | The same replies through Giskard's `Conformity` check. |

Versions: promptfoo 0.126.0, garak 0.17.0, Giskard 3.0.1. The promptfoo and Giskard runs need a grading model; we used claude-haiku-5-5.
