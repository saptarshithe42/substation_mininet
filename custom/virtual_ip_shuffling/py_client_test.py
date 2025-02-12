import socket

# HOST = "127.0.0.1"
# HOST = "h2.com"
# HOST = "10.0.0.2"
HOST = "10.0.0.36"

choice = input("Enter receiver IP manually (y / n): ")

if choice == "y":
    HOST = input("Enter receiver IP : ")

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.connect((HOST, 12345))
server_socket.send(b"hi")
