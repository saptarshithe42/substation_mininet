from scapy.all import send, IP, UDP

src_ip = "10.0.0.1"
# dst_ip = "10.0.0.2"
dst_ip = "191.168.0.103"
src_port = 57466
dst_port = 12345

# seq = 748204115
# ack = 1318239129
# flag = "R"

ip = IP(src=src_ip, dst=dst_ip)
udp = UDP(sport=src_port, dport=dst_port)
# tcp = TCP(sport=src_port, dport=dst_port, seq=seq, ack=ack, flags=flag)
pkt = ip / udp

# while True:
#     pkt[TCP].ack += 173
#     send(pkt)

send(pkt)
