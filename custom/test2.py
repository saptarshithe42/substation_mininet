"""
Custom topology with moving target defense (IP changing)

Topology:
   h1 --- s3 --- s4 --- h2

The script defines a custom topology and demonstrates dynamic IP address changes.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import OVSSwitch
from time import sleep


class MyTopo(Topo):
    "Simple topology with two switches and two hosts."

    def build(self):
        # Add hosts and switches
        leftHost = self.addHost("h1", ip="10.0.0.1/24")
        rightHost = self.addHost("h2", ip="10.0.0.2/24")
        leftSwitch = self.addSwitch("s3")
        rightSwitch = self.addSwitch("s4")

        # Add links
        self.addLink(leftHost, leftSwitch)
        self.addLink(leftSwitch, rightSwitch)
        self.addLink(rightSwitch, rightHost)


if __name__ == "__main__":
    # Initialize Mininet with the custom topology
    topo = MyTopo()
    net = Mininet(topo=topo, switch=OVSSwitch, build=False)
    net.build()
    net.start()

    try:
        # Get the host instances
        h1 = net.get("h1")
        h2 = net.get("h2")

        # Dynamic IP change demonstration
        print("Starting Moving Target Defense (IP change)...")
        for i in range(3):
            new_ip_h1 = f"10.0.0.{i+3}/24"
            print(f"[Iteration {i+1}] Changing h1 IP to {new_ip_h1}")
            h1.setIP(new_ip_h1)

            # Check connectivity after each IP change
            print("Testing connectivity...")
            result = h1.cmd(f"ping -c 1 {h2.IP()}")
            print(result)

            sleep(5)  # Wait before the next IP change

    except KeyboardInterrupt:
        print("Stopping the network.")
    finally:
        CLI(net)  # Drop into CLI for further testing if needed
        net.stop()
