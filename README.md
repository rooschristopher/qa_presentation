# Feature Flag Service Project

## Overview

This project implements a feature flag system using Docker Compose, consisting of a central `feature-flag-service` and three downstream microservices (`microservice-a`, `microservice-b`, `microservice-c`). The `feature-flag-service` manages a bitmask-based feature set (`X-Feature-Set`), adjustable via `X-Enabled-Features` and `X-Suppressed-Features` headers, and passes it downstream. Each microservice evaluates this bitmask against specific indices or combinations to execute conditional logic, simulating feature toggling in a distributed system.

### Key Components
- **`feature-flag-service`**: 
  - Computes the `X-Feature-Set` bitmask from a base value, enabling or suppressing features.
  - Maintains a feature name list (`FEATURES`) for lookup.
  - Provides endpoints for feature toggling and computation.
- **`microservice-a`, `microservice-b`, `microservice-c`**:
  - Process the `X-Feature-Set` bitmask to execute logic for individual indices (0, 1, 2) and combinations (`[0, 1]`, `[0, 2]`, `[1, 2]`).
  - Chain requests sequentially, building a cumulative response.

### Directory Structure
```
project_root/
├── feature_flags/
│   ├── Dockerfile
│   └── app.py
├── microservices/
│   ├── a/
│   │   ├── Dockerfile
│   │   └── app.py
│   ├── b/
│   │   ├── Dockerfile
│   │   └── app.py
│   ├── c/
│   │   ├── Dockerfile
│   │   └── app.py
├── docker-compose.yml
└── README.md
```

## Setup Instructions

### Prerequisites
- Docker and Docker Compose installed on your system.
- Ubuntu or a compatible OS (tested on Ubuntu as of March 9, 2025).

### Running the Project
1. **Clone the Repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd project_root/
   ```
2. **Build and Start Services**:
   ```bash
   docker-compose up --build
   ```
   - Builds and runs all services in the background.
   - Ports: `5000` (feature-flag-service), `5001` (microservice-a), `5002` (microservice-b), `5003` (microservice-c).
3. **Verify Services**:
   ```bash
   docker ps
   ```
   - Ensure all four containers are running.
4. **View Logs**:
   ```bash
   docker-compose logs -f
   ```

### Stopping the Project
```bash
docker-compose down
```

## Feature Flag Logic

### Feature Set
- **Header**: `X-Feature-Set` is an integer bitmask (e.g., `4` = binary `100`, `5` = `101`).
- **Default**: `4` (index 2 enabled, representing a production feature).
- **Adjustment**:
  - `X-Enabled-Features`: Adds features (bitmask or comma-separated indices, e.g., `1` or `0,1`).
  - `X-Suppressed-Features`: Removes features (bitmask or indices, e.g., `2`), taking precedence over enabled features.
- **Computation**: `final_feature_set = (base | enabled) & ~suppressed`.

### Feature Indices
- `0`: Bit 0 (value `1`)
- `1`: Bit 1 (value `2`)
- `2`: Bit 2 (value `4`)
- Example: `5` (binary `101`) enables indices 0 and 2.

### Feature Names
- Maintained in `feature-flag-service`: `["feature1", "feature2", "feature3"]` (indices 0, 1, 2).
- Accessible via `/feature/<index>` endpoint.

## API Endpoints

### Feature Flag Service (`localhost:5000`)
- **`/healthcheck` (GET)**:
  - Returns service status.
  - Example: `curl http://localhost:5000/healthcheck`
  - Response: `{"name": "Feature Flag Server", "version": "0.0.1"}`
- **`/feature/<index>` (GET)**:
  - Returns the feature name at the given index.
  - Example: `curl http://localhost:5000/feature/1`
  - Response: `{"index": 1, "feature": "feature2"}`
- **`/compute-feature-set` (GET)**:
  - Computes a new `X-Feature-Set` from `feature_set`, `enable`, and `suppressed` query parameters.
  - Parameters:
    - `feature_set` (int, required): Base bitmask.
    - `enable` (str, optional): Bitmask or indices to enable (e.g., `0,1`).
    - `suppressed` (str, optional): Bitmask or indices to suppress (e.g., `2`).
  - Example: `curl "http://localhost:5000/compute-feature-set?feature_set=4&enable=0"`
  - Response: `{"new_feature_set": 5}`
- **`/` (POST)**:
  - Computes `X-Feature-Set` from headers and forwards it downstream.
  - Headers:
    - `X-Feature-Set` (int, optional): Base bitmask (defaults to `4`).
    - `X-Enabled-Features` (str, optional): Features to enable.
    - `X-Suppressed-Features` (str, optional): Features to suppress.
  - Example: `curl -X POST -H "X-Feature-Set: 4" -H "X-Enabled-Features: 0" http://localhost:5000/`
  - Response: See downstream logic below.

### Downstream Microservices
- **`/api` (POST)**:
  - Evaluates `X-Feature-Set` against individual indices (`0`, `1`, `2`) and combinations (`[0, 1]`, `[0, 2]`, `[1, 2]`).
  - Appends messages to the response if all required indices are enabled.
  - Chains to the next service (a → b → c).

## Example Curl Commands

### Feature Flag Computation
- **Base 4 + Enable 0**:
  ```bash
  curl "http://localhost:5000/compute-feature-set?feature_set=4&enable=0"
  ```
  - Response: `{"new_feature_set": 5}`

- **Base 5 + Suppress 0**:
  ```bash
  curl "http://localhost:5000/compute-feature-set?feature_set=5&suppressed=0"
  ```
  - Response: `{"new_feature_set": 4}`

### Feature Name Lookup
- **Get Feature at Index 2**:
  ```bash
  curl http://localhost:5000/feature/2
  ```
  - Response: `{"index": 2, "feature": "feature3"}`

### Downstream Logic Execution
- **Default Feature Set (4)**:
  ```bash
  curl -X POST http://localhost:5000/
  ```
  - Response:
    ```json
    {
      "Service One": ["Feature 2 logic executed in Service 1"],
      "Service Two": ["Feature 2 logic executed in Service 2"],
      "Service Three": ["Feature 2 logic executed in Service 3"]
    }
    ```

- **Enable 0 and 2 (5)**:
  ```bash
  curl -X POST -H "X-Feature-Set: 5" http://localhost:5000/
  ```
  - Response:
    ```json
    {
      "Service One": [
        "Feature 0 logic executed in Service 1",
        "Feature 2 logic executed in Service 1",
        "Combination 0+2 logic executed in Service 1"
      ],
      "Service Two": [
        "Feature 0 logic executed in Service 2",
        "Feature 2 logic executed in Service 2",
        "Combination 0+2 logic executed in Service 2"
      ],
      "Service Three": [
        "Feature 0 logic executed in Service 3",
        "Feature 2 logic executed in Service 3",
        "Combination 0+2 logic executed in Service 3"
      ]
    }
    ```

- **Enable All (7)**:
  ```bash
  curl -X POST -H "X-Feature-Set: 7" http://localhost:5000/
  ```
  - Response:
    ```json
    {
      "Service One": [
        "Feature 0 logic executed in Service 1",
        "Feature 1 logic executed in Service 1",
        "Feature 2 logic executed in Service 1",
        "Combination 0+1 logic executed in Service 1",
        "Combination 0+2 logic executed in Service 1",
        "Combination 1+2 logic executed in Service 1"
      ],
      "Service Two": [
        "Feature 0 logic executed in Service 2",
        "Feature 1 logic executed in Service 2",
        "Feature 2 logic executed in Service 2",
        "Combination 0+1 logic executed in Service 2",
        "Combination 0+2 logic executed in Service 2",
        "Combination 1+2 logic executed in Service 2"
      ],
      "Service Three": [
        "Feature 0 logic executed in Service 3",
        "Feature 1 logic executed in Service 3",
        "Feature 2 logic executed in Service 3",
        "Combination 0+1 logic executed in Service 3",
        "Combination 0+2 logic executed in Service 3",
        "Combination 1+2 logic executed in Service 3"
      ]
    }
    ```

## Architecture Notes
- **Networking**: Uses a custom `app-network` (bridge) with hostnames for service resolution (`feature-flag-service`, `microservice-a`, etc.).
- **Bitmask**: `X-Feature-Set` is an integer transmitted as a string header (e.g., `"5"`) but processed as a bitmask internally.
- **Downstream Logic**: Microservices execute logic only if **all** indices in a `FeatureFlag` check are enabled (e.g., `FeatureFlag([0, 2])` requires both 0 and 2).

## Development
- **Date**: Updated as of March 9, 2025.
- **Dependencies**: Flask, Requests (installed via Dockerfiles).
- **Docker**: Uses `python:3.9-slim` base image for lightweight containers.


