import socket

def evaluate_my_ip():
    ips = []
    for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
        if not ip.startswith("127."):
            ips.append(ip)
    for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]:
        s.connect(("8.8.8.8", 53))
        ips.append(s.getsockname()[0])
        s.close()
    print(*ips)


if __name__ == "__main__":
    evaluate_my_ip()

