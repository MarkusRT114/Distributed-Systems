import socket
import json
import threading
import time

class Election:
    # Chang-Roberts Election Algorithm über TCP
    
    def __init__(self, node, ring):
        self.node = node
        self.ring = ring
        self.election_socket = None
        self.election_in_progress = False
        self.running = False
        
        self.ring.set_election(self)
        
        self.election_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.election_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.election_socket.bind(("", self.node.port + 1000))
        self.election_socket.listen(5)
        
        print(f"[ELECTION] TCP auf Port {self.node.port + 1000}")
    
    def start(self):
        self.running = True
        threading.Thread(target=self._listen, daemon=True).start()
    
    def stop(self):
        self.running = False
        if self.election_socket:
            try:
                self.election_socket.close()
            except:
                pass
    
    def start_election(self):
        if self.election_in_progress:
            return
        
        self.election_in_progress = True
        self.node.is_leader = False
        self.node.current_leader_id = None
        
        print(f"[ELECTION] Node {self.node.id[:8]} startet Election")
        self._send_election(self.node.id)
    
    def _send_election(self, candidate_id):
        neighbor = self.ring.get_right_neighbor()
        if not neighbor:
            self.node.is_leader = True
            self.node.current_leader_id = self.node.id
            self.election_in_progress = False
            print(f"[ELECTION] Node {self.node.id[:8]} ist alleine - wird Leader")
            return
        
        msg = json.dumps({"type": "election", "candidate_id": candidate_id})
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            target_ip = neighbor.get("ip", "127.0.0.1")
            sock.connect((target_ip, neighbor["port"] + 1000))
            sock.sendall(msg.encode())
            sock.close()
        except Exception as e:
            print(f"[ELECTION] Fehler: {e}")
            self.election_in_progress = False
    
    def _send_leader(self, leader_id):
        neighbor = self.ring.get_right_neighbor()
        if not neighbor:
            return
        
        msg = json.dumps({"type": "leader", "leader_id": leader_id})
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            target_ip = neighbor.get("ip", "127.0.0.1")
            sock.connect((target_ip, neighbor["port"] + 1000))
            sock.sendall(msg.encode())
            sock.close()
        except Exception as e:
            print(f"[ELECTION] Fehler: {e}")
    
    def _listen(self):
        while self.running:
            try:
                conn, _ = self.election_socket.accept()
                data = conn.recv(1024)
                msg = json.loads(data.decode())
                conn.close()
                
                if msg["type"] == "election":
                    candidate_id = msg["candidate_id"]
                    
                    if candidate_id > self.node.id:
                        self._send_election(candidate_id)
                    elif candidate_id < self.node.id:
                        if not self.election_in_progress:
                            self.start_election()
                    else:
                        self.node.is_leader = True
                        self.node.current_leader_id = self.node.id
                        self.election_in_progress = False
                        print(f"[ELECTION] Node {self.node.id[:8]} ist LEADER")
                        
                        # Sende State-Sync wenn ich Leader werde
                        def delayed_sync():
                            time.sleep(2)
                            if hasattr(self.node, 'shopping_list') and hasattr(self.node, 'coord_socket'):
                                items = self.node.shopping_list.get_items()
                                if items:
                                    print(f"[ELECTION] Neuer Leader sendet State-Sync ({len(items)} Items)")
                                    for item in items:
                                        try:
                                            self.node._broadcast_update("sync", item)
                                        except Exception as e:
                                            print(f"[ELECTION] Sync-Fehler: {e}")
                        
                        threading.Thread(target=delayed_sync, daemon=True).start()
                        self._send_leader(self.node.id)
                
                elif msg["type"] == "leader":
                    leader_id = msg["leader_id"]
                    self.node.current_leader_id = leader_id
                    
                    if leader_id == self.node.id:
                        if not self.node.is_leader:
                            self.node.is_leader = True
                            print(f"[ELECTION] Node {self.node.id[:8]} ist LEADER")
                            
                            # Sende State-Sync wenn ich Leader werde
                            def delayed_sync():
                                time.sleep(2)
                                if hasattr(self.node, 'shopping_list') and hasattr(self.node, 'coord_socket'):
                                    items = self.node.shopping_list.get_items()
                                    if items:
                                        print(f"[ELECTION] Neuer Leader sendet State-Sync ({len(items)} Items)")
                                        for item in items:
                                            try:
                                                self.node._broadcast_update("sync", item)
                                            except Exception as e:
                                                print(f"[ELECTION] Sync-Fehler: {e}")
                            
                            threading.Thread(target=delayed_sync, daemon=True).start()
                    else:
                        self.node.is_leader = False
                        self.election_in_progress = False
                        print(f"[ELECTION] Node {leader_id[:8]} ist Leader")
                        
                        if leader_id != self.node.id:
                            self._send_leader(leader_id)
            
            except Exception as e:
                if self.running:
                    pass