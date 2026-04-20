import socket
import sys

def sqroots(coeffs: str) -> str:
    a, b, c = map(int, coeffs.split())
    
    if a == 0:
        raise ValueError("a can't be zero")

    d = b ** 2 - 4 * a * c
    
    if d < 0:
        return ""

    if d == 0:
        return f"{(d ** 0.5 - b) / 2 / a}"

    return f"{(d ** 0.5 - b) / 2 / a} {(-d ** 0.5 - b) / 2 / a}"

def sqrootnet(coeffs: str, s: socket.socket) -> str:
    s.sendall((coeffs + "\n").encode())
    return s.recv(128).decode().strip()

if __name__ == "__main__":
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 1337))
        s.sendall(sys.argv[1].encode() + b'\n')
        print(s.recv(1024).rstrip().decode())
