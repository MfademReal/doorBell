 
import numpy as np
import cv2
from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import pyaudio
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Global variables to manage the audio stream thread
audio_thread = None
audio_streaming = False

# Video stream function
def gen_frames():
    """Generate frames from the camera."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Unable to access the camera.")
        return
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        cap.release()

# Audio stream function
def stream_audio():
    """Stream audio from the microphone."""
    global audio_streaming
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
    audio_streaming = True
    try:
        while audio_streaming:
            data = stream.read(1024)
            socketio.emit('audio', {'audio': data}, broadcast=True)
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Serve video feed."""
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    global audio_thread
    if audio_thread is None:
        audio_thread = threading.Thread(target=stream_audio)
        audio_thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    global audio_streaming
    audio_streaming = False

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
                                      
