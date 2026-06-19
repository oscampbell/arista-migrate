from typing import Set, Dict, List
from router_migrate.models import DeviceIR, MigrationIR, InterfaceIR, IPAddress

class Migrator:
    def __init__(self, source_device: DeviceIR, target_snippet: DeviceIR, source_vendor: str, target_vendor: str, renames: Dict[str, str] = None):
        self.source_device = source_device
        self.target_snippet = target_snippet
        self.source_vendor = source_vendor
        self.target_vendor = target_vendor
        self.renames = renames or {}
        self.migration_ir = MigrationIR(source_vendor=source_vendor, target_vendor=target_vendor)

    def analyze(self) -> MigrationIR:
        needed_vrfs: Set[str] = set()
        needed_acls: Set[str] = set()
        needed_vlans: Set[str] = set()
        needed_ips: List[IPAddress] = []

        # 1. Interfaces
        for iface_name in self.target_snippet.interfaces.keys():
            iface = self.source_device.interfaces.get(iface_name)
            if not iface:
                self.migration_ir.warnings.append(f"Interface {iface_name} not found in source config")
                continue
                
            # If we rename, change the name in the IR
            new_name = self.renames.get(iface_name, iface_name)
            migrated_iface = InterfaceIR(
                name=new_name,
                description=iface.description,
                vrf=iface.vrf,
                ip_addresses=iface.ip_addresses,
                acl_in=iface.acl_in,
                acl_out=iface.acl_out,
                vlan=iface.vlan,
                enabled=iface.enabled,
                switchport=iface.switchport,
                switchport_mode=iface.switchport_mode,
                switchport_access_vlan=iface.switchport_access_vlan,
                switchport_trunk_vlans=iface.switchport_trunk_vlans,
                mtu=iface.mtu,
                speed=iface.speed,
                load_interval=iface.load_interval,
                raw_lines=iface.raw_lines
            )
            self.migration_ir.interfaces.append(migrated_iface)
            
            if iface.vrf:
                needed_vrfs.add(iface.vrf)
            if iface.acl_in:
                needed_acls.add(iface.acl_in)
            if iface.acl_out:
                needed_acls.add(iface.acl_out)
            if iface.vlan:
                needed_vlans.add(iface.vlan)
            if iface.switchport_access_vlan:
                needed_vlans.add(iface.switchport_access_vlan)
            for v in iface.switchport_trunk_vlans:
                needed_vlans.add(v)
            needed_ips.extend(iface.ip_addresses)

        # Look up missing info in source device if the snippet was incomplete
        # Usually target_snippet might just be the interface, but we need the full VRF from source_device
        
        # 2. VRFs
        for vrf_name in needed_vrfs:
            if vrf_name in self.source_device.vrfs:
                self.migration_ir.vrfs.append(self.source_device.vrfs[vrf_name])
            else:
                self.migration_ir.warnings.append(f"VRF {vrf_name} referenced but not found in source config")

        # 3. VLANs
        for vlan_id in needed_vlans:
            if vlan_id in self.source_device.vlans:
                self.migration_ir.vlans.append(self.source_device.vlans[vlan_id])
            else:
                self.migration_ir.warnings.append(f"VLAN {vlan_id} referenced but not found in source config")

        # 4. ACLs
        for acl_name in needed_acls:
            if acl_name in self.source_device.acls:
                self.migration_ir.acls.append(self.source_device.acls[acl_name])
            else:
                self.migration_ir.warnings.append(f"ACL {acl_name} referenced but not found in source config")

        # 5. BGP
        needed_route_maps: Set[str] = set()
        needed_prefix_lists: Set[str] = set()

        for vrf_name in needed_vrfs:
            if vrf_name in self.source_device.bgp_vrfs:
                bgp_stanza = self.source_device.bgp_vrfs[vrf_name]
                self.migration_ir.bgp_vrfs.append(bgp_stanza)
                for neighbor in bgp_stanza.neighbors.values():
                    if neighbor.route_map_in: needed_route_maps.add(neighbor.route_map_in)
                    if neighbor.route_map_out: needed_route_maps.add(neighbor.route_map_out)
                    if neighbor.prefix_list_in: needed_prefix_lists.add(neighbor.prefix_list_in)
                    if neighbor.prefix_list_out: needed_prefix_lists.add(neighbor.prefix_list_out)
                for redist_rm in [m for m in bgp_stanza.redistribute if "route-map" in m]:
                    # simplistic extraction, assuming redist_rm string has the route-map name
                    # this logic might need refinement depending on how parser handles `redistribute`
                    parts = redist_rm.split("route-map")
                    if len(parts) > 1:
                        rm_name = parts[1].strip()
                        needed_route_maps.add(rm_name)

        # 6. Route Maps & Prefix Lists (Resolve transitively)
        visited_rms: Set[str] = set()
        while needed_route_maps - visited_rms:
            rm_name = (needed_route_maps - visited_rms).pop()
            visited_rms.add(rm_name)
            if rm_name in self.source_device.route_maps:
                rm = self.source_device.route_maps[rm_name]
                self.migration_ir.route_maps.append(rm)
                for rule in rm.rules:
                    # extract prefix lists from match clauses
                    for match in rule.match_clauses:
                        if "prefix-list" in match:
                            parts = match.split("prefix-list")
                            if len(parts) > 1:
                                needed_prefix_lists.add(parts[1].strip())
            else:
                self.migration_ir.warnings.append(f"Route Map {rm_name} not found")

        for pl_name in needed_prefix_lists:
            if pl_name in self.source_device.prefix_lists:
                self.migration_ir.prefix_lists.append(self.source_device.prefix_lists[pl_name])
            else:
                self.migration_ir.warnings.append(f"Prefix List {pl_name} not found")

        # 7. Static Routes
        for sr in self.source_device.static_routes:
            # check if static route is relevant (matches VRF or falls within subnet of the interface)
            if sr.vrf in needed_vrfs:
                self.migration_ir.static_routes.append(sr)
                continue
            
            # Simple IP check (could be improved with ipaddress module)
            sr_prefix = sr.prefix.split("/")[0] if "/" in sr.prefix else sr.prefix
            pfx3 = ".".join(sr_prefix.split(".")[:3])
            
            is_relevant = False
            for ip in needed_ips:
                if sr_prefix == ip.address or ip.address.startswith(pfx3 + "."):
                    is_relevant = True
                    break
            
            if is_relevant:
                self.migration_ir.static_routes.append(sr)

        return self.migration_ir
