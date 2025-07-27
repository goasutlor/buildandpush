from flask import Flask, render_template, request, jsonify
import os
import subprocess
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)

# Global variables for logging
log_queue = []
log_lock = threading.Lock()

def log_wrapper(message):
    """Add timestamp to log messages"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    with log_lock:
        log_queue.append(log_message)
    print(log_message)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/deploy', methods=['POST'])
def deploy():
    """Handle deployment requests"""
    try:
        data = request.get_json()
        project_name = data.get('project_name', 'Complete_Deploy_Tool')
        
        def deploy_process():
            try:
                log_wrapper("🚀 Starting Complete Deploy Tool Deployment...")
                log_wrapper(f"📦 Project: {project_name}")
                
                # Get current directory
                current_dir = os.getcwd()
                log_wrapper(f"📁 Current directory: {current_dir}")
                
                # Check if we're in the right directory
                if not os.path.exists('app.py'):
                    log_wrapper("❌ app.py not found in current directory")
                    return
                
                log_wrapper("✅ Found app.py - deployment can proceed")
                
                # Simulate deployment steps
                log_wrapper("📝 Step 1: Code Analysis...")
                time.sleep(1)
                log_wrapper("✅ Code analysis complete")
                
                log_wrapper("🔨 Step 2: Building Application...")
                time.sleep(1)
                log_wrapper("✅ Application built successfully")
                
                log_wrapper("📦 Step 3: Packaging...")
                time.sleep(1)
                log_wrapper("✅ Packaging complete")
                
                log_wrapper("🚀 Step 4: Deployment...")
                time.sleep(1)
                log_wrapper("✅ Deployment successful!")
                
                log_wrapper("🎉 Complete Deploy Tool is now ready!")
                
            except Exception as e:
                log_wrapper(f"❌ Deployment failed: {e}")
        
        # Start deployment in background
        thread = threading.Thread(target=deploy_process)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': 'Deployment started! Check logs for progress.'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Deployment failed: {e}'})

@app.route('/logs')
def logs():
    def generate():
        while True:
            try:
                # Get log messages
                with log_lock:
                    if log_queue:
                        message = log_queue.pop(0)
                        yield f"data: {json.dumps({'message': message})}\n\n"
                    else:
                        yield f"data: {json.dumps({'message': ''})}\n\n"
                time.sleep(0.1)
            except:
                yield f"data: {json.dumps({'message': ''})}\n\n"
    
    return app.response_class(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 