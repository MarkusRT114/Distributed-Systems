import socket
import json
import threading

class Election:
    # Chang-Roberts Leader Election mit TCP
    
    def __init__(self, node, ring):
        self.node = node
        self.ring = ring
        
        # TCP Socket für Election (zuverlässig)
        self.election_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.election_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.election_port = self.node.port + 1000
        self.election_socket.bind(("", self.election_port))
        self.election_socket.listen(5)
        
        self.running = False
        self.election_in_progress = False
        
        print(f"[ELECTION] TCP auf Port {self.election_port}")
    
    def start(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()
    
    def stop(self):
        self.running = False
        try:
            self.election_socket.close()
        except:
            pass
    
    def start_election(self):
        if self.election_in_progress:
            return
        
        self.election_in_progress = True
        print(f"[ELECTION] Node {self.node.id[:8]} startet Election")
        self._send_election(self.node.id)
    
    def _send_election(self, candidate_id):
        neighbor = self.ring.get_right_neighbor()
        if not neighbor:
            self.node.is_leader = True
            self.node.current_leader_id = self.node.id
            self.election_in_progress = False
            return
        
        msg = json.dumps({"type": "election", "candidate_id": candidate_id})
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("127.0.0.1", neighbor["port"] + 1000))
            sock.sendall(msg.encode())
            sock.close()
        except Exception as e:
            print(f"[ELECTION] Fehler: {e}")
    
    def _send_leader(self):
        neighbor = self.ring.get_right_neighbor()
        if not neighbor:
            return
        
        msg = json.dumps({"type": "leader", "leader_id": self.node.id})
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(("127.0.0.1", neighbor["port"] + 1000))
            sock.sendall(msg.encode())
            sock.close()
        except:
            pass
    
    def _listen(self):
        while self.running:
            try:
                conn, _ = self.election_socket.accept()
                conn.settimeout(2)
                data = conn.recv(1024)
                conn.close()
                
                if not data:
                    continue
                
                msg = json.loads(data.decode())
                
                if msg["type"] == "election":
                    candidate_id = msg["candidate_id"]
                    
                    if candidate_id == self.node.id:
                        print(f"[ELECTION] Node {self.node.id[:8]} ist LEADER")
                        self.node.is_leader = True
                        self.node.current_leader_id = self.node.id
                        self.election_in_progress = False
                        self._send_leader()
                    
                    elif candidate_id > self.node.id:
                        self._send_election(candidate_id)
                    
                    else:
                        if not self.election_in_progress:
                            self.election_in_progress = True
                            self._send_election(self.node.id)
                
                elif msg["type"] == "leader":
                    leader_id = msg["leader_id"]
                    self.node.current_leader_id = leader_id
                    
                    if leader_id != self.node.id:
                        print(f"[ELECTION] Node {leader_id[:8]} ist Leader")
                        self.node.is_leader = False
                        self.election_in_progress = False
                        
                        # Weiterleiten
                        neighbor = self.ring.get_right_neighbor()
                        if neighbor:
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(2)
                                sock.connect(("127.0.0.1", neighbor["port"] + 1000))
                                sock.sendall(data)
                                sock.close()
                            except:
                                pass
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    pass