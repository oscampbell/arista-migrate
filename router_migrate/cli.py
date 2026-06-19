#!/usr/bin/env python3
"""
router-migrate
──────────────
Extracts everything needed to migrate an interface from one router
to another: VRFs, VLANs, ACLs, prefix-lists, route-maps, static routes,
and BGP VRF stanzas — all pulled from the source router's running-config.

Usage:
    python3 -m router_migrate.cli -t <target> -s <source> --source-vendor <sv> --target-vendor <tv> [options]
"""

import argparse
import sys
import re
from router_migrate.parsers.mlx import MlxParser
from router_migrate.parsers.arista import AristaParser
from router_migrate.generators.arista import AristaGenerator
from router_migrate.generators.mlx import MlxGenerator
from router_migrate.analyzers.migrator import Migrator

def main():
    parser = argparse.ArgumentParser(
        description="Universal Router Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-t", "--target", required=True,
                        help="Target: the interface stanza(s) you want to migrate")
    parser.add_argument("-s", "--source", required=True,
                        help="Source: full running-config of the existing router")
    parser.add_argument("--source-vendor", required=True, choices=["mlx", "arista"],
                        help="Vendor of the source configuration")
    parser.add_argument("--target-vendor", required=True, choices=["arista", "mlx"],
                        help="Target vendor to migrate to")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file (default: stdout)")
    parser.add_argument("--new-interface", action="append", default=[],
                        metavar="OLD=NEW",
                        help="Interface rename on new device, e.g. --new-interface ethernet 1/1=Ethernet5")

    args = parser.parse_args()

    try:
        with open(args.target) as f:
            target_text = f.read()
        with open(args.source) as f:
            fullconfig_text = f.read()
    except FileNotFoundError as e:
        sys.exit(f"[error] {e}")

    # Build renames map
    renames = {}
    for spec in args.new_interface:
        if "=" not in spec:
            sys.exit(f"[error] --new-interface must be OLD=NEW, got: {spec}")
        old, new = spec.split("=", 1)
        renames[old.strip()] = new.strip()

    # 1. Parse
    if args.source_vendor == "mlx":
        parser_obj = MlxParser()
    else:
        parser_obj = AristaParser()

    source_device = parser_obj.parse(fullconfig_text)
    target_snippet = parser_obj.parse_snippet(target_text)

    # 2. Analyze & Extract
    migrator = Migrator(source_device, target_snippet, args.source_vendor, args.target_vendor, renames)
    migration_ir = migrator.analyze()

    # 3. Generate
    if args.target_vendor == "arista":
        generator = AristaGenerator()
    else:
        generator = MlxGenerator()

    output_text = generator.generate(migration_ir)

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_text)
        print(f"Output written to: {args.output}")
    else:
        print(output_text)

if __name__ == "__main__":
    main()
