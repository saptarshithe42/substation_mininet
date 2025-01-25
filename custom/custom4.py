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
    "Simple topology with two switches and two hosts."

    def build(self):
        s1 = self.addSwitch("r1", ip="0.0.0.0", protocols="OpenFlow13")
        s2 = self.addSwitch("r2", ip="0.0.0.0", protocols="OpenFlow13")
        h1 = self.addHost("h1", ip="10.0.0.1", defaultRoute=None)
        h2 = self.addHost("h2", ip="10.0.0.2", defaultRoute=None)
        h3 = self.addHost("h3", ip="10.0.0.3", defaultRoute=None)
        h4 = self.addHost("h4", ip="10.0.0.4", defaultRoute=None)
        self.addLink(h1, s1)
        self.addLink(s1, h2)
        self.addLink(s1, s2)
        self.addLink(s2, h3)
        self.addLink(s2, h4)


def randomIPGenerator():
    num = random.randint(1, 254)
    ip = f"10.0.0.{num}"
    return ip


def fetchHostIDs():
    try:
        url = f"http://{ONOS_IP}:{ONOS_PORT}/onos/v1/hosts"
        auth = (ONOS_USER, ONOS_PASS)
        response = requests.get(url, auth=auth)

        # print(response.content.decode())

        response = response.content.decode()

        response = json.loads(response)

        hosts = response["hosts"]

        # print(hosts)

        hostIDs = []

        for host in hosts:
            hostIDs.append(host["id"])

        # print(hostIDs)

        return hostIDs

    except Exception as e:
        print(e)


def deleteHostEntryFromOnos(hostID):
    url = f"http://{ONOS_IP}:{ONOS_PORT}/onos/v1/hosts/{hostID}"
    auth = (ONOS_USER, ONOS_PASS)
    response = requests.delete(url, auth=auth)
    print(response.status_code)


def shuffleIP(net: Mininet):
    try:
        while True:
            sleep(SHUFFLE_INTERVAL)
            net.pingAll()

            n: int = len(net.hosts)
            print(n)

            # print(net.hosts)

            hostIDs = fetchHostIDs()

            newIPs = []

            while len(newIPs) < n:
                ip = randomIPGenerator()

                while ip in newIPs:
                    ip = randomIPGenerator()

                newIPs.append(ip)

            for i in range(n):
                host: Host = net.get(f"h{i+1}")
                host.setIP(newIPs[i])
                deleteHostEntryFromOnos(hostIDs[i])

            print("IPs shuffled")
            net.pingAll()

        # pass
    except Exception as e:
        print(e)
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
