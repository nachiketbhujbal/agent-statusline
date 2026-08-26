# Field reference

Ten rows, each fitted to the terminal — see
[INTERNALS.md](INTERNALS.md#width-fitting) for how wrapping and truncation work.

The working rule is that it is easier to delete a field after living with it than
to miss a signal you never knew existed, so anything cheaply derivable is shown until it
proves useless — and things that proved useless *have* been deleted (see the cache bar in
[ADR 0013](adrs/0013-remove-the-cache-warmth-bar.md)).

**Source** — `payload` = the JSON Claude Code pipes in · `transcript` = derived from the
session `.jsonl` · `probe` = a cached subprocess/file read · `ledger` = `cost-ledger.json` ·
`derived` = computed from the others.

Rows appear in the order below, which is `ORDER` in `statusline.py` — sorted by how often
a row answers a question worth asking, not by how the data happens to arrive.

| row | purpose |
| --- | --- |
| `PROJECT` | where you are: directory, git state, session name |
| `MODEL` | what is answering: model, effort, thinking, permission mode, version |
| `CONTEXT` | context window + this session's own token throughput |
| `USAGE` | account-wide rate limits, burn rate, projection |
| `COST` | money |
| `SYSTEM` | machine pressure |
| `TOOLS` | what the session actually did |
| `CACHE` | prompt-cache economics |
| `TOKENS` | token flow, cumulative and for the last turn |
| `TIMING` | where wall-clock time went |

`PROJECT` is first because it answers "where am I?", the question you ask most often and
the one with the worst consequences when you get it wrong.

---

## PROJECT

| field | source | meaning |
| --- | --- | --- |
| `acme-web/services` | payload | project dir, then `/subdir` when the cwd differs from it |
| `+N dirs` | payload | extra workspace dirs added with `/add-dir` |
| `↳repo branch` | probe | git branch. The `↳repo` prefix means the branch belongs to a repo **below** the cwd, not the cwd itself |
| *(branch colour)* | probe | red on `main`/`master`, green on anything else |
| `*` | probe | tracked files modified |
| `⑂wt` | probe | this is a git worktree, not the main checkout |
| `↑N` `↓N` `≡` | probe | commits ahead / behind upstream; `≡` means in sync |
| `(no upstream)` | probe | branch has no tracking branch |
| `stashN` | probe | stash entries |
| `no git` | probe | the directory is not a repository |
| `“session name”` | payload | the session's title, when it has one |

## MODEL

| field | source | meaning |
| --- | --- | --- |
| `Opus 5:high` | payload | model display name : reasoning effort level |
| `think` / `no-think` | payload | extended thinking on or off |
| `fast off` / `FAST ON` | payload | fast mode. Shown even when off, red when on, because silence would hide it |
| `auto` | transcript | permission mode — see the colour table below |
| *(style name)* | payload | output style, hidden when `default` |
| *(tier)* | transcript | `service_tier`, hidden when `standard` |
| `v2.1.246` | payload | Claude Code version |

**Permission-mode colours match Claude Code's own indicator** under the prompt, rather
than inventing a scheme. The mapping was read out of the binary (v2.1.246) and lives in
`MODES` in `statusline.py`:

| mode | shown as | colour | Claude Code's colour key |
| --- | --- | --- | --- |
| `default` | `manual` | grey | `inactive` |
| `plan` | `plan` | cyan | `planMode` |
| `acceptEdits` | `accept edits` | magenta | `autoAccept` |
| `auto` | `auto` | yellow | `warning` |
| `bypassPermissions` | `bypass permissions` | red | `error` |
| `dontAsk` | `don't ask` | red | `error` |

Deliberately duplicated with the indicator under the prompt: the status line is where you
look for session state, and one glance should answer it.

## CONTEXT

| field | source | meaning |
| --- | --- | --- |
| `ctx[███░░░] 24%` | payload | context window used. Yellow ≥50%, red ≥80%, `⚠` appended ≥80% |
| `242k/1M` | payload | live context tokens / real window size |
| `session 9.55M in` | transcript | every input token served this session — cache reads + writes + uncached |
| `128k out` | transcript | output tokens generated |
| `65.4k thinking` | transcript | the subset of output that was thinking |
| `104 api turns` | transcript | assistant responses carrying a usage block |
| `avg 90.7k/1.23k per turn` | derived | mean in/out tokens per api turn |

`session … in` is far larger than the context window and that is correct — it is every
token *served across every turn*, and cache reads dominate it.

## USAGE

| field | source | meaning |
| --- | --- | --- |
| `5h [███] 15.0%` | payload | 5-hour window used. **Over 100% is normal** if you have credits |
| `@20.0%/h` | derived | burn rate, back-computed from `resets_at`. **Hidden once past 100%** |
| `▸ 100%` | derived | projected usage at reset if the rate holds. Red ≥100%. **Hidden once past 100%** |
| `+2% over` | payload | how far past the included allowance, shown instead of the projection |
| `(reset Wed 19:30 \| 4h14m)` | derived | when the window resets, and time remaining |
| `OVERAGE` | derived | past 100%; spend is now credit-funded |
| `7d [...]` | payload | the same for the 7-day window |

Burn rate and projection are suppressed above 100% on purpose — both are computed *from*
that number, and it may be pinned rather than climbing. See
[ADR 0009](adrs/0009-suppress-derived-rate-limit-figures-in-overage.md).

## COST

| field | source | meaning |
| --- | --- | --- |
| `$2.10 session` | ledger | **lifetime** cost of this session across every resume |
| `(run $X · N runs)` | ledger | shown only after a resume: this run's own spend, and the run count |
| `24h / 7d / 30d` | ledger | spend across all sessions in those windows |
| `last5 · all` | ledger | the five most recently updated rows, and everything |
| `(5 convos · 6 sess · 1 fork)` | ledger | conversations, real sessions, forks |
| `+174/-0 lines` | payload | lines added/removed this session |
| `credits on` | probe | credits enabled, not currently in overage |
| `on credits` | payload+probe | past the 5h limit on a model that draws credits. **No dollar figure** |
| `overage included for <model>` | probe | past the limit, but this model is exempt from drawing |
| `credits OFF (reason)` | probe | credits unavailable — red |

Cost is the payload's `total_cost_usd` **passed straight through**, never recomputed from
tokens × a price table, which would drift silently when prices change. The credit *balance*
is not obtainable locally at all — see [ADR 0001](adrs/0001-exactly-accountable-money.md).

## SYSTEM

Segments are ordered so the two figures people compare sit side by side, with machine-wide
pressure after them and disk last — disk is the first thing worth losing on a narrow window.

| field | source | meaning |
| --- | --- | --- |
| `this session 540M · 5 proc · pid 4821` | probe | this session **and every process it spawned**, so it moves as tools run |
| `all claude 512M · 1 proc · 3.1% of ram` | probe | resident memory of every claude process on the machine, and its share of total RAM |
| `ram[██████░░] 62% of 32.0G` | probe | system memory in use. Yellow ≥70%, red ≥88% |
| `4.2G compressed` | probe | memory macOS has compressed in place rather than paging to disk |
| `disk[████░░░░] 48% · 210G free` | probe | the filesystem holding the cwd. Yellow ≥80%, red ≥92% |

The two memory figures answer different questions and routinely disagree:

- **`all claude`** is every claude binary on the machine, across all your windows. It is the
  number to compare against total RAM, which is why its share is printed next to it.
- **`this session`** is *this* conversation plus its children — the Python probes, anything
  a Bash call started. It can exceed `all claude` while tools are running, and shrink below
  it when they finish.

`this session` is found by walking up the parent chain from the status-line process until
it hits a claude process, so the pid is **discovered, not guessed**. The pid is displayed
because during a real incident, working out which process was which took far longer than
it should have (see [ADR 0006](adrs/0006-cached-probes-only.md)).

**`compressed`** is macOS's memory compressor: rather than paging inactive memory out to
disk, the kernel compresses those pages in place. A few gigabytes is normal and healthy. It
becomes interesting when it grows while `ram %` stays flat — that is real pressure being
absorbed rather than relieved, and it is the warning that comes before swapping starts.

## TOOLS

| field | source | meaning |
| --- | --- | --- |
| `48 calls` | transcript | total tool calls |
| `Bash47 Edit12 …` | transcript | four most-used tools |
| `1 tool errors` | transcript | tool results flagged `is_error`. Red when nonzero |
| `N api errors` | transcript | `<synthetic>` assistant messages — API failures. Hidden at zero |
| `6 files edited · 14 read` | transcript | distinct paths via `Edit`/`Write`/`NotebookEdit` vs `Read` |
| `0 subagents` | transcript | `isSidechain` messages |
| `0 compactions` | transcript | context compaction events. Red when nonzero |
| `cmds /effort2` | transcript | slash commands used |

**`files edited · read` counts tools, not filesystem activity.** Anything touched through
Bash — `cat`, `sed -i`, a script — is invisible here and will read as `0 files edited`
during a session that changed plenty. This is a known limitation, not a bug.

**`compactions` is the one to watch.** Nonzero means context was summarised and detail is
gone. Its detection is written defensively and has never actually fired locally; verify it
the first time a real compaction happens.

## CACHE

| field | source | meaning |
| --- | --- | --- |
| `97.9% hit` | transcript | cache reads / all served input tokens |
| `1h ttl` / `5m ttl` | transcript | which TTL is live, read from the newest write's bucket. **Red on `5m`** |
| `(assumed)` | derived | no cache write seen yet, so the TTL is the fallback rather than observed |
| `▸ expires 16:15` | derived | wall-clock time the cache goes cold if nothing touches it |
| `COLD` | derived | TTL elapsed; the next turn re-sends the whole conversation |
| `0.14x vs all-uncached` | derived | cost of served tokens relative to sending them all uncached (0.1x read, 1.25x write). Unit-free, **not dollars** |
| `writes 313k 1h · 0 5m` | transcript | cumulative cache writes per TTL bucket. A growing `5m` figure means the TTL switched |

**`5m` is the field to watch.** An account crossing into usage overage drops from a 1-hour
cache TTL to 300 seconds, mid-session, between one turn and the next. The cache then dies
between turns and every turn re-sends the conversation as writes.

## TOKENS

| field | source | meaning |
| --- | --- | --- |
| `total reused / written / uncached` | transcript | cumulative. **reused** = cache hits (0.1x) · **written** = new cache entries (1.25x) · **uncached** = never cached (1.0x) |
| `turn reused / written / uncached` | payload | the same three for the most recent turn only |

## TIMING

| field | source | meaning |
| --- | --- | --- |
| `turn 4m last · 4m median · 9m max (12 timed)` | transcript | wall time per turn from `system/turn_duration`; last 60 kept |
| `wall 43m · api 11m (26% busy)` | payload | total elapsed vs time actually spent waiting on the API |
| `hooks 2 runs · 136ms median · 0 errors` | transcript | hook executions from `stop_hook_summary`. Errors red |

**`% busy` is the number that matters.** Low means the session is human-paced — reading and
typing — and high means it is genuinely compute-bound. `hooks` is the only place a slow or
failing hook surfaces at all.
