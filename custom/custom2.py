"""
Custom topology with moving target defense (IP changing)

Topology:
   h1 --- s3 --- s4 --- h2

The script defines a custom topology and demonstrates dynamic IP address changes.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSSwitch, RemoteController
from time import sleep
import random
import threading


class MyTopo(Topo):
    "Simple topology with two switches and two hosts."

    def build(self):
        # Add hosts and switches
        leftHost = self.addHost("h1", ip="10.0.0.1/24")
        rightHost = self.addHost("h2", ip="10.0.0.2/24")
        leftSwitch = self.addSwitch("s3", protocols="OpenFlow13")
        rightSwitch = self.addSwitch("s4", protocols="OpenFlow13")

        # Add links
        self.addLink(leftHost, leftSwitch)
        self.addLink(leftSwitch, rightSwitch)
        self.addLink(rightSwitch, rightHost)


def randomIPGenerator():
    num = random.randint(0, 255)
    ip = f"10.0.0.{num}"
    return ip


def shuffleIP(net):
    try:
        while True:
            sleep(3)
            h1 = net.get("h1")
            h2 = net.get("h2")

            ip1 = randomIPGenerator()
            ip2 = randomIPGenerator()

            while ip1 == ip2:
                ip2 = randomIPGenerator()

            h1.cmd("ip neigh flush dev h1-eth0")
            h2.cmd("ip neigh flush dev h2-eth0")

            h1.setIP(ip1)
            h2.setIP(ip2)

            # h1.cmd(f"arping -c 1 -I h1-eth0 {ip1}")
            # h2.cmd(f"arping -c 1 -I h2-eth0 {ip2}")
        # pass
    except:
        print("shuffleIP thread terminated")

    # print("set IP")


def startCLI(net):
    CLI(net)


if __name__ == "__main__":
    # Initialize Mininet with the custom topology
    topo = MyTopo()

    onos_controller = RemoteController("c0", ip="127.0.0.1", port=6653)

    net = Mininet(topo=topo, switch=OVSSwitch, build=False, controller=None)

    net.addController(onos_controller)

    net.build()
    net.start()

    t1 = threading.Thread(target=shuffleIP, name="shuffleIP", args=[net])
    t2 = threading.Thread(target=startCLI, name="startCLI", args=[net])

    try:
        t1.start()
        t2.start()

    except KeyboardInterrupt:
        print("Stopping the network.")
    finally:
        # CLI(net)  # Drop into CLI for further testing if needed
        t1.join()
        t2.join()
        net.stop()
