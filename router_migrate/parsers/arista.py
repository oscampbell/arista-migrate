import re
from typing import List, Dict
from router_migrate.parsers.base import BaseParser
from router_migrate.models import DeviceIR, InterfaceIR, VrfIR, VlanIR, AclIR, AclRuleIR, BgpVrfIR, BgpNeighborIR, StaticRouteIR, RouteMapIR, RouteMapRuleIR, IPAddress, PrefixListIR, PrefixListRuleIR

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

    def _parse_acl_rule(self, raw_line: str) -> AclRuleIR:
        rule = AclRuleIR(action="permit", protocol="ip", source="any", destination="any", raw_line=raw_line)
        parts = raw_line.split()
        if not parts: return rule
        
        if parts[0].isdigit():
            parts.pop(0)
            
        if not parts: return rule
        rule.action = parts.pop(0)
        
        if not parts: return rule
        rule.protocol = parts.pop(0)
        
        if not parts: return rule
        if parts[0] == "any":
            rule.source = "any"
            parts.pop(0)
        elif parts[0] == "host":
            parts.pop(0)
            rule.source = f"host {parts.pop(0)}" if parts else "any"
        else:
            ip = parts.pop(0)
            mask = parts.pop(0) if parts else "0.0.0.0"
            rule.source = f"{ip} {mask}"
            
        if parts and parts[0] in ["eq", "gt", "lt", "neq", "range"]:
            op = parts.pop(0)
            port = parts.pop(0)
            if op == "range":
                port2 = parts.pop(0) if parts else ""
                rule.source_port = f"{op} {port} {port2}".strip()
            else:
                rule.source_port = f"{op} {port}"

        if not parts: return rule
        if parts[0] == "any":
            rule.destination = "any"
            parts.pop(0)
        elif parts[0] == "host":
            parts.pop(0)
            rule.destination = f"host {parts.pop(0)}" if parts else "any"
        else:
            ip = parts.pop(0)
            mask = parts.pop(0) if parts else "0.0.0.0"
            rule.destination = f"{ip} {mask}"
            
        if parts and parts[0] in ["eq", "gt", "lt", "neq", "range"]:
            op = parts.pop(0)
            port = parts.pop(0)
            if op == "range":
                port2 = parts.pop(0) if parts else ""
                rule.destination_port = f"{op} {port} {port2}".strip()
            else:
                rule.destination_port = f"{op} {port}"
                
        if "log" in parts:
            rule.log = True
            
        return rule

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
                    elif line.startswith("mtu"):
                        iface.mtu = int(line.split()[1])
                    elif line.startswith("speed"):
                        iface.speed = line.replace("speed", "").strip()
                    elif line.startswith("load-interval"):
                        iface.load_interval = int(line.split()[1])
                    elif line.startswith("ip address"):
                        parts = line.split()
                        sec = "secondary" in parts
                        if len(parts) >= 3:
                            if "/" in parts[2]:
                                addr, mask = parts[2].split("/")
                                iface.ip_addresses.append(IPAddress(address=addr, mask=mask, secondary=sec))
                            elif len(parts) >= 4:
                                iface.ip_addresses.append(IPAddress(address=parts[2], mask=parts[3], secondary=sec))
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
                    if line.startswith("permit") or line.startswith("deny") or (line.split()[0].isdigit() and (line.split()[1] == "permit" or line.split()[1] == "deny")):
                        acl.rules.append(self._parse_acl_rule(line))
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
                                if "prefix-list" in line:
                                    pl_index = parts.index("prefix-list")
                                    if len(parts) > pl_index + 2:
                                        direction = parts[pl_index + 2]
                                        pl_name = parts[pl_index + 1]
                                        if direction == "in":
                                            ir.bgp_vrfs[current_vrf].neighbors[ip].prefix_list_in = pl_name
                                        elif direction == "out":
                                            ir.bgp_vrfs[current_vrf].neighbors[ip].prefix_list_out = pl_name

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
        
            # Prefix List
            elif header.startswith("ip prefix-list"):
                for line in block:
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[2]
                        if name not in ir.prefix_lists:
                            ir.prefix_lists[name] = PrefixListIR(name=name, raw_lines=[])
                        
                        rule = PrefixListRuleIR(action="permit", prefix="0.0.0.0/0", raw_line=line)
                        if "seq" in parts:
                            seq_idx = parts.index("seq")
                            rule.seq = int(parts[seq_idx + 1])
                        
                        if "permit" in parts:
                            rule.action = "permit"
                            p_idx = parts.index("permit")
                            rule.prefix = parts[p_idx + 1]
                        elif "deny" in parts:
                            rule.action = "deny"
                            d_idx = parts.index("deny")
                            rule.prefix = parts[d_idx + 1]
                            
                        if "le" in parts:
                            le_idx = parts.index("le")
                            rule.le = int(parts[le_idx + 1])
                        if "ge" in parts:
                            ge_idx = parts.index("ge")
                            rule.ge = int(parts[ge_idx + 1])
                            
                        ir.prefix_lists[name].rules.append(rule)
                        ir.prefix_lists[name].raw_lines.append(line)

        # Static Routes
        for line in config_text.splitlines():
            line = line.strip()
            if line.startswith("ip route "):
                parts = line.split()
                sr = StaticRouteIR(prefix="", next_hop="", raw_line=line)
                
                # ip route vrf CDCN 0.0.0.0/0 10.32.2.146
                # ip route 193.203.70.160/29 193.203.70.98
                if "vrf" in parts:
                    v_idx = parts.index("vrf")
                    sr.vrf = parts[v_idx + 1]
                    sr.prefix = parts[v_idx + 2]
                    sr.next_hop = parts[v_idx + 3] if len(parts) > v_idx + 3 else ""
                else:
                    sr.prefix = parts[2]
                    sr.next_hop = parts[3] if len(parts) > 3 else ""
                    
                ir.static_routes.append(sr)

        return ir

    def parse_snippet(self, snippet_text: str) -> DeviceIR:
        return self.parse(snippet_text)
