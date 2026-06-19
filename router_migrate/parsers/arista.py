import re
from typing import List, Dict
from router_migrate.parsers.base import BaseParser
from router_migrate.models import DeviceIR, InterfaceIR, VrfIR, VlanIR, AclIR, AclRuleIR, BgpVrfIR, BgpNeighborIR, StaticRouteIR, RouteMapIR, RouteMapRuleIR, IPAddress

class AristaParser(BaseParser):
    def _split_blocks(self, text: str) -> List[List[str]]:
        blocks = []
        current_block = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("!"):
                continue
            if line.startswith(" "):
                current_block.append(stripped)
            else:
                if current_block:
                    blocks.append(current_block)
                current_block = [stripped]
        if current_block:
            blocks.append(current_block)
        return blocks

    def parse(self, config_text: str) -> DeviceIR:
        ir = DeviceIR()
        blocks = self._split_blocks(config_text)
        
        for block in blocks:
            header = block[0]
            
            # Interface
            if header.startswith("interface "):
                iface_name = header.split("interface ")[1].strip()
                iface = InterfaceIR(name=iface_name, raw_lines=block)
                for line in block[1:]:
                    if line.startswith("description"):
                        iface.description = line.replace("description", "").strip()
                    elif line.startswith("vrf"):
                        iface.vrf = line.replace("vrf", "").strip()
                    elif line.startswith("ip address"):
                        parts = line.split()
                        if len(parts) >= 3:
                            if "/" in parts[2]:
                                addr, mask = parts[2].split("/")
                                iface.ip_addresses.append(IPAddress(address=addr, mask=mask))
                            elif len(parts) >= 4:
                                iface.ip_addresses.append(IPAddress(address=parts[2], mask=parts[3]))
                    elif line.startswith("ip access-group"):
                        parts = line.split()
                        if len(parts) >= 4:
                            acl_name = parts[2]
                            direction = parts[3]
                            if direction == "in":
                                iface.acl_in = acl_name
                            else:
                                iface.acl_out = acl_name
                    elif line == "shutdown":
                        iface.enabled = False
                    elif line == "no shutdown":
                        iface.enabled = True
                ir.interfaces[iface_name] = iface

            # VRF
            elif header.startswith("vrf instance "):
                vrf_name = header.split("vrf instance ")[1].strip()
                vrf = VrfIR(name=vrf_name, raw_lines=block)
                for line in block[1:]:
                    if line.startswith("rd "):
                        vrf.rd = line.replace("rd ", "").strip()
                    elif line.startswith("route-target export"):
                        vrf.rt_export.append(line.replace("route-target export ", "").strip())
                    elif line.startswith("route-target import"):
                        vrf.rt_import.append(line.replace("route-target import ", "").strip())
                    elif line.startswith("route-target both"):
                        rt = line.replace("route-target both ", "").strip()
                        vrf.rt_export.append(rt)
                        vrf.rt_import.append(rt)
                ir.vrfs[vrf_name] = vrf

            # VLAN
            elif header.startswith("vlan "):
                parts = header.split()
                if len(parts) >= 2:
                    vlan_id = parts[1]
                    vlan = VlanIR(vlan_id=vlan_id, raw_lines=block)
                    for line in block[1:]:
                        if line.startswith("name "):
                            vlan.name = line.replace("name ", "").strip()
                    ir.vlans[vlan_id] = vlan

            # ACL
            elif header.startswith("ip access-list"):
                parts = header.split()
                name = parts[-1]
                acl = AclIR(name=name, type="extended", raw_lines=block)
                for line in block[1:]:
                    acl.rules.append(AclRuleIR(action="", protocol="", source="", destination="", raw_line=line))
                ir.acls[name] = acl

            # BGP
            elif header.startswith("router bgp"):
                current_vrf = None
                for line in block[1:]:
                    if line.startswith("vrf "):
                        current_vrf = line.split("vrf ")[-1].strip()
                        if current_vrf not in ir.bgp_vrfs:
                            ir.bgp_vrfs[current_vrf] = BgpVrfIR(vrf=current_vrf, raw_lines=[])
                    elif current_vrf:
                        ir.bgp_vrfs[current_vrf].raw_lines.append(line)
                        if line.startswith("neighbor"):
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[1]
                                if ip not in ir.bgp_vrfs[current_vrf].neighbors:
                                    ir.bgp_vrfs[current_vrf].neighbors[ip] = BgpNeighborIR(ip=ip, raw_lines=[])
                                if "route-map" in line:
                                    rm_index = parts.index("route-map")
                                    if len(parts) > rm_index + 2:
                                        direction = parts[rm_index + 1]
                                        rm_name = parts[rm_index + 2]
                                        if direction == "in":
                                            ir.bgp_vrfs[current_vrf].neighbors[ip].route_map_in = rm_name
                                        elif direction == "out":
                                            ir.bgp_vrfs[current_vrf].neighbors[ip].route_map_out = rm_name

            # Route Map
            elif header.startswith("route-map"):
                parts = header.split()
                if len(parts) >= 3:
                    name = parts[1]
                    action = parts[2]
                    seq = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 10
                    if name not in ir.route_maps:
                        ir.route_maps[name] = RouteMapIR(name=name, raw_lines=[])
                    
                    rm_rule = RouteMapRuleIR(action=action, sequence=seq, raw_lines=block)
                    for line in block[1:]:
                        if line.startswith("match"):
                            rm_rule.match_clauses.append(line)
                        elif line.startswith("set"):
                            rm_rule.set_clauses.append(line)
                    ir.route_maps[name].rules.append(rm_rule)
                    ir.route_maps[name].raw_lines.extend(block)
        
        # Static Routes
        for line in config_text.splitlines():
            line = line.strip()
            if line.startswith("ip route "):
                ir.static_routes.append(StaticRouteIR(prefix="", next_hop="", raw_line=line))

        return ir

    def parse_snippet(self, snippet_text: str) -> DeviceIR:
        return self.parse(snippet_text)
