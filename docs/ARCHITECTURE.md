<p align="center">
  <img src="assets/hero.svg" alt="multivendor-cli-configurator — architecture" width="100%">
</p>

# 🏛️ multivendor-cli-configurator — Architecture

A **zero-dependency, single-file HTML cheatsheet** that puts **~52,031 network CLI
commands across 17 vendors & tools** into one searchable, filterable,
deep-linkable browser page. The runtime is one ~5,800-line `index.html` of vanilla
JavaScript that fetches a flat `commands.json` (cache-then-revalidate via IndexedDB)
and renders everything **client-side** in three views — Cards, Table, and Compare —
**with no backend**. A separate offline, **stdlib-only Python pipeline** under
`scripts/` parses published vendor docs into per-source JSON, merges and dedupes them
into `commands.json`, which is committed and auto-deployed via **GitHub Pages**.
Beyond lookup, the UI generates **vendor-correct automation snippets**
(NETCONF / ncclient / Netmiko / Ansible / Bash) by regex-extracting values from each
command.

---

## Table of Contents

1. [System Context](#1-system-context)
2. [Container & Component Map](#2-container--component-map)
3. [Runtime Boot Sequence](#3-runtime-boot-sequence)
4. [Build & Data-Flow Pipeline](#4-build--data-flow-pipeline)
5. [Render-Dispatch State Machine](#5-render-dispatch-state-machine)
6. [Command Data Model](#6-command-data-model)
7. [Tech Stack](#7-tech-stack)

---

## 1. System Context

The whole system is **one static page + one JSON file**. Network engineers interact
with it directly in a browser; published vendor docs and a live FRR lab feed an
offline pipeline; GitHub Pages serves the artifacts; and generated automation snippets
eventually target real devices out-of-band.

```mermaid
flowchart TB
    eng["👩‍💻 Network Engineers<br/>browse · search · compare"]:::actor
    docs["📚 Vendor Docs<br/>Cisco · Junos · EOS · FRR · DCN"]:::source
    lab["🐳 10-node Docker<br/>FRR Lab (live capture)"]:::source

    subgraph SYS["multivendor-cli-configurator"]
      app["🖥️ index.html<br/>single-file web app"]:::core
      data["🗃️ commands.json<br/>~52,031 records"]:::store
      pipe["🐍 scripts/ Python ETL<br/>parse · merge · clean"]:::build
    end

    pages["☁️ GitHub Pages<br/>static host + auto-deploy"]:::ext
    devices["🌐 Target Devices<br/>Netmiko / Ansible / NETCONF"]:::target

    eng -->|"open page"| app
    app -->|"fetch once"| data
    docs --> pipe
    lab --> pipe
    pipe -->|"generates"| data
    pipe -->|"push to main"| pages
    pages -->|"serves"| app
    app -.->|"copy snippets (user-run)"| devices

    classDef actor  fill:#0e7490,stroke:#5eead4,color:#fff
    classDef source fill:#475569,stroke:#94a3b8,color:#fff
    classDef core   fill:#15803d,stroke:#39ff14,color:#fff
    classDef store  fill:#0d9488,stroke:#5eead4,color:#fff
    classDef build  fill:#a16207,stroke:#ffd152,color:#fff
    classDef ext    fill:#334155,stroke:#94a3b8,color:#fff
    classDef target fill:#b91c1c,stroke:#fb7185,color:#fff
```

---

## 2. Container & Component Map

`index.html` is a monolith by file count but cleanly layered by concern: a boot/cache
layer, a global state + render dispatcher, a filter/deep-link engine, a concept-alignment
compare engine, and an automation/code-generation layer — all over an in-memory `DATA`
array hydrated from `commands.json`.

```mermaid
flowchart TB
    subgraph BROWSER["🖥️ index.html — single-file client app"]
      direction TB
      boot["⚡ Data Loader & Cache<br/>loadCommandsWithCache · bootRender<br/>idbGet/idbPut · HEAD revalidate"]:::svc
      state["🧠 Global state + render()<br/>DATA · vendor/os/role/cat Sets<br/>el() + replaceChildren()"]:::core
      filter["🔎 Filter & Deep-Link<br/>matches · parseQuery<br/>syncUrl · encodeWorkspace"]:::svc
      compare["🔗 Compare / Concept Align<br/>conceptKey · lookupConcept<br/>CONCEPT_SYNONYMS (37)"]:::accent
      auto["🔧 Automation Generators<br/>AUTOMATION_MAPPINGS · compilePlaybook<br/>Netmiko · Ansible · NETCONF · Bash"]:::danger
    end

    json[("🗃️ commands.json")]:::store
    persist[["💾 IndexedDB · localStorage<br/>?ws= base64 deep-link"]]:::ext

    json --> boot --> state
    state --> filter --> state
    state --> compare
    state --> auto
    boot <--> persist
    filter <--> persist

    classDef core   fill:#15803d,stroke:#39ff14,color:#fff
    classDef svc    fill:#0e7490,stroke:#5eead4,color:#fff
    classDef accent fill:#0d9488,stroke:#5eead4,color:#fff
    classDef danger fill:#b91c1c,stroke:#fb7185,color:#fff
    classDef store  fill:#0d9488,stroke:#5eead4,color:#fff
    classDef ext    fill:#475569,stroke:#94a3b8,color:#fff
```

---

## 3. Runtime Boot Sequence

On load the app renders **instantly from the IndexedDB cache** if present, then
HEAD-revalidates `commands.json` against a stored ETag + Content-Length and only
re-fetches and re-renders when the artifact actually changed — a classic
cache-then-revalidate path that keeps a 17 MB corpus feeling instant.

```mermaid
sequenceDiagram
    actor User
    participant B as Browser (index.html)
    participant IDB as IndexedDB (mvc-cli-cache)
    participant CDN as GitHub Pages

    User->>B: open page
    B->>IDB: idbGet(cached corpus)
    alt cache hit
        IDB-->>B: cached DATA
        B->>B: bootRender() → render() (badge: cached)
    end
    B->>CDN: HEAD commands.json (ETag + length)
    alt changed or no cache
        CDN-->>B: new ETag / length
        B->>CDN: GET commands.json (no-store)
        CDN-->>B: ~52,031 records
        B->>IDB: idbPut(corpus, ETag)
        B->>B: bootRender() → render() (badge: fresh)
    else unchanged
        CDN-->>B: 304 / same ETag (badge: revalidated)
    end
    B-->>User: filtered cards / table / compare
```

---

## 4. Build & Data-Flow Pipeline

The offline Python pipeline (never shipped to the browser) turns published vendor
books and a live FRR lab into one deduped JSON array: per-source parsers emit
intermediate JSON, a master merger folds in community markdown + seed + DCN corpus,
and quality utilities repair and quarantine bad rows before the final commit.

```mermaid
flowchart LR
    src["📚 scripts/sources/*<br/>vendor books · docs (gitignored)"]:::source
    parsers["🐍 parse_*.py<br/>encor · junos · arista · frr · cisco · extras"]:::build
    inter["🧩 per-source JSON<br/>encor.json · junos.json · …"]:::build
    master["🔀 parse.py + merge_dcn_corpus.py<br/>merge + dedupe by normalized cmd"]:::accent
    clean["🧹 clean_titles.py + audit_data_quality.py<br/>repair prose · quarantine bad rows"]:::accent
    out[("🗃️ commands.json<br/>~52,031 records")]:::store
    web["🖥️ index.html<br/>fetch() at boot"]:::core

    src --> parsers --> inter --> master --> clean --> out --> web

    classDef source fill:#475569,stroke:#94a3b8,color:#fff
    classDef build  fill:#a16207,stroke:#ffd152,color:#fff
    classDef accent fill:#0d9488,stroke:#5eead4,color:#fff
    classDef store  fill:#0d9488,stroke:#5eead4,color:#fff
    classDef core   fill:#15803d,stroke:#39ff14,color:#fff
```

---

## 5. Render-Dispatch State Machine

Every user action mutates the global `state`, which the `render()` dispatcher reads to
filter `DATA` via `matches()` and route to exactly one of three view renderers. State
is persisted to `localStorage` and serialized into a shareable base64 `?ws=` URL.

```mermaid
stateDiagram-v2
    [*] --> Booting
    Booting --> Filtering: bootRender() assigns DATA
    Filtering --> Cards: state.view = cards
    Filtering --> Table: state.view = table
    Filtering --> Compare: state.view = compare

    Cards --> Filtering: search / filter / fav
    Table --> Filtering: search / filter / sort
    Compare --> Filtering: vendor subset change

    Cards --> Automate: open Automate / queue CLI
    Compare --> Automate: See equivalents ↗
    Automate --> Filtering: close drawer

    Filtering --> Filtering: syncUrl() → ?ws= deep-link
    note right of Filtering
      matches() = filter Sets
      AND parseQuery operators
      AND haystack search
    end note
```

---

## 6. Command Data Model

There is **no database** — the entire "schema" is the shape of each record in the flat
`commands.json` array. Records share a common shape; FRR rows add optional provenance
flags, and the Compare engine derives a stable `conceptKey` slug to line up
semantically-equivalent rows across vendors.

```mermaid
erDiagram
    COMMAND {
        string os    "e.g. IOS-XE, Junos, EOS"
        string vendor "Cisco, Juniper, Arista, FRR, …"
        string role  "router / switch / firewall"
        string cat   "BGP, OSPF, VLAN, Interfaces, …"
        string title "human label (cleaned)"
        string cmd   "the literal CLI command"
        string desc  "what it does"
        bool   live  "FRR only: seen on Docker lab"
        bool   in_docs "FRR only: present in docs"
    }
    CONCEPT {
        string conceptKey "normalized slug e.g. bgp:peer"
        string label      "display name"
    }
    VENDOR {
        string name "1 of 17"
        int    count "commands contributed"
    }
    VENDOR ||--o{ COMMAND : "contributes"
    CONCEPT ||--o{ COMMAND : "aligns (CONCEPT_SYNONYMS)"
```

---

## 7. Tech Stack

| Layer | Technology |
|---|---|
| **Runtime UI** | Vanilla JavaScript · HTML · CSS — zero framework, zero build, zero JS dependencies |
| **Boot & cache** | Fetch API (HEAD/GET, `cache:'no-store'`) · IndexedDB (`mvc-cli-cache`) |
| **Persistence** | `localStorage` · base64 `?ws=` deep-link URLs |
| **Compare engine** | `conceptKey` slugs · 37-entry `CONCEPT_SYNONYMS` · CSS grid |
| **Automation** | Regex extraction → NETCONF / ncclient / Netmiko / Ansible / Bash via lookup tables |
| **Data pipeline** | Python 3 standard library only (`json`, `pathlib`, `re`) — no third-party deps |
| **Data artifact** | `commands.json` — ~17 MB flat array of ~52,031 records |
| **Hosting / CI** | GitHub Pages — static host, auto-deploy on push to `main` |
| **Tests** | Node.js `assert` + source-extraction testing (`tests/stress_test.js`) |

---

<p align="center"><sub>
Diagrams render natively on GitHub. Hero banner is a handcrafted animated SVG
(SMIL + CSS keyframes, with a <code>prefers-reduced-motion</code> guard).
</sub></p>
