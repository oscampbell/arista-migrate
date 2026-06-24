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
import os
import logging
from router_migrate import __version__
from router_migrate.parsers.mlx import MlxParser
from router_migrate.parsers.arista import AristaParser
from router_migrate.parsers.cisco import CiscoParser
from router_migrate.parsers.juniper import JuniperParser
from router_migrate.parsers.brocade import BrocadeParser
from router_migrate.parsers.huawei import HuaweiParser
from router_migrate.generators.arista import AristaGenerator
from router_migrate.generators.mlx import MlxGenerator
from router_migrate.generators.cisco import CiscoGenerator
from router_migrate.generators.juniper import JuniperGenerator
from router_migrate.generators.brocade import BrocadeGenerator
from router_migrate.generators.huawei import HuaweiGenerator
from router_migrate.analyzers.migrator import Migrator

def main():
    parser = argparse.ArgumentParser(
        description="Universal Router Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-t", "--target", required=True,
                        help="Target: the interface stanza(s) you want to migrate (use '-' for stdin)")
    parser.add_argument("-s", "--source", required=True,
                        help="Source: full running-config of the existing router (use '-' for stdin)")
    parser.add_argument("--source-vendor", required=True, choices=["mlx", "arista", "cisco", "juniper", "brocade", "huawei"],
                        help="Vendor of the source configuration")
    parser.add_argument("--target-vendor", required=True, choices=["arista", "mlx", "cisco", "juniper", "brocade", "huawei"],
                        help="Target vendor to migrate to")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file (default: stdout)")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Force overwrite if output file already exists")
    parser.add_argument("--new-interface", action="append", default=[],
                        metavar="OLD=NEW",
                        help="Interface rename on new device, e.g. --new-interface ethernet 1/1=Ethernet5")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose logging")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}",
                        help="Show the version of the tool")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    try:
        if args.target == "-":
            target_text = sys.stdin.read()
        else:
            with open(args.target) as f:
                target_text = f.read()

        if args.source == "-":
            if args.target == "-":
                sys.exit("[error] cannot read both target and source from stdin")
            fullconfig_text = sys.stdin.read()
        else:
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
    elif args.source_vendor == "arista":
        parser_obj = AristaParser()
    elif args.source_vendor == "cisco":
        parser_obj = CiscoParser()
    elif args.source_vendor == "juniper":
        parser_obj = JuniperParser()
    elif args.source_vendor == "brocade":
        parser_obj = BrocadeParser()
    elif args.source_vendor == "huawei":
        parser_obj = HuaweiParser()
    else:
        sys.exit(f"[error] unknown source vendor: {args.source_vendor}")

    source_device = parser_obj.parse(fullconfig_text)
    target_snippet = parser_obj.parse_snippet(target_text)

    # 2. Analyze & Extract
    migrator = Migrator(source_device, target_snippet, args.source_vendor, args.target_vendor, renames)
    migration_ir = migrator.analyze()

    # 3. Generate
    if args.target_vendor == "arista":
        generator = AristaGenerator()
    elif args.target_vendor == "mlx":
        generator = MlxGenerator()
    elif args.target_vendor == "cisco":
        generator = CiscoGenerator()
    elif args.target_vendor == "juniper":
        generator = JuniperGenerator()
    elif args.target_vendor == "brocade":
        generator = BrocadeGenerator()
    elif args.target_vendor == "huawei":
        generator = HuaweiGenerator()
    else:
        sys.exit(f"[error] unknown target vendor: {args.target_vendor}")

    output_text = generator.generate(migration_ir)

    # Output
    if args.output:
        if os.path.exists(args.output) and not args.force:
            sys.exit(f"[error] Output file '{args.output}' already exists. Use -f or --force to overwrite.")
        with open(args.output, "w") as f:
            f.write(output_text)
        print(f"Output written to: {args.output}")
    else:
        print(output_text)

if __name__ == "__main__":
    main()
