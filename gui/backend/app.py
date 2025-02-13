from flask import Flask, render_template
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def home():
    return render_template("index.html")  # Serve the simple landing page

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=443, debug=True)
