from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict

@dataclass
class IPAddress:
    address: str
    mask: str # e.g. "24" or "255.255.255.0"
    secondary: bool = False

@dataclass
class InterfaceIR:
    name: str
    description: Optional[str] = None
    vrf: Optional[str] = None
    ip_addresses: List[IPAddress] = field(default_factory=list)
    acl_in: Optional[str] = None
    acl_out: Optional[str] = None
    vlan: Optional[str] = None
    enabled: bool = True
    switchport: bool = False
    switchport_mode: Optional[str] = None # 'access' or 'trunk'
    switchport_access_vlan: Optional[str] = None
    switchport_trunk_vlans: List[str] = field(default_factory=list)
    mtu: Optional[int] = None
    speed: Optional[str] = None
    load_interval: Optional[int] = None
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class VrfIR:
    name: str
    rd: Optional[str] = None
    rt_import: List[str] = field(default_factory=list)
    rt_export: List[str] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class VlanIR:
    vlan_id: str
    name: Optional[str] = None
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class AclRuleIR:
    action: str # 'permit' or 'deny'
    protocol: str # 'ip', 'tcp', 'udp', 'icmp', etc.
    source: str # IP/mask or 'any' or 'host IP'
    destination: str # IP/mask or 'any' or 'host IP'
    source_port: Optional[str] = None # e.g. 'eq 80', 'range 1000 2000'
    destination_port: Optional[str] = None
    log: bool = False
    raw_line: str = ""

@dataclass
class AclIR:
    name: str
    type: str # 'standard', 'extended', etc.
    rules: List[AclRuleIR] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class StaticRouteIR:
    prefix: str
    next_hop: str
    vrf: Optional[str] = None
    distance: Optional[int] = None
    raw_line: str = ""

@dataclass
class PrefixListRuleIR:
    action: str # 'permit' or 'deny'
    prefix: str
    ge: Optional[int] = None
    le: Optional[int] = None
    seq: Optional[int] = None
    raw_line: str = ""

@dataclass
class PrefixListIR:
    name: str
    rules: List[PrefixListRuleIR] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class RouteMapRuleIR:
    action: str # 'permit' or 'deny'
    sequence: int
    match_clauses: List[str] = field(default_factory=list)
    set_clauses: List[str] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class RouteMapIR:
    name: str
    rules: List[RouteMapRuleIR] = field(default_factory=list)
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class BgpNeighborIR:
    ip: str
    remote_as: Optional[str] = None
    description: Optional[str] = None
    route_map_in: Optional[str] = None
    route_map_out: Optional[str] = None
    prefix_list_in: Optional[str] = None
    prefix_list_out: Optional[str] = None
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class BgpVrfIR:
    vrf: str
    asn: Optional[str] = None
    neighbors: Dict[str, BgpNeighborIR] = field(default_factory=dict)
    redistribute: List[str] = field(default_factory=list) # e.g. ["connected", "static"]
    raw_lines: List[str] = field(default_factory=list)

@dataclass
class DeviceIR:
    interfaces: Dict[str, InterfaceIR] = field(default_factory=dict)
    vrfs: Dict[str, VrfIR] = field(default_factory=dict)
    vlans: Dict[str, VlanIR] = field(default_factory=dict)
    acls: Dict[str, AclIR] = field(default_factory=dict)
    static_routes: List[StaticRouteIR] = field(default_factory=list)
    prefix_lists: Dict[str, PrefixListIR] = field(default_factory=dict)
    route_maps: Dict[str, RouteMapIR] = field(default_factory=dict)
    bgp_vrfs: Dict[str, BgpVrfIR] = field(default_factory=dict)

@dataclass
class MigrationIR:
    source_vendor: str
    target_vendor: str
    interfaces: List[InterfaceIR] = field(default_factory=list)
    vrfs: List[VrfIR] = field(default_factory=list)
    vlans: List[VlanIR] = field(default_factory=list)
    acls: List[AclIR] = field(default_factory=list)
    static_routes: List[StaticRouteIR] = field(default_factory=list)
    prefix_lists: List[PrefixListIR] = field(default_factory=list)
    route_maps: List[RouteMapIR] = field(default_factory=list)
    bgp_vrfs: List[BgpVrfIR] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
