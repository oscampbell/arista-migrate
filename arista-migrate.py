#!/usr/bin/env python3
"""
arista-migrate.py
─────────────────
Extracts everything needed to migrate an interface from one Arista router
to another: VRFs, VLANs, ACLs, prefix-lists, route-maps, static routes,
and BGP VRF stanzas — all pulled from the source router's running-config.

Usage:
    python3 arista-migrate.py -t <target> -s <source> [options]

    -t / --target       The interface config you want to migrate
                        (just the relevant interface stanza(s))
    -s / --source       Full running-config of the source router
    -o / --output       Output file  (default: auto-named from interface)
    --new-interface     Rename the interface on the new device, e.g.
                        --new-interface Ethernet38=Ethernet5
    --no-color          Disable ANSI colour output

Example:
    python3 arista-migrate.py \\
        -t config \\
        -s oldrouter \\
        --new-interface Ethernet38=Ethernet5
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# ANSI colours
# ─────────────────────────────────────────────────────────────────────────────

RESET   = "\033[0m"
BOLD    = "\033[1m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"

USE_COLOR = True

def c(text, *codes):
    if not USE_COLOR:
        return str(text)
    return "".join(codes) + str(text) + RESET


# ─────────────────────────────────────────────────────────────────────────────
# Config block parser
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConfigBlock:
    header: str
    lines:  List[str]
    kind:   str
    name:   str


def parse_blocks(text: str) -> List[ConfigBlock]:
    blocks: List[ConfigBlock] = []
    raw_lines = text.splitlines()
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i].rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("!") or stripped.startswith("#"):
            i += 1
            continue

        # Must be a top-level (non-indented) line
        if line and line[0] == " ":
            i += 1
            continue

        body = [stripped]
        j = i + 1
        while j < len(raw_lines):
            nxt = raw_lines[j].rstrip()
            if not nxt or nxt == "!":
                j += 1
                break
            if nxt and nxt[0] == " ":
                body.append(nxt.strip())
                j += 1
            else:
                break

        kind, name = classify_block(stripped)
        blocks.append(ConfigBlock(header=stripped, lines=body, kind=kind, name=name))
        i = j

    return blocks


def classify_block(header: str) -> Tuple[str, str]:
    h = header.strip()

    m = re.match(r'^interface\s+(\S+)', h)
    if m:
        return "interface", m.group(1)

    m = re.match(r'^vrf instance\s+(\S+)', h)
    if m:
        return "vrf_instance", m.group(1)

    m = re.match(r'^ip access-list(?:\s+\w+)?\s+(\S+)', h)
    if m:
        return "acl", m.group(1)

    m = re.match(r'^router bgp\s+(\d+)', h)
    if m:
        return "router_bgp", m.group(1)

    m = re.match(r'^route-map\s+(\S+)', h)
    if m:
        return "route_map", m.group(1)

    m = re.match(r'^ip prefix-list\s+(\S+)', h)
    if m:
        return "prefix_list", m.group(1)

    m = re.match(r'^ip route(?:\s+vrf\s+(\S+))?', h)
    if m:
        return "static_route", m.group(1) or "__default__"

    m = re.match(r'^ip routing(?:\s+vrf\s+(\S+))?', h)
    if m:
        return "ip_routing", m.group(1) or "__default__"

    m = re.match(r'^vlan\s+(\d+)$', h)
    if m:
        return "vlan", m.group(1)

    return "other", h


# ─────────────────────────────────────────────────────────────────────────────
# Snippet analysis
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SnippetInfo:
    base_interfaces: Set[str] = field(default_factory=set)
    sub_interfaces:  Set[str] = field(default_factory=set)
    vrfs:            Set[str] = field(default_factory=set)
    acls:            Set[str] = field(default_factory=set)
    vlans:           Set[str] = field(default_factory=set)
    vlan_ids:        Set[str] = field(default_factory=set)
    ip_addresses:    Set[str] = field(default_factory=set)
    networks:        Set[str] = field(default_factory=set)


def extract_snippet_info(snippet_text: str) -> SnippetInfo:
    info = SnippetInfo()
    blocks = parse_blocks(snippet_text)

    for blk in blocks:
        if blk.kind != "interface":
            continue

        iface = blk.name
        info.sub_interfaces.add(iface)
        base = re.sub(r'\.\d+$', '', iface)
        info.base_interfaces.add(base)

        for line in blk.lines:
            m = re.search(r'\bvrf\s+(\S+)', line)
            if m and m.group(1) not in ('instance', 'MGMT'):
                info.vrfs.add(m.group(1))

            m = re.search(r'ip access-group\s+(\S+)', line)
            if m:
                info.acls.add(m.group(1))

            m = re.search(r'encapsulation dot1q vlan\s+(\d+)', line)
            if m:
                info.vlans.add(m.group(1))
                info.vlan_ids.add(m.group(1))

            for m in re.finditer(r'ip address\s+(\d+\.\d+\.\d+\.\d+)/(\d+)', line):
                info.ip_addresses.add(m.group(1))
                info.networks.add(f"{m.group(1)}/{m.group(2)}")

    return info


# ─────────────────────────────────────────────────────────────────────────────
# BGP block splitter
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BgpVrfStanza:
    vrf:          str
    lines:        List[str]
    prefix_lists: Set[str] = field(default_factory=set)
    route_maps:   Set[str] = field(default_factory=set)


def split_bgp_block(bgp_block: ConfigBlock) -> Tuple[List[str], List[BgpVrfStanza]]:
    global_lines: List[str] = [bgp_block.header]
    vrf_stanzas:  List[BgpVrfStanza] = []

    current_vrf:   Optional[str]  = None
    current_lines: List[str]      = []
    af_buffer:     List[str]      = []
    in_af:         bool           = False

    for raw in bgp_block.lines:
        stripped = raw.strip()

        m = re.match(r'^vrf\s+(\S+)$', stripped)
        if m:
            if current_vrf is not None:
                if in_af and af_buffer:
                    current_lines.extend(af_buffer)
                    af_buffer = []
                    in_af = False
                stanza = BgpVrfStanza(vrf=current_vrf, lines=current_lines)
                _extract_bgp_deps(stanza)
                vrf_stanzas.append(stanza)
            current_vrf   = m.group(1)
            current_lines = [f"   vrf {current_vrf}"]
            in_af = False
            af_buffer = []
            continue

        if current_vrf is None:
            global_lines.append("   " + stripped)
        else:
            if re.match(r'^address-family\s+', stripped):
                in_af = True
                af_buffer = [f"      {stripped}"]
            elif in_af:
                if stripped == "!":
                    af_buffer.append("      !")
                    current_lines.extend(af_buffer)
                    af_buffer = []
                    in_af = False
                else:
                    af_buffer.append(f"         {stripped}")
            else:
                current_lines.append(f"      {stripped}")

    if current_vrf is not None:
        if in_af and af_buffer:
            current_lines.extend(af_buffer)
        stanza = BgpVrfStanza(vrf=current_vrf, lines=current_lines)
        _extract_bgp_deps(stanza)
        vrf_stanzas.append(stanza)

    return global_lines, vrf_stanzas


def _extract_bgp_deps(stanza: BgpVrfStanza):
    for line in stanza.lines:
        m = re.search(r'prefix-list\s+(\S+)', line)
        if m:
            stanza.prefix_lists.add(m.group(1))
        m = re.search(r'route-map\s+(\S+)', line)
        if m:
            stanza.route_maps.add(m.group(1))


def extract_global_bgp_redist_maps(global_lines: List[str]) -> Set[str]:
    maps: Set[str] = set()
    for line in global_lines:
        m = re.search(r'redistribute\s+\w+\s+route-map\s+(\S+)', line)
        if m:
            maps.add(m.group(1))
    return maps


# ─────────────────────────────────────────────────────────────────────────────
# Static route relevance
# ─────────────────────────────────────────────────────────────────────────────

def is_static_route_relevant(blk: ConfigBlock, info: SnippetInfo) -> bool:
    line = blk.header
    m = re.match(r'ip route vrf (\S+)', line)
    if m and m.group(1) in info.vrfs:
        return True

    ips_in_line = re.findall(r'(\d+\.\d+\.\d+\.\d+)', line)
    for ip in ips_in_line:
        if ip in info.ip_addresses:
            return True
        pfx3 = ".".join(ip.split(".")[:3])
        for known_ip in info.ip_addresses:
            if known_ip.startswith(pfx3 + "."):
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Interface renaming
# ─────────────────────────────────────────────────────────────────────────────

def build_rename_map(info: SnippetInfo, renames: List[str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    for spec in renames:
        if "=" not in spec:
            sys.exit(f"[error] --new-interface must be OLD=NEW, got: {spec}")
        old, new = spec.split("=", 1)
        old, new = old.strip(), new.strip()
        rename_map[old] = new
        for sub in info.sub_interfaces:
            if sub.startswith(old + "."):
                rename_map[sub] = new + sub[len(old):]
    return rename_map


def apply_renames(text: str, rename_map: Dict[str, str]) -> str:
    for old, new in sorted(rename_map.items(), key=lambda x: -len(x[0])):
        text = re.sub(r'\b' + re.escape(old) + r'\b', new, text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Extraction result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    vrf_instances:    List[ConfigBlock]  = field(default_factory=list)
    ip_routing_lines: List[str]          = field(default_factory=list)
    vlans:            List[ConfigBlock]  = field(default_factory=list)
    interfaces:       List[ConfigBlock]  = field(default_factory=list)
    acls:             List[ConfigBlock]  = field(default_factory=list)
    prefix_lists:     List[ConfigBlock]  = field(default_factory=list)
    route_maps:       List[ConfigBlock]  = field(default_factory=list)
    bgp_vrf_stanzas:  List[BgpVrfStanza] = field(default_factory=list)
    static_routes:    List[ConfigBlock]  = field(default_factory=list)
    warnings:         List[str]          = field(default_factory=list)


def extract(snippet_text: str, fullconfig_text: str,
             renames: List[str]) -> Tuple[ExtractionResult, SnippetInfo, Dict[str, str]]:

    info       = extract_snippet_info(snippet_text)
    rename_map = build_rename_map(info, renames)
    result     = ExtractionResult()
    all_blocks = parse_blocks(fullconfig_text)

    by_kind: Dict[str, List[ConfigBlock]] = defaultdict(list)
    for blk in all_blocks:
        by_kind[blk.kind].append(blk)

    # 1. VRF instances
    for blk in by_kind["vrf_instance"]:
        if blk.name in info.vrfs:
            result.vrf_instances.append(blk)

    # 2. ip routing
    for blk in by_kind["ip_routing"]:
        if blk.name in info.vrfs:
            result.ip_routing_lines.append(blk.header)

    # 3. VLANs
    for blk in by_kind["vlan"]:
        if blk.name in info.vlan_ids:
            result.vlans.append(blk)

    # 4. Interfaces — also collect any additional ACLs/VRFs
    for blk in by_kind["interface"]:
        base = re.sub(r'\.\d+$', '', blk.name)
        if blk.name in info.sub_interfaces or base in info.base_interfaces:
            result.interfaces.append(blk)
            for line in blk.lines:
                m = re.search(r'ip access-group\s+(\S+)', line)
                if m:
                    info.acls.add(m.group(1))
                m = re.search(r'\bvrf\s+(\S+)', line)
                if m and m.group(1) not in ('instance', 'MGMT'):
                    info.vrfs.add(m.group(1))

    # 5. ACLs
    for blk in by_kind["acl"]:
        if blk.name in info.acls:
            result.acls.append(blk)

    # 6. BGP
    bgp_prefix_lists: Set[str] = set()
    bgp_route_maps:   Set[str] = set()

    for blk in by_kind["router_bgp"]:
        global_lines, vrf_stanzas = split_bgp_block(blk)
        global_redist = extract_global_bgp_redist_maps(global_lines)
        bgp_route_maps.update(global_redist)
        for stanza in vrf_stanzas:
            if stanza.vrf in info.vrfs:
                result.bgp_vrf_stanzas.append(stanza)
                bgp_prefix_lists.update(stanza.prefix_lists)
                bgp_route_maps.update(stanza.route_maps)

    # 7. Route-maps (resolve prefix-list deps transitively)
    rm_by_name: Dict[str, List[ConfigBlock]] = defaultdict(list)
    for blk in by_kind["route_map"]:
        rm_by_name[blk.name].append(blk)

    needed_rms: Set[str]  = set(bgp_route_maps)
    visited_rms: Set[str] = set()
    all_pfx: Set[str]     = set(bgp_prefix_lists)

    while needed_rms - visited_rms:
        for rm_name in list(needed_rms - visited_rms):
            visited_rms.add(rm_name)
            rm_blocks = rm_by_name.get(rm_name, [])
            if not rm_blocks:
                result.warnings.append(f"Route-map '{rm_name}' referenced but not found")
                continue
            for rm_blk in rm_blocks:
                result.route_maps.append(rm_blk)
                for line in rm_blk.lines:
                    m = re.search(r'prefix-list\s+(\S+)', line)
                    if m:
                        all_pfx.add(m.group(1))

    # 8. Prefix lists
    for blk in by_kind["prefix_list"]:
        if blk.name in all_pfx:
            result.prefix_lists.append(blk)

    # 9. Static routes
    for blk in by_kind["static_route"]:
        if is_static_route_relevant(blk, info):
            result.static_routes.append(blk)

    # 10. Apply renames to interfaces
    if rename_map:
        def rb(blk: ConfigBlock) -> ConfigBlock:
            return ConfigBlock(
                header=apply_renames(blk.header, rename_map),
                lines=[apply_renames(l, rename_map) for l in blk.lines],
                kind=blk.kind, name=blk.name
            )
        result.interfaces = [rb(b) for b in result.interfaces]

    return result, info, rename_map


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────

SEP = "!" + "─" * 70

def render_block_text(blk: ConfigBlock) -> str:
    lines = []
    if blk.lines:
        lines.append(blk.lines[0])
        for line in blk.lines[1:]:
            lines.append("   " + line)
    lines.append("!")
    return "\n".join(lines)


BANNER_WIDTH = 70

def _banner(title: str, char: str = "█") -> List[str]:
    """Return a hard-to-miss block banner as a list of comment lines."""
    bar  = "! " + char * (BANNER_WIDTH - 2)
    pad  = "! " + " " * (BANNER_WIDTH - 2)
    body = f"! {title}"
    body = body + " " * max(0, BANNER_WIDTH - len(body))
    return [bar, pad, body, pad, bar]


def render_output(result: ExtractionResult, info: SnippetInfo,
                   target_text: str, rename_map: Dict[str, str]) -> str:
    out = []

    def section(title: str):
        out.append("")
        out.append(SEP)
        out.append(f"! SECTION: {title}")
        out.append(SEP)

    # ── File header
    ifaces_str  = ", ".join(sorted(info.sub_interfaces))
    vrfs_str    = ", ".join(sorted(info.vrfs))
    acls_str    = ", ".join(sorted(info.acls))
    out.append("! " + "═" * 68)
    out.append("! ARISTA MIGRATION CONFIG EXTRACT")
    out.append(f"! Source interfaces : {ifaces_str}")
    out.append(f"! VRFs              : {vrfs_str}")
    out.append(f"! ACLs              : {acls_str}")
    if rename_map:
        for old, new in rename_map.items():
            out.append(f"! Rename            : {old} -> {new}")
    out.append("! " + "═" * 68)

    # ══════════════════════════════════════════════════════════════════
    # PART 1 — REFERENCE ONLY (do not paste)
    # ══════════════════════════════════════════════════════════════════
    out.append("")
    out.extend(_banner("PART 1 of 2 — REFERENCE ONLY — DO NOT PASTE THIS INTO THE NEW ROUTER"))
    out.append("!")
    out.append("! This is the original target config that was submitted for migration.")
    out.append("! It is included here for reference only so you can cross-check the")
    out.append("! extracted config below.  Scroll past Part 1 before copying anything.")
    out.append("!")
    out.append(target_text.strip())
    out.append("")
    out.extend(_banner("END OF PART 1 — DO NOT PASTE ANYTHING ABOVE THIS LINE"))

    # ══════════════════════════════════════════════════════════════════
    # PART 2 — MIGRATION CONFIG (paste this)
    # ══════════════════════════════════════════════════════════════════
    out.append("")
    out.extend(_banner("PART 2 of 2 — MIGRATION CONFIG — PASTE FROM HERE", char="▓"))
    out.append("!")
    out.append("! Everything below has been extracted from the source router config.")
    out.append("! Review each section carefully before applying to the new router.")
    out.append("!")

    if result.vrf_instances:
        section("VRF INSTANCE DEFINITIONS")
        for blk in result.vrf_instances:
            out.append(render_block_text(blk))

    if result.ip_routing_lines:
        section("IP ROUTING VRF STATEMENTS")
        for line in sorted(set(result.ip_routing_lines)):
            out.append(line)
        out.append("!")

    if result.vlans:
        section("VLAN DEFINITIONS")
        for blk in result.vlans:
            out.append(render_block_text(blk))

    if result.interfaces:
        section("INTERFACES (base + sub-interfaces from full config)")
        for blk in result.interfaces:
            out.append(render_block_text(blk))

    if result.acls:
        section("ACCESS LISTS")
        for blk in result.acls:
            out.append(render_block_text(blk))

    if result.static_routes:
        section("STATIC ROUTES")
        for blk in result.static_routes:
            out.append(blk.header)
        out.append("!")

    if result.bgp_vrf_stanzas:
        section("BGP VRF STANZAS  (paste inside 'router bgp <ASN>')")
        for stanza in result.bgp_vrf_stanzas:
            for line in stanza.lines:
                out.append(line)
            out.append("   !")

    if result.prefix_lists:
        section("PREFIX LISTS")
        seen = set()
        for blk in result.prefix_lists:
            h = blk.header
            if h not in seen:
                seen.add(h)
                out.append(h)
        out.append("!")

    if result.route_maps:
        section("ROUTE MAPS")
        seen_h = set()
        for blk in result.route_maps:
            if blk.header not in seen_h:
                seen_h.add(blk.header)
                out.append(render_block_text(blk))

    if result.warnings:
        section("WARNINGS")
        for w in result.warnings:
            out.append(f"! [WARN] {w}")

    out.append("")
    out.extend(_banner("END OF PART 2 — END OF MIGRATION CONFIG", char="▓"))
    out.append("")

    return "\n".join(out)


def render_summary(result: ExtractionResult, info: SnippetInfo):
    print(c("\n╔═══════════════════════════════════════════════════════╗", CYAN, BOLD), file=sys.stderr)
    print(c("║       ARISTA MIGRATION EXTRACTOR — SUMMARY           ║", CYAN, BOLD), file=sys.stderr)
    print(c("╚═══════════════════════════════════════════════════════╝", CYAN, BOLD), file=sys.stderr)

    def row(label, value):
        print(f"  {c(label + ':', BOLD):<38} {c(value, GREEN)}", file=sys.stderr)

    row("Base interface(s)",    ", ".join(sorted(info.base_interfaces)) or "(none)")
    row("Sub-interface(s)",     ", ".join(sorted(info.sub_interfaces)) or "(none)")
    row("VRF(s) found",         ", ".join(sorted(info.vrfs)) or "(none)")
    row("ACL(s) found",         ", ".join(sorted(info.acls)) or "(none)")
    row("VLAN(s) found",        ", ".join(sorted(info.vlan_ids)) or "(none)")
    row("Interfaces extracted", str(len(result.interfaces)))
    row("ACLs extracted",       str(len(result.acls)))
    row("BGP VRF stanzas",      str(len(result.bgp_vrf_stanzas)))
    row("Prefix-lists",         str(len(set(b.header for b in result.prefix_lists))))
    row("Route-map blocks",     str(len(set(b.header for b in result.route_maps))))
    row("Static routes",        str(len(result.static_routes)))

    if result.warnings:
        print(c("\n  WARNINGS:", YELLOW, BOLD), file=sys.stderr)
        for w in result.warnings:
            print(c(f"    ⚠  {w}", YELLOW), file=sys.stderr)
    print(file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def auto_output_name(info: SnippetInfo, rename_map: Dict[str, str]) -> str:
    """Generate an output filename from the base interface name."""
    # Prefer the new (renamed) interface name if one was given
    bases = sorted(info.base_interfaces)
    if bases:
        iface = bases[0]
        # Apply rename if present
        new_iface = rename_map.get(iface, iface)
        # Sanitise for filesystem: Ethernet38 -> Ethernet38
        safe = re.sub(r'[^A-Za-z0-9_\-.]', '_', new_iface)
        return f"migrate-{safe}.txt"
    return "migrate-output.txt"


def main():
    global USE_COLOR

    # Print friendly help when called with no arguments
    if len(sys.argv) == 1:
        print(__doc__)
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-t", "--target",        required=True,
                        help="Target: the interface stanza(s) you want to migrate")
    parser.add_argument("-s", "--source",        required=True,
                        help="Source: full running-config of the existing router")
    parser.add_argument("-o", "--output",        default=None,
                        help="Output file (default: auto-named from interface, e.g. migrate-Ethernet38.txt)")
    parser.add_argument("--new-interface",        action="append", default=[],
                        metavar="OLD=NEW",
                        help="Interface rename on new device, e.g. --new-interface Ethernet38=Ethernet5")
    parser.add_argument("--no-color",             action="store_true",
                        help="Disable ANSI colour output")

    args = parser.parse_args()
    USE_COLOR = not args.no_color

    try:
        target_text     = open(args.target).read()
        fullconfig_text = open(args.source).read()
    except FileNotFoundError as e:
        sys.exit(c(f"[error] {e}", RED))

    result, info, rename_map = extract(target_text, fullconfig_text, args.new_interface)
    render_summary(result, info)
    output_text = render_output(result, info, target_text, rename_map)

    # Determine output path
    out_path = args.output if args.output else auto_output_name(info, rename_map)

    with open(out_path, "w") as f:
        f.write(output_text)
    print(c(f"  ✓ Output written to: {out_path}", GREEN, BOLD), file=sys.stderr)


if __name__ == "__main__":
    main()
