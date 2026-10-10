from fastapi import FastAPI

from adapters.inbound.http.health import create_router as create_health_router
from application.get_node_status import NODE_VERSION
from domain.node_identity import NodeIdentity

# The fictional Governance / Ethics Authority of the demo dataset
# (demo-data/organizations.json). One Governance Node process (ADR-0003).
DEMO_IDENTITY = NodeIdentity(
    node_ref="node-governance", organization_ref="org-governance"
)
# Suggested Governance Node port (ADR-0003); the Federation Service defaults to it.
PORT = 8200


def create_app(identity: NodeIdentity = DEMO_IDENTITY) -> FastAPI:
    app = FastAPI(title="Governance Node", version=NODE_VERSION)
    app.include_router(create_health_router(identity))
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
