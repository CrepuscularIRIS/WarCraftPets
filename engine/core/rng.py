from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SeqRNG:
    seq_hit: List[float] = field(default_factory=list)
    seq_gate: List[float] = field(default_factory=list)
    seq_var: List[float] = field(default_factory=list)
    seq_crit: List[float] = field(default_factory=list)
    used: Dict[str, int] = field(default_factory=lambda: {"hit":0, "gate":0, "var":0, "crit":0})

    def rand_hit(self) -> float:
        self.used["hit"] += 1
        return self.seq_hit.pop(0) if self.seq_hit else 0.0

    def rand_gate(self) -> float:
        self.used["gate"] += 1
        return self.seq_gate.pop(0) if self.seq_gate else 0.0

    def rand_variance(self) -> float:
        self.used["var"] += 1
        return self.seq_var.pop(0) if self.seq_var else 1.0

    def rand_crit(self) -> float:
        self.used["crit"] += 1
        return self.seq_crit.pop(0) if self.seq_crit else 1.0
