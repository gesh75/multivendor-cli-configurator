#!/usr/bin/env python3
"""
expand_thin_vendors.py — grow thin vendor / topic surfaces identified in gap analysis.

Adds curated, publicly-documented CLI for:
  - Nokia SR OS (beyond shell builtins)
  - SONiC (OSPF, VXLAN/EVPN, ACL, LAG, interface IP)
  - NVIDIA Cumulus NVUE (VXLAN/EVPN, OSPF, LAG, ACL, BFD)
  - Huawei VRP (OSPF depth, ISIS, MPLS, VXLAN)
  - Aruba / Extreme / Mikrotik essentials that were missing
  - Extra modern-ops (telemetry / hardening) where still sparse

Dedupes by (vendor, normalized cmd). Idempotent merge into commands.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

OUT = pathlib.Path(__file__).resolve().parent.parent / "commands.json"


def norm_cmd(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


REC: list[dict] = []


def r(vendor, os_, role, cat, title, cmd, desc):
    REC.append(
        {
            "os": os_,
            "role": role,
            "vendor": vendor,
            "cat": cat,
            "title": title,
            "cmd": cmd,
            "desc": desc,
        }
    )


# ───────────────────────── Nokia SR OS ─────────────────────────
r("Nokia", "sros", "router", "System", "Configure system name",
  'configure system name "PE1"',
  "Set the SR OS system name.")
r("Nokia", "sros", "router", "Interfaces", "Configure network interface IP",
  "configure router interface \"to-P1\" address 10.0.0.1/30 port 1/1/1",
  "Create a network interface with IPv4 and bind it to a port.")
r("Nokia", "sros", "router", "Interfaces", "Show router interfaces",
  "show router interface",
  "Display SR OS router interface state.")
r("Nokia", "sros", "router", "BGP", "Enable BGP autonomous system",
  "configure router autonomous-system 65001",
  "Set the local AS used by BGP on SR OS.")
r("Nokia", "sros", "router", "BGP", "Configure BGP group and neighbor",
  "configure router bgp group \"EBGP\" peer-as 65002 neighbor 10.0.0.2",
  "Create an EBGP group and neighbor.")
r("Nokia", "sros", "router", "BGP", "Show BGP summary",
  "show router bgp summary",
  "Display BGP peer summary on SR OS.")
r("Nokia", "sros", "router", "OSPF", "Enable OSPF area 0 interface",
  "configure router ospf area 0.0.0.0 interface \"to-P1\"",
  "Enable OSPF on an interface in area 0.")
r("Nokia", "sros", "router", "OSPF", "Show OSPF neighbors",
  "show router ospf neighbor",
  "Display OSPF adjacency state.")
r("Nokia", "sros", "router", "ISIS", "Enable IS-IS interface",
  "configure router isis 0 area-id 49.0001 interface \"to-P1\" interface-type point-to-point",
  "Enable IS-IS level-2 on a P2P interface.")
r("Nokia", "sros", "router", "ISIS", "Show IS-IS adjacency",
  "show router isis adjacency",
  "Display IS-IS adjacency table.")
r("Nokia", "sros", "router", "MPLS", "Enable MPLS and LDP on interface",
  "configure router mpls interface \"to-P1\"\nconfigure router ldp interface-parameters interface \"to-P1\"",
  "Enable MPLS and LDP on a network interface.")
r("Nokia", "sros", "router", "MPLS", "Show LDP bindings",
  "show router ldp bindings",
  "Display LDP label bindings.")
r("Nokia", "sros", "router", "Routing", "Configure static route",
  "configure router static-route-entry 192.0.2.0/24 next-hop 10.0.0.2",
  "Install a static IPv4 route.")
r("Nokia", "sros", "router", "VLAN", "Configure VPLS service",
  "configure service vpls 100 customer 1 create vpn-id 100",
  "Create a VPLS service instance.")
r("Nokia", "sros", "router", "VXLAN", "Configure VXLAN VPLS binding",
  "configure service vpls 100 vxlan vni 10000 create",
  "Bind a VPLS service to a VXLAN VNI.")
r("Nokia", "sros", "router", "EVPN", "Enable EVPN-VXLAN on VPLS",
  "configure service vpls 100 bgp-evpn vxlan evi 100",
  "Enable BGP-EVPN VXLAN for a VPLS EVI.")
r("Nokia", "sros", "router", "Security", "Configure management IP filter",
  "configure system security management-interface ip filter",
  "Restrict management-plane access with an IP filter.")
r("Nokia", "sros", "router", "AAA", "Configure RADIUS server",
  "configure system security radius server 1 address 10.0.0.10 secret \"SECRET\"",
  "Add a RADIUS server for AAA.")
r("Nokia", "sros", "router", "Logging", "Configure syslog server",
  "configure log syslog 1 address 10.0.0.20",
  "Send logs to a remote syslog host.")
r("Nokia", "sros", "router", "SNMP", "Configure SNMP community",
  'configure system security snmp community "monitor" r version both',
  "Create a read-only SNMP community.")
r("Nokia", "sros", "router", "NTP", "Configure NTP server",
  "configure system time ntp server 10.0.0.30",
  "Add an NTP server.")
r("Nokia", "sros", "router", "HA", "Configure VRRP on interface",
  "configure router interface \"to-LAN\" vrrp 1 backup 192.168.1.1 priority 200",
  "Configure VRRP backup address and priority.")
r("Nokia", "sros", "router", "BFD", "Enable BFD on OSPF interface",
  "configure router ospf area 0.0.0.0 interface \"to-P1\" bfd-enable",
  "Enable BFD for faster OSPF failure detection.")
r("Nokia", "sros", "router", "Troubleshooting", "Show router route-table",
  "show router route-table",
  "Display the IPv4 route table.")

# ───────────────────────── SONiC ─────────────────────────
r("SONiC", "sonic", "switch", "OSPF", "Enable FRR OSPF in SONiC",
  "vtysh -c 'configure terminal' -c 'router ospf' -c 'network 10.0.0.0/24 area 0'",
  "Configure OSPF via FRR vtysh on SONiC.")
r("SONiC", "sonic", "switch", "OSPF", "Show OSPF neighbors (vtysh)",
  "vtysh -c 'show ip ospf neighbor'",
  "Display OSPF neighbors from the FRR OSPF daemon.")
r("SONiC", "sonic", "switch", "VXLAN", "Create VXLAN tunnel map",
  "config vxlan add Vlan100 10000",
  "Map VLAN 100 to VNI 10000.")
r("SONiC", "sonic", "switch", "VXLAN", "Show VXLAN tunnel",
  "show vxlan tunnel",
  "Display VXLAN tunnel endpoints.")
r("SONiC", "sonic", "switch", "EVPN", "Enable EVPN in FRR",
  "vtysh -c 'configure terminal' -c 'router bgp 65001' -c 'address-family l2vpn evpn' -c 'advertise-all-vni'",
  "Advertise all VNIs into L2VPN EVPN.")
r("SONiC", "sonic", "switch", "EVPN", "Show EVPN VNI",
  "vtysh -c 'show evpn vni'",
  "Display EVPN VNI table.")
r("SONiC", "sonic", "switch", "Interfaces", "Configure interface IPv4",
  "config interface ip add Ethernet0 10.0.0.1/30",
  "Assign an IPv4 address to an Ethernet interface.")
r("SONiC", "sonic", "switch", "Interfaces", "Show IP interfaces",
  "show ip interfaces",
  "List interface IPv4 addresses.")
r("SONiC", "sonic", "switch", "VLAN", "Create VLAN",
  "config vlan add 100",
  "Create VLAN 100.")
r("SONiC", "sonic", "switch", "VLAN", "Add tagged member",
  "config vlan member add 100 Ethernet4 -u",
  "Add Ethernet4 as a tagged member of VLAN 100 (omit -u for untagged).")
r("SONiC", "sonic", "switch", "EtherChannel", "Create portchannel",
  "config portchannel add PortChannel1\nconfig portchannel member add PortChannel1 Ethernet0",
  "Create a PortChannel and add a member.")
r("SONiC", "sonic", "switch", "ACL", "Create ACL rule",
  "config acl add table DATAACL L3\nconfig acl rule add DATAACL RULE1 --priority 10 --src_ip 10.0.0.0/24 --action FORWARD",
  "Create an L3 ACL table and permit rule.")
r("SONiC", "sonic", "switch", "Routing", "Add static route",
  "config route add prefix 192.0.2.0/24 nexthop 10.0.0.2",
  "Install a static IPv4 route.")
r("SONiC", "sonic", "switch", "BGP", "Show BGP summary",
  "show ip bgp summary",
  "Display BGP peer summary (FRR-backed).")
r("SONiC", "sonic", "switch", "System", "Set hostname",
  "config hostname leaf1\nsudo config save -y",
  "Set the SONiC hostname and persist config.")
r("SONiC", "sonic", "switch", "Security", "Show ACL tables",
  "show acl table",
  "List configured ACL tables.")
r("SONiC", "sonic", "switch", "BFD", "Show BFD peers",
  "vtysh -c 'show bfd peers'",
  "Display BFD peer state from FRR.")

# ───────────────────────── NVIDIA Cumulus NVUE ─────────────────────────
r("NVIDIA", "nvue", "switch", "VXLAN", "Create VXLAN interface + VNI",
  "nv set bridge domain br_default vlan 100 vni 10000\nnv config apply",
  "Map VLAN 100 to VXLAN VNI 10000.")
r("NVIDIA", "nvue", "switch", "VXLAN", "Show VXLAN VNIs",
  "nv show nve vxlan",
  "Display VXLAN NVE configuration.")
r("NVIDIA", "nvue", "switch", "EVPN", "Enable EVPN",
  "nv set evpn enable on\nnv set vrf default router bgp autonomous-system 65001\nnv config apply",
  "Enable EVPN and set BGP AS for the default VRF.")
r("NVIDIA", "nvue", "switch", "EVPN", "Show EVPN",
  "nv show evpn",
  "Display EVPN global state.")
r("NVIDIA", "nvue", "switch", "OSPF", "Enable OSPF on interface",
  "nv set interface swp1 router ospf area 0\nnv set vrf default router ospf enable on\nnv config apply",
  "Enable OSPF area 0 on swp1.")
r("NVIDIA", "nvue", "switch", "OSPF", "Show OSPF neighbors",
  "nv show vrf default router ospf neighbor",
  "Display OSPF neighbors.")
r("NVIDIA", "nvue", "switch", "ISIS", "Enable IS-IS",
  "nv set vrf default router isis enable on\nnv set interface swp1 router isis enable on\nnv config apply",
  "Enable IS-IS on an interface.")
r("NVIDIA", "nvue", "switch", "EtherChannel", "Create bond / LAG",
  "nv set interface bond1 bond member swp1,swp2\nnv set interface bond1 bond lacp-rate fast\nnv config apply",
  "Create an LACP bond with two members.")
r("NVIDIA", "nvue", "switch", "ACL", "Create ACL permit rule",
  "nv set acl ACL1 type ipv4\nnv set acl ACL1 rule 10 match ip src-ip 10.0.0.0/24\nnv set acl ACL1 rule 10 action permit\nnv config apply",
  "Create an IPv4 ACL permitting a source prefix.")
r("NVIDIA", "nvue", "switch", "Security", "Apply ACL to interface",
  "nv set interface swp1 acl ACL1 inbound\nnv config apply",
  "Bind an ACL inbound on an interface.")
r("NVIDIA", "nvue", "switch", "BFD", "Enable BFD with BGP",
  "nv set vrf default router bgp neighbor 10.0.0.2 bfd enable on\nnv config apply",
  "Enable BFD for a BGP neighbor.")
r("NVIDIA", "nvue", "switch", "HA", "Configure VRR",
  "nv set interface vlan100 ip vrr address 192.168.1.1/24\nnv set interface vlan100 ip vrr state up\nnv config apply",
  "Configure VRR virtual address on a VLAN SVI.")
r("NVIDIA", "nvue", "switch", "MPLS", "Enable MPLS",
  "nv set system forwarding mpls enable on\nnv config apply",
  "Enable MPLS forwarding.")
r("NVIDIA", "nvue", "switch", "QoS", "Set interface QoS rewrite",
  "nv set interface swp1 qos egress-queue-mapping default\nnv config apply",
  "Apply default egress queue mapping.")
r("NVIDIA", "nvue", "switch", "Multicast", "Enable IGMP snooping",
  "nv set bridge domain br_default multicast snooping enable on\nnv config apply",
  "Enable IGMP snooping on the bridge domain.")

# ───────────────────────── Huawei VRP ─────────────────────────
r("Huawei", "vrp", "router", "OSPF", "Enable OSPF process and area network",
  "ospf 1 router-id 1.1.1.1\n area 0.0.0.0\n  network 10.0.0.0 0.0.0.255",
  "Start OSPF process 1 and advertise a network in area 0.")
r("Huawei", "vrp", "router", "OSPF", "OSPF interface cost",
  "interface GigabitEthernet0/0/0\n ospf cost 10",
  "Set OSPF metric on an interface.")
r("Huawei", "vrp", "router", "OSPF", "Display OSPF peers",
  "display ospf peer",
  "Show OSPF neighbor state.")
r("Huawei", "vrp", "router", "OSPF", "Display OSPF routing table",
  "display ospf routing",
  "Show OSPF-learned routes.")
r("Huawei", "vrp", "router", "ISIS", "Enable IS-IS",
  "isis 1\n network-entity 49.0001.0000.0000.0001.00\ninterface GigabitEthernet0/0/0\n isis enable 1",
  "Configure IS-IS process and enable on an interface.")
r("Huawei", "vrp", "router", "ISIS", "Display IS-IS peer",
  "display isis peer",
  "Show IS-IS adjacency.")
r("Huawei", "vrp", "router", "MPLS", "Enable MPLS LDP",
  "mpls lsr-id 1.1.1.1\nmpls\nmpls ldp\ninterface GigabitEthernet0/0/0\n mpls\n mpls ldp",
  "Enable MPLS and LDP globally and on an interface.")
r("Huawei", "vrp", "router", "MPLS", "Display MPLS LDP peer",
  "display mpls ldp peer",
  "Show LDP peer sessions.")
r("Huawei", "vrp", "router", "VXLAN", "Configure VXLAN VNI bridge-domain",
  "bridge-domain 100\n vxlan vni 10000",
  "Create a bridge-domain and bind VXLAN VNI 10000.")
r("Huawei", "vrp", "router", "VXLAN", "Configure NVE source",
  "interface Nve1\n source 10.0.0.1\n vni 10000 head-end peer-list protocol bgp",
  "Configure NVE source VTEP and VNI peer discovery via BGP.")
r("Huawei", "vrp", "router", "EVPN", "Enable BGP EVPN address-family",
  "bgp 65001\n l2vpn-family evpn\n  peer 10.0.0.2 enable",
  "Enable L2VPN EVPN address-family and activate a peer.")
r("Huawei", "vrp", "router", "EVPN", "Display BGP EVPN routes",
  "display bgp evpn all routing-table",
  "Show EVPN routes.")
r("Huawei", "vrp", "router", "QoS", "Configure traffic classifier",
  "traffic classifier VOICE operator or\n if-match dscp ef",
  "Match EF-marked voice traffic.")
r("Huawei", "vrp", "router", "Multicast", "Enable PIM SM",
  "multicast routing-enable\ninterface GigabitEthernet0/0/0\n pim sm",
  "Enable multicast routing and PIM-SM on an interface.")
r("Huawei", "vrp", "router", "BFD", "Configure BFD session",
  "bfd\nsession OSPF-TO-P1 bind peer-ip 10.0.0.2 interface GigabitEthernet0/0/0",
  "Create a BFD session to a peer.")
r("Huawei", "vrp", "router", "HA", "Configure VRRP",
  "interface Vlanif100\n vrrp vrid 1 virtual-ip 192.168.1.1\n vrrp vrid 1 priority 120",
  "Configure VRRP virtual IP and priority.")
r("Huawei", "vrp", "router", "Security", "Configure ACL",
  "acl number 3000\n rule 10 permit ip source 10.0.0.0 0.0.0.255",
  "Create an advanced ACL permitting a source subnet.")
r("Huawei", "vrp", "router", "SNMP", "Configure SNMP agent",
  "snmp-agent\nsnmp-agent community read cipher public",
  "Enable SNMP and set a read community.")
r("Huawei", "vrp", "router", "System", "Configure sysname",
  "sysname PE1",
  "Set the VRP system name (hostname).")

# ───────────────────────── Aruba AOS-CX essentials ─────────────────────────
r("Aruba", "aoscx", "switch", "VXLAN", "Enable VXLAN",
  "vxlan enable\ninterface vxlan 1\n source-ip 10.0.0.1\n vni 10000",
  "Enable VXLAN and bind VNI 10000 to a source VTEP IP.")
r("Aruba", "aoscx", "switch", "EVPN", "Enable EVPN",
  "evpn\n vlan 100\n  rd auto\n  route-target both auto",
  "Enable EVPN for VLAN 100 with auto RD/RT.")
r("Aruba", "aoscx", "switch", "Security", "Configure ACL",
  "access-list ip OFFICE\n 10 permit any 10.0.0.0/24 any",
  "Create an IPv4 ACL permitting a source prefix.")
r("Aruba", "aoscx", "switch", "ACL", "Apply ACL to interface",
  "interface 1/1/1\n apply access-list ip OFFICE in",
  "Apply an ACL inbound on an interface.")
r("Aruba", "aoscx", "switch", "QoS", "Configure queue profile",
  "qos queue-profile default\n map dscp 46 local-priority 5",
  "Map DSCP EF to a local priority queue.")
r("Aruba", "aoscx", "switch", "Multicast", "Enable IGMP snooping",
  "vlan 100\n igmp snooping enable",
  "Enable IGMP snooping on a VLAN.")
r("Aruba", "aoscx", "switch", "MPLS", "Note: MPLS limited on AOS-CX",
  "show capacities-status | include MPLS",
  "Check whether MPLS features are licensed/supported on this platform.")
r("Aruba", "aoscx", "switch", "ISIS", "IS-IS not typically used on AOS-CX access",
  "show running-config | include isis",
  "Probe for IS-IS support on this AOS-CX image.")
r("Aruba", "aoscx", "switch", "BFD", "Enable BFD for OSPF",
  "router ospf 1\n area 0.0.0.0\ninterface 1/1/1\n ip ospf bfd",
  "Enable BFD on an OSPF interface.")
r("Aruba", "aoscx", "switch", "HA", "Configure VSX keepalive",
  "vsx\n inter-switch-link 1/1/50\n keepalive peer 10.0.0.2 source 10.0.0.1",
  "Configure VSX ISL and keepalive.")

# ───────────────────────── Extreme EXOS essentials ─────────────────────────
r("Extreme", "exos", "switch", "BGP", "Configure BGP neighbor",
  "enable bgp\nconfigure bgp AS-number 65001\ncreate bgp neighbor 10.0.0.2 remote-AS-number 65002",
  "Enable BGP and create a neighbor.")
r("Extreme", "exos", "switch", "BGP", "Show BGP neighbors",
  "show bgp neighbor",
  "Display BGP neighbor state.")
r("Extreme", "exos", "switch", "VXLAN", "Configure VXLAN VTEP",
  "create virtual-network VN100 flooding local-only\nconfigure virtual-network VN100 vxlan vni 10000",
  "Create a VXLAN virtual network with VNI 10000.")
r("Extreme", "exos", "switch", "EVPN", "Enable BGP EVPN",
  "enable bgp\nconfigure bgp neighbor 10.0.0.2 address-family l2vpn-evpn add",
  "Activate L2VPN EVPN address-family on a BGP neighbor.")
r("Extreme", "exos", "switch", "VLAN", "Create VLAN",
  "create vlan v100 tag 100",
  "Create VLAN v100 with 802.1Q tag 100.")
r("Extreme", "exos", "switch", "Interfaces", "Configure VLAN IP",
  "configure vlan v100 ipaddress 192.168.1.1 255.255.255.0",
  "Assign an IPv4 address to a VLAN interface.")
r("Extreme", "exos", "switch", "Routing", "Show iproute",
  "show iproute",
  "Display the IP routing table.")
r("Extreme", "exos", "switch", "AAA", "Configure RADIUS",
  "configure radius primary server 10.0.0.10 client-ip 10.0.0.1 vr VR-Default shared-secret SECRET",
  "Add a primary RADIUS server.")
r("Extreme", "exos", "switch", "System", "Configure snmp sysName",
  "configure snmp sysName leaf1",
  "Set SNMP sysName (commonly used as device hostname identity).")

# ───────────────────────── Mikrotik RouterOS essentials ─────────────────────────
r("Mikrotik", "routeros", "router", "System", "Set identity (hostname)",
  "/system identity set name=PE1",
  "Set the RouterOS identity/hostname.")
r("Mikrotik", "routeros", "router", "SNMP", "Enable SNMP community",
  "/snmp community set public name=public",
  "Configure the default SNMP community.")
r("Mikrotik", "routeros", "router", "AAA", "Add RADIUS client",
  "/radius add address=10.0.0.10 secret=SECRET service=login",
  "Add a RADIUS server for login AAA.")
r("Mikrotik", "routeros", "router", "VLAN", "Create VLAN interface",
  "/interface vlan add name=vlan100 vlan-id=100 interface=ether1",
  "Create a VLAN 100 subinterface.")
r("Mikrotik", "routeros", "router", "EtherChannel", "Create bonding interface",
  "/interface bonding add name=bond1 slaves=ether1,ether2 mode=802.3ad",
  "Create an LACP bond.")
r("Mikrotik", "routeros", "router", "OSPF", "Show OSPF neighbors",
  "/routing ospf neighbor print",
  "Display OSPF neighbors.")

# ───────────────────────── FortiOS / PAN-OS small fills ─────────────────────────
r("FortiOS", "fortios", "firewall", "Routing", "Configure static route",
  "config router static\n edit 1\n  set dst 192.0.2.0 255.255.255.0\n  set gateway 10.0.0.2\n  set device port1\n next\nend",
  "Add an IPv4 static route.")
r("FortiOS", "fortios", "firewall", "Interfaces", "Configure interface IP",
  "config system interface\n edit port1\n  set ip 10.0.0.1 255.255.255.0\n  set allowaccess ping https ssh\n next\nend",
  "Set interface IPv4 address and management access.")
r("FortiOS", "fortios", "firewall", "AAA", "Configure RADIUS server",
  "config user radius\n edit \"RAD1\"\n  set server 10.0.0.10\n  set secret SECRET\n next\nend",
  "Add a RADIUS server object.")
r("PAN-OS", "panos", "firewall", "Routing", "Configure static route",
  "set network virtual-router default routing-table ip static-route TO-LAB nexthop ip-address 10.0.0.2 destination 192.0.2.0/24",
  "Add a static route in the default virtual router.")
r("PAN-OS", "panos", "firewall", "NTP", "Configure NTP servers",
  "set deviceconfig system ntp-servers primary-ntp-server ntp-server-address 10.0.0.30",
  "Set the primary NTP server.")
r("PAN-OS", "panos", "firewall", "SNMP", "Configure SNMP",
  "set deviceconfig system snmp-setting access-setting version v2c snmp-community-string public",
  "Enable SNMPv2c with a community string.")
r("PAN-OS", "panos", "firewall", "AAA", "Configure RADIUS profile",
  "set shared server-profile radius RAD1 server RAD1 address 10.0.0.10 secret SECRET",
  "Add a RADIUS server profile.")

# ───────────────────────── NX-OS expansion beyond VXLAN seed ─────────────────────────
r("Cisco", "nxos", "switch", "System", "Set hostname",
  "hostname LEAF-01",
  "Set the NX-OS switch hostname.")
r("Cisco", "nxos", "switch", "Interfaces", "Configure L3 interface IP",
  "interface Ethernet1/1\n no switchport\n ip address 10.0.0.1/30\n no shutdown",
  "Convert a port to L3 and assign IPv4.")
r("Cisco", "nxos", "switch", "VLAN", "Create VLAN",
  "vlan 100\n name USERS",
  "Create and name VLAN 100.")
r("Cisco", "nxos", "switch", "BGP", "Configure BGP neighbor",
  "feature bgp\nrouter bgp 65001\n neighbor 10.0.0.2 remote-as 65002\n  address-family ipv4 unicast",
  "Enable BGP and configure an IPv4 neighbor.")
r("Cisco", "nxos", "switch", "OSPF", "Enable OSPF",
  "feature ospf\nrouter ospf UNDERLAY\ninterface Ethernet1/1\n ip router ospf UNDERLAY area 0",
  "Enable OSPF and place an interface in area 0.")
r("Cisco", "nxos", "switch", "VXLAN", "Enable VXLAN NVE",
  "feature nv overlay\nfeature vn-segment-vlan-based\ninterface nve1\n source-interface loopback1\n member vni 10000",
  "Enable NV overlay and bind VNI on NVE1.")
r("Cisco", "nxos", "switch", "EVPN", "Enable BGP EVPN",
  "nv overlay evpn\nrouter bgp 65001\n address-family l2vpn evpn\n  retain route-target all",
  "Enable EVPN and activate L2VPN EVPN address-family.")
r("Cisco", "nxos", "switch", "EtherChannel", "Configure vPC / port-channel",
  "feature vpc\nvpc domain 1\n peer-keepalive destination 192.168.255.2 source 192.168.255.1\ninterface port-channel10\n vpc 10",
  "Configure a vPC domain and member port-channel.")
r("Cisco", "nxos", "switch", "AAA", "Configure RADIUS",
  "radius-server host 10.0.0.10 key SECRET\naaa authentication login default group radius",
  "Add RADIUS and use it for login authentication.")
r("Cisco", "nxos", "switch", "Hardening", "CoPP default",
  "copp profile strict",
  "Apply the strict Control-Plane Policing profile.")

# ───────────────────────── IOS-XE explicit samples ─────────────────────────
r("Cisco", "iosxe", "router", "Telemetry", "Enable NETCONF/YANG",
  "netconf-yang\nnetconf ssh",
  "Enable NETCONF over SSH on IOS-XE.")
r("Cisco", "iosxe", "router", "Automation", "Enable RESTCONF",
  "restconf\nip http secure-server",
  "Enable RESTCONF HTTPS transport.")
r("Cisco", "iosxe", "router", "Automation", "Guest Shell Python",
  "guestshell enable\nguestshell run python3 --version",
  "Enable Guest Shell and verify on-box Python.")
r("Cisco", "iosxe", "router", "Provisioning", "PnP / ZTP status",
  "show pnp status\nshow install summary",
  "Check Plug-and-Play / install state for day-0 bring-up.")

# ───────────────────────── NX-OS depth (wave-2) ─────────────────────────
r("Cisco", "nxos", "switch", "BGP", "NX-OS BGP underlay neighbor",
  "router bgp 65001\n neighbor 10.0.0.2 remote-as 65001\n  update-source loopback0\n  address-family ipv4 unicast\n   send-community both",
  "iBGP underlay neighbor with update-source loopback.")
r("Cisco", "nxos", "switch", "OSPF", "NX-OS OSPF interface network",
  "feature ospf\nrouter ospf UNDERLAY\ninterface Ethernet1/1\n ip router ospf UNDERLAY area 0.0.0.0",
  "Enable OSPF and place an interface in area 0.")
r("Cisco", "nxos", "switch", "ISIS", "NX-OS IS-IS underlay",
  "feature isis\nrouter isis UNDERLAY\n net 49.0001.0000.0000.0001.00\ninterface Ethernet1/1\n ip router isis UNDERLAY",
  "Enable IS-IS and advertise an interface into the underlay.")
r("Cisco", "nxos", "switch", "BFD", "NX-OS BFD for BGP",
  "feature bfd\nrouter bgp 65001\n neighbor 10.0.0.2\n  bfd",
  "Enable BFD and attach it to a BGP neighbor.")
r("Cisco", "nxos", "switch", "ACL", "NX-OS IP access-list",
  "ip access-list ACL-MGMT\n 10 permit ip 10.0.0.0/24 any\n 20 deny ip any any",
  "Create a named IPv4 ACL for management filtering.")
r("Cisco", "nxos", "switch", "Spanning-Tree", "NX-OS spanning-tree mode",
  "spanning-tree mode rapid-pvst\nspanning-tree vlan 1-100 priority 4096",
  "Set rapid-PVST and bridge priority for VLANs.")
r("Cisco", "nxos", "switch", "VLAN", "NX-OS VLAN with vn-segment",
  "vlan 100\n name WEB\n vn-segment 10100",
  "Map a VLAN to a VXLAN VNI via vn-segment.")
r("Cisco", "nxos", "switch", "Interfaces", "NX-OS layer-3 interface",
  "interface Ethernet1/1\n no switchport\n ip address 10.0.0.1/30\n no shutdown",
  "Convert a port to routed mode and assign an IPv4 address.")
r("Cisco", "nxos", "switch", "NTP", "NX-OS NTP server",
  "ntp server 10.0.0.30 use-vrf management",
  "Point NX-OS at an NTP server in the management VRF.")
r("Cisco", "nxos", "switch", "SNMP", "NX-OS SNMPv2 community",
  "snmp-server community MONITOR group network-operator",
  "Create a read-only SNMP community.")
r("Cisco", "nxos", "switch", "Logging", "NX-OS remote syslog",
  "logging server 10.0.0.20 5 use-vrf management",
  "Send informational-and-above logs to a remote syslog host.")
r("Cisco", "nxos", "switch", "Troubleshooting", "NX-OS show VXLAN / NVE",
  "show nve peers\nshow nve vni\nshow bgp l2vpn evpn summary",
  "Verify NVE peers, VNIs, and EVPN BGP session health.")

# ───────────────────────── IOS-XE depth (wave-2) ─────────────────────────
r("Cisco", "iosxe", "router", "BGP", "IOS-XE BGP neighbor",
  "router bgp 65001\n bgp log-neighbor-changes\n neighbor 10.0.0.2 remote-as 65002\n address-family ipv4\n  neighbor 10.0.0.2 activate",
  "Configure an EBGP neighbor and activate IPv4.")
r("Cisco", "iosxe", "router", "OSPF", "IOS-XE OSPF network",
  "router ospf 1\n network 10.0.0.0 0.0.0.255 area 0\n passive-interface default\n no passive-interface GigabitEthernet0/0",
  "Enable OSPF area 0 with selective passive interfaces.")
r("Cisco", "iosxe", "router", "VXLAN", "IOS-XE BGP EVPN NVE",
  "l2vpn evpn\nbridge-domain 100\nmember vni 10100\ninterface nve1\n source-interface Loopback0\n member vni 10100 ingress-replication",
  "Basic IOS-XE EVPN/NVE membership for a VNI.")
r("Cisco", "iosxe", "router", "BFD", "IOS-XE BFD template",
  "bfd-template single-hop EDGE\n interval min-tx 50 min-rx 50 multiplier 3\ninterface GigabitEthernet0/0\n bfd template EDGE",
  "Apply a single-hop BFD template to an interface.")
r("Cisco", "iosxe", "router", "Spanning-Tree", "IOS-XE rapid-PVST",
  "spanning-tree mode rapid-pvst\nspanning-tree portfast default",
  "Enable rapid-PVST and default PortFast on access ports.")
r("Cisco", "iosxe", "router", "EtherChannel", "IOS-XE LACP port-channel",
  "interface GigabitEthernet0/1\n channel-group 10 mode active\ninterface Port-channel10\n switchport mode trunk",
  "Bundle a member into LACP port-channel 10.")
r("Cisco", "iosxe", "router", "NTP", "IOS-XE NTP server",
  "ntp server 10.0.0.30",
  "Configure an NTP server on IOS-XE.")
r("Cisco", "iosxe", "router", "SNMP", "IOS-XE SNMPv2 community",
  "snmp-server community MONITOR ro",
  "Create a read-only SNMP community.")
r("Cisco", "iosxe", "router", "Logging", "IOS-XE remote syslog",
  "logging host 10.0.0.20\nlogging trap informational",
  "Send informational traps to a remote syslog host.")
r("Cisco", "iosxe", "router", "AAA", "IOS-XE RADIUS login",
  "radius server AAA1\n address ipv4 10.0.0.10 auth-port 1812 acct-port 1813\n key SECRET\naaa authentication login default group radius local",
  "Define a RADIUS server and prefer it for login.")
r("Cisco", "iosxe", "router", "Hardening", "IOS-XE control-plane service-policy",
  "policy-map COPP\n class class-default\n  police 80000 conform-action transmit exceed-action drop\ncontrol-plane\n service-policy input COPP",
  "Apply a basic CoPP policy to the control plane.")
r("Cisco", "iosxe", "router", "Troubleshooting", "IOS-XE platform / YANG status",
  "show platform software yang-management process\nshow netconf-yang status\nshow restconf",
  "Verify YANG/NETCONF/RESTCONF process health on IOS-XE.")

# ───────────────────────── Extreme essentials ─────────────────────────
r("Extreme", "exos", "switch", "Spanning-Tree", "Enable EXOS STP",
  "enable stpd s0\nconfigure stpd s0 mode dot1w\nconfigure stpd s0 priority 4096",
  "Enable STPD s0 in 802.1w mode with bridge priority.")
r("Extreme", "exos", "switch", "Spanning-Tree", "Show EXOS STP",
  "show stpd\nshow stpd s0",
  "Display STPD state and per-instance detail.")
r("Extreme", "exos", "switch", "ACL", "Create EXOS policy ACL",
  "create access-list MGMT_ONLY \"source-address 10.0.0.0/24;\"\nconfigure access-list MGMT_ONLY ports 1:1",
  "Create a simple source ACL and bind it to a port.")
r("Extreme", "exos", "switch", "EtherChannel", "Configure EXOS sharing / LAG",
  "enable sharing 1 grouping 1-2 algorithm address-based L3_L4 lacp",
  "Create an LACP load-share group on ports 1-2.")
r("Extreme", "exos", "switch", "BFD", "Enable EXOS BFD",
  "enable bfd\nconfigure bfd vlan UNDERLAY destinations 10.0.0.2",
  "Enable BFD and track a VLAN destination.")
r("Extreme", "exos", "switch", "Security", "EXOS management ACL",
  "configure snmp access-profile MGMT_ONLY\nconfigure ssh2 access-profile MGMT_ONLY",
  "Restrict SNMP and SSH with an access profile.")
r("Extreme", "exos", "switch", "QoS", "EXOS QoS profile",
  "configure qosprofile qp3 minbw 10 maxbw 50 ports all",
  "Set min/max bandwidth on a QoS profile.")
r("Extreme", "exos", "switch", "Multicast", "EXOS IGMP snooping",
  "enable igmp snooping\nenable igmp snooping vlan DATA",
  "Enable IGMP snooping globally and on a VLAN.")
r("Extreme", "exos", "switch", "Hardening", "EXOS failsafe account",
  "configure account admin max-failed-logins 5\nenable idletimeout",
  "Limit failed logins and enable idle timeout.")
r("Extreme", "exos", "switch", "Telemetry", "EXOS sFlow",
  "enable sflow\nconfigure sflow collector 10.0.0.40 port 6343\nconfigure sflow agent 10.0.0.1",
  "Enable sFlow toward a collector.")

# ───────────────────────── SR OS extras ─────────────────────────
r("Nokia", "sros", "router", "ACL", "SR OS filter for management",
  "configure filter ip-filter 10 create entry 10 match src-ip 10.0.0.0/24 action forward",
  "Permit management subnet through an IP filter.")
r("Nokia", "sros", "router", "Spanning-Tree", "SR OS mVPLS STP",
  "configure service vpls 100 stp mode rstp",
  "Enable RSTP on a VPLS service.")
r("Nokia", "sros", "router", "QoS", "SR OS SAP ingress policy",
  "configure qos sap-ingress 10 create queue 1 create",
  "Create a basic SAP-ingress QoS policy.")
r("Nokia", "sros", "router", "NAT", "SR OS NAT inside",
  "configure service nat nat-policy \"NAT44\" create",
  "Create a NAT44 policy container on SR OS.")
r("Nokia", "sros", "router", "Hardening", "SR OS cpm-filter",
  "configure system security cpm-filter ip-filter entry 10 action drop",
  "Drop unmatched control-plane traffic via CPM filter.")
r("Nokia", "sros", "router", "Telemetry", "SR OS gRPC telemetry",
  "configure system grpc allow-unsecure-connection\nconfigure system telemetry destination-group \"COLLECTOR\"",
  "Enable gRPC and a telemetry destination group.")

# ───────────────────────── FRR NTP/AAA notes via system ─────────────────────────
r("FRR", "frr", "router", "NTP", "Host NTP (FRR runs on Linux)",
  "sudo timedatectl set-ntp true\n# or: sudo apt install chrony && sudo systemctl enable --now chrony",
  "FRR has no on-box NTP CLI — sync time on the Linux host.")
r("FRR", "frr", "router", "AAA", "Host AAA via sshd + RADIUS (optional)",
  "sudo apt install libpam-radius-auth\n# map sshd PAM to RADIUS — FRR vtysh uses host auth",
  "FRR inherits AAA from the Linux host PAM/sshd stack.")


def main() -> None:
    data = json.load(open(OUT))
    keys = {(row["vendor"], norm_cmd(row["cmd"])) for row in data}
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
