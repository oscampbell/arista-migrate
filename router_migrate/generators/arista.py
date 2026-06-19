from typing import List
from router_migrate.generators.base import BaseGenerator
from router_migrate.models import MigrationIR, AclRuleIR

class AristaGenerator(BaseGenerator):
    def _generate_acl_rule(self, rule: AclRuleIR) -> str:
        if not rule.action or not rule.protocol:
            translated = rule.raw_line
            if "access-list" in translated:
                parts = translated.split(maxsplit=2)
                if len(parts) > 2:
                    translated = parts[2]
            return translated
        
        parts = [rule.action, rule.protocol, rule.source]
        if rule.source_port:
            parts.append(rule.source_port)
            
        parts.append(rule.destination)
        if rule.destination_port:
            parts.append(rule.destination_port)
            
        if rule.log:
            parts.append("log")
            
        return " ".join(parts)

    def generate(self, migration_ir: MigrationIR) -> str:
        out: List[str] = []
        
        out.append("!" + "=" * 68)
        out.append("! ARISTA MIGRATION CONFIG EXTRACT")
        out.append(f"! Source Vendor: {migration_ir.source_vendor}")
        out.append("!" + "=" * 68)
        out.append("")

        # VRFs
        if migration_ir.vrfs:
            out.append("! SECTION: VRF INSTANCE DEFINITIONS")
            out.append("!" + "-" * 68)
            for vrf in migration_ir.vrfs:
                out.append(f"vrf instance {vrf.name}")
                if vrf.rd:
                    out.append(f"   rd {vrf.rd}")
                for rt in vrf.rt_import:
                    out.append(f"   route-target import {rt}")
                for rt in vrf.rt_export:
                    out.append(f"   route-target export {rt}")
                out.append("!")
            out.append("")

            out.append("! SECTION: IP ROUTING VRF STATEMENTS")
            out.append("!" + "-" * 68)
            for vrf in migration_ir.vrfs:
                out.append(f"ip routing vrf {vrf.name}")
            out.append("!")
            out.append("")

        # VLANs
        if migration_ir.vlans:
            out.append("! SECTION: VLAN DEFINITIONS")
            out.append("!" + "-" * 68)
            for vlan in migration_ir.vlans:
                out.append(f"vlan {vlan.vlan_id}")
                if vlan.name:
                    out.append(f"   name {vlan.name}")
                out.append("!")
            out.append("")

        # Interfaces
        if migration_ir.interfaces:
            out.append("! SECTION: INTERFACES")
            out.append("!" + "-" * 68)
            for iface in migration_ir.interfaces:
                out.append(f"interface {iface.name}")
                if iface.description:
                    out.append(f"   description {iface.description}")
                if iface.load_interval:
                    out.append(f"   load-interval {iface.load_interval}")
                if iface.mtu:
                    out.append(f"   mtu {iface.mtu}")
                if iface.speed:
                    out.append(f"   speed {iface.speed}")
                    
                if not iface.enabled:
                    out.append("   shutdown")
                else:
                    out.append("   no shutdown")
                    
                if iface.vlan:
                    out.append(f"   encapsulation dot1q vlan {iface.vlan}")
                if iface.vrf:
                    out.append(f"   vrf {iface.vrf}")
                for ip in iface.ip_addresses:
                    sec = " secondary" if ip.secondary else ""
                    out.append(f"   ip address {ip.address}/{ip.mask}{sec}")
                if iface.acl_in:
                    out.append(f"   ip access-group {iface.acl_in} in")
                if iface.acl_out:
                    out.append(f"   ip access-group {iface.acl_out} out")
                out.append("!")
            out.append("")

        # ACLs
        if migration_ir.acls:
            out.append("! SECTION: ACCESS LISTS")
            out.append("!" + "-" * 68)
            for acl in migration_ir.acls:
                # We do a basic best effort translation of the raw line for now
                out.append(f"ip access-list {acl.name}")
                for rule in acl.rules:
                    out.append(f"   {self._generate_acl_rule(rule)}")
                out.append("!")
            out.append("")

        # Static Routes
        if migration_ir.static_routes:
            out.append("! SECTION: STATIC ROUTES")
            out.append("!" + "-" * 68)
            for sr in migration_ir.static_routes:
                vrf_str = f"vrf {sr.vrf} " if sr.vrf else ""
                out.append(f"ip route {vrf_str}{sr.prefix} {sr.next_hop}")
            out.append("!")
            out.append("")

        # BGP
        if migration_ir.bgp_vrfs:
            out.append("! SECTION: BGP VRF STANZAS (paste inside 'router bgp <ASN>')")
            out.append("!" + "-" * 68)
            for bgp in migration_ir.bgp_vrfs:
                out.append(f"   vrf {bgp.vrf}")
                # We need to translate MLX BGP VRF lines to Arista
                for line in bgp.raw_lines:
                    # Very crude translation for demonstration
                    line = line.strip()
                    if line.startswith("neighbor"):
                        out.append(f"      {line}")
                out.append("   !")
            out.append("")



        # Prefix Lists & Route Maps
        if migration_ir.prefix_lists:
            out.append("! SECTION: PREFIX LISTS")
            out.append("!" + "-" * 68)
            for pl in migration_ir.prefix_lists:
                for rule in pl.rules:
                    seq_str = f" seq {rule.seq}" if rule.seq else ""
                    ge_str = f" ge {rule.ge}" if rule.ge else ""
                    le_str = f" le {rule.le}" if rule.le else ""
                    out.append(f"ip prefix-list {pl.name}{seq_str} {rule.action} {rule.prefix}{ge_str}{le_str}")
            out.append("!")
            out.append("")

        if migration_ir.route_maps:
            out.append("! SECTION: ROUTE MAPS")
            out.append("!" + "-" * 68)
            for rm in migration_ir.route_maps:
                for rule in rm.rules:
                    out.append(f"route-map {rm.name} {rule.action} {rule.sequence}")
                    for match in rule.match_clauses:
                        out.append(f"   {match}")
                    for set_c in rule.set_clauses:
                        out.append(f"   {set_c}")
                out.append("!")
            out.append("")

        if migration_ir.warnings:
            out.append("! WARNINGS:")
            for w in migration_ir.warnings:
                out.append(f"! [WARN] {w}")

        return "\n".join(out)
