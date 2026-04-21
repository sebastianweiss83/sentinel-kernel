"""Hash-chain linkage across attestations within an agent namespace.

Each attestation carries a `previous_hash` that points at the prior
attestation in the same namespace. The first attestation in a
namespace anchors to a deterministic genesis hash. A walker can
detect any inserted, deleted, or modified attestation.
"""

from sentinel.chain.namespace import ChainNamespace, compute_genesis_hash
from sentinel.chain.walker import ChainVerification, verify_chain

__all__ = [
    "ChainNamespace",
    "ChainVerification",
    "compute_genesis_hash",
    "verify_chain",
]
