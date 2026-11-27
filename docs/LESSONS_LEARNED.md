# Lessons Learned

Problems found while auditing, hardening and evaluating this codebase, and the rule each
one left.

## Backend and data

| What happened | Cause | Rule |
|---------------|-------|------|
| Audit events were never saved | The middleware used its own session and never committed | A session you open, you commit |
| A fast worker could update zero rows | The job was enqueued before the request committed | Commit, then publish |
| A queue outage left runs `pending` forever | Nothing marked them failed | Every exit path sets a final status |
| A timed-out job stayed `running` | Cancellation is not an `Exception`, so the handler missed it | Handle cancellation explicitly |
| Async endpoints stalled under load | Blocking calls ran on the event loop | Move blocking work to threads |
| Queue depth metric was meaningless | `inc()` and `dec()` ran in two different processes | Read shared state when scraped |
| Metric cardinality grew without limit | Raw paths with UUIDs were used as labels | Label with route templates |
| Cached runs could cross tenants | Cache keys had no organization | Scope every key by tenant |
| Duplicate Kafka events inflated profiles | Counters updated even when the insert was skipped | Update counters only for rows actually inserted |

## Security

| What happened | Cause | Rule |
|---------------|-------|------|
| Production could start with a default JWT secret or PII salt | Only a warning was logged | Fail fast on insecure defaults |
| Static analysis flagged API key hashing | SHA-256 looked like password hashing | Fast hashes suit random 256-bit keys, not passwords; record why |

## Tests and CI

| What happened | Cause | Rule |
|---------------|-------|------|
| CI integration tests ran against an empty database | No migration step | CI must build the schema it tests |
| Tests failed with "attached to a different loop" | Module-level pools outlived each test's event loop | Release pools after every test |
| An auth test got 200 instead of 401 | The setting is read at import; changing the env var later did nothing | Patch the value the code actually reads |
| The type check passed locally and failed in CI | CI resolved newer library stubs | Check against the environment CI uses |
| An SDK upgrade could break every simulation | A newer SDK drops an argument the client sends, and the version range allowed it | Cap a dependency at the release that breaks you, and tell the bot too |

## Evaluation

| What happened | Cause | Rule |
|---------------|-------|------|
| The persona looked worse than random | The prompt asked about buying; the data measured clicks | Ask about the outcome you measure |
| The first comparison mixed two changes | The baseline differed from the persona in both persona and wording | Change one thing per comparison |
| Many tests couldn't be ranked | Scores fell on a few values, with many ties | Report ties, not just accuracy |
| Old tests had unreliable randomization | A caching problem at Upworthy in 2013 | Read the dataset's corrections before using it |
| A local model crashed under GPU pressure | The model didn't fit in 8 GB | Record crashes and retries; never drop them silently |
| An early lead for the persona disappeared | At 57 tests the click-worded persona led by 5 points; at 200 it trailed by 7 | Decide the sample size before the run and don't draw conclusions mid-run |
| Results risked being overwritten by reruns | One output path per model | Save each run separately, with prompt fingerprints |

## Documentation

| What happened | Cause | Rule |
|---------------|-------|------|
| The README described features the code didn't have | It followed the plan, not the code | Check claims against the code before publishing |
| Schedules and ports in the docs were wrong | Copied from older versions | Quote values from the source, not from memory |

## Product lesson

A convincing demo can hide a missing link. Ingestion, features and inference each work,
but the path users click through does not connect behavioral data to the prompt. And a
persona that sounds right can still pick winners no better than chance. Test the
end-to-end claim against real outcomes, not only each layer.
