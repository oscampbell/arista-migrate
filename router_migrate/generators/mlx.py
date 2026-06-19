from typing import List
from router_migrate.generators.base import BaseGenerator
from router_migrate.models import MigrationIR

class MlxGenerator(BaseGenerator):
    def generate(self, migration_ir: MigrationIR) -> str:
        out: List[str] = []
        
        out.append("!" + "=" * 68)
        out.append("! MLX MIGRATION CONFIG EXTRACT")
        out.append(f"! Source Vendor: {migration_ir.source_vendor}")
        out.append("!" + "=" * 68)
        out.append("")

        # VRFs
        if migration_ir.vrfs:
            out.append("! SECTION: VRF DEFINITIONS")
            out.append("!" + "-" * 68)
            for vrf in migration_ir.vrfs:
                out.append(f"vrf {vrf.name}")
                if vrf.rd:
                    out.append(f" rd {vrf.rd}")
                for rt in vrf.rt_import:
                    out.append(f" route-target import {rt}")
                for rt in vrf.rt_export:
                    out.append(f" route-target export {rt}")
                out.append("!")
            out.append("")

        # VLANs
        if migration_ir.vlans:
            out.append("! SECTION: VLAN DEFINITIONS")
            out.append("!" + "-" * 68)
            for vlan in migration_ir.vlans:
                out.append(f"vlan {vlan.vlan_id}")
                if vlan.name:
                    out.append(f" name {vlan.name}")
                out.append("!")
            out.append("")

        # Interfaces
        if migration_ir.interfaces:
            out.append("! SECTION: INTERFACES")
            out.append("!" + "-" * 68)
            for iface in migration_ir.interfaces:
                out.append(f"interface {iface.name}")
                if iface.description:
                    out.append(f" port-name {iface.description}")
                if not iface.enabled:
                    out.append(" disable")
                else:
                    out.append(" enable")
                if iface.vrf:
                    out.append(f" vrf forwarding {iface.vrf}")
                for ip in iface.ip_addresses:
                    out.append(f" ip address {ip.address}/{ip.mask}")
                if iface.acl_in:
                    out.append(f" ip access-group {iface.acl_in} in")
                if iface.acl_out:
                    out.append(f" ip access-group {iface.acl_out} out")
                out.append("!")
            out.append("")

        # ACLs
        if migration_ir.acls:
            out.append("! SECTION: ACCESS LISTS")
            out.append("!" + "-" * 68)
            for acl in migration_ir.acls:
                # Basic translation
                out.append(f"ip access-list extended {acl.name}")
                for rule in acl.rules:
                    translated = rule.raw_line
                    # Remove "ip access-list" from raw Arista line if any
                    out.append(f" {translated}")
                out.append("!")
            out.append("")

        # Static Routes
        if migration_ir.static_routes:
            out.append("! SECTION: STATIC ROUTES")
            out.append("!" + "-" * 68)
            for sr in migration_ir.static_routes:
                out.append(sr.raw_line)
            out.append("!")
            out.append("")

        # BGP
        if migration_ir.bgp_vrfs:
            out.append("! SECTION: BGP VRF STANZAS")
            out.append("!" + "-" * 68)
            out.append("router bgp")
            for bgp in migration_ir.bgp_vrfs:
                out.append(f" address-family ipv4 unicast vrf {bgp.vrf}")
                for line in bgp.raw_lines:
                    line = line.strip()
                    if line.startswith("neighbor"):
                        out.append(f"  {line}")
                out.append(" exit-address-family")
            out.append("!")
            out.append("")

        # Prefix Lists & Route Maps
        if migration_ir.prefix_lists:
            out.append("! SECTION: PREFIX LISTS")
            out.append("!" + "-" * 68)
            for pl in migration_ir.prefix_lists:
                for rule in pl.rules:
                    out.append(rule.raw_line)
            out.append("!")
            out.append("")

        if migration_ir.route_maps:
            out.append("! SECTION: ROUTE MAPS")
            out.append("!" + "-" * 68)
            for rm in migration_ir.route_maps:
                for rule in rm.rules:
                    out.append(f"route-map {rm.name} {rule.action} {rule.sequence}")
                    for match in rule.match_clauses:
                        out.append(f" {match}")
                    for set_c in rule.set_clauses:
                        out.append(f" {set_c}")
                out.append("!")
            out.append("")

        if migration_ir.warnings:
            out.append("! WARNINGS:")
            for w in migration_ir.warnings:
                out.append(f"! [WARN] {w}")

        return "\n".join(out)
