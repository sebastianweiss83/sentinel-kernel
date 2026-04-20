"""sentinel.chain — hash-chain linkage across attestations.

Each attestation within a namespace carries a ``previous_hash``
pointing to the prior attestation in the same namespace. The first
attestation per namespace anchors to a deterministic genesis hash.
Anyone holding the full chain can verify that no attestation has
been inserted, deleted, or modified without also computing a
contradictory hash.

Namespace convention
--------------------
An *agent namespace* is a tuple of
``(agent_id, jurisdiction, policy_family)``. The namespace string is
the canonical serialisation of that tuple and is what the genesis
hash commits to.

Example
-------
.. code-block:: python

    from sentinel.chain import ChainNamespace, verify_chain
    from sentinel.core.attestation import generate_attestation

    ns = ChainNamespace(
        agent_id="risk-agent",
        jurisdiction="EU-DE",
        policy_family="bafin-bait-8",
    )

    first = generate_attestation(sentinel, chain_namespace=ns)
    second = generate_attestation(
        sentinel, chain_namespace=ns, previous_hash=first["attestation_hash"]
    )

    result = verify_chain([first, second])
    assert result.verified
"""

from sentinel.chain.namespace import ChainNamespace, compute_genesis_hash
from sentinel.chain.walker import ChainVerification, verify_chain

__all__ = [
    "ChainNamespace",
    "ChainVerification",
    "compute_genesis_hash",
    "verify_chain",
]
