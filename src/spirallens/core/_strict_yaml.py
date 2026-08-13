"""Private factory for strict :mod:`yaml` loader subclasses."""

from __future__ import annotations

from typing import Any

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode


def make_strict_safe_loader(
    error_type: type[Exception],
    *,
    string_keys_message: str = "all YAML mapping keys must be strings",
) -> type[yaml.SafeLoader]:
    """Return an isolated SafeLoader rejecting ambiguous mapping syntax."""

    class _StrictSafeLoader(yaml.SafeLoader):
        def compose_node(self, parent: Any, index: Any) -> Any:
            if self.check_event(AliasEvent):
                raise error_type("YAML aliases are not allowed")
            return super().compose_node(parent, index)

    def _construct_mapping(
        loader: _StrictSafeLoader,
        node: MappingNode,
        deep: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(node, MappingNode):
            raise error_type("expected a YAML mapping")
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                raise error_type("YAML merge keys are not allowed")
            key = loader.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise error_type(string_keys_message)
            if key in mapping:
                raise error_type(f"duplicate YAML key {key!r}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    _StrictSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping,
    )
    return _StrictSafeLoader
