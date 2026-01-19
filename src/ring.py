class Ring:
    # Ring Topology - Nodes im Ring organisieren
    
    def __init__(self, node, discovery):
        self.node = node
        self.discovery = discovery
        self.left_neighbor = None
        self.right_neighbor = None
        self.election = None
        
        self.discovery.on_peer_removed = self.handle_peer_removal
        self.discovery.on_peer_added = self.handle_peer_addition
    
    def set_election(self, election):
        self.election = election
    
    def handle_peer_removal(self, removed_peers):
        print(f"[RING] Peer-Verlust erkannt - Ring-Update")
        self.update_ring()
        
        if self.node.current_leader_id in removed_peers:
            print(f"[RING] Leader ausgefallen - starte Re-Election")
            self.node.is_leader = False
            self.node.current_leader_id = None
            
            if self.election:
                import threading
                def delayed_election():
                    import time
                    time.sleep(2)
                    
                    peers = self.discovery.get_peers()
                    if not peers:
                        self.node.is_leader = True
                        self.node.current_leader_id = self.node.id
                        print(f"[ELECTION] Node {self.node.id[:8]} ist alleine - wird Leader")
                        return
                    
                    if not self.election.election_in_progress:
                        self.election.start_election()
                
                threading.Thread(target=delayed_election, daemon=True).start()
    
    def handle_peer_addition(self):
        print(f"[RING] Neuer Peer joint - Ring-Update + State-Sync")
        self.update_ring()
        
        # Leader sendet State nur bei NEUEN Peers
        if self.node.is_leader and hasattr(self.node, 'shopping_list') and hasattr(self.node, 'coord_socket'):
            items = self.node.shopping_list.get_items()
            if items:
                import threading
                import time
                
                def delayed_sync():
                    time.sleep(2)
                    print(f"[RING] Leader sendet State-Sync ({len(items)} Items)")
                    for item in items:
                        try:
                            self.node._broadcast_update("sync", item)
                        except Exception as e:
                            print(f"[RING] Sync-Fehler: {e}")
                
                threading.Thread(target=delayed_sync, daemon=True).start()
    
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