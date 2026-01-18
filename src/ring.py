class Ring:
    # Ring Topology - Nodes im Ring organisieren
    
    def __init__(self, node, discovery):
        self.node = node
        self.discovery = discovery
        self.left_neighbor = None
        self.right_neighbor = None
        
        # Registriere Callback für Peer-Verlust
        self.discovery.on_peer_removed = self.update_ring
    
    def update_ring(self):
        # Aktualisiert Ring basierend auf Peers
        peers = self.discovery.get_peers()
        
        if not peers:
            self.left_neighbor = None
            self.right_neighbor = None
            print(f"[RING] Kein Ring - Node alleine")
            return
        
        # Sortiere alle IDs (inkl. eigener)
        all_ids = sorted([self.node.id] + list(peers.keys()))
        my_index = all_ids.index(self.node.id)
        
        # Bestimme Nachbarn (mit wrap-around)
        left_id = all_ids[(my_index - 1) % len(all_ids)]
        right_id = all_ids[(my_index + 1) % len(all_ids)]
        
        # Wenn left_id == eigene ID, dann alleine
        if left_id == self.node.id:
            self.left_neighbor = None
            self.right_neighbor = None
            print(f"[RING] Nur ein Node")
            return
        
        # Setze Nachbarn
        self.left_neighbor = {
            "id": left_id,
            "port": peers.get(left_id, {}).get("port", self.node.port)
        }
        self.right_neighbor = {
            "id": right_id,
            "port": peers.get(right_id, {}).get("port", self.node.port)
        }
        
        print(f"[RING] Links: {left_id[:8]} | Ich: {self.node.id[:8]} | Rechts: {right_id[:8]}")
    
    def get_right_neighbor(self):
        return self.right_neighbor