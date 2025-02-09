import socket

HOST = "h2.com"
PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Manually resolve the IP
real_ip = socket.gethostbyname(HOST)
print(f"Resolved {HOST} to {real_ip}")

# Send data
client_socket.sendto(b"hi", (real_ip, PORT))
