# server.py
import asyncio
import websockets

# This set will store all connected clients
connected_clients = set()

async def handler(websocket, path):
    """
    Handles a new client connection.
    """
    # Add the new client to our set of connected clients
    connected_clients.add(websocket)
    print(f"New client connected! Total clients: {len(connected_clients)}")
    
    try:
        # Listen for messages from this client
        async for message in websocket:
            print(f"Received message from a client: {message}")
            
            # --- This is where your game logic would go ---
            # 1. Parse the message (e.g., "PLAY_CARD,epstein,100,200")
            # 2. Update the authoritative game state on the server.
            # 3. Create a new state packet to send back.
            
            # Broadcast the message to all other clients
            # (In a real game, you would send a processed game state update)
            for client in connected_clients:
                if client != websocket: # Don't send the message back to the sender
                    await client.send(f"Another player sent: {message}")

    except websockets.ConnectionClosed:
        print("A client disconnected.")
    finally:
        # Remove the client when they disconnect
        connected_clients.remove(websocket)

async def main():
    # IMPORTANT: Host on 'localhost' for safe local development.
    # DO NOT use your public IP address here.
    async with websockets.serve(handler, "localhost", 8765):
        print("Server started on ws://localhost:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())