from flask import Flask, request, jsonify
import requests
import logging
import os

app = Flask(__name__)

# Default logging format without custom fields
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')

# Custom formatter for requests with extra fields
request_log_format = logging.Formatter('%(asctime)s [%(levelname)s] trace_id=%(trace_id)s endpoint=%(endpoint)s featureset=%(featureset)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(request_log_format)
app.logger.handlers.clear()
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

class FeatureFlag:
    def __init__(self, required_indices):
        self.required_indices = required_indices

    def is_enabled(self, bitmask):
        if isinstance(bitmask, str):
            try:
                bitmask = int(bitmask)
            except ValueError:
                return False
        # Check if all required indices are enabled in the bitmask
        return all(bitmask & (1 << index) for index in self.required_indices)

@app.route('/api', methods=['POST'])
def api():
    trace_id = request.headers.get('X-Trace-ID', 'unknown')
    feature_set = request.headers.get('X-Feature-Set', '0')
    
    app.logger.info("", extra={'trace_id': trace_id, 'endpoint': '/api', 'featureset': feature_set})
    
    data = []
    # Individual features
    if FeatureFlag([0]).is_enabled(feature_set):
        data.append("Feature 0 logic executed in Service 1")
    if FeatureFlag([1]).is_enabled(feature_set):
        data.append("Feature 1 logic executed in Service 1")
    if FeatureFlag([2]).is_enabled(feature_set):
        data.append("Feature 2 logic executed in Service 1")
    
    # Example combinations
    if FeatureFlag([0, 1]).is_enabled(feature_set):
        data.append("Combination 0+1 logic executed in Service 1")
    if FeatureFlag([0, 2]).is_enabled(feature_set):
        data.append("Combination 0+2 logic executed in Service 1")
    if FeatureFlag([1, 2]).is_enabled(feature_set):
        data.append("Combination 1+2 logic executed in Service 1")
    
    response_dict = {"Service One": data}
    
    downstream_url = os.getenv('DOWNSTREAM_URL', 'http://microservice-b:5002/api')
    downstream_headers = {'X-Feature-Set': feature_set, 'X-Trace-ID': trace_id}
    try:
        response = requests.post(downstream_url, headers=downstream_headers, timeout=5)
        response.raise_for_status()
        downstream_dict = response.json()
        response_dict.update(downstream_dict)
    except requests.RequestException as e:
        app.logger.error(f"Failed to forward to {downstream_url}: {e}")
    
    return jsonify(response_dict), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
