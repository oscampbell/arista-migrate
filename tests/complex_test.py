import os
import subprocess

COMPLEX_ARISTA_SRC = """
interface Ethernet38
   description MR-OSV8-C-1-LDC24-GB::8::10GB-1310
   load-interval 5
   mtu 9000
   speed forced 10000full
   no switchport
   no mpls ip
!
interface Ethernet38.476
   description CDCN::MR-OSV8-C-1-LDC24-GB
   mtu 9000
   encapsulation dot1q vlan 476
   vrf CDCN
   ip address 10.32.2.145/29
!
interface Ethernet38.1064
   mtu 9000
   encapsulation dot1q vlan 1064
   ip address 193.203.70.97/28
   ip address 89.16.226.201/30 secondary
   ip address 193.203.71.233/29 secondary
   ip access-group STANDARD-IN-ACL in
!
vrf instance CDCN
   description Customer DCN
   rd 127:427
!
vlan 476
!
ip access-list STANDARD-IN-ACL
   10 deny ip any 10.0.0.0/8
   20 deny ip any 192.168.0.0/16
   30 deny ip any 172.16.0.0/12
   40 deny ip 10.0.0.0/8 any
   50 deny ip 192.168.0.0/16 any
   60 deny ip 172.16.0.0/12 any
   70 permit ip any any
!
ip route 193.203.70.160/29 193.203.70.98
ip route vrf TRANSIT-BYPASS 193.203.70.24/29 193.203.71.102 name PIXELOGIC
ip route vrf TRANSIT-BYPASS 193.203.83.32/29 193.203.71.102 name PIXELOGIC
ip route vrf CDCN 0.0.0.0/0 10.32.2.146
!
router bgp 65000
   vrf CDCN
      rd 127:427
      neighbor 10.32.14.1 remote-as 4200000500
      neighbor 10.32.14.1 description LPC-DCN-FIREWALL-CLUSTER
      redistribute connected
      redistribute static
      !
      address-family ipv4
         neighbor 10.32.14.1 prefix-list DEFAULT-ROUTE in
         neighbor 10.32.14.1 prefix-list LDP02-CDCN-RANGES out
      !
   !
!
ip prefix-list DEFAULT-ROUTE seq 10 permit 0.0.0.0/0
ip prefix-list LDP02-CDCN-RANGES seq 10 permit 10.32.2.0/24 le 32
ip prefix-list LDP02-CDCN-RANGES seq 20 permit 10.32.135.0/24 le 32
ip prefix-list SOHONET-RIPE-PREFIX seq 10 permit 193.203.64.0/19 le 32
ip prefix-list SOHONET-RIPE-PREFIX seq 20 permit 89.16.224.0/19 le 32
ip prefix-list SOHONET-RIPE-PREFIX seq 30 permit 46.248.224.0/19 le 32
ip prefix-list SOHONET-RIPE-PREFIX seq 40 permit 185.116.56.0/22 le 32
ip prefix-list SOHONET-RIPE-PREFIX seq 50 permit 94.143.248.0/21 le 32
!
route-map AR-7280SR248YC6-I-1-LDP02-GB-REDIST-TO-BGP permit 10
   match ip address prefix-list SOHONET-RIPE-PREFIX
   set community 5555:12011
!
"""

COMPLEX_ARISTA_TGT = """
interface Ethernet38
interface Ethernet38.476
interface Ethernet38.1064
"""

def main():
    os.makedirs("test_configs", exist_ok=True)
    with open("test_configs/complex_arista_src.cfg", "w") as f:
        f.write(COMPLEX_ARISTA_SRC)
    with open("test_configs/complex_arista_tgt.cfg", "w") as f:
        f.write(COMPLEX_ARISTA_TGT)
        
    cmd = [
        "python3", "-m", "router_migrate.cli",
        "-s", "test_configs/complex_arista_src.cfg",
        "-t", "test_configs/complex_arista_tgt.cfg",
        "--source-vendor", "arista",
        "--target-vendor", "arista"
    ]
    
    print("Testing complex Arista config...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("STDOUT:")
    print(res.stdout)
    if res.stderr:
        print("STDERR:")
        print(res.stderr)

if __name__ == "__main__":
    main()
