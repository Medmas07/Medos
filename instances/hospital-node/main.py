from fastapi import FastAPI

# Runtime skeleton only (HC-110). The health endpoint (HC-111), per-hospital
# configuration (HC-112), and clinical APIs (HC-113+) arrive with their tickets.
app = FastAPI(title="Hospital Node", version="0.1.0")
