from flask import Flask, request, jsonify
import requests
import logging
import os

app = Flask(__name__)

# Log to stdout
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] trace_id=%(trace_id)s endpoint=%(endpoint)s featureset=%(featureset)s')

class FeatureFlag:
    def __init__(self, required_indices):
        self.required_indices = required_indices

    def is_enabled(self, bitmask):
        if isinstance(bitmask, str):
            try:
                bitmask = int(bitmask)
            except ValueError:
                return False
        return all(bitmask & (1 << index) for index in self.required_indices)

@app.route('/api', methods=['POST'])
def api():
    trace_id = request.headers.get('X-Trace-ID', 'unknown')
    featureset = request.headers.get('X-Enabled-Features', '0')
    
    # Log request details to stdout
    logging.info('', extra={'trace_id': trace_id, 'endpoint': '/api', 'featureset': featureset})
    
    # Local data for Service Two
    data = []
    if FeatureFlag([0]).is_enabled(featureset):
        data.append('Feature Flag at Index 0 is Enabled for Service 2')
    if FeatureFlag([1]).is_enabled(featureset):
        data.append('Feature Flag at Index 1 is Enabled for Service 2')
    if FeatureFlag([2]).is_enabled(featureset):
        data.append('Feature Flag at Index 2 is Enabled for Service 2')
    
    # Aggregate response
    response_dict = {"Service Two": data}
    
    # Forward to downstream3
    downstream_url = os.getenv('DOWNSTREAM_URL', 'http://downstream3:5003/api')
    try:
        response = requests.post(downstream_url, headers=request.headers, timeout=5)
        response.raise_for_status()
        downstream_dict = response.json()
        response_dict.update(downstream_dict)
    except requests.RequestException as e:
        logging.error(f"Failed to forward to {downstream_url}: {e}")
    
    return jsonify(response_dict), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002)

