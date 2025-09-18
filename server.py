# server.py
import asyncio
import websockets
import json
import time
import os  # Import the 'os' module
from websockets import http

# --- Game Constants (Translate from your JS) ---
ELIXIR_INTERVAL = 2.8
# Define card stats here so the server knows the rules
CARDS = {
    'jew': {'cost': 4, 'type': 'BUILDING', 'stats': {'hp': 300, 'elixirRate': 5.0, 'lifetime': 60}},
    'jfk': {'cost': 5, 'type': 'UNIT', 'stats': {'hp': 1963, 'damage': 150, 'speed': 48}},
    # TODO: Add ALL your other cards here for the server to use
}


GAME_ROOMS = {}
waiting_players = []

class Game:
    """A class to manage a single game instance for two players."""
    def __init__(self, room_id, player1_ws, player2_ws):
        self.room_id = room_id
        self.players = {player1_ws: 'player1', player2_ws: 'player2'}
        self.is_running = True
        self.last_update_time = time.time()
        
        # This is the authoritative game state
        self.game_state = {
            'player1': {'elixir': 5, 'elixir_timer': 0, 'units': [], 'buildings': []},
            'player2': {'elixir': 5, 'elixir_timer': 0, 'units': [], 'buildings': []},
        }
        print(f"Game room {self.room_id} created.")

    def handle_input(self, player_ws, data):
        """Processes an input message (e.g., playing a card) from a player."""
        player_key = self.players.get(player_ws)
        if not player_key: return

        if data.get('type') == 'play_card':
            card_id = data['payload']['cardId']
            card_info = CARDS.get(card_id)
            if not card_info: return
            
            player_state = self.game_state[player_key]
            if player_state['elixir'] >= card_info['cost']:
                player_state['elixir'] -= card_info['cost']
                print(f"{player_key} played {card_id}")
                
                # TODO: You need to add logic here to properly spawn units/buildings
                # into the game state with all their required properties.

    def update_game_logic(self, dt):
        """The core simulation step. All game logic goes here."""
        for player_key in ['player1', 'player2']:
            player_state = self.game_state[player_key]
            
            # 1. Update Elixir
            player_state['elixir_timer'] += dt
            if player_state['elixir'] < 10 and player_state['elixir_timer'] >= ELIXIR_INTERVAL:
                player_state['elixir'] += 1
                player_state['elixir_timer'] -= ELIXIR_INTERVAL
            
            # TODO: 2. Update Building Logic (lifetime, elixir generation)
            # TODO: 3. Update Unit Movement (translate moveUnitOnPath from JS)
            # TODO: 4. Handle Targeting and Attacks, etc.

    async def game_loop(self):
        """Runs the main loop for this specific game instance."""
        p1_ws, p2_ws = self.players.keys()
        await asyncio.wait([
            p1_ws.send(json.dumps({"type": "game_start", "player": "player1"})),
            p2_ws.send(json.dumps({"type": "game_start", "player": "player2"}))
        ])

        while self.is_running:
            current_time = time.time()
            dt = current_time - self.last_update_time
            self.last_update_time = current_time
            
            self.update_game_logic(dt)
            
            p1_state = {"type": "game_state", "you": self.game_state['player1'], "opponent": self.game_state['player2']}
            p2_state = {"type": "game_state", "you": self.game_state['player2'], "opponent": self.game_state['player1']}
            
            await asyncio.wait([
                p1_ws.send(json.dumps(p1_state)),
                p2_ws.send(json.dumps(p2_state))
            ])
            
            await asyncio.sleep(1/30) # Aim for 30 updates per second

async def health_check(path):
    """A simple HTTP health check endpoint for Render."""
    if path == "/health":
        return http.Response(status_code=200, headers={"Content-Type": "text/plain"}, body=b"OK")

async def matchmaking(websocket):
    """Handles putting players into a game room."""
    waiting_players.append(websocket)
    if len(waiting_players) >= 2:
        p1 = waiting_players.pop(0)
        p2 = waiting_players.pop(0)
        game = Game(f"room_{p1.id}", p1, p2)
        GAME_ROOMS[game.room_id] = game
        asyncio.create_task(game.game_loop())

async def handler(websocket):
    """Main connection handler."""
    print(f"Client connected: {websocket.id}")
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get('type') == 'find_game':
                await matchmaking(websocket)
            else:
                for game in GAME_ROOMS.values():
                    if websocket in game.players:
                        game.handle_input(websocket, data)
                        break
    except websockets.exceptions.ConnectionClosed:
        print(f"Client {websocket.id} disconnected.")
    finally:
        if websocket in waiting_players: waiting_players.remove(websocket)
        room_to_remove = None
        for room_id, game in GAME_ROOMS.items():
            if websocket in game.players:
                game.is_running = False
                room_to_remove = room_id
                break
        if room_to_remove: del GAME_ROOMS[room_to_remove]

async def main():
    # Get the port from the environment variable provided by Render.
    # Fall back to 42069 for local testing.
    port = int(os.environ.get("PORT", 42069))
    
    # We don't handle SSL here. Render's load balancer handles wss:// encryption for us.
    async with websockets.serve(
        handler,
        "0.0.0.0",
        port,
        process_request=health_check
    ):
        print(f"Server started on port {port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
