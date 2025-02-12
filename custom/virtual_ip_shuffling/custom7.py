"""
Custom topology with moving target defense (IP changing)

Topology:
   h1 --- s3 --- s4 --- h2

The script defines a custom topology and demonstrates dynamic IP address changes.
"""

import requests.auth
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSSwitch, RemoteController, Host
from time import sleep
import random
import threading
import requests
import json
from types import SimpleNamespace

ONOS_IP = "127.0.0.1"
ONOS_PORT = "8181"
ONOS_USER = "onos"
ONOS_PASS = "rocks"

SHUFFLE_INTERVAL = 5


class MyTopo(Topo):
    "Simple topology example."

    def build(self):
        s1 = self.addSwitch("s1", ip="0.0.0.0", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", ip="0.0.0.0", protocols="OpenFlow13")
        s3 = self.addSwitch("s3", ip="0.0.0.0", protocols="OpenFlow13")

        h1 = self.addHost("h1", ip="10.0.0.1", defaultRoute=None)
        h2 = self.addHost("h2", ip="10.0.0.2", defaultRoute=None)
        h3 = self.addHost("h3", ip="10.0.0.3", defaultRoute=None)
        h4 = self.addHost("h4", ip="10.0.0.4", defaultRoute=None)

        self.addLink(s1, s2)
        self.addLink(s2, s3)

        self.addLink(s1, h1)
        self.addLink(s1, h2)
        self.addLink(s3, h3)
        self.addLink(s3, h4)


def startCLI(net):
    CLI(net)


if __name__ == "__main__":
    # Initialize Mininet with the custom topology
    topo = MyTopo()

    remote_controller = RemoteController("c0", ip="127.0.0.1", port=6653)

    net = Mininet(topo=topo, switch=OVSSwitch, build=False, controller=None)

    net.addController(remote_controller)

    net.build()
    net.start()

    t2 = threading.Thread(target=startCLI, name="startCLI", args=[net])

    try:
        t2.start()
        h1: Host = net.get("h1")
        h1.cmd("sudo python3 dns_server.py")
        h2: Host = net.get("h2")
        h2.cmd('echo "nameserver 10.0.0.9" | sudo tee /etc/resolv.conf')
        h3: Host = net.get("h3")
        h3.cmd('echo "nameserver 10.0.0.9" | sudo tee /etc/resolv.conf')
        h4: Host = net.get("h4")
        h4.cmd('echo "nameserver 10.0.0.9" | sudo tee /etc/resolv.conf')

    except KeyboardInterrupt:
        print("Stopping the network.")
    finally:
        # CLI(net)  # Drop into CLI for further testing if needed
        t2.join()
        net.stop()
