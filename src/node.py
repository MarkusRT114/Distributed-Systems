import uuid
import socket
import json
import threading
from shopping_list import ShoppingList

class Node:
    # Ein Node im Shopping-List-Netzwerk
    
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.port = None
        self.shopping_list = ShoppingList()
        self.is_leader = False
        self.current_leader_id = None
        self.sequence_number = 0
        self.election = None
        self.coord_socket = None
        self.coord_running = False
        
        print(f"[NODE] Erstellt: {self.id[:8]}")
    
    def set_coordinator(self, election):
        self.election = election
        
        self.coord_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.coord_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.coord_socket.bind(("", self.port + 2000))
        
        print(f"[COORD] Node {self.id[:8]} bereit")
    
    def start_coordinator(self):
        self.coord_running = True
        threading.Thread(target=self._coord_listen, daemon=True).start()
    
    def stop_coordinator(self):
        self.coord_running = False
        if self.coord_socket:
            self.coord_socket.close()
    
    def send_to_leader(self, action, item):
        if self.is_leader:
            if action == "add":
                self.shopping_list.add_item(item)
            elif action == "remove":
                self.shopping_list.remove_item(item)
            self._broadcast_update(action, item)
            return
        
        if not self.current_leader_id:
            print(f"[COORD] Kein Leader bekannt!")
            return
        
        peers = self.election.ring.discovery.get_peers()
        
        if self.current_leader_id == self.id:
            leader_port = self.port
        else:
            peer_info = peers.get(self.current_leader_id)
            if not peer_info:
                print(f"[COORD] Leader nicht gefunden!")
                return
            leader_port = peer_info["port"]
        
        msg = json.dumps({"type": "req", "action": action, "item": item})
        try:
            self.coord_socket.sendto(msg.encode(), ("127.0.0.1", leader_port + 2000))
        except Exception as e:
            print(f"[COORD] Fehler: {e}")
    
    def _broadcast_update(self, action, item):
        self.sequence_number += 1
        
        msg = json.dumps({
            "type": "upd",
            "action": action,
            "item": item,
            "seq": self.sequence_number
        })
        
        peers = self.election.ring.discovery.get_peers()
        
        for peer_id, peer_info in peers.items():
            try:
                self.coord_socket.sendto(msg.encode(), ("127.0.0.1", peer_info["port"] + 2000))
            except:
                pass
    
    def _coord_listen(self):
        while self.coord_running:
            try:
                data, _ = self.coord_socket.recvfrom(1024)
                msg = json.loads(data.decode())
                
                if msg["type"] == "req" and self.is_leader:
                    action, item = msg["action"], msg["item"]
                    
                    if action == "add":
                        self.shopping_list.add_item(item)
                    elif action == "remove":
                        self.shopping_list.remove_item(item)
                    
                    self._broadcast_update(action, item)
                
                elif msg["type"] == "upd":
                    action, item = msg["action"], msg["item"]
                    seq = msg.get("seq", 0)
                    
                    print(f"[COORD] Update #{seq}: {action} {item}")
                    
                    if action == "add" and item not in self.shopping_list.items:
                        self.shopping_list.items.append(item)
                    elif action == "remove" and item in self.shopping_list.items:
                        self.shopping_list.items.remove(item)
            except:
                pass
    
    def show_list(self):
        print(f"\n[Node {self.id[:8]}]")
        print(self.shopping_list)
    
    def get_info(self):
        leader = "Ja" if self.is_leader else "Nein"
        items = len(self.shopping_list.get_items())
        return f"Node {self.id[:8]} | Port: {self.port} | Leader: {leader} | Items: {items}"