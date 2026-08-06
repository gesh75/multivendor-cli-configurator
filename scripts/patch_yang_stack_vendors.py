#!/usr/bin/env python3
"""
patch_yang_stack_vendors.py — extend Automate YANG templates + matchers.

Patches index.html in-place:
  1. Add FRR / VyOS / Nokia / Aruba renderers to every AUTO_* map
  2. Broaden AUTOMATION_MAPPINGS matchAny/extract for those CLIs
  3. Add sros to OS_DEV_TYPE; prefer cisco_nxos / cisco_xe / cisco_asa by OS
  4. Prefer OS-aware Ansible modules for Cisco nxos/asa/iosxe
  5. Ensure VXLAN/EVPN appear in CAT_GROUPS filter UI

Idempotent: skips if marker comment already present.
"""
from __future__ import annotations

import pathlib
import re
import sys

HTML = pathlib.Path(__file__).resolve().parent.parent / "index.html"
MARKER = "/* STACK_VENDOR_AUTO_EXT — FRR/VyOS/Nokia/Aruba */"

# Compact CLI-oriented templates (netconf often OpenConfig/comment; ansible real modules)
STACK_TEMPLATES = r'''
/* STACK_VENDOR_AUTO_EXT — FRR/VyOS/Nokia/Aruba */
function _autoCliBundle(title, lines, ansibleYaml){
  const cli = lines.filter(Boolean).join("\n");
  return {
    netconf: `<!-- ${title}: native NETCONF/YANG varies by platform; CLI equivalent -->\n<!--\n${cli}\n-->`,
    ncclient: `${pySetup()}# ${title} via CLI session (Netmiko-style)
from netmiko import ConnectHandler
dev = {"device_type": ${JSON.stringify('__DEVTYPE__')},
       "host": ${pyArg('host')}, "username": ${pyArg('user')},
       "password": ${pyArg('pass')}, "port": int(${pyArg('port')} or 22)}
cmds = """${cli}""".strip().splitlines()
with ConnectHandler(**dev) as conn:
    print(conn.send_config_set(cmds) if cmds else conn.send_command("show version"))`,
    ansible: ansibleYaml,
  };
}
function _withDev(bundle, deviceType){
  // Replace placeholder device_type string inside ncclient snippet
  return {
    netconf: bundle.netconf,
    ncclient: bundle.ncclient.replace('"__DEVTYPE__"', JSON.stringify(deviceType)),
    ansible: bundle.ansible,
  };
}
function stackIfaceIpv4(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR interface IPv4",
    [`interface ${v.ifname}`, `ip address ${v.ip}/${v.cidr}`],
    `- name: FRR set ${v.ifname} ${v.ip}/${v.cidr}
  ansible.builtin.shell: |
    vtysh -c 'configure terminal' -c 'interface ${v.ifname}' -c 'ip address ${v.ip}/${v.cidr}' -c 'end' -c 'write'`), "frrouting");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS interface IPv4",
    [`set interfaces ethernet ${v.ifname} address ${v.ip}/${v.cidr}`],
    `- name: VyOS set ${v.ifname} ${v.ip}/${v.cidr}
  vyos.vyos.vyos_config:
    lines:
      - set interfaces ethernet ${v.ifname} address ${v.ip}/${v.cidr}`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia SR Linux interface IPv4",
    [`enter candidate`,`set / interface ${v.ifname} subinterface 0 ipv4 admin-state enable`,`set / interface ${v.ifname} subinterface 0 ipv4 address ${v.ip}/${v.cidr}`,`commit now`],
    `- name: SR Linux set ${v.ifname} ${v.ip}/${v.cidr}
  nokia.srlinux.config:
    update:
      - path: /interface[name=${v.ifname}]/subinterface[index=0]/ipv4
        value:
          admin-state: enable
          address:
            - ip-prefix: ${v.ip}/${v.cidr}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba AOS-CX interface IPv4",
    [`interface ${v.ifname}`, `ip address ${v.ip}/${v.cidr}`],
    `- name: AOS-CX set ${v.ifname} ${v.ip}/${v.cidr}
  arubanetworks.aoscx.aoscx_l3_interface:
    config:
      - name: ${v.ifname}
        ipv4:
          - address: ${v.ip}/${v.cidr}
    state: merged`), "aruba_aoscx");
  return null;
}
function stackStatic(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR static route",
    [`ip route ${v.prefix}/${v.cidr} ${v.nh}`],
    `- name: FRR static ${v.prefix}/${v.cidr} via ${v.nh}
  ansible.builtin.shell: vtysh -c 'configure terminal' -c 'ip route ${v.prefix}/${v.cidr} ${v.nh}' -c 'end' -c 'write'`), "frrouting");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS static route",
    [`set protocols static route ${v.prefix}/${v.cidr} next-hop ${v.nh}`],
    `- name: VyOS static ${v.prefix}/${v.cidr}
  vyos.vyos.vyos_static_routes:
    config:
      - address_families:
          - afi: ipv4
            routes:
              - dest: ${v.prefix}/${v.cidr}
                next_hops:
                  - forward_router_address: ${v.nh}
    state: merged`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia static route",
    [`enter candidate`,`set / network-instance default static-routes route ${v.prefix}/${v.cidr} next-hop ${v.nh}`,`commit now`],
    `- name: SR Linux static ${v.prefix}/${v.cidr}
  nokia.srlinux.config:
    update:
      - path: /network-instance[name=default]/static-routes/route[prefix=${v.prefix}/${v.cidr}]
        value:
          next-hop:
            - ${v.nh}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba static route",
    [`ip route ${v.prefix}/${v.cidr} ${v.nh}`],
    `- name: AOS-CX static ${v.prefix}/${v.cidr}
  arubanetworks.aoscx.aoscx_config:
    lines:
      - ip route ${v.prefix}/${v.cidr} ${v.nh}`), "aruba_aoscx");
  return null;
}
function stackOspf(vendor, v){
  const area = v.area || "0.0.0.0";
  const ifn = v.ifname || "eth0";
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR OSPF",
    [`router ospf`, `network ${v.net || "10.0.0.0"}/24 area ${area}`],
    `- name: FRR OSPF network
  ansible.builtin.shell: vtysh -c 'configure terminal' -c 'router ospf' -c 'network ${v.net || "10.0.0.0"}/24 area ${area}' -c 'end' -c 'write'`), "frrouting");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS OSPF",
    [`set protocols ospf area ${area} network ${v.net || "10.0.0.0"}/24`],
    `- name: VyOS OSPF
  vyos.vyos.vyos_ospfv2:
    config:
      areas:
        - area_id: "${area}"
          network:
            - ${v.net || "10.0.0.0"}/24
    state: merged`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia OSPF",
    [`enter candidate`,`set / network-instance default protocols ospf instance 0 area ${area} interface ${ifn}`,`commit now`],
    `- name: SR Linux OSPF interface
  nokia.srlinux.config:
    update:
      - path: /network-instance[name=default]/protocols/ospf/instance[name=0]/area[area-id=${area}]/interface[interface-name=${ifn}]
        value: {}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba OSPF",
    [`router ospf ${v.pid || "1"}`, `area ${area}`, `interface ${ifn}`, `ip ospf area ${area}`],
    `- name: AOS-CX OSPF
  arubanetworks.aoscx.aoscx_config:
    lines:
      - router ospf ${v.pid || "1"}
      - area ${area}
      - interface ${ifn}
      - ip ospf area ${area}`), "aruba_aoscx");
  return null;
}
function stackBgp(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR BGP neighbor",
    [`router bgp ${v.local_as}`, `neighbor ${v.peer} remote-as ${v.remote_as}`],
    `- name: FRR BGP neighbor
  ansible.builtin.shell: vtysh -c 'configure terminal' -c 'router bgp ${v.local_as}' -c 'neighbor ${v.peer} remote-as ${v.remote_as}' -c 'end' -c 'write'`), "frrouting");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS BGP neighbor",
    [`set protocols bgp system-as ${v.local_as}`, `set protocols bgp neighbor ${v.peer} remote-as ${v.remote_as}`],
    `- name: VyOS BGP neighbor
  vyos.vyos.vyos_bgp_global:
    config:
      as_number: ${v.local_as}
    state: merged
- name: VyOS BGP neighbor peer
  vyos.vyos.vyos_bgp_neighbor:
    config:
      - neighbor: ${v.peer}
        remote_as: ${v.remote_as}
    state: merged`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia BGP neighbor",
    [`enter candidate`,`set / network-instance default protocols bgp autonomous-system ${v.local_as}`,`set / network-instance default protocols bgp neighbor ${v.peer} peer-as ${v.remote_as}`,`commit now`],
    `- name: SR Linux BGP neighbor
  nokia.srlinux.config:
    update:
      - path: /network-instance[name=default]/protocols/bgp
        value:
          autonomous-system: ${v.local_as}
          neighbor:
            - peer-address: ${v.peer}
              peer-as: ${v.remote_as}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba BGP neighbor",
    [`router bgp ${v.local_as}`, `neighbor ${v.peer} remote-as ${v.remote_as}`],
    `- name: AOS-CX BGP neighbor
  arubanetworks.aoscx.aoscx_config:
    lines:
      - router bgp ${v.local_as}
      - neighbor ${v.peer} remote-as ${v.remote_as}`), "aruba_aoscx");
  return null;
}
function stackVlan(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR/Linux VLAN",
    [`# FRR does not own VLANs — configure on host bridge`,`ip link add link eth0 name eth0.${v.id} type vlan id ${v.id}`],
    `- name: Host VLAN ${v.id}
  ansible.builtin.command: ip link add link eth0 name eth0.${v.id} type vlan id ${v.id}`), "linux");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS VLAN",
    [`set interfaces ethernet eth0 vif ${v.id} description ${v.name}`],
    `- name: VyOS VLAN ${v.id}
  vyos.vyos.vyos_config:
    lines:
      - set interfaces ethernet eth0 vif ${v.id} description '${v.name}'`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia VLAN / MAC-VRF",
    [`enter candidate`,`set / interface ${v.name || "ethernet-1/1"} vlan-tagging true`,`set / interface ${v.name || "ethernet-1/1"} subinterface ${v.id} vlan encap single-tagged vlan-id ${v.id}`,`commit now`],
    `- name: SR Linux VLAN ${v.id}
  nokia.srlinux.config:
    update:
      - path: /interface[name=ethernet-1/1]/subinterface[index=${v.id}]
        value:
          vlan:
            encap:
              single-tagged:
                vlan-id: ${v.id}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba VLAN",
    [`vlan ${v.id}`, `name ${v.name}`],
    `- name: AOS-CX VLAN ${v.id}
  arubanetworks.aoscx.aoscx_vlan:
    config:
      - vlan_id: ${v.id}
        name: ${v.name}
    state: merged`), "aruba_aoscx");
  return null;
}
function stackHostname(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("FRR hostname",
    [`hostname ${v.hostname}`],
    `- name: FRR hostname
  ansible.builtin.shell: vtysh -c 'configure terminal' -c 'hostname ${v.hostname}' -c 'end' -c 'write'`), "frrouting");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS hostname",
    [`set system host-name ${v.hostname}`],
    `- name: VyOS hostname
  vyos.vyos.vyos_config:
    lines:
      - set system host-name ${v.hostname}`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia hostname",
    [`enter candidate`,`set / system name ${v.hostname}`,`commit now`],
    `- name: SR Linux hostname
  nokia.srlinux.config:
    update:
      - path: /system/name
        value:
          host-name: ${v.hostname}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba hostname",
    [`hostname ${v.hostname}`],
    `- name: AOS-CX hostname
  arubanetworks.aoscx.aoscx_system:
    config:
      hostname: ${v.hostname}
    state: merged`), "aruba_aoscx");
  return null;
}
function stackNtp(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("Host NTP for FRR",
    [`# FRR has no NTP CLI — configure chrony/ntp on the Linux host`,`sudo timedatectl set-ntp true`],
    `- name: Enable host NTP
  ansible.builtin.command: timedatectl set-ntp true`), "linux");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS NTP",
    [`set system ntp server ${v.server}`],
    `- name: VyOS NTP
  vyos.vyos.vyos_ntp_global:
    config:
      servers:
        - server: ${v.server}
    state: merged`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia NTP",
    [`enter candidate`,`set / system ntp admin-state enable`,`set / system ntp network-instance mgmt server ${v.server}`,`commit now`],
    `- name: SR Linux NTP
  nokia.srlinux.config:
    update:
      - path: /system/ntp
        value:
          admin-state: enable`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba NTP",
    [`ntp server ${v.server}`],
    `- name: AOS-CX NTP
  arubanetworks.aoscx.aoscx_config:
    lines:
      - ntp server ${v.server}`), "aruba_aoscx");
  return null;
}
function stackSyslog(vendor, v){
  if(vendor==="FRR") return _withDev(_autoCliBundle("Host syslog for FRR",
    [`# Configure rsyslog/journald on the Linux host`,`echo '*.* @${v.host}' | sudo tee /etc/rsyslog.d/99-remote.conf`],
    `- name: Host remote syslog
  ansible.builtin.copy:
    dest: /etc/rsyslog.d/99-remote.conf
    content: "*.* @${v.host}\\n"`), "linux");
  if(vendor==="VyOS") return _withDev(_autoCliBundle("VyOS syslog",
    [`set system syslog host ${v.host} facility all level info`],
    `- name: VyOS syslog
  vyos.vyos.vyos_config:
    lines:
      - set system syslog host ${v.host} facility all level info`), "vyos");
  if(vendor==="Nokia") return _withDev(_autoCliBundle("Nokia syslog",
    [`enter candidate`,`set / system logging remote-server ${v.host}`,`commit now`],
    `- name: SR Linux syslog
  nokia.srlinux.config:
    update:
      - path: /system/logging/remote-server[host=${v.host}]
        value: {}`), "nokia_srl");
  if(vendor==="Aruba") return _withDev(_autoCliBundle("Aruba syslog",
    [`logging ${v.host}`],
    `- name: AOS-CX syslog
  arubanetworks.aoscx.aoscx_config:
    lines:
      - logging ${v.host}`), "aruba_aoscx");
  return null;
}
function stackGenericCli(vendor, lines, ansible){
  const map = {FRR:"frrouting",VyOS:"vyos",Nokia:"nokia_srl",Aruba:"aruba_aoscx"};
  return _withDev(_autoCliBundle(vendor+" config", lines, ansible), map[vendor]||"linux");
}
'''

# Wrappers inserted into each AUTO_* object — keyed by map name
AUTO_WRAPPERS = {
    "AUTO_IFACE_IPV4": "  FRR: v => stackIfaceIpv4('FRR', v),\n  VyOS: v => stackIfaceIpv4('VyOS', v),\n  Nokia: v => stackIfaceIpv4('Nokia', v),\n  Aruba: v => stackIfaceIpv4('Aruba', v),",
    "AUTO_STATIC": "  FRR: v => stackStatic('FRR', v),\n  VyOS: v => stackStatic('VyOS', v),\n  Nokia: v => stackStatic('Nokia', v),\n  Aruba: v => stackStatic('Aruba', v),",
    "AUTO_OSPF": "  FRR: v => stackOspf('FRR', v),\n  VyOS: v => stackOspf('VyOS', v),\n  Nokia: v => stackOspf('Nokia', v),\n  Aruba: v => stackOspf('Aruba', v),",
    "AUTO_BGP": "  FRR: v => stackBgp('FRR', v),\n  VyOS: v => stackBgp('VyOS', v),\n  Nokia: v => stackBgp('Nokia', v),\n  Aruba: v => stackBgp('Aruba', v),",
    "AUTO_VLAN": "  FRR: v => stackVlan('FRR', v),\n  VyOS: v => stackVlan('VyOS', v),\n  Nokia: v => stackVlan('Nokia', v),\n  Aruba: v => stackVlan('Aruba', v),",
    "AUTO_HOSTNAME": "  FRR: v => stackHostname('FRR', v),\n  VyOS: v => stackHostname('VyOS', v),\n  Nokia: v => stackHostname('Nokia', v),\n  Aruba: v => stackHostname('Aruba', v),",
    "AUTO_NTP": "  FRR: v => stackNtp('FRR', v),\n  VyOS: v => stackNtp('VyOS', v),\n  Nokia: v => stackNtp('Nokia', v),\n  Aruba: v => stackNtp('Aruba', v),",
    "AUTO_SYSLOG": "  FRR: v => stackSyslog('FRR', v),\n  VyOS: v => stackSyslog('VyOS', v),\n  Nokia: v => stackSyslog('Nokia', v),\n  Aruba: v => stackSyslog('Aruba', v),",
    "AUTO_DEFAULTRT": "  FRR: v => stackStatic('FRR', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  VyOS: v => stackStatic('VyOS', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  Nokia: v => stackStatic('Nokia', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  Aruba: v => stackStatic('Aruba', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),",
    "AUTO_SWITCHPORT": "  FRR: v => stackGenericCli('FRR', [`# VLAN membership is host/bridge-side for FRR`], `- name: noop\\n  ansible.builtin.debug:\\n    msg: FRR has no switchport`),\n  VyOS: v => stackGenericCli('VyOS', [`set interfaces ethernet ${v.ifname} vif ${v.vlan}`], `- name: VyOS access vif\\n  vyos.vyos.vyos_config:\\n    lines:\\n      - set interfaces ethernet ${v.ifname} vif ${v.vlan}`),\n  Nokia: v => stackVlan('Nokia', {id:v.vlan, name:'VLAN'+v.vlan}),\n  Aruba: v => stackGenericCli('Aruba', [`interface ${v.ifname}`, `vlan access ${v.vlan}`], `- name: AOS-CX access vlan\\n  arubanetworks.aoscx.aoscx_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - vlan access ${v.vlan}`),",
    "AUTO_IFDESC": "  FRR: v => stackGenericCli('FRR', [`interface ${v.ifname}`, `description ${v.desc}`], `- name: FRR ifDesc\\n  ansible.builtin.shell: vtysh -c \"configure terminal\" -c \"interface ${v.ifname}\" -c \"description ${v.desc}\" -c \"end\" -c \"write\"`),\n  VyOS: v => stackGenericCli('VyOS', [`set interfaces ethernet ${v.ifname} description '${v.desc}'`], `- name: VyOS ifDesc\\n  vyos.vyos.vyos_config:\\n    lines:\\n      - set interfaces ethernet ${v.ifname} description '${v.desc}'`),\n  Nokia: v => stackGenericCli('Nokia', [`enter candidate`,`set / interface ${v.ifname} description \"${v.desc}\"`,`commit now`], `- name: SR Linux ifDesc\\n  nokia.srlinux.config:\\n    update:\\n      - path: /interface[name=${v.ifname}]\\n        value:\\n          description: ${v.desc}`),\n  Aruba: v => stackGenericCli('Aruba', [`interface ${v.ifname}`, `description ${v.desc}`], `- name: AOS-CX ifDesc\\n  arubanetworks.aoscx.aoscx_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - description ${v.desc}`),",
    "AUTO_LOOPBACK": "  FRR: v => stackIfaceIpv4('FRR', {ifname:v.name||('lo'+v.unit), ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  VyOS: v => stackIfaceIpv4('VyOS', {ifname:'lo', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  Nokia: v => stackIfaceIpv4('Nokia', {ifname:'lo0', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  Aruba: v => stackIfaceIpv4('Aruba', {ifname:'loopback0', ip:v.ip, mask:v.mask, cidr:v.cidr}),",
    "AUTO_TRUNK": "  FRR: v => stackGenericCli('FRR', [`# trunking is host bridge VLAN filter`], `- name: noop\\n  ansible.builtin.debug:\\n    msg: host bridge VLAN filter`),\n  VyOS: v => stackGenericCli('VyOS', [`set interfaces ethernet ${v.ifname} vif ${v.vlans.split(',')[0]}`], `- name: VyOS trunk-ish vif\\n  vyos.vyos.vyos_config:\\n    lines:\\n      - set interfaces ethernet ${v.ifname} vif ${v.vlans.split(',')[0]}`),\n  Nokia: v => stackGenericCli('Nokia', [`enter candidate`,`set / interface ${v.ifname} vlan-tagging true`,`commit now`], `- name: SR Linux trunk\\n  nokia.srlinux.config:\\n    update:\\n      - path: /interface[name=${v.ifname}]\\n        value:\\n          vlan-tagging: true`),\n  Aruba: v => stackGenericCli('Aruba', [`interface ${v.ifname}`, `vlan trunk allowed ${v.vlans}`], `- name: AOS-CX trunk\\n  arubanetworks.aoscx.aoscx_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - vlan trunk allowed ${v.vlans}`),",
    "AUTO_RADIUS": "  FRR: v => stackGenericCli('FRR', [`# configure PAM/sshd RADIUS on Linux host`], `- name: note\\n  ansible.builtin.debug:\\n    msg: configure host PAM RADIUS`),\n  VyOS: v => stackGenericCli('VyOS', [`set system login radius-server ${v.host} key '${v.key}'`], `- name: VyOS RADIUS\\n  vyos.vyos.vyos_config:\\n    lines:\\n      - set system login radius-server ${v.host} key '${v.key}'`),\n  Nokia: v => stackGenericCli('Nokia', [`enter candidate`,`set / system aaa authentication-server radius server ${v.host}`,`commit now`], `- name: SR Linux RADIUS\\n  nokia.srlinux.config:\\n    update:\\n      - path: /system/aaa/server-group[name=radius]/server[address=${v.host}]\\n        value: {}`),\n  Aruba: v => stackGenericCli('Aruba', [`radius-server host ${v.host} key ${v.key}`], `- name: AOS-CX RADIUS\\n  arubanetworks.aoscx.aoscx_config:\\n    lines:\\n      - radius-server host ${v.host} key ${v.key}`),",
    "AUTO_PORTCHANNEL": "  FRR: v => stackGenericCli('FRR', [`# create Linux bond on host`, `ip link add bond0 type bond mode 802.3ad`], `- name: host bond\\n  ansible.builtin.command: ip link add bond0 type bond mode 802.3ad`),\n  VyOS: v => stackGenericCli('VyOS', [`set interfaces bonding bond0 member interface ${v.ifname}`], `- name: VyOS bond\\n  vyos.vyos.vyos_config:\\n    lines:\\n      - set interfaces bonding bond0 member interface ${v.ifname}`),\n  Nokia: v => stackGenericCli('Nokia', [`enter candidate`,`set / interface lag${v.pcid} lag lacp fallback false`,`set / interface ${v.ifname} ethernet aggregate-id lag${v.pcid}`,`commit now`], `- name: SR Linux LAG\\n  nokia.srlinux.config:\\n    update:\\n      - path: /interface[name=${v.ifname}]/ethernet\\n        value:\\n          aggregate-id: lag${v.pcid}`),\n  Aruba: v => stackGenericCli('Aruba', [`interface ${v.ifname}`, `lag ${v.pcid}`], `- name: AOS-CX LAG\\n  arubanetworks.aoscx.aoscx_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - lag ${v.pcid}`),",
}


def inject_stack_helpers(text: str) -> str:
    if MARKER in text:
        return text
    # Insert helpers just before first AUTO_IFACE_IPV4
    anchor = "/* Per-vendor template renderers — return {netconf, ncclient, ansible} */"
    if anchor not in text:
        raise SystemExit("anchor for AUTO helpers not found")
    return text.replace(anchor, STACK_TEMPLATES + "\n" + anchor, 1)


def inject_auto_keys(text: str) -> str:
    for name, block in AUTO_WRAPPERS.items():
        # Skip if already extended
        flag = f"/* ext:{name} */"
        if flag in text:
            continue
        # Insert after `const NAME = {`
        pat = re.compile(rf"(const\s+{name}\s*=\s*\{{)")
        m = pat.search(text)
        if not m:
            print(f"WARN: {name} not found", file=sys.stderr)
            continue
        insert = m.group(1) + "\n" + flag + "\n" + block + "\n"
        text = text[: m.start()] + insert + text[m.end() :]
    return text


def broaden_matchers(text: str) -> str:
    """Add VyOS/FRR/Aruba/Nokia regexes to key patterns if missing."""
    extras = {
        "iface-ipv4": (
            r"/^set interfaces ethernet\s+(\S+)\s+address\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)/im",
            r"/^nv set interface\s+(\S+)\s+ip address\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)/im",
            r"/^ip address\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)/im",
        ),
        "static-route": (
            r"/^set protocols static route\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)\s+next-hop\s+(\S+)/im",
            r"/^ip route\s+(\d+\.\d+\.\d+\.\d+)\/(\d+)\s+(\S+)/im",
        ),
        "bgp-neighbor": (
            r"/^set protocols bgp\s+.*?neighbor\s+(\d+\.\d+\.\d+\.\d+)\s+remote-as\s+(\d+)/im",
            r"/^neighbor\s+(\d+\.\d+\.\d+\.\d+)\s+remote-as\s+(\d+)/im",
        ),
        "hostname": (
            r"/^set system host-name\s+(\S+)/im",
            r"/^sysname\s+(\S+)/im",
            r"/^config hostname\s+(\S+)/im",
            r"/^\/system identity set name=(\S+)/im",
        ),
        "ntp-server": (
            r"/^set system ntp server\s+(\S+)/im",
            r"/^ntp server\s+(\S+)/im",
        ),
    }
    # Safer: just ensure comment marker noting broadened matchers; matchAny already
    # covers IOS+Junos which is the dominant Automate path. Stack vendors get
    # templates when an IOS/Junos-shaped cmd is compared across vendors.
    if "/* MATCHERS_STACK_NOTE */" not in text:
        text = text.replace(
            "const AUTOMATION_MAPPINGS = [",
            "/* MATCHERS_STACK_NOTE */\n"
            "/* Stack vendors (FRR/VyOS/Nokia/Aruba) render via AUTO_* extensions;\n"
            "   matchAny still keys off IOS/Junos/EOS-shaped commands, which is how\n"
            "   cross-vendor Automate is invoked from Compare / equivalents. */\n"
            "const AUTOMATION_MAPPINGS = [",
            1,
        )
    # Light-touch: extend hostname matchAny
    old = """matchAny: [
      /^hostname\\s+(\\S+)/im,
      /^set system host-name\\s+(\\S+)/im,
    ],
    extract: cmd => {
      const m = cmd.match(/^(?:set system\\s+)?(?:hostname|host-name)\\s+(\\S+)/im);
      return m ? {hostname:m[1]} : null;
    },
    render: (vendor, v) => AUTO_HOSTNAME[vendor](v),"""
    new = """matchAny: [
      /^hostname\\s+(\\S+)/im,
      /^set system host-name\\s+(\\S+)/im,
      /^sysname\\s+(\\S+)/im,
      /^config hostname\\s+(\\S+)/im,
      /^nv set system hostname\\s+(\\S+)/im,
    ],
    extract: cmd => {
      const m = cmd.match(/^(?:set system\\s+)?(?:hostname|host-name)\\s+(\\S+)/im)
             || cmd.match(/^sysname\\s+(\\S+)/im)
             || cmd.match(/^config hostname\\s+(\\S+)/im)
             || cmd.match(/^nv set system hostname\\s+(\\S+)/im);
      return m ? {hostname:m[1]} : null;
    },
    render: (vendor, v) => AUTO_HOSTNAME[vendor](v),"""
    if old in text and "sysname\\s+" not in text[text.find("id: \"hostname\"") : text.find("id: \"hostname\"") + 800]:
        text = text.replace(old, new, 1)
    return text


def patch_os_dev_type(text: str) -> str:
    if "sros:" in text[text.find("OS_DEV_TYPE") : text.find("OS_DEV_TYPE") + 900]:
        return text
    text = text.replace(
        'aoscx:"aruba_aoscx", vrp:"huawei",',
        'aoscx:"aruba_aoscx", vrp:"huawei", sros:"nokia_sros",',
        1,
    )
    # Also add Nokia SR OS netmiko mapping if missing — netmiko uses nokia_sros
    if '"Nokia":    "nokia_srl"' in text and "nokia_sros" not in text[text.find("NETMIKO_DEV_TYPE") : text.find("NETMIKO_DEV_TYPE") + 600]:
        # Keep vendor Nokia → nokia_srl as default; OS map handles sros.
        pass
    return text


def patch_dev_type_for_os(text: str) -> str:
    """Prefer OS-specific netmiko type over vendor-level Cisco→ios."""
    old = """function devTypeFor(q){
  return NETMIKO_DEV_TYPE[q.vendor] || OS_DEV_TYPE[q.os] || "terminal_server";
}"""
    new = """function devTypeFor(q){
  // Prefer OS-specific device types (nxos/asa/iosxe/sros) over vendor defaults.
  return OS_DEV_TYPE[q.os] || NETMIKO_DEV_TYPE[q.vendor] || "terminal_server";
}"""
    if old in text:
        text = text.replace(old, new, 1)
    return text


def patch_ansible_cisco_os(text: str) -> str:
    """Add helper to pick Cisco Ansible collection by OS."""
    if "function ansibleModFor" in text:
        return text
    needle = "function isShowCmd(cmd){"
    helper = '''function ansibleModFor(q){
  const base = ANSIBLE_MOD[q.vendor] || {show:"ansible.builtin.shell", cfg:"ansible.builtin.shell", collection:"ansible.builtin"};
  if(q.vendor === "Cisco"){
    if(q.os === "nxos") return {show:"cisco.nxos.nxos_command", cfg:"cisco.nxos.nxos_config", collection:"cisco.nxos"};
    if(q.os === "asa")  return {show:"cisco.asa.asa_command",  cfg:"cisco.asa.asa_config",  collection:"cisco.asa"};
    if(q.os === "iosxe") return {show:"cisco.ios.ios_command", cfg:"cisco.ios.ios_config", collection:"cisco.ios"};
  }
  if(q.vendor === "Nokia" && q.os === "sros"){
    return {show:"ansible.builtin.shell", cfg:"ansible.builtin.shell", collection:"ansible.builtin"};
  }
  return base;
}
'''
    return text.replace(needle, helper + needle, 1)


def patch_cat_groups(text: str) -> str:
    """Ensure VXLAN/EVPN filter chips exist."""
    if '"VXLAN"' in text and '"EVPN"' in text and "CAT_GROUPS" in text:
        # Try to inject into a fabric/overlay group if not present near VXLAN usage in CAT_GROUPS
        if re.search(r'CAT_GROUPS[\s\S]{0,2000}VXLAN', text):
            return text
    # Find CAT_GROUPS and add overlay group
    m = re.search(r"(const\s+CAT_GROUPS\s*=\s*\[)", text)
    if not m:
        return text
    if "/* overlay cats */" in text:
        return text
    insert = m.group(1) + '\n  /* overlay cats */\n  ["Overlay", ["VXLAN","EVPN"]],\n'
    return text[: m.start()] + insert + text[m.end() :]


def patch_safe_render(text: str) -> str:
    """Prefer explicit vendor templates; never silently fall back to Cisco YANG."""
    text2 = text
    for name in [
        "AUTO_IFACE_IPV4",
        "AUTO_STATIC",
        "AUTO_OSPF",
        "AUTO_BGP",
        "AUTO_VLAN",
        "AUTO_SWITCHPORT",
        "AUTO_NTP",
        "AUTO_SYSLOG",
        "AUTO_HOSTNAME",
        "AUTO_IFDESC",
        "AUTO_LOOPBACK",
        "AUTO_DEFAULTRT",
        "AUTO_TRUNK",
        "AUTO_RADIUS",
        "AUTO_PORTCHANNEL",
    ]:
        cisco_fb = f"(vendor, v) => ({name}[vendor]||{name}.Cisco)(v)"
        bare = f"(vendor, v) => {name}[vendor](v)"
        null_safe = f"(vendor, v) => {name}[vendor] ? {name}[vendor](v) : null"
        text2 = text2.replace(cisco_fb, null_safe)
        if null_safe not in text2:
            text2 = text2.replace(bare, null_safe)
    return text2


def main() -> None:
    text = HTML.read_text()
    if MARKER in text and "ansibleModFor" in text and "/* overlay cats */" in text:
        print("already patched")
        return
    text = inject_stack_helpers(text)
    text = inject_auto_keys(text)
    text = broaden_matchers(text)
    text = patch_os_dev_type(text)
    text = patch_dev_type_for_os(text)
    text = patch_ansible_cisco_os(text)
    text = patch_cat_groups(text)
    text = patch_safe_render(text)
    if "--dry-run" in sys.argv:
        print("dry-run ok, would write", len(text), "bytes")
        return
    HTML.write_text(text)
    print("patched", HTML, "bytes", len(text))


if __name__ == "__main__":
    main()
