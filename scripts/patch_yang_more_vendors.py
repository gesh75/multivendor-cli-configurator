#!/usr/bin/env python3
"""
patch_yang_more_vendors.py — close Automate fallback gaps.

Previously Huawei / NVIDIA / SONiC / Extreme / Mikrotik fell through to
AUTO_*.Cisco (dangerous YANG/IOS snippets). This pass injects CLI-first
Netmiko/Ansible renderers for those vendors into every AUTO_* map.

Idempotent via /* MORE_VENDOR_AUTO_EXT */ marker.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = ROOT / "index.html"
MARKER = "/* MORE_VENDOR_AUTO_EXT — Huawei/NVIDIA/SONiC/Extreme/Mikrotik */"

MORE_HELPERS = r'''
/* MORE_VENDOR_AUTO_EXT — Huawei/NVIDIA/SONiC/Extreme/Mikrotik */
function moreIfaceIpv4(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei VRP interface IPv4",
    [`system-view`,`interface ${v.ifname}`,`ip address ${v.ip} ${v.mask}`,`quit`],
    `- name: VRP IPv4 ${v.ifname}
  community.network.ce_config:
    lines:
      - interface ${v.ifname}
      - ip address ${v.ip} ${v.mask}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVIDIA NVUE interface IPv4",
    [`nv set interface ${v.ifname} ip address ${v.ip}/${v.cidr}`,`nv config apply`],
    `- name: NVUE IPv4 ${v.ifname}
  nvidia.nvue.command:
    commands:
      - nv set interface ${v.ifname} ip address ${v.ip}/${v.cidr}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC interface IPv4",
    [`sudo config interface ip add ${v.ifname} ${v.ip}/${v.cidr}`],
    `- name: SONiC IPv4 ${v.ifname}
  ansible.builtin.shell: sudo config interface ip add ${v.ifname} ${v.ip}/${v.cidr}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("Extreme EXOS interface IPv4",
    [`configure vlan ${v.ifname} ipaddress ${v.ip} ${v.mask}`],
    `- name: EXOS IPv4
  community.network.exos_config:
    lines:
      - configure vlan ${v.ifname} ipaddress ${v.ip} ${v.mask}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS interface IPv4",
    [`/ip address add address=${v.ip}/${v.cidr} interface=${v.ifname}`],
    `- name: RouterOS IPv4
  community.routeros.command:
    commands:
      - /ip address add address=${v.ip}/${v.cidr} interface=${v.ifname}`), "mikrotik_routeros");
  return null;
}
function moreStatic(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei static route",
    [`system-view`,`ip route-static ${v.prefix} ${v.mask} ${v.nh}`],
    `- name: VRP static
  community.network.ce_config:
    lines:
      - ip route-static ${v.prefix} ${v.mask} ${v.nh}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE static route",
    [`nv set vrf default router static ${v.prefix}/${v.cidr} via ${v.nh}`,`nv config apply`],
    `- name: NVUE static
  nvidia.nvue.command:
    commands:
      - nv set vrf default router static ${v.prefix}/${v.cidr} via ${v.nh}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC static route",
    [`sudo config route add prefix ${v.prefix}/${v.cidr} nexthop ${v.nh}`],
    `- name: SONiC static
  ansible.builtin.shell: sudo config route add prefix ${v.prefix}/${v.cidr} nexthop ${v.nh}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS static route",
    [`configure iproute add ${v.prefix} ${v.mask} ${v.nh}`],
    `- name: EXOS static
  community.network.exos_config:
    lines:
      - configure iproute add ${v.prefix} ${v.mask} ${v.nh}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS static route",
    [`/ip route add dst-address=${v.prefix}/${v.cidr} gateway=${v.nh}`],
    `- name: RouterOS static
  community.routeros.command:
    commands:
      - /ip route add dst-address=${v.prefix}/${v.cidr} gateway=${v.nh}`), "mikrotik_routeros");
  return null;
}
function moreOspf(vendor, v){
  const area = v.area || "0.0.0.0";
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei OSPF",
    [`system-view`,`ospf 1`,`area ${area}`,`network ${v.net || "10.0.0.0"} ${v.wildcard || "0.0.0.255"}`],
    `- name: VRP OSPF
  community.network.ce_config:
    lines:
      - ospf 1
      - area ${area}
      - network ${v.net || "10.0.0.0"} ${v.wildcard || "0.0.0.255"}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE OSPF",
    [`nv set vrf default router ospf area ${area}`,`nv config apply`],
    `- name: NVUE OSPF
  nvidia.nvue.command:
    commands:
      - nv set vrf default router ospf area ${area}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC OSPF via FRR vtysh",
    [`sudo vtysh -c 'configure terminal' -c 'router ospf' -c 'network ${v.net || "10.0.0.0"}/24 area ${area}' -c 'end' -c 'write'`],
    `- name: SONiC OSPF
  ansible.builtin.shell: sudo vtysh -c 'configure terminal' -c 'router ospf' -c 'network ${v.net || "10.0.0.0"}/24 area ${area}' -c 'end' -c 'write'`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS OSPF",
    [`enable ospf`,`configure ospf add vlan ${v.ifname || "UNDERLAY"} area ${area}`],
    `- name: EXOS OSPF
  community.network.exos_config:
    lines:
      - enable ospf
      - configure ospf add vlan ${v.ifname || "UNDERLAY"} area ${area}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS OSPF",
    [`/routing ospf instance add name=def redistribute=connected`,`/routing ospf interface-template add interfaces=${v.ifname} area=backbone`],
    `- name: RouterOS OSPF
  community.routeros.command:
    commands:
      - /routing ospf instance add name=def redistribute=connected`), "mikrotik_routeros");
  return null;
}
function moreBgp(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei BGP neighbor",
    [`system-view`,`bgp ${v.local_as}`,`peer ${v.peer} as-number ${v.remote_as}`],
    `- name: VRP BGP
  community.network.ce_config:
    lines:
      - bgp ${v.local_as}
      - peer ${v.peer} as-number ${v.remote_as}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE BGP neighbor",
    [`nv set vrf default router bgp autonomous-system ${v.local_as}`,`nv set vrf default router bgp neighbor ${v.peer} remote-as ${v.remote_as}`,`nv config apply`],
    `- name: NVUE BGP
  nvidia.nvue.command:
    commands:
      - nv set vrf default router bgp autonomous-system ${v.local_as}
      - nv set vrf default router bgp neighbor ${v.peer} remote-as ${v.remote_as}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC BGP neighbor",
    [`sudo config bgp autonomous-system ${v.local_as}`,`sudo config bgp neighbor add ${v.peer} remote-as ${v.remote_as}`],
    `- name: SONiC BGP
  ansible.builtin.shell: |
    sudo config bgp autonomous-system ${v.local_as}
    sudo config bgp neighbor add ${v.peer} remote-as ${v.remote_as}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS BGP neighbor",
    [`enable bgp`,`configure bgp as-number ${v.local_as}`,`configure bgp add neighbor ${v.peer} remote-as ${v.remote_as}`],
    `- name: EXOS BGP
  community.network.exos_config:
    lines:
      - enable bgp
      - configure bgp as-number ${v.local_as}
      - configure bgp add neighbor ${v.peer} remote-as ${v.remote_as}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS BGP neighbor",
    [`/routing bgp connection add name=to-peer remote.address=${v.peer} remote.as=${v.remote_as} local.role=ebgp`],
    `- name: RouterOS BGP
  community.routeros.command:
    commands:
      - /routing bgp connection add name=to-peer remote.address=${v.peer} remote.as=${v.remote_as} local.role=ebgp`), "mikrotik_routeros");
  return null;
}
function moreVlan(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei VLAN",
    [`system-view`,`vlan ${v.id}`,`name ${v.name}`],
    `- name: VRP VLAN
  community.network.ce_config:
    lines:
      - vlan ${v.id}
      - name ${v.name}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE VLAN",
    [`nv set bridge domain br_default vlan ${v.id}`,`nv config apply`],
    `- name: NVUE VLAN
  nvidia.nvue.command:
    commands:
      - nv set bridge domain br_default vlan ${v.id}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC VLAN",
    [`sudo config vlan add ${v.id}`],
    `- name: SONiC VLAN
  ansible.builtin.shell: sudo config vlan add ${v.id}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS VLAN",
    [`create vlan ${v.name} tag ${v.id}`],
    `- name: EXOS VLAN
  community.network.exos_config:
    lines:
      - create vlan ${v.name} tag ${v.id}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS VLAN",
    [`/interface vlan add name=${v.name} vlan-id=${v.id} interface=bridge1`],
    `- name: RouterOS VLAN
  community.routeros.command:
    commands:
      - /interface vlan add name=${v.name} vlan-id=${v.id} interface=bridge1`), "mikrotik_routeros");
  return null;
}
function moreHostname(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei sysname",
    [`system-view`,`sysname ${v.hostname}`],
    `- name: VRP sysname
  community.network.ce_config:
    lines:
      - sysname ${v.hostname}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE hostname",
    [`nv set system hostname ${v.hostname}`,`nv config apply`],
    `- name: NVUE hostname
  nvidia.nvue.command:
    commands:
      - nv set system hostname ${v.hostname}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC hostname",
    [`sudo config hostname ${v.hostname}`],
    `- name: SONiC hostname
  ansible.builtin.shell: sudo config hostname ${v.hostname}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS hostname",
    [`configure snmp sysName ${v.hostname}`],
    `- name: EXOS hostname
  community.network.exos_config:
    lines:
      - configure snmp sysName ${v.hostname}`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS identity",
    [`/system identity set name=${v.hostname}`],
    `- name: RouterOS identity
  community.routeros.command:
    commands:
      - /system identity set name=${v.hostname}`), "mikrotik_routeros");
  return null;
}
function moreNtp(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei NTP",
    [`system-view`,`ntp-service unicast-server ${v.server}`],
    `- name: VRP NTP
  community.network.ce_config:
    lines:
      - ntp-service unicast-server ${v.server}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE NTP",
    [`nv set system ntp server ${v.server}`,`nv config apply`],
    `- name: NVUE NTP
  nvidia.nvue.command:
    commands:
      - nv set system ntp server ${v.server}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC NTP",
    [`sudo config ntp add ${v.server}`],
    `- name: SONiC NTP
  ansible.builtin.shell: sudo config ntp add ${v.server}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS NTP",
    [`configure ntp server add ${v.server}`,`enable ntp`],
    `- name: EXOS NTP
  community.network.exos_config:
    lines:
      - configure ntp server add ${v.server}
      - enable ntp`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS NTP",
    [`/system ntp client set enabled=yes servers=${v.server}`],
    `- name: RouterOS NTP
  community.routeros.command:
    commands:
      - /system ntp client set enabled=yes servers=${v.server}`), "mikrotik_routeros");
  return null;
}
function moreSyslog(vendor, v){
  if(vendor==="Huawei") return _withDev(_autoCliBundle("Huawei syslog",
    [`system-view`,`info-center loghost ${v.host}`],
    `- name: VRP syslog
  community.network.ce_config:
    lines:
      - info-center loghost ${v.host}`), "huawei");
  if(vendor==="NVIDIA") return _withDev(_autoCliBundle("NVUE syslog",
    [`nv set system syslog server ${v.host}`,`nv config apply`],
    `- name: NVUE syslog
  nvidia.nvue.command:
    commands:
      - nv set system syslog server ${v.host}
      - nv config apply`), "linux");
  if(vendor==="SONiC") return _withDev(_autoCliBundle("SONiC syslog",
    [`sudo config syslog add ${v.host}`],
    `- name: SONiC syslog
  ansible.builtin.shell: sudo config syslog add ${v.host}`), "linux");
  if(vendor==="Extreme") return _withDev(_autoCliBundle("EXOS syslog",
    [`configure syslog add ${v.host} local use-local-time`],
    `- name: EXOS syslog
  community.network.exos_config:
    lines:
      - configure syslog add ${v.host} local use-local-time`), "extreme_exos");
  if(vendor==="Mikrotik") return _withDev(_autoCliBundle("RouterOS syslog",
    [`/system logging action set remote remote=${v.host}`],
    `- name: RouterOS syslog
  community.routeros.command:
    commands:
      - /system logging action set remote remote=${v.host}`), "mikrotik_routeros");
  return null;
}
function moreGeneric(vendor, lines, ansible, dev){
  return _withDev(_autoCliBundle(vendor+" config", lines, ansible), dev);
}
'''

MORE_WRAPPERS = {
    "AUTO_IFACE_IPV4": "  Huawei: v => moreIfaceIpv4('Huawei', v),\n  NVIDIA: v => moreIfaceIpv4('NVIDIA', v),\n  SONiC: v => moreIfaceIpv4('SONiC', v),\n  Extreme: v => moreIfaceIpv4('Extreme', v),\n  Mikrotik: v => moreIfaceIpv4('Mikrotik', v),",
    "AUTO_STATIC": "  Huawei: v => moreStatic('Huawei', v),\n  NVIDIA: v => moreStatic('NVIDIA', v),\n  SONiC: v => moreStatic('SONiC', v),\n  Extreme: v => moreStatic('Extreme', v),\n  Mikrotik: v => moreStatic('Mikrotik', v),",
    "AUTO_OSPF": "  Huawei: v => moreOspf('Huawei', v),\n  NVIDIA: v => moreOspf('NVIDIA', v),\n  SONiC: v => moreOspf('SONiC', v),\n  Extreme: v => moreOspf('Extreme', v),\n  Mikrotik: v => moreOspf('Mikrotik', v),",
    "AUTO_BGP": "  Huawei: v => moreBgp('Huawei', v),\n  NVIDIA: v => moreBgp('NVIDIA', v),\n  SONiC: v => moreBgp('SONiC', v),\n  Extreme: v => moreBgp('Extreme', v),\n  Mikrotik: v => moreBgp('Mikrotik', v),",
    "AUTO_VLAN": "  Huawei: v => moreVlan('Huawei', v),\n  NVIDIA: v => moreVlan('NVIDIA', v),\n  SONiC: v => moreVlan('SONiC', v),\n  Extreme: v => moreVlan('Extreme', v),\n  Mikrotik: v => moreVlan('Mikrotik', v),",
    "AUTO_HOSTNAME": "  Huawei: v => moreHostname('Huawei', v),\n  NVIDIA: v => moreHostname('NVIDIA', v),\n  SONiC: v => moreHostname('SONiC', v),\n  Extreme: v => moreHostname('Extreme', v),\n  Mikrotik: v => moreHostname('Mikrotik', v),",
    "AUTO_NTP": "  Huawei: v => moreNtp('Huawei', v),\n  NVIDIA: v => moreNtp('NVIDIA', v),\n  SONiC: v => moreNtp('SONiC', v),\n  Extreme: v => moreNtp('Extreme', v),\n  Mikrotik: v => moreNtp('Mikrotik', v),",
    "AUTO_SYSLOG": "  Huawei: v => moreSyslog('Huawei', v),\n  NVIDIA: v => moreSyslog('NVIDIA', v),\n  SONiC: v => moreSyslog('SONiC', v),\n  Extreme: v => moreSyslog('Extreme', v),\n  Mikrotik: v => moreSyslog('Mikrotik', v),",
    "AUTO_DEFAULTRT": "  Huawei: v => moreStatic('Huawei', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  NVIDIA: v => moreStatic('NVIDIA', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  SONiC: v => moreStatic('SONiC', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  Extreme: v => moreStatic('Extreme', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),\n  Mikrotik: v => moreStatic('Mikrotik', {prefix:'0.0.0.0', cidr:'0', mask:'0.0.0.0', nh:v.nh}),",
    "AUTO_LOOPBACK": "  Huawei: v => moreIfaceIpv4('Huawei', {ifname:v.name||'LoopBack0', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  NVIDIA: v => moreIfaceIpv4('NVIDIA', {ifname:v.name||'lo', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  SONiC: v => moreIfaceIpv4('SONiC', {ifname:v.name||'Loopback0', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  Extreme: v => moreIfaceIpv4('Extreme', {ifname:v.name||'Default', ip:v.ip, mask:v.mask, cidr:v.cidr}),\n  Mikrotik: v => moreIfaceIpv4('Mikrotik', {ifname:v.name||'bridge1', ip:v.ip, mask:v.mask, cidr:v.cidr}),",
    "AUTO_SWITCHPORT": "  Huawei: v => moreGeneric('Huawei', [`system-view`,`interface ${v.ifname}`,`port link-type access`,`port default vlan ${v.vlan}`], `- name: VRP access\\n  community.network.ce_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - port default vlan ${v.vlan}`, 'huawei'),\n  NVIDIA: v => moreGeneric('NVIDIA', [`nv set interface ${v.ifname} bridge domain br_default access ${v.vlan}`,`nv config apply`], `- name: NVUE access\\n  nvidia.nvue.command:\\n    commands: ['nv set interface ${v.ifname} bridge domain br_default access ${v.vlan}','nv config apply']`, 'linux'),\n  SONiC: v => moreGeneric('SONiC', [`sudo config vlan member add ${v.vlan} ${v.ifname}`], `- name: SONiC access\\n  ansible.builtin.shell: sudo config vlan member add ${v.vlan} ${v.ifname}`, 'linux'),\n  Extreme: v => moreGeneric('Extreme', [`configure vlan ${v.vlan} add ports ${v.ifname} untagged`], `- name: EXOS access\\n  community.network.exos_config:\\n    lines:\\n      - configure vlan ${v.vlan} add ports ${v.ifname} untagged`, 'extreme_exos'),\n  Mikrotik: v => moreGeneric('Mikrotik', [`/interface bridge port set [find interface=${v.ifname}] pvid=${v.vlan}`], `- name: RouterOS access\\n  community.routeros.command:\\n    commands: ['/interface bridge port set [find interface=${v.ifname}] pvid=${v.vlan}']`, 'mikrotik_routeros'),",
    "AUTO_IFDESC": "  Huawei: v => moreGeneric('Huawei', [`system-view`,`interface ${v.ifname}`,`description ${v.desc}`], `- name: VRP ifDesc\\n  community.network.ce_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - description ${v.desc}`, 'huawei'),\n  NVIDIA: v => moreGeneric('NVIDIA', [`nv set interface ${v.ifname} description '${v.desc}'`,`nv config apply`], `- name: NVUE ifDesc\\n  nvidia.nvue.command:\\n    commands: [\"nv set interface ${v.ifname} description '${v.desc}'\",'nv config apply']`, 'linux'),\n  SONiC: v => moreGeneric('SONiC', [`sudo config interface description ${v.ifname} '${v.desc}'`], `- name: SONiC ifDesc\\n  ansible.builtin.shell: sudo config interface description ${v.ifname} '${v.desc}'`, 'linux'),\n  Extreme: v => moreGeneric('Extreme', [`configure ports ${v.ifname} display-string ${v.desc}`], `- name: EXOS ifDesc\\n  community.network.exos_config:\\n    lines:\\n      - configure ports ${v.ifname} display-string ${v.desc}`, 'extreme_exos'),\n  Mikrotik: v => moreGeneric('Mikrotik', [`/interface set ${v.ifname} comment=\"${v.desc}\"`], `- name: RouterOS ifDesc\\n  community.routeros.command:\\n    commands: ['/interface set ${v.ifname} comment=\"${v.desc}\"']`, 'mikrotik_routeros'),",
    "AUTO_TRUNK": "  Huawei: v => moreGeneric('Huawei', [`system-view`,`interface ${v.ifname}`,`port link-type trunk`,`port trunk allow-pass vlan ${v.vlans}`], `- name: VRP trunk\\n  community.network.ce_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - port trunk allow-pass vlan ${v.vlans}`, 'huawei'),\n  NVIDIA: v => moreGeneric('NVIDIA', [`nv set interface ${v.ifname} bridge domain br_default vlan ${v.vlans}`,`nv config apply`], `- name: NVUE trunk\\n  nvidia.nvue.command:\\n    commands: ['nv set interface ${v.ifname} bridge domain br_default vlan ${v.vlans}','nv config apply']`, 'linux'),\n  SONiC: v => moreGeneric('SONiC', [`sudo config vlan member add ${v.vlans.split(',')[0]} ${v.ifname} -t`], `- name: SONiC trunk\\n  ansible.builtin.shell: sudo config vlan member add ${v.vlans.split(',')[0]} ${v.ifname} -t`, 'linux'),\n  Extreme: v => moreGeneric('Extreme', [`configure vlan ${v.vlans.split(',')[0]} add ports ${v.ifname} tagged`], `- name: EXOS trunk\\n  community.network.exos_config:\\n    lines:\\n      - configure vlan ${v.vlans.split(',')[0]} add ports ${v.ifname} tagged`, 'extreme_exos'),\n  Mikrotik: v => moreGeneric('Mikrotik', [`/interface bridge vlan add bridge=bridge1 tagged=${v.ifname} vlan-ids=${v.vlans}`], `- name: RouterOS trunk\\n  community.routeros.command:\\n    commands: ['/interface bridge vlan add bridge=bridge1 tagged=${v.ifname} vlan-ids=${v.vlans}']`, 'mikrotik_routeros'),",
    "AUTO_RADIUS": "  Huawei: v => moreGeneric('Huawei', [`system-view`,`radius-server template AAA`,`radius-server shared-key cipher ${v.key}`,`radius-server authentication ${v.host}`], `- name: VRP RADIUS\\n  community.network.ce_config:\\n    lines:\\n      - radius-server authentication ${v.host}`, 'huawei'),\n  NVIDIA: v => moreGeneric('NVIDIA', [`nv set system aaa authentication-order radius`,`nv config apply`], `- name: NVUE RADIUS note\\n  nvidia.nvue.command:\\n    commands: ['nv set system aaa authentication-order radius','nv config apply']`, 'linux'),\n  SONiC: v => moreGeneric('SONiC', [`# configure host PAM/RADIUS for SONiC mgmt plane`], `- name: SONiC RADIUS note\\n  ansible.builtin.debug:\\n    msg: configure host PAM RADIUS`, 'linux'),\n  Extreme: v => moreGeneric('Extreme', [`configure radius-server add ${v.host} shared-secret ${v.key}`], `- name: EXOS RADIUS\\n  community.network.exos_config:\\n    lines:\\n      - configure radius-server add ${v.host} shared-secret ${v.key}`, 'extreme_exos'),\n  Mikrotik: v => moreGeneric('Mikrotik', [`/radius add address=${v.host} secret=${v.key} service=login`], `- name: RouterOS RADIUS\\n  community.routeros.command:\\n    commands: ['/radius add address=${v.host} secret=${v.key} service=login']`, 'mikrotik_routeros'),",
    "AUTO_PORTCHANNEL": "  Huawei: v => moreGeneric('Huawei', [`system-view`,`interface Eth-Trunk${v.pcid}`,`mode lacp-static`,`quit`,`interface ${v.ifname}`,`eth-trunk ${v.pcid}`], `- name: VRP Eth-Trunk\\n  community.network.ce_config:\\n    lines:\\n      - interface ${v.ifname}\\n      - eth-trunk ${v.pcid}`, 'huawei'),\n  NVIDIA: v => moreGeneric('NVIDIA', [`nv set interface bond${v.pcid} bond member ${v.ifname}`,`nv config apply`], `- name: NVUE bond\\n  nvidia.nvue.command:\\n    commands: ['nv set interface bond${v.pcid} bond member ${v.ifname}','nv config apply']`, 'linux'),\n  SONiC: v => moreGeneric('SONiC', [`sudo config portchannel add PortChannel${v.pcid}`,`sudo config portchannel member add PortChannel${v.pcid} ${v.ifname}`], `- name: SONiC LAG\\n  ansible.builtin.shell: |\\n    sudo config portchannel add PortChannel${v.pcid}\\n    sudo config portchannel member add PortChannel${v.pcid} ${v.ifname}`, 'linux'),\n  Extreme: v => moreGeneric('Extreme', [`enable sharing ${v.pcid} grouping ${v.ifname} algorithm address-based L3_L4 lacp`], `- name: EXOS LAG\\n  community.network.exos_config:\\n    lines:\\n      - enable sharing ${v.pcid} grouping ${v.ifname} algorithm address-based L3_L4 lacp`, 'extreme_exos'),\n  Mikrotik: v => moreGeneric('Mikrotik', [`/interface bonding add name=bond${v.pcid} slaves=${v.ifname} mode=802.3ad`], `- name: RouterOS bond\\n  community.routeros.command:\\n    commands: ['/interface bonding add name=bond${v.pcid} slaves=${v.ifname} mode=802.3ad']`, 'mikrotik_routeros'),",
}


def inject_helpers(text: str) -> str:
    if MARKER in text:
        return text
    anchor = "/* Per-vendor template renderers — return {netconf, ncclient, ansible} */"
    if anchor not in text:
        raise SystemExit("AUTO renderer anchor not found")
    return text.replace(anchor, MORE_HELPERS + "\n" + anchor, 1)


def inject_keys(text: str) -> str:
    for name, block in MORE_WRAPPERS.items():
        flag = f"/* more:{name} */"
        if flag in text:
            continue
        # Prefer inserting after existing stack ext flag, else after const {
        stack_flag = f"/* ext:{name} */"
        if stack_flag in text:
            # insert after the stack wrapper block — find flag and insert after next blank-ish
            idx = text.find(stack_flag)
            # find end of first vendor block cluster: look for blank line after Aruba/FRR keys
            # Simpler: insert right after the flag line
            nl = text.find("\n", idx)
            insert_at = nl + 1
            text = text[:insert_at] + flag + "\n" + block + "\n" + text[insert_at:]
            continue
        m = re.search(rf"(const\s+{name}\s*=\s*\{{)", text)
        if not m:
            print(f"WARN: {name} not found", file=sys.stderr)
            continue
        insert = m.group(1) + "\n" + flag + "\n" + block + "\n"
        text = text[: m.start()] + insert + text[m.end() :]
    return text


def main() -> None:
    text = HTML.read_text()
    if MARKER in text and all(f"/* more:{n} */" in text for n in MORE_WRAPPERS):
        print("already patched")
        return
    text = inject_helpers(text)
    text = inject_keys(text)
    if "--dry-run" in sys.argv:
        print("dry-run ok, would write", len(text), "bytes")
        return
    HTML.write_text(text)
    print("patched", HTML, "bytes", len(text))


if __name__ == "__main__":
    main()
