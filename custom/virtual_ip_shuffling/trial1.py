import binascii
import struct

from dnslib import DNSRecord, RR, QTYPE, DNSHeader, A
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, udp
from ryu.lib import hub
import socket

from ip_mapping import IPMapping
from ip_shuffler import IPShuffler
import dnslib


class DNSRedirect(app_manager.RyuApp):
    """Ryu App to intercept DNS responses (UDP src_port=53) and send them to the controller while forwarding normal traffic"""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DNSRedirect, self).__init__(*args, **kwargs)
        self.ip_map = IPMapping()
        self.ip_shuffler = IPShuffler(self.ip_map)
        hub.spawn(self.ip_shuffler.shuffle_ip_by_priority, base_interval=30)
        # hub.spawn(self.ip_shuffler.shuffle_all_ip, shuffle_interval=5)
        # hub.spawn(self.ip_shuffler.shuffle_all_ip2)
        hub.spawn(self.ip_map.print_mapping, self.ip_map)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """Install default forwarding rules and send DNS responses to the controller"""
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # 1️⃣ Default rule: Forward all packets normally
        match_default = parser.OFPMatch()
        actions_default = [parser.OFPActionOutput(ofproto.OFPP_NORMAL)]
        instructions_default = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions_default)
        ]
        flow_mod_default = parser.OFPFlowMod(
            datapath=datapath,
            priority=100,
            match=match_default,
            instructions=instructions_default,
        )
        datapath.send_msg(flow_mod_default)
        self.logger.info("✅ Installed default forwarding rule (priority=100)")

        # 2️⃣ DNS rule: Send DNS responses (src_port=53) to the controller
        match_dns = parser.OFPMatch(
            eth_type=0x0800,  # IPv4
            ip_proto=17,  # UDP
            udp_src=53,  # Source port 53 (DNS response)
            ipv4_src="10.0.0.3",
            ip_dscp=0,
        )
        actions_dns = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        instructions_dns = [
            parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions_dns)
        ]
        flow_mod_dns = parser.OFPFlowMod(
            datapath=datapath,
            priority=200,
            match=match_dns,
            instructions=instructions_dns,
        )
        datapath.send_msg(flow_mod_dns)
        self.logger.info("✅ Installed DNS interception rule (priority=200)")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Handle intercepted DNS response packets"""
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info(msg.data)
        self.logger.info("==================")

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        ip = pkt.get_protocol(ipv4.ipv4)
        udp_pkt = pkt.get_protocol(udp.udp)


        if udp_pkt and udp_pkt.src_port == 53:  # Only process DNS responses
            # self.logger.info(f"🔥 Intercepted DNS Response: {ip.src} → {ip.dst}")
            # self.logger.info(f"📡 Raw Packet Data: {msg.data.hex()}")
            self.logger.info(f"Intercepted DNS Response: {ip.src} → {ip.dst}")
            self.logger.info("==================")
            self.logger.info(f"Raw Packet Data: {msg.data.hex()}")
            self.logger.info("==================")
            self.logger.info(msg.data)
            self.logger.info("==================")

            self.logger.info(pkt)
            self.logger.info("==================")

            self.logger.info(pkt.protocols[-1])
            dns_payload = pkt.protocols[-1]
            self.logger.info(dns_payload.hex())
            self.logger.info("==================")
            self.logger.info(binascii.unhexlify(dns_payload.hex()))
            self.logger.info("==================")
            dns_packet: DNSRecord = dnslib.DNSRecord.parse(dns_payload)
            self.logger.info(dns_packet)
            self.logger.info("==================")
            self.logger.info(dns_packet.questions)
            self.logger.info("==================")
            self.logger.info(dns_packet.questions[0])
            self.logger.info("==================")
            self.logger.info(dns_packet.a)
            self.logger.info("==================")
            rr: RR = dns_packet.a
            self.logger.info(str(rr.rdata))
            self.logger.info("==================")
            self.logger.info(rr.rname)
            self.logger.info("==================")

            virtual_ip = self.ip_map.get_virtual_ip(str(rr.rdata))
            self.logger.info(virtual_ip)

            dns_reply = DNSRecord(
                DNSHeader(id=dns_packet.header.id, qr=1, aa=1, ra=1), q=dns_packet.q
            )

            qname = str(dns_packet.q.qname)
            qtype = QTYPE[dns_packet.q.qtype]

            dns_reply.add_answer(RR(qname, QTYPE.A, rdata=A(virtual_ip)))

            self.logger.info("================== Constructed DNS Reply ==================")
            self.logger.info(dns_reply)
            self.logger.info("==================")
            self.logger.info(dns_reply.pack())
            self.logger.info("==================")

            #######################

            eth_reply = ethernet.ethernet(
                dst=eth.dst,
                src=eth.src,
                ethertype=eth.ethertype
            )

            # IP Header
            ip_reply = ipv4.ipv4(
                dst=ip.dst,
                src=ip.src,
                proto=ip.proto,
                ttl=64,
                tos=(10 << 2)  # DSCP = 10 (left shift by 2 bits to align)
            )

            # UDP Header
            udp_reply = udp.udp(
                dst_port=udp_pkt.dst_port,  # Swap src/dst ports
                src_port=udp_pkt.src_port,
                total_length=8 + len(dns_reply.pack())
            )

            # Construct new packet
            pkt = packet.Packet()
            pkt.add_protocol(eth_reply)
            pkt.add_protocol(ip_reply)
            pkt.add_protocol(udp_reply)
            pkt.add_protocol(dns_reply.pack())
            pkt.serialize()

            in_port = msg.match["in_port"]  # Get input port (to send the response back)

            # Build PacketOut message

            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=msg.match['in_port'],
                actions=actions,
                data=pkt.data
            )
            datapath.send_msg(out)

