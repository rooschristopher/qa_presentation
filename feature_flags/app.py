from flask import Flask, jsonify, request
import requests
import uuid
import os
import logging

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

DEFAULT_FEATURE_SET = 4  # Default bitmask (index 2 enabled, e.g., prod)
FEATURES = ["feature1", "feature2", "feature3"]  # Feature list for name lookup

def parse_indices(header_value):
    """Parse header value as either a bitmask integer or comma-separated indices."""
    if not header_value:
        return set()
    try:
        bitmask = int(header_value)
        indices = {i for i in range(len(FEATURES)) if bitmask & (1 << i)}
        return indices
    except ValueError:
        indices = {int(i.strip()) for i in header_value.split(',') if i.strip().isdigit() and int(i.strip()) < len(FEATURES)}
        return indices

def compute_feature_set(base_feature_set, enable=None, suppressed=None):
    """Compute the final feature set from base, enabled, and suppressed features."""
    base_bitmask = int(base_feature_set)
    enabled_indices = parse_indices(enable)
    suppressed_indices = parse_indices(suppressed)
    
    enabled_bitmask = sum(1 << i for i in enabled_indices)
    suppressed_bitmask = sum(1 << i for i in suppressed_indices)
    final_feature_set = (base_bitmask | enabled_bitmask) & ~suppressed_bitmask
    
    return final_feature_set

def generate_trace_id():
    return str(uuid.uuid4())

@app.route("/healthcheck")
def health_check():
    return jsonify({"name": "Feature Flag Server", "version": "0.0.1"})

@app.route("/feature/<int:index>")
def get_feature_name(index):
    """Return the feature name at the given index."""
    if 0 <= index < len(FEATURES):
        return jsonify({"index": index, "feature": FEATURES[index]})
    return jsonify({"error": f"Index {index} out of range (0-{len(FEATURES)-1})"}), 400

@app.route("/compute-feature-set")
def compute_feature_set_endpoint():
    """Compute and return the new feature set based on query parameters."""
    feature_set = request.args.get('feature_set', default=DEFAULT_FEATURE_SET, type=int)
    enable = request.args.get('enable', default=None, type=str)
    suppressed = request.args.get('suppressed', default=None, type=str)
    
    try:
        new_feature_set = compute_feature_set(feature_set, enable, suppressed)
        return jsonify({"new_feature_set": new_feature_set})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/", methods=["POST"])
def forward_features():
    headers = request.headers
    
    # Get base feature set from header or default
    base_feature_set = int(headers.get('X-Feature-Set', DEFAULT_FEATURE_SET))
    
    # Parse enable/suppress headers
    enabled_indices = parse_indices(headers.get('X-Enabled-Features', ''))
    suppressed_indices = parse_indices(headers.get('X-Suppressed-Features', ''))
    
    # Compute final feature set: base + enabled - suppressed
    base_bitmask = base_feature_set
    enabled_bitmask = sum(1 << i for i in enabled_indices)
    suppressed_bitmask = sum(1 << i for i in suppressed_indices)
    final_feature_set = (base_bitmask | enabled_bitmask) & ~suppressed_bitmask
    
    trace_id = headers.get('X-Trace-ID', generate_trace_id())
    downstream_url = os.getenv('DOWNSTREAM_URL', 'http://microservice-a:5001/api')
    downstream_headers = {'X-Feature-Set': str(final_feature_set), 'X-Trace-ID': trace_id}

    try:
        app.logger.info("Processing request", extra={'trace_id': trace_id, 'endpoint': '/', 'featureset': final_feature_set})
        response = requests.post(downstream_url, headers=downstream_headers, timeout=5)
        response.raise_for_status()
        app.logger.info(f"Successfully forwarded to {downstream_url}")
        downstream_data = response.json()
        return jsonify(downstream_data)
    except requests.RequestException as e:
        app.logger.error(f"Failed to forward to downstream service: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
