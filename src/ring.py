class Ring:
    # Ring Topology - Nodes im Ring organisieren
    
    def __init__(self, node, discovery):
        self.node = node
        self.discovery = discovery
        self.left_neighbor = None
        self.right_neighbor = None
        self.election = None
        
        self.discovery.on_peer_removed = self.handle_peer_removal
    
    def set_election(self, election):
        # Wird nach Election-Initialisierung aufgerufen
        self.election = election
    
    def handle_peer_removal(self, removed_peers):
        # Wird aufgerufen wenn Peers entfernt wurden
        print(f"[RING] Peer-Verlust erkannt - Ring-Update")
        self.update_ring()
        
        # Prüfe ob Leader ausgefallen ist
        if self.node.current_leader_id in removed_peers:
            print(f"[RING] Leader ausgefallen - starte Re-Election")
            self.node.is_leader = False
            self.node.current_leader_id = None
            
            # Starte neue Election nach kurzer Verzögerung
            if self.election:
                import threading
                def delayed_election():
                    import time
                    time.sleep(1)
                    if not self.election.election_in_progress:
                        self.election.start_election()
                
                threading.Thread(target=delayed_election, daemon=True).start()
    
    def update_ring(self):
        peers = self.discovery.get_peers()
        
        if not peers:
            self.left_neighbor = None
            self.right_neighbor = None
            print(f"[RING] Kein Ring - Node alleine")
            return
        
        all_ids = sorted([self.node.id] + list(peers.keys()))
        my_index = all_ids.index(self.node.id)
        
        left_id = all_ids[(my_index - 1) % len(all_ids)]
        right_id = all_ids[(my_index + 1) % len(all_ids)]
        
        if left_id == self.node.id:
            self.left_neighbor = None
            self.right_neighbor = None
            print(f"[RING] Nur ein Node")
            return
        
        self.left_neighbor = {
            "id": left_id,
            "port": peers.get(left_id, {}).get("port", self.node.port),
            "ip": peers.get(left_id, {}).get("ip", "127.0.0.1")
        }
        self.right_neighbor = {
            "id": right_id,
            "port": peers.get(right_id, {}).get("port", self.node.port),
            "ip": peers.get(right_id, {}).get("ip", "127.0.0.1")
        }
        
        print(f"[RING] Links: {left_id[:8]} | Ich: {self.node.id[:8]} | Rechts: {right_id[:8]}")
    
    def get_right_neighbor(self):
        return self.right_neighbor