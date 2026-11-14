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

Local tools can query the documented subset of session, model, context, cost,
turn, line, and timestamp fields through `agent-statusline metrics
<session-id>`; see [INTERNALS.md](INTERNALS.md#public-per-session-metrics).
The separate context guard prefers that session-scoped context evidence and
warns on `Stop` at 80% by default; its threshold, message, and event timing are
documented under [configurable context guard](INTERNALS.md#configurable-context-guard).

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

## Configurable field groups

Starting with v0.5.1, a row's list under `[display.fields]` selects from
these case-sensitive IDs. The table shows renderer priority. Reordering an
array does not change the display. A group may contain multiple values
that are presented together and only appears when its normal data is available.

| Row | Field IDs in display priority |
| --- | --- |
| `PROJECT` | `directory`, `added_dirs`, `branch` (Git state), `session_name` |
| `MODEL` | `model` (with effort), `thinking`, `fast_mode`, `permission_mode`, `output_style`, `service_tier`, `version` |
| `CONTEXT` | `window` (with usage, token count and visual warning), `session_throughput` |
| `USAGE` | `five_hour`, `seven_day` (each includes its window's rate, projection and reset when available) |
| `COST` | `session` (with resume details), `rolling` (24h/7d/30d), `history` (last5, all, and counts), `lines`, `credits` |
| `SYSTEM` | `session_processes`, `all_claude`, `memory`, `disk` |
| `TOOLS` | `calls`, `top_tools`, `tool_errors`, `api_errors`, `files`, `subagents`, `compactions`, `commands` |
| `CACHE` | `hit_rate`, `ttl` (with expiry), `relative_cost`, `writes` |
| `TOKENS` | `total`, `turn` |
| `TIMING` | `turn_duration`, `wall_api`, `hooks` |

Omit a row's list to show all its groups as usual. Use `[display.rows]` to
hide a whole row. Empty lists, duplicate IDs, and unknown IDs are invalid.
Run `agent-statusline config fields` for the complete catalog, or
`agent-statusline config fields PROJECT` to see one row.

Visibility filters presentation after collection and calculation; it does not
stop the ledger or probe scheduling. Current group selectors cannot split
compound values such as `rolling` into individual periods. The planned
[element controls](CUSTOMIZATION_DESIGN.md#configuration-model-before-the-editor)
are not yet accepted TOML keys and do not change this shipped catalog.

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
| `5h [███] 15%` | payload | floored 5-hour window used; 99.5 displays 99, never early 100. **Over 100% is normal** if you have credits |
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
| `(run $X · N runs)` | ledger | shown only after a resume: this run's own estimate, and the run count |
| `24h / 7d / 30d` | ledger | recorded estimates across all sessions in those windows |
| `≥$` before a rolling amount | ledger | the attributable portion of recorded estimates for that horizon |
| `last5 · all` | ledger | the five most recently updated rows, and everything |
| `(5 convos · 6 sess · 1 fork)` | ledger | conversations, real sessions, forks |
| `+174/-0 lines` | payload | lines added/removed this session |
| `credits on` | probe | credits enabled, not currently in overage |
| `on credits` | payload+probe | past the 5h limit on a model that draws credits. **No dollar figure** |
| `overage included for <model>` | probe | past the limit, but this model is exempt from drawing |
| `credits OFF (reason)` | probe | credits unavailable — red |

Each cost amount uses the host's `total_cost_usd`, which Claude
Code calculates as an estimate. Claude Code uses list pricing or its configured
model pricing. Session, run, recent and all-time amounts accumulate the host
values. Rolling windows use timestamped positive lifetime deltas. When timing
evidence is incomplete, `≥$` gives a lower bound on the recorded estimates
attributable to that window. Billing is determined separately by the provider.
Set `display.show_cost_estimate_marker = true` to display `~$` (or `≥~$`
for an incomplete window) in the status line and `ledger show`. The default
uses ordinary dollar amounts.
See the [Claude Code status line reference](https://code.claude.com/docs/en/statusline#available-data),
[ADR 0065](adrs/0065-make-cost-estimate-marker-optional.md) and
[ADR 0022](adrs/0022-account-rolling-costs-with-timestamped-deltas.md).

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

The RAM percentage uses each host's native kernel view: active, wired, and
compressed pages on macOS; `MemTotal - MemAvailable` on Linux. Linux therefore
does not count readily reclaimable caches as pressure. Under WSL, `MemTotal`
is the capacity visible to the Linux environment, so a distro limited to 8 GB
correctly reports pressure against 8 GB rather than all physical Windows RAM.
Compressed memory remains a macOS-only segment.

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
The combined process snapshot is cached separately for each host session identifier, with
a parent-process fallback when no valid string identifier is available, so concurrent
sessions cannot borrow one another's `this session` evidence (see
[ADR 0024](adrs/0024-scope-process-probes-by-session.md)).

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
| `3 subagents` | main transcript | Distinct agents confirmed by structured results matched to this session's `Agent` or legacy `Task` calls, including background launches. `subagents n/a` means the count cannot be established. Older sidechain evidence can appear as `subagent msgs`. |
| `0 compactions` | transcript | context compaction events. Red when nonzero |
| `cmds /effort2` | transcript | slash commands used |

**`files edited · read` counts tools, not filesystem activity.** Anything touched through
Bash — `cat`, `sed -i`, a script — is invisible here and will read as `0 files edited`
during a session that changed plenty. This is a known limitation, not a bug.

**`compactions` counts events in this transcript.** An explicit compaction
boundary and its linked summary count once, including across redraws;
summary-only transcripts remain supported. Counts include inherited transcript
history on resume or fork. Separate transcript paths retain independent counts.
The observed marker relationship and its verification limits are recorded in
[RESEARCH.md](RESEARCH.md#compaction-records-and-session-isolation).

## CACHE

| field | source | meaning |
| --- | --- | --- |
| `97.9% hit` | transcript | cache reads / all served input tokens |
| `1h ttl` / `5m ttl` | payload, else transcript | native cache TTL on Claude Code v2.1.251+; five minutes is a normal supported option |
| `(estimated)` / `(assumed)` | derived | older-client fallback uses the newest write bucket; before any bucket, assumes one hour |
| `▸ expires 16:15` | payload, else derived | native expiry when supplied; legacy timestamp-based expiry is only an estimate |
| `COLD` | payload | native warmth is false, or its expiry has passed; does not promise a full cache miss |
| `possibly cold` | derived | the legacy estimated window elapsed; mixed prefixes and timing are not fully observable |
| `cache not observed` | payload | the host has not observed cache tokens; caching may be off or unreported |
| `warm` | payload | native state is warm but a usable expiry clock was not supplied |
| `0.14x vs all-uncached (list)` | transcript | unit-free input ratio at published Claude API list prices for one supported model with known write TTL buckets |
| `writes 313k 1h · 0 5m` | transcript | cumulative writes per TTL bucket; different TTLs may coexist |

The ratio weights fresh input at 1×, five-minute writes at 1.25× and one-hour
writes at 2×. The read weight comes from the recorded model ID. Mixed-model
sessions and sessions with unsupported model IDs or incomplete write evidence
keep the other cache fields. See [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
and [ADR 0062](adrs/0062-qualify-cache-list-price-ratio.md).


The native payload covers the main conversation and excludes subagents.
Our transcript hit rate, write totals and relative multiplier retain their
existing scope. Native lifetime state does not replace those metrics.
A five-minute TTL does not itself diagnose a billing problem. Claude Code
chooses defaults by request type and billing mode, and users can override them.
See [Anthropic's caching guide](https://code.claude.com/docs/en/prompt-caching)
and [ADR 0058](adrs/0058-prefer-native-prompt-cache-state.md).

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
