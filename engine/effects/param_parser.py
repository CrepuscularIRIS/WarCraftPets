import re

def _to_num(s: str):
    s = (s or "").strip()
    if s == "" or s.lower() == "null":
        return 0
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        return s


_CAMEL_1 = re.compile(r"([a-z0-9])([A-Z])")
_CAMEL_2 = re.compile(r"([A-Z]+)([A-Z][a-z])")
_MULTI_US = re.compile(r"_+")

# Backward-compatible aliases (historical handler naming)
_ALIASES = {
    "tick_down_first_round": "tickdown_first_round",
}


def _to_snake(label: str) -> str:
    # Normalize ParamLabel tokens (DB2) to snake_case keys used by handlers.
    s = (label or "").strip().replace(" ", "_")
    s = _CAMEL_2.sub(r"\1_\2", s)
    s = _CAMEL_1.sub(r"\1_\2", s)
    s = _MULTI_US.sub("_", s)
    s = s.lower().strip("_")
    return _ALIASES.get(s, s)


class ParamParser:
    @staticmethod
    def parse(param_label: str, param_raw: str) -> dict:
        labels = [x.strip() for x in (param_label or "").split(",")]
        raws = [x.strip() for x in (param_raw or "").split(",")]

        n = max(len(labels), len(raws), 6)
        labels += [""] * (n - len(labels))
        raws += ["0"] * (n - len(raws))

        out = {}
        for lab, val in zip(labels, raws):
            if not lab:
                continue
            key = _to_snake(lab)
            if not key:
                continue
            out[key] = _to_num(val)
        return out
