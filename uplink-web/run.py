"""Entry point for the Uplink web game."""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.extensions import socketio
from app.game.game_loop import game_loop

app = create_app()

# Start the background game loop
game_loop.start(app)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=app.debug)
