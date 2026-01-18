import socket
import json
import threading
import time

class Discovery:
    # UDP Discovery - Nodes finden sich im Netzwerk
    
    def __init__(self, node, listen_port=None):
        self.node_id = node.id
        self.broadcast_port = 5000
        self.broadcast_ip = "255.255.255.255"
        
        if listen_port:
            self.listen_port = listen_port
        else:
            self.listen_port = self._find_free_port()
        
        node.port = self.listen_port
        self.peers = {}
        self.on_peer_removed = None
        
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_socket.bind(("", self.listen_port))
        
        self.broadcast_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.broadcast_recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
        
        self.broadcast_recv_socket.bind(("", self.broadcast_port))
        self.running = False
        
        print(f"[DISCOVERY] Node {self.node_id[:8]} auf Port {self.listen_port}")
    
    def _find_free_port(self, start_port=5001, max_attempts=100):
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind(('', port))
                test_socket.close()
                time.sleep(0.1)
                return port
            except OSError:
                continue
        raise Exception("Kein freier Port gefunden!")
    
    def cleanup_peers(self):
        current_time = time.time()
        inactive_peers = []
        
        for peer_id, peer_info in self.peers.items():
            if current_time - peer_info["timestamp"] > 10:
                inactive_peers.append(peer_id)
        
        for peer_id in inactive_peers:
            print(f"[DISCOVERY] Peer {peer_id[:8]} timeout - entfernt")
            del self.peers[peer_id]
        
        if inactive_peers and self.on_peer_removed:
            self.on_peer_removed(inactive_peers)
        
        return len(inactive_peers) > 0
    
    def send_announcement(self):
        message = {
            "type": "announcement",
            "node_id": self.node_id,
            "port": self.listen_port
        }
        
        data = json.dumps(message).encode('utf-8')
        self.broadcast_socket.sendto(data, (self.broadcast_ip, self.broadcast_port))
        
        for peer_id, peer_info in list(self.peers.items()):
            try:
                self.broadcast_socket.sendto(data, (peer_info["ip"], peer_info["port"]))
            except:
                pass
    
    def listen_for_announcements(self):
        while self.running:
            try:
                data, addr = self.broadcast_recv_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                if message["node_id"] == self.node_id:
                    continue
                
                peer_id = message["node_id"]
                peer_port = message.get("port", self.broadcast_port)
                peer_ip = addr[0]
                
                if peer_id not in self.peers:
                    print(f"[DISCOVERY] Neuer Peer: {peer_id[:8]} auf {peer_ip}:{peer_port}")
                
                self.peers[peer_id] = {
                    "port": peer_port,
                    "ip": peer_ip,
                    "timestamp": time.time()
                }
                
            except Exception as e:
                if self.running:
                    print(f"[DISCOVERY] Fehler: {e}")
    
    def start(self):
        self.running = True
        
        listen_thread = threading.Thread(target=self.listen_for_announcements)
        listen_thread.daemon = True
        listen_thread.start()
        
        def announce_loop():
            while self.running:
                self.send_announcement()
                self.cleanup_peers()
                time.sleep(2)
        
        announce_thread = threading.Thread(target=announce_loop)
        announce_thread.daemon = True
        announce_thread.start()
        
        print(f"[DISCOVERY] Service gestartet")
    
    def stop(self):
        self.running = False
        try:
            self.broadcast_socket.close()
            self.recv_socket.close()
            self.broadcast_recv_socket.close()
        except:
            pass
        print(f"[DISCOVERY] Service gestoppt")
    
    def get_peers(self):
        return self.peers.copy()