import socket
import json
import threading
import time

class Election:
    # Chang-Roberts Leader Election Algorithmus
    
    def __init__(self, node, ring):
        # node: Das eigene Node-Objekt
        # ring: Die Ring-Instanz
        
        self.node = node
        self.ring = ring
        
        # Socket für Election-Nachrichten
        self.election_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.election_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Binde auf Node-Port + 1000 (um Kollision mit Discovery zu vermeiden)
        self.election_port = self.node.port + 1000
        self.election_socket.bind(("", self.election_port))
        
        # Election läuft?
        self.running = False
        self.election_in_progress = False
        
        print(f"[ELECTION] Initialisiert für Node {self.node.id[:8]} auf Port {self.election_port}")
    
    def start_election(self):
        # Startet eine neue Leader Election
        
        if self.election_in_progress:
            print(f"[ELECTION] Election läuft bereits")
            return
        
        self.election_in_progress = True
        print(f"[ELECTION] Node {self.node.id[:8]} startet Election")
        
        # Sende eigene ID an rechten Nachbarn
        self.send_election_message(self.node.id)
    
    def send_election_message(self, candidate_id):
        # Sendet Election-Nachricht an rechten Nachbarn
        
        right_neighbor = self.ring.get_right_neighbor()
        
        if not right_neighbor:
            # Kein Ring - wir sind alleine, also Leader!
            print(f"[ELECTION] Keine anderen Nodes - Node {self.node.id[:8]} ist Leader")
            self.node.is_leader = True
            self.election_in_progress = False
            return
        
        message = {
            "type": "election",
            "candidate_id": candidate_id
        }
        
        data = json.dumps(message).encode('utf-8')
        
        # Sende an rechten Nachbarn (auf dessen Election-Port)
        target_port = right_neighbor["port"] + 1000
        
        try:
            self.election_socket.sendto(data, ("127.0.0.1", target_port))
            print(f"[ELECTION] Sende Kandidat {candidate_id[:8]} an {right_neighbor['id'][:8]}")
        except Exception as e:
            print(f"[ELECTION] Fehler beim Senden: {e}")
    
    def send_leader_announcement(self):
        # Verkündet dass dieser Node der Leader ist
        
        message = {
            "type": "leader",
            "leader_id": self.node.id
        }
        
        data = json.dumps(message).encode('utf-8')
        
        # Sende an rechten Nachbarn
        right_neighbor = self.ring.get_right_neighbor()
        if right_neighbor:
            target_port = right_neighbor["port"] + 1000
            try:
                self.election_socket.sendto(data, ("127.0.0.1", target_port))
                print(f"[ELECTION] Leader-Announcement gesendet")
            except Exception as e:
                print(f"[ELECTION] Fehler beim Leader-Announcement: {e}")
    
    def listen_for_election(self):
        # Hört auf Election-Nachrichten
        
        while self.running:
            try:
                data, addr = self.election_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                if message["type"] == "election":
                    # Election-Nachricht empfangen
                    candidate_id = message["candidate_id"]
                    
                    if candidate_id == self.node.id:
                        # Eigene ID kam zurück - ICH BIN DER LEADER!
                        print(f"[ELECTION] Node {self.node.id[:8]} ist der LEADER!")
                        self.node.is_leader = True
                        self.election_in_progress = False
                        
                        # Verkünde es allen
                        self.send_leader_announcement()
                    
                    elif candidate_id > self.node.id:
                        # Kandidat hat höhere ID - weiterleiten
                        print(f"[ELECTION] Kandidat {candidate_id[:8]} > meine ID {self.node.id[:8]} - weiterleiten")
                        self.send_election_message(candidate_id)
                    
                    else:
                        # Meine ID ist höher - sende meine ID weiter
                        print(f"[ELECTION] Meine ID {self.node.id[:8]} > Kandidat {candidate_id[:8]} - sende meine ID")
                        if not self.election_in_progress:
                            self.election_in_progress = True
                            self.send_election_message(self.node.id)
                
                elif message["type"] == "leader":
                    # Leader wurde verkündet
                    leader_id = message["leader_id"]
                    
                    if leader_id == self.node.id:
                        # Das bin ich - stoppe Weiterleitung
                        print(f"[ELECTION] Leader-Announcement vollständig")
                    else:
                        # Anderer Node ist Leader
                        print(f"[ELECTION] Node {leader_id[:8]} ist der Leader")
                        self.node.is_leader = False
                        self.election_in_progress = False
                        
                        # Leite Announcement weiter
                        right_neighbor = self.ring.get_right_neighbor()
                        if right_neighbor:
                            target_port = right_neighbor["port"] + 1000
                            self.election_socket.sendto(data, ("127.0.0.1", target_port))
                
            except Exception as e:
                if self.running:
                    print(f"[ELECTION] Fehler beim Empfangen: {e}")
    
    def start(self):
        # Startet Election Service
        self.running = True
        
        # Thread für Empfangen
        listen_thread = threading.Thread(target=self.listen_for_election)
        listen_thread.daemon = True
        listen_thread.start()
        
        print(f"[ELECTION] Service gestartet für Node {self.node.id[:8]}")
    
    def stop(self):
        # Stoppt Election Service
        self.running = False
        try:
            self.election_socket.close()
        except:
            pass
        print(f"[ELECTION] Service gestoppt für Node {self.node.id[:8]}")