"""Known architecture-factor primitives used for transport accounting."""

from spirallens.factors.attention_routing import (
    attention_routing_jvp,
    softmax_jvp,
)
from spirallens.factors.attention_value import attention_value_jvp
from spirallens.factors.layernorm import layernorm, layernorm_jacobian, layernorm_jvp
from spirallens.factors.mlp import gelu_tanh_derivative, mlp_jvp
from spirallens.factors.rope import apply_rope, derotate_rope, rope_angles

__all__ = [
    "apply_rope",
    "attention_routing_jvp",
    "attention_value_jvp",
    "derotate_rope",
    "gelu_tanh_derivative",
    "layernorm",
    "layernorm_jacobian",
    "layernorm_jvp",
    "mlp_jvp",
    "rope_angles",
    "softmax_jvp",
]
