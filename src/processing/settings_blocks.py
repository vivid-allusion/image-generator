"""Per-file setting blocks (```aspect_ratio, ```resolution, ```size, …).

A block is accepted only when the profile's model declares that setting in its
own endpoint file (engine_<platform>/endpoints/*/<file>.toml) and, for a select
setting, the value is one of its options. Anything else rejects the file.
"""

import tomllib
from pathlib import Path
from typing import Any

_BOOLS = {"on": True, "true": True, "yes": True, "off": False, "false": False, "no": False}


def endpoint_params(profile: dict[str, Any], search_paths: list[Path]) -> dict[str, Any] | None:
    """Return the `[params]` table of the profile's endpoint file, or None if not found."""
    platform, endpoint = profile.get("platform"), profile.get("endpoint")
    for root in search_paths:
        for toml in sorted(root.glob(f"engine-{platform}/engine_{platform}/endpoints/*/*.toml")):
            try:
                data = tomllib.loads(toml.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if data.get("endpoint") == endpoint:
                return data.get("params", {})
    return None


def resolve_settings(raw: dict[str, str], params: dict[str, Any] | None) -> dict[str, Any]:
    """Map block values to profile parameters; ValueError when a block is refused."""
    out: dict[str, Any] = {}
    for block, value in raw.items():
        if params is None:
            raise ValueError(
                f"```{block} block ({value!r}) cannot be checked: the model's endpoint file was not found"
            )
        spec = params.get(block)
        if spec is None:
            raise ValueError(f"```{block} block ({value!r}): this model has no such setting")
        if spec.get("type") == "boolean":
            if value.lower() not in _BOOLS:
                raise ValueError(f"```{block} block: {value!r} is not on/off/true/false/yes/no")
            out[block] = _BOOLS[value.lower()]
            continue
        if spec.get("type") in ("integer", "number"):
            convert = int if spec["type"] == "integer" else float
            try:
                out[block] = convert(value)
            except ValueError:
                raise ValueError(f"```{block} block: {value!r} is not a {spec['type']}") from None
            continue
        options = [str(o.get("value")) for o in spec.get("options", [])]
        if options and value not in options:
            raise ValueError(
                f"```{block} block: {value!r} is not one of this model's options ({', '.join(options)})"
            )
        out[block] = value
    return out
