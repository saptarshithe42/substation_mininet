"""Custom topology example

Two directly connected switches plus a host for each switch:

   host --- switch --- switch --- host

Adding the 'topos' dict with a key/value pair to generate our newly defined
topology enables one to pass in '--topo=mytopo' from the command line.
"""

from mininet.topo import Topo


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


topos = {"mytopo": (lambda: MyTopo())}
