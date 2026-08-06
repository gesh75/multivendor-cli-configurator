# Architecture

> How vendor sources turn into **70,006** searchable, automatable commands in a
> single static HTML file. **FRR rows additionally carry a `live` flag** when
> the exact command was observed running on the 10-node Docker FRR lab.

![Architecture diagram](docs/img/architecture.svg)

---

## TL;DR

- **17 vendors / tools, 21 OS surfaces, 70,006 commands** — Cisco (IOS / IOS-XE / NX-OS / ASA), Juniper (Junos), Arista (EOS), FRR (FRRouting), VyOS, Huawei VRP, Aruba AOS-CX, Extreme EXOS, FortiOS, PAN-OS, Mikrotik RouterOS, NVIDIA Cumulus NVUE, Nokia (SR Linux + SR OS), SONiC, plus Microsoft PowerShell, Linux iproute2, and Wireshark tshark.
- **Reproducible Python pipeline** — every command can be traced back to a published source via a stdlib-only parser in `scripts/`.
- **Single static file** — `index.html` is vanilla JS + a `fetch('commands.json')`. No framework. No build step for the UI. Hosted on GitHub Pages.
- **Zero credentials on disk** — automation snippets use `${conn().host}` interpolations driven by a sessionStorage-only connection state with a redact toggle for safe screenshots.
- **Coverage-gap tooling** — `fix_coverage_gaps.py` retags NX-OS/IOS-XE and promotes VXLAN/EVPN/STP/BFD/LACP categories; `expand_thin_vendors.py` grows thin surfaces; `patch_yang_stack_vendors.py` + `patch_yang_more_vendors.py` extend Automate templates beyond Cisco fallback; `deep_gap_dig.py` gates OS/cat/Automate floors.

---

## Data pipeline (3 stages)

### 1 · Vendor sources (`scripts/sources/*.md`)

All public publications, dropped in as raw markdown. Each vendor has 1–3 books plus the DCN multivendor corpus and modern-ops seed.

| Vendor | Sources | Notes |
|---|---|---|
| **Cisco** | ENCOR / ENARSI Portable CG · ASA 9.24 CLI Reference · IOS OSPF Command Reference · VXLAN BGP EVPN NX-OS Reference · IOS Master Command List | `ios` / `iosxe` / `nxos` / `asa` |
| **Juniper** | Junos OS CLI Reference · Day One guides | `junos` |
| **Arista** | EOS User Guide (official) | `eos` |
| **FRR** | FRR Master CLI Reference ∪ Docker FRR live capture | `frr` + `live`/`in_docs` flags |
| **DCN corpus** | VyOS · Huawei · Aruba · Extreme · FortiOS · PAN-OS · RouterOS · NVUE · SR Linux · SONiC · Microsoft · Linux · Wireshark | bulk of mid-tier vendors |
| **Modern-ops + gap fills** | `parse_modern.py` · `expand_thin_vendors.py` | Telemetry / Automation / Provisioning / Optics / Hardening + thin-vendor fills |

The `scripts/sources/` folder is `.gitignored` — only the resulting JSON is checked in.

### 2 · Parsers (`scripts/parse_*.py`)

One parser per source format. All are pure Python 3 stdlib — no dependencies.

| Parser | Output |
|---|---|
| `parse_encor.py` / `parse_junos.py` / `parse_arista.py` / `parse_cisco_ospf.py` / `parse_cisco_extras.py` / `parse_frr.py` | per-source JSON |
| `merge_dcn_corpus.py` / `parse.py` | merge + dedupe → `commands.json` |
| `parse_modern.py` | modern-ops categories |
| `expand_thin_vendors.py` | SONiC / NVIDIA / Huawei / SR OS / NX-OS / Extreme / essentials fills |
| `fix_coverage_gaps.py` | NX-OS/IOS-XE retag, VXLAN/EVPN/STP/BFD/LACP cats, taxonomy/placeholder cleanup |
| `patch_yang_more_vendors.py` | Automate CLI templates for Huawei · NVIDIA · SONiC · Extreme · Mikrotik |
| `deep_gap_dig.py` | OS/cat/Automate floor gate (critical regressions fail) |
| `clean_titles.py` / `audit_data_quality.py` / `check_consistency.py` | quality + docs drift gate |

### 3 · `commands.json`

Single source of truth (~18 MB). Each row is:

```json
{
  "os":     "ios",
  "role":   "router",
  "vendor": "Cisco",
  "cat":    "BGP",
  "title":  "router bgp [ASN]",
  "cmd":    "router bgp 65001\n neighbor 10.0.0.2 remote-as 65002",
  "desc":   "BGP > Configure neighbor"
}
```

OS surfaces include `ios`, `iosxe`, `nxos`, `asa`, `junos`, `eos`, `frr`, `vyos`, `sonic`, `nvue`, `panos`, `srlinux`, `sros`, `fortios`, `routeros`, `exos`, `aoscx`, `vrp`, `powershell`, `linux`, `tshark`.

Dedicated overlay categories: **`VXLAN`**, **`EVPN`**, plus promoted L2/HA surfaces **`Spanning-Tree`**, **`EtherChannel`**, **`BFD`**.

FRR rows may also carry `live` / `in_docs` provenance flags.

---

## UI architecture (`index.html`)

### Automate drawer

1. **YANG Automate** — 15 patterns (`iface-ipv4`, `static-route`, `ospf-network`, `bgp-neighbor`, `vlan`, …). Templates cover **Cisco · Juniper · Arista · FRR · VyOS · Nokia · Aruba · Huawei · NVIDIA · SONiC · Extreme · Mikrotik** (CLI-first for non-YANG stacks; no silent Cisco fallback). Matchers still key off IOS/Junos-shaped commands; other vendors render when Automate is opened from Compare / equivalents.
2. **SSH Automate** — Netmiko + Ansible + NAPALM for every vendor. `devTypeFor()` prefers **OS-specific** device types (`cisco_nxos`, `cisco_asa`, `cisco_xe`, `nokia_sros`). `ansibleModFor()` selects `cisco.nxos` / `cisco.asa` collections when the queued command is NX-OS or ASA.

### Parse Output modal

Built-in show-output parsers (Cisco BGP/route/intf/OSPF + Junos BGP/route). Expanding EOS/FRR/VyOS parsers remains a follow-up.

---

## Hosting

```
push to main
  └─► GitHub Actions: gh-pages (built-in)
       └─► https://gesh75.github.io/multivendor-cli-configurator/
```

`index.html` + `commands.json` is the entire deployment.

---

## Regenerating `commands.json`

```bash
cd scripts
# 1. Run per-source parsers as needed, then merge
python3 parse.py
python3 parse_modern.py
python3 expand_thin_vendors.py
python3 fix_coverage_gaps.py
python3 clean_titles.py
python3 audit_data_quality.py
python3 check_consistency.py
python3 deep_gap_dig.py
# 2. Optional UI Automate extension (idempotent)
python3 patch_yang_stack_vendors.py
python3 patch_yang_more_vendors.py
```


Stdlib only. No virtualenv required.
