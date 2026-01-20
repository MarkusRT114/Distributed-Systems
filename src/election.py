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
    
    def _start_list_check(self):
        """Startet List-Check im Ring - längste Liste gewinnt"""
        time.sleep(2)
        
        my_items = self.node.shopping_list.get_items()
        
        msg = {
            "type": "list_check",
            "items": my_items,
            "count": len(my_items),
            "originator": self.node.id
        }
        
        print(f"[LIST-CHECK] Leader startet List-Check (eigene Liste: {len(my_items)} Items)")
        self._send_list_check(msg)
    
    def _send_list_check(self, msg):
        """Sendet List-Check Message an rechten Nachbarn"""
        neighbor = self.ring.get_right_neighbor()
        if not neighbor:
            # Kein Nachbar - übernehme eigene Liste und sende Update
            self._broadcast_list_update(msg["items"])
            return
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            target_ip = neighbor.get("ip", "127.0.0.1")
            sock.connect((target_ip, neighbor["port"] + 1000))
            sock.sendall(json.dumps(msg).encode())
            sock.close()
        except Exception as e:
            print(f"[LIST-CHECK] Fehler: {e}")
    
    def _broadcast_list_update(self, items):
        """Sendet finale Liste an alle Nodes (Phase 2)"""
        time.sleep(1)
        print(f"[LIST-CHECK] Längste Liste gefunden: {len(items)} Items")
        
        # Eigene Liste übernehmen
        self.node.shopping_list.items = items.copy()
        
        # An alle senden
        if hasattr(self.node, 'coord_socket') and self.node.coord_socket:
            for item in items:
                try:
                    self.node._broadcast_update("sync", item)
                except Exception as e:
                    print(f"[LIST-CHECK] Sync-Fehler: {e}")
    
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
                        
                        # Starte List-Check
                        threading.Thread(target=self._start_list_check, daemon=True).start()
                        self._send_leader(self.node.id)
                
                elif msg["type"] == "leader":
                    leader_id = msg["leader_id"]
                    self.node.current_leader_id = leader_id
                    
                    if leader_id == self.node.id:
                        if not self.node.is_leader:
                            self.node.is_leader = True
                            print(f"[ELECTION] Node {self.node.id[:8]} ist LEADER")
                            
                            # Starte List-Check
                            threading.Thread(target=self._start_list_check, daemon=True).start()
                    else:
                        self.node.is_leader = False
                        self.election_in_progress = False
                        print(f"[ELECTION] Node {leader_id[:8]} ist Leader")
                        
                        if leader_id != self.node.id:
                            self._send_leader(leader_id)
                
                elif msg["type"] == "list_check":
                    originator = msg["originator"]
                    
                    # Kommt zu mir (Originator) zurück?
                    if originator == self.node.id:
                        # List-Check abgeschlossen - längste Liste gefunden
                        winning_items = msg["items"]
                        print(f"[LIST-CHECK] Check abgeschlossen - längste Liste: {len(winning_items)} Items")
                        self._broadcast_list_update(winning_items)
                    else:
                        # Vergleichen
                        my_items = self.node.shopping_list.get_items()
                        my_count = len(my_items)
                        incoming_count = msg["count"]
                        
                        if incoming_count >= my_count:
                            # Eingehende Liste ist länger/gleich - weiterleiten
                            print(f"[LIST-CHECK] Eingehende Liste länger ({incoming_count} >= {my_count}) - weiterleiten")
                            self._send_list_check(msg)
                        else:
                            # Meine Liste ist länger - ersetzen und weiterleiten
                            print(f"[LIST-CHECK] Meine Liste länger ({my_count} > {incoming_count}) - eigene senden")
                            new_msg = {
                                "type": "list_check",
                                "items": my_items,
                                "count": my_count,
                                "originator": originator
                            }
                            self._send_list_check(new_msg)
            
            except Exception as e:
                if self.running:
                    pass