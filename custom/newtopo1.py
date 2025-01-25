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
        r1 = self.addSwitch("r1", ip="0.0.0.0")
        r2 = self.addSwitch("r2", ip="0.0.0.0")
        h1 = self.addHost("h1", ip="10.0.0.1", defaultRoute=None)
        h2 = self.addHost("h2", ip="10.0.0.2", defaultRoute=None)
        h3 = self.addHost("h3", ip="10.0.0.3", defaultRoute=None)
        h4 = self.addHost("h4", ip="10.0.0.4", defaultRoute=None)
        self.addLink(h1, r1)
        self.addLink(r1, h2)
        self.addLink(r1, r2)
        self.addLink(r2, h3)
        self.addLink(r2, h4)


topos = {"mytopo": (lambda: MyTopo())}
