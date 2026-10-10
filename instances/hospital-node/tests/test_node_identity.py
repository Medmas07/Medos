import pytest

from domain.node_identity import InvalidNodeIdentity, NodeIdentity


@pytest.mark.parametrize("ref", ["", "-leading-dash", "has space", "a" * 129])
@pytest.mark.parametrize("field", ["node_ref", "organization_ref"])
def test_rejects_refs_that_are_not_opaque(field, ref):
    refs = {"node_ref": "node-ok", "organization_ref": "org-ok", field: ref}

    with pytest.raises(InvalidNodeIdentity, match=field):
        NodeIdentity(**refs)
