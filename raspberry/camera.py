from flask import Flask, Response
import cv2

app = Flask(__name__)

# Use the Raspberry Pi camera or USB webcam
camera = cv2.VideoCapture(0)  # 0 = default camera

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # Stream as multipart HTTP response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Runs independently on port 5001
    app.run(host='0.0.0.0', port=5001, threaded=True)
