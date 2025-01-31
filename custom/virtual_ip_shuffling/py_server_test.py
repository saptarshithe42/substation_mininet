import socket


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(("", 12345))

server_socket.listen(1)


try:
    while True:
        print("Waiting for client")
        conn, addr = server_socket.accept()
        data = conn.recv(1024)
        print(data)
        print()

except KeyboardInterrupt:
    print("Stopped by Ctrl+C")
finally:
    server_socket.close()
