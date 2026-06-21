#!/usr/bin/env python3
"""
parse_modern.py — curated "modern ops" command corpus.

Adds the four coverage gaps the cheatsheet was thin on:
  - Telemetry      : gNMI / gRPC dial-out / NETCONF / RESTCONF / streaming
  - Automation     : on-box programmability, model-driven config, scripting
  - Provisioning   : ZTP / day-0 / zero-touch bring-up
  - Optics         : interface breakout + transceiver/DOM diagnostics
  - Hardening       : security baselines (telnet off, SSH ciphers, CoPP, MACsec)

Schema: { os, role, vendor, cat, title, cmd, desc }
Hand-curated, publicly documented vendor syntax. Merges into commands.json
deduping by (vendor, normalized cmd) — same key the rest of the pipeline uses.
"""
import json, re, pathlib, sys

OUT = pathlib.Path(__file__).parent.parent / "commands.json"

def norm_cmd(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())

REC = []
def r(vendor, os_, role, cat, title, cmd, desc):
    REC.append({"os": os_, "role": role, "vendor": vendor,
                "cat": cat, "title": title, "cmd": cmd, "desc": desc})

# ───────────────────────── TELEMETRY ─────────────────────────
# gNMI client (gnmic) — vendor-agnostic but most-used against EOS/SR Linux/SONiC
r("Arista","eos","switch","Telemetry","gNMI Get (gnmic)",
  "gnmic -a <switch>:6030 -u admin -p admin --insecure get --path /interfaces/interface/state/counters",
  "Pull interface counters once over gNMI from an EOS device.")
r("Arista","eos","switch","Telemetry","gNMI Subscribe sample (gnmic)",
  "gnmic -a <switch>:6030 -u admin -p admin --insecure subscribe --path /interfaces/interface/state/counters --mode sample --sample-interval 10s",
  "Stream interface counters every 10s via gNMI sample subscription.")
r("Arista","eos","switch","Telemetry","gNMI Subscribe on-change (gnmic)",
  "gnmic -a <switch>:6030 --insecure subscribe --path /network-instances/.../state --mode on_change",
  "Receive updates only when a leaf changes (on-change subscription).")
r("Arista","eos","switch","Telemetry","Enable gNMI server (EOS)",
  "management api gnmi\n transport grpc default\n provider eos-native",
  "Enable the on-box gNMI/gRPC transport on Arista EOS.")
r("Arista","eos","switch","Telemetry","Enable streaming telemetry to collector",
  "daemon TerminAttr\n exec /usr/bin/TerminAttr -ingestgrpcurl=<cvp>:9910 -taillogs\n no shutdown",
  "Stream state to CloudVision / a gRPC collector via TerminAttr.")
r("Cisco","ios","router","Telemetry","Model-driven telemetry dial-out (IOS-XE)",
  "telemetry ietf subscription 101\n encoding encode-kvgpb\n filter xpath /interfaces-ios-xe-oper:interfaces/interface/statistics\n stream yang-push\n update-policy periodic 1000\n receiver ip address <collector> 57500 protocol grpc-tcp",
  "Periodic gRPC dial-out streaming telemetry subscription on IOS-XE.")
r("Cisco","nxos","switch","Telemetry","Streaming telemetry path (NX-OS)",
  "telemetry\n destination-group 1\n  ip address <collector> port 50001 protocol gRPC encoding GPB\n sensor-group 1\n  path sys/intf depth 0\n subscription 1\n  dst-grp 1\n  snsr-grp 1 sample-interval 10000",
  "Configure NX-OS model-driven telemetry to a gRPC collector at 10s.")
r("Juniper","junos","router","Telemetry","gRPC streaming telemetry (JTI)",
  "set services analytics streaming-server collector address <ip> port 50051\nset services analytics export-profile prof reporting-rate 30",
  "Junos Telemetry Interface gRPC export profile (native sensors).")
r("Juniper","junos","router","Telemetry","gNMI / OpenConfig subscribe",
  "set system services extension-service request-response grpc clear-text port 32767",
  "Enable the gNMI/gRPC server on Junos for OpenConfig telemetry.")
r("Nokia","srlinux","router","Telemetry","gNMI subscribe (SR Linux)",
  "gnmic -a <node>:57400 --skip-verify -u admin -p admin subscribe --path /interface[name=ethernet-1/1]/statistics",
  "Subscribe to per-interface statistics on Nokia SR Linux over gNMI (port 57400).")
r("Nokia","srlinux","router","Telemetry","Enable gNMI server (SR Linux)",
  "enter candidate\nset / system gnmi-server network-instance mgmt admin-state enable\ncommit now",
  "Enable the gNMI server in the mgmt network-instance on SR Linux.")
r("NVIDIA","nvue","switch","Telemetry","gNMI server (Cumulus NVUE)",
  "nv set system gnmi-server listening-address 0.0.0.0\nnv config apply",
  "Turn on the gNMI server on Cumulus Linux via NVUE.")
r("SONiC","sonic","switch","Telemetry","gNMI / telemetry container status",
  "show feature status | grep telemetry\ndocker ps | grep telemetry",
  "Verify the gNMI/telemetry (gnmi) container is running on SONiC.")
r("SONiC","sonic","switch","Telemetry","gNMI get via gnmic",
  "gnmic -a <device>:8080 --insecure -u admin -p YourPaSsWoRd get --path /interfaces/interface/state",
  "Query SONiC interface state over gNMI (default telemetry port 8080).")
# sFlow / NetFlow / IPFIX
r("Arista","eos","switch","Telemetry","sFlow export",
  "sflow sample 16384\nsflow destination <collector>\nsflow run",
  "Enable sFlow sampling and export on EOS.")
r("Cisco","ios","router","Telemetry","Flexible NetFlow / IPFIX",
  "flow exporter EXP\n destination <collector>\n transport udp 4739\nflow monitor MON\n exporter EXP\n record netflow ipv4 original-input\ninterface Gi0/0\n ip flow monitor MON input",
  "Flexible NetFlow with IPFIX (UDP/4739) export on IOS-XE.")
r("Juniper","junos","router","Telemetry","Inline IPFIX (jflow)",
  "set services flow-monitoring version-ipfix template IPv4 flow-active-timeout 60\nset forwarding-options sampling instance S family inet output flow-server <ip> port 4739",
  "Inline-jflow IPFIX sampling/export on Junos.")
r("VyOS","vyos","router","Telemetry","sFlow agent",
  "set system sflow interface eth0\nset system sflow server <collector> port 6343",
  "Configure sFlow export on VyOS.")

# ───────────────────────── AUTOMATION ─────────────────────────
r("Cisco","ios","router","Automation","NETCONF over SSH enable",
  "netconf-yang\nnetconf ssh",
  "Enable the NETCONF/YANG agent (port 830) on IOS-XE.")
r("Cisco","ios","router","Automation","RESTCONF enable",
  "restconf\nip http secure-server",
  "Enable RESTCONF (HTTPS) on IOS-XE for model-driven config.")
r("Cisco","ios","router","Automation","Guest Shell / on-box Python",
  "guestshell enable\nguestshell run python3 /flash/script.py",
  "Run on-box Python from the IOS-XE Guest Shell container.")
r("Cisco","ios","router","Automation","EEM applet (event automation)",
  "event manager applet LINKDOWN\n event syslog pattern \"Interface GigabitEthernet0/1, changed state to down\"\n action 1.0 cli command \"enable\"\n action 2.0 syslog msg \"Gi0/1 went down\"",
  "Embedded Event Manager applet reacting to a syslog event.")
r("Cisco","nxos","switch","Automation","On-box Python / bash",
  "feature bash-shell\nrun bash python3 /bootflash/script.py",
  "Enable and run on-box scripting on NX-OS.")
r("Juniper","junos","router","Automation","NETCONF over SSH",
  "set system services netconf ssh",
  "Enable NETCONF on port 830 for ncclient/Ansible on Junos.")
r("Juniper","junos","router","Automation","Commit script / SLAX op",
  "set system scripts op file myscript.slax\nop myscript",
  "Register and run a Junos op (SLAX/Python) automation script.")
r("Juniper","junos","router","Automation","JET / Python on-box",
  "set system scripts language python3\nset event-options event-script file handler.py",
  "Enable Python scripting and an event handler on Junos.")
r("Arista","eos","switch","Automation","eAPI (JSON-RPC) enable",
  "management api http-commands\n protocol https\n no shutdown",
  "Enable Arista eAPI (HTTPS JSON-RPC) for programmatic control.")
r("Arista","eos","switch","Automation","Config session (commit/rollback)",
  "configure session add-vlan\n vlan 200\n name PROD\ncommit\n# or: abort / rollback clean-config",
  "Stage changes in a named config session, then commit or abort — safe automation.")
r("Nokia","srlinux","router","Automation","JSON-RPC / candidate config",
  "enter candidate\nset / interface ethernet-1/1 admin-state enable\ndiff\ncommit now",
  "Declarative candidate→commit workflow on SR Linux (also exposed via JSON-RPC).")
r("FortiOS","fortios","firewall","Automation","REST API admin + token",
  "config system api-user\n edit \"automation\"\n  set api-key ENC ...\n  set accprofile \"super_admin\"\n next\nend",
  "Create a REST API user/token for FortiGate automation (cmdb/monitor).")
r("PAN-OS","panos","firewall","Automation","XML API key",
  "request api key\n# GET https://<fw>/api/?type=keygen&user=admin&password=...",
  "Generate the PAN-OS XML API key used for programmatic config/ops.")
r("VyOS","vyos","router","Automation","Config-mode scripting / commit",
  "configure\nset interfaces ethernet eth1 address 10.0.0.1/24\ncommit\nsave\nexit",
  "VyOS structured config with atomic commit (HTTP API mirrors this).")
r("NVIDIA","nvue","switch","Automation","NVUE REST API apply",
  "nv config apply\n# REST: PATCH /nvue_v1/ with revisionID then apply",
  "NVUE declarative apply; the same model is exposed over the REST API.")

# ───────────────────────── PROVISIONING (ZTP) ─────────────────────────
r("Arista","eos","switch","Provisioning","ZTP status / cancel",
  "show zerotouch\nzerotouch cancel\nzerotouch disable",
  "Inspect Zero Touch Provisioning state and opt out to a normal boot on EOS.")
r("Cisco","ios","router","Provisioning","Network Plug-and-Play (PnP) discovery",
  "pnp profile pnp-zero-touch\n transport https ipv4 <pnp-server> port 443",
  "Point IOS-XE PnP agent at a controller for day-0 onboarding.")
r("Cisco","ios","router","Provisioning","ZTP Guest Shell (IOS-XE)",
  "# DHCP option 67 -> http://<srv>/ztp.py ; runs in Guest Shell at first boot\nshow guestshell\nguestshell run python3 /flash/ztp.py",
  "IOS-XE day-0 Python ZTP delivered via DHCP option 67.")
r("Cisco","nxos","switch","Provisioning","POAP (PowerOn Auto Provisioning)",
  "# abort to manual setup at boot prompt:\nskip poap\nshow boot",
  "NX-OS POAP day-0 provisioning; 'skip' drops to the manual setup dialog.")
r("Juniper","junos","router","Provisioning","ZTP via DHCP",
  "set chassis auto-image-upgrade\n# DHCP options 150/43 hand off image + config URL at boot",
  "Enable Junos Zero Touch Provisioning (auto image + config from DHCP).")
r("Juniper","junos","router","Provisioning","ZTP status",
  "show system autoinstallation status",
  "Check the Junos auto-install / ZTP progress.")
r("SONiC","sonic","switch","Provisioning","ZTP control",
  "sudo ztp status\nsudo ztp enable\nsudo ztp run\nsudo ztp disable",
  "Manage SONiC ZTP (DHCP-driven provisioning.json) from the CLI.")
r("NVIDIA","nvue","switch","Provisioning","Cumulus ZTP",
  "ztp -s\nztp --status\nztp --disable",
  "Cumulus Linux ZTP: run the ZTP script, check status, or disable.")
r("Nokia","srlinux","router","Provisioning","ZTP / auto-boot",
  "show system boot\n# ZTP pulls config/image via DHCP opt 66/67 + ztp-server",
  "SR Linux Zero Touch Provisioning state at first boot.")
r("Aruba","aoscx","switch","Provisioning","ZTP / Aruba Central onboarding",
  "show aruba-central\nshow ztp information",
  "AOS-CX day-0: ZTP + Aruba Central activation status.")
r("FortiOS","fortios","firewall","Provisioning","Zero-touch via FortiManager",
  "config system central-management\n set type fortimanager\n set fmg <ip>\nend",
  "FortiGate zero-touch onboarding through FortiManager / FortiDeploy.")

# ───────────────────────── OPTICS / BREAKOUT ─────────────────────────
r("Arista","eos","switch","Optics","Interface breakout 4x25G",
  "interface Ethernet1/1\n speed forced 100gfull\ninterface Ethernet1\n# 100G->4x25G:\n  speed 25g-4",
  "Break a 100G port into 4x25G on EOS (verify with 'show interfaces status').")
r("Arista","eos","switch","Optics","Show transceiver / DOM",
  "show interfaces transceiver detail\nshow interfaces transceiver dom",
  "Read optic type, Rx/Tx power and DOM thresholds on EOS.")
r("Cisco","nxos","switch","Optics","Port breakout (NX-OS)",
  "interface breakout module 1 port 1 map 25g-4x",
  "Split a 100G QSFP port into 4x25G on NX-OS.")
r("Cisco","ios","router","Optics","Show transceiver / DOM",
  "show interfaces transceiver detail\nshow hw-module subslot transceiver",
  "Display optic vendor, wavelength and digital optical monitoring values.")
r("Cisco","ios","router","Optics","Breakout (IOS-XE)",
  "controller TenGigabitEthernet0/0/0\n breakout 4x10",
  "Configure a breakout group on IOS-XE platforms that support it.")
r("Juniper","junos","router","Optics","Channelize / breakout",
  "set chassis fpc 0 pic 0 port 1 number-of-sub-ports 4 speed 25g",
  "Channelize a 100G port into 4x25G sub-ports on Junos.")
r("Juniper","junos","router","Optics","Show optics / DOM",
  "show interfaces diagnostics optics et-0/0/1",
  "Per-lane Rx/Tx power, bias and temperature for an optic on Junos.")
r("Nokia","srlinux","router","Optics","Breakout port",
  "enter candidate\nset / interface ethernet-1/1 breakout-mode num-channels 4 channel-speed 25G\ncommit now",
  "Declarative 4x25G breakout on SR Linux.")
r("NVIDIA","nvue","switch","Optics","Breakout (NVUE)",
  "nv set interface swp1 link breakout 4x25G\nnv config apply",
  "Break swp1 into 4x25G on Cumulus via NVUE.")
r("Aruba","aoscx","switch","Optics","Split / breakout interface",
  "interface 1/1/1\n split\nshow interface transceiver detail",
  "Enable a split (breakout) interface and read optic DOM on AOS-CX.")
r("Extreme","exos","switch","Optics","Show optical / DOM",
  "show ports transceiver information detail",
  "Per-port transceiver DOM (power/temp) on EXOS.")
r("SONiC","sonic","switch","Optics","Transceiver / DOM + breakout",
  "show interfaces transceiver eeprom\nshow interfaces transceiver presence\nsudo config interface breakout Ethernet0 '4x25G'",
  "Read SFP EEPROM/presence and set a dynamic port breakout on SONiC.")
r("Cisco","nxos","switch","Optics","Show transceiver (NX-OS)",
  "show interface ethernet1/1 transceiver details",
  "Optic type and DOM Rx/Tx power for a single NX-OS port.")

# ───────────────────────── HARDENING ─────────────────────────
r("Cisco","ios","router","Hardening","Disable telnet, SSH-only mgmt",
  "line vty 0 15\n transport input ssh\n exec-timeout 5 0\nip ssh version 2",
  "Force SSHv2-only management access and idle timeout on VTYs.")
r("Cisco","ios","router","Hardening","Harden SSH ciphers / KEX",
  "ip ssh server algorithm encryption aes256-gcm aes256-ctr\nip ssh server algorithm mac hmac-sha2-256\nip ssh server algorithm kex diffie-hellman-group14-sha256",
  "Restrict SSH to strong ciphers/MAC/KEX on IOS-XE.")
r("Cisco","ios","router","Hardening","Control-plane policing (CoPP)",
  "control-plane\n service-policy input COPP-POLICY",
  "Apply a CoPP policy to rate-limit traffic punted to the control plane.")
r("Cisco","ios","router","Hardening","Disable risky services",
  "no ip http server\nno cdp run\nno service pad\nservice password-encryption\nlogin block-for 60 attempts 3 within 30",
  "Turn off legacy/unneeded services and add login brute-force protection.")
r("Cisco","ios","switch","Hardening","MACsec (802.1AE) on link",
  "interface Gi1/0/1\n macsec\n mka policy MKA-POL\n mka pre-shared-key key-chain KC",
  "Enable MACsec link-layer encryption with MKA on a switchport.")
r("Juniper","junos","router","Hardening","SSH-only, no telnet",
  "delete system services telnet\nset system services ssh protocol-version v2\nset system services ssh ciphers aes256-gcm@openssh.com",
  "Remove telnet and pin SSHv2 with a strong cipher on Junos.")
r("Juniper","junos","router","Hardening","Loopback / control-plane filter (lo0)",
  "set interfaces lo0 unit 0 family inet filter input PROTECT-RE",
  "Protect the Routing Engine by filtering traffic to lo0 (control plane).")
r("Juniper","junos","router","Hardening","MACsec connectivity association",
  "set security macsec connectivity-association CA1 pre-shared-key ckn <hex> cak <hex>\nset security macsec interfaces ge-0/0/1 connectivity-association CA1",
  "Configure MACsec with a pre-shared CAK/CKN on a Junos interface.")
r("Arista","eos","switch","Hardening","Management SSH hardening",
  "management ssh\n cipher aes256-gcm@openssh.com\n idle-timeout 5\nno service telnet",
  "Strong SSH ciphers, idle timeout and telnet disabled on EOS.")
r("Arista","eos","switch","Hardening","Control-plane ACL (CoPP)",
  "system control-plane\n ip access-group COPP-IN in",
  "Apply a control-plane ACL to protect the EOS CPU.")
r("FortiOS","fortios","firewall","Hardening","Admin access + strong crypto",
  "config system global\n set admin-ssh-grace-time 30\n set strong-crypto enable\n set admintimeout 5\nend",
  "Enforce strong crypto, short admin timeout and SSH grace on FortiGate.")
r("FortiOS","fortios","firewall","Hardening","Restrict admin to trusted hosts",
  "config system admin\n edit admin\n  set trusthost1 10.0.0.0 255.255.255.0\n next\nend",
  "Lock the FortiGate admin account to a management subnet.")
r("PAN-OS","panos","firewall","Hardening","Disable telnet/HTTP mgmt",
  "set deviceconfig system service disable-telnet yes\nset deviceconfig system service disable-http yes",
  "Disable insecure management services on Palo Alto.")
r("PAN-OS","panos","firewall","Hardening","Permitted management IPs",
  "set deviceconfig system permitted-ip 10.0.0.0/24",
  "Restrict which subnets may reach the PAN-OS management interface.")
r("Aruba","aoscx","switch","Hardening","SSH-only + login hardening",
  "no telnet-server\nssh server vrf mgmt\naaa authentication login default group radius local",
  "Disable telnet, bind SSH to the mgmt VRF, and require AAA login on AOS-CX.")
r("Huawei","vrp","router","Hardening","Disable telnet, enforce SSH",
  "undo telnet server enable\nstelnet server enable\nssh server cipher aes256_gcm",
  "Turn off telnet and enforce STelnet (SSH) with strong ciphers on VRP.")
r("Nokia","srlinux","router","Hardening","SSH server + ACL",
  "enter candidate\nset / system ssh-server network-instance mgmt admin-state enable\ncommit now",
  "Restrict SSH to the mgmt network-instance on SR Linux.")
r("VyOS","vyos","router","Hardening","SSH hardening",
  "set service ssh disable-password-authentication\nset service ssh ciphers aes256-gcm@openssh.com\ndelete service telnet",
  "Key-only SSH with a strong cipher and no telnet on VyOS.")
r("Mikrotik","routeros","router","Hardening","Disable insecure services",
  "/ip service disable telnet,ftp,www,api\n/ip service set ssh port=2200",
  "Disable telnet/FTP/HTTP/API and move SSH off the default port on RouterOS.")
r("Linux","linux","router","Hardening","Host SSH daemon hardening",
  "sudo sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config\nsudo systemctl reload ssh",
  "Disable SSH password auth on a Linux network host.")

# ───────────────────────── merge ─────────────────────────
def main():
    data = json.load(open(OUT))
    keys = {(r_["vendor"], norm_cmd(r_["cmd"])) for r_ in data}
    added = skipped = 0
    for rec in REC:
        k = (rec["vendor"], norm_cmd(rec["cmd"]))
        if k in keys:
            skipped += 1
            continue
        keys.add(k)
        data.append(rec)
        added += 1
    if "--dry-run" in sys.argv:
        print(f"[dry-run] candidates={len(REC)} would-add={added} dup-skip={skipped}")
        return
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"added={added} dup-skip={skipped} total={len(data)}")

if __name__ == "__main__":
    main()
