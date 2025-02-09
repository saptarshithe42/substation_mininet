import struct

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


class DNSRedirect(app_manager.RyuApp):
    """Ryu App to intercept DNS responses (UDP src_port=53) and send them to the controller while forwarding normal
    traffic"""

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(DNSRedirect, self).__init__(*args, **kwargs)
        self.ip_map = IPMapping()
        self.ip_shuffler = IPShuffler(self.ip_map)
        hub.spawn(self.ip_shuffler.shuffle_ip_by_priority, base_interval=3600)
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

        for virtual_ip in self.ip_map.all_virtual_ips:
            match_virtual = parser.OFPMatch(
                eth_type=0x0800,  # IPv4
                ipv4_dst=virtual_ip  # Traffic destined for virtual IP
            )
            actions_virtual = [
                parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
            ]
            instructions_virtual = [
                parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions_virtual)
            ]
            flow_mod_virtual = parser.OFPFlowMod(
                datapath=datapath,
                priority=250,  # Higher priority for virtual IP handling
                match=match_virtual,
                instructions=instructions_virtual,
            )
            datapath.send_msg(flow_mod_virtual)

        self.logger.info("✅ Installed rule to intercept packets to virtual IPs (priority=250)")

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

        self.logger.info(pkt)
        self.logger.info("==================")

        if udp_pkt and udp_pkt.src_port == 53:  # Only process DNS responses
            # self.logger.info(f"🔥 Intercepted DNS Response: {ip.src} → {ip.dst}")
            # self.logger.info(f"📡 Raw Packet Data: {msg.data.hex()}")
            self.logger.info(f"Intercepted DNS Response: {ip.src} → {ip.dst}")
            self.logger.info("==================")
            self.logger.info(f"Raw Packet Data: {msg.data.hex()}")
            self.logger.info("==================")
            self.logger.info(msg.data)
            self.logger.info("==================")

            in_port = msg.match["in_port"]  # Get input port (to send the response back)

            modified_packet = self.modify_dns_packet(msg.data)

            # Build PacketOut message

            actions = [parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=msg.match['in_port'],
                actions=actions,
                data=packet.Packet(modified_packet).data,
            )
            datapath.send_msg(out)

        elif ip and ip.dst in self.ip_map.virtual_to_real_ip_map:
            real_ip = self.ip_map.get_real_ip(ip.dst)
            self.logger.info(f"Virtual IP : {ip.dst} <--> Real IP : {real_ip}")

    def modify_dns_packet(self, pkt_data):
        # DNS response starts after UDP header
        dns_start = 42  # Ethernet (14) + IP (20) + UDP (8)

        try:
            # Extract DNS header
            transaction_id = pkt_data[dns_start:dns_start + 2]
            flags = pkt_data[dns_start + 2:dns_start + 4]
            questions = struct.unpack('!H', pkt_data[dns_start + 4:dns_start + 6])[0]
            answers = struct.unpack('!H', pkt_data[dns_start + 6:dns_start + 8])[0]

            # Check if it's a DNS response
            if int.from_bytes(flags, 'big') & 0x8000 == 0:
                return None

            # Pointer to first query
            query_ptr = dns_start + 12

            # Skip queries
            for _ in range(questions):
                while pkt_data[query_ptr] != 0:
                    query_ptr += pkt_data[query_ptr] + 1
                query_ptr += 5  # Skip null terminator and query type/class

            # Modify answers
            modified_pkt = bytearray(pkt_data)
            for _ in range(answers):
                # Name (could be pointer)
                if pkt_data[query_ptr] & 0xC0 == 0xC0:
                    query_ptr += 2
                else:
                    while pkt_data[query_ptr] != 0:
                        query_ptr += pkt_data[query_ptr] + 1
                    query_ptr += 1

                # Type and Class
                record_type = struct.unpack('!H', pkt_data[query_ptr:query_ptr + 2])[0]
                query_ptr += 4

                # TTL
                ttl = struct.unpack('!I', pkt_data[query_ptr:query_ptr + 4])[0]
                query_ptr += 4

                # Data Length
                data_len = struct.unpack('!H', pkt_data[query_ptr:query_ptr + 2])[0]
                query_ptr += 2

                # IP Address (A record)
                if record_type == 1:  # A record
                    ip = socket.inet_ntoa(pkt_data[query_ptr:query_ptr + 4])
                    self.logger.info(f"original ip answer : {ip}")
                    self.logger.info("==================")

                    virtual_ip = self.ip_map.get_virtual_ip(ip)

                    # Replace IP
                    new_ip = socket.inet_aton(virtual_ip)
                    modified_pkt[query_ptr:query_ptr + 4] = new_ip

                query_ptr += data_len

            # Modify source IP in the IP header (bytes 26-30)
            # new_src_ip = socket.inet_aton("10.0.0.3")  # New source IP
            # modified_pkt[26:30] = new_src_ip

            modified_pkt[15] = (modified_pkt[15] & 0x03) | (10 << 2)  # Set DSCP = 10

            modified_pkt = self.recalculate_checksums(modified_pkt)

            # self.logger.info(modified_pkt)
            self.logger.info(bytes(modified_pkt))
            self.logger.info("==================")

            return bytes(modified_pkt)
        except Exception as e:
            self.logger.error(f"DNS packet modification error: {e}")
            return None

    def recalculate_checksums(self, pkt):
        """Recalculate IP and UDP checksums after modification"""

        # 1️⃣ Fix IP Checksum
        pkt[24:26] = b'\x00\x00'  # Reset IP checksum field
        ip_header = pkt[14:34]  # Extract IP header (20 bytes)
        ip_checksum = self.calculate_checksum(ip_header)
        pkt[24:26] = struct.pack("!H", ip_checksum)

        # 2️⃣ Fix UDP Checksum
        pkt[40:42] = b'\x00\x00'  # Reset UDP checksum field
        udp_length = struct.unpack("!H", pkt[38:40])[0]
        pseudo_header = pkt[26:30] + pkt[30:34] + struct.pack("!BBH", 0, 17, udp_length)
        udp_checksum = self.calculate_checksum(pseudo_header + pkt[34:34 + udp_length])

        if udp_checksum == 0:
            udp_checksum = 0xFFFF  # UDP checksum can't be zero
        pkt[40:42] = struct.pack("!H", udp_checksum)

        return pkt

    def calculate_checksum(self, data):
        """Calculate checksum for IP or UDP headers"""
        if len(data) % 2 == 1:
            data += b'\x00'  # Pad if odd length

        checksum = sum(struct.unpack("!%dH" % (len(data) // 2), data))
        checksum = (checksum >> 16) + (checksum & 0xFFFF)  # Add carry
        checksum = ~checksum & 0xFFFF  # One's complement
        return checksum
