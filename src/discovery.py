import socket
import json
import threading
import time

class Discovery:
    # UDP Discovery - Nodes finden sich im Netzwerk
    
    def __init__(self, node, listen_port=None):
        # node: Das Node-Objekt
        # listen_port: Optional - wenn None, finde automatisch einen freien Port
        
        self.node_id = node.id
        self.broadcast_port = 5000
        self.broadcast_ip = "255.255.255.255"
        
        # Port finden
        if listen_port:
            self.listen_port = listen_port
        else:
            self.listen_port = self._find_free_port()
        
        # Setze Port im Node
        node.port = self.listen_port
        
        # Liste der gefundenen Nodes
        self.peers = {}
        
        # Socket für Broadcast senden
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Socket für Empfangen (auf eigenem Port)
        self.recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.recv_socket.bind(("", self.listen_port))
        
        # Socket für Broadcast empfangen (Port 5000)
        self.broadcast_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Auf Mac: SO_REUSEPORT damit mehrere Processes den gleichen Port nutzen können
        try:
            self.broadcast_recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass  # Windows hat kein SO_REUSEPORT
        
        self.broadcast_recv_socket.bind(("", self.broadcast_port))
        
        self.running = False
        
        print(f"[DISCOVERY] Node {self.node_id[:8]} hört auf Port {self.listen_port}")
    
    def _find_free_port(self, start_port=5001, max_attempts=100):
        # Findet automatisch einen freien Port
        
        for port in range(start_port, start_port + max_attempts):
            try:
                test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_socket.bind(('', port))
                test_socket.close()
                
                # Kurze Pause damit Port wirklich frei wird
                time.sleep(0.1)
                
                return port
            except OSError:
                continue
        
        raise Exception("Kein freier Port gefunden!")
    
    def send_announcement(self):
        # Sendet Announcement mit eigener Port-Info
        message = {
            "type": "announcement",
            "node_id": self.node_id,
            "port": self.listen_port
        }
        
        data = json.dumps(message).encode('utf-8')
        
        # Sende an Broadcast Port
        self.broadcast_socket.sendto(data, (self.broadcast_ip, self.broadcast_port))
        
        # Sende auch direkt an bekannte Peers
        for peer_id, peer_info in self.peers.items():
            try:
                self.broadcast_socket.sendto(data, ("127.0.0.1", peer_info["port"]))
            except:
                pass
    
    def listen_for_announcements(self):
        # Hört auf Broadcast Port (5000)
        while self.running:
            try:
                data, addr = self.broadcast_recv_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                # Ignoriere eigene Nachrichten
                if message["node_id"] == self.node_id:
                    continue
                
                # Peer speichern mit Port-Info
                peer_id = message["node_id"]
                peer_port = message.get("port", self.broadcast_port)
                
                if peer_id not in self.peers:
                    print(f"[DISCOVERY] Neuer Peer: {peer_id[:8]} auf Port {peer_port}")
                
                self.peers[peer_id] = {
                    "port": peer_port,
                    "timestamp": time.time()
                }
                
            except Exception as e:
                if self.running:
                    print(f"[DISCOVERY] Fehler beim Empfangen: {e}")
    
    def start(self):
        # Startet Discovery Service
        self.running = True
        
        # Thread für Empfangen
        listen_thread = threading.Thread(target=self.listen_for_announcements)
        listen_thread.daemon = True
        listen_thread.start()
        
        # Thread für regelmäßiges Senden
        def announce_loop():
            while self.running:
                self.send_announcement()
                time.sleep(2)  # Alle 2 Sekunden
        
        announce_thread = threading.Thread(target=announce_loop)
        announce_thread.daemon = True
        announce_thread.start()
        
        print(f"[DISCOVERY] Service gestartet für Node {self.node_id[:8]}")
    
    def stop(self):
        # Stoppt Discovery Service
        self.running = False
        try:
            self.broadcast_socket.close()
            self.recv_socket.close()
            self.broadcast_recv_socket.close()
        except:
            pass
        print(f"[DISCOVERY] Service gestoppt für Node {self.node_id[:8]}")
    
    def get_peers(self):
        # Gibt Dictionary aller Peers zurück
        return self.peers.copy()