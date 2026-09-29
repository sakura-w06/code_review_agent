import hashlib
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class ReviewState:
    messages: List[Dict] = field(default_factory=list)
    code_snapshot: str = ""
    code_hash: str = ""
    findings: List[Dict] = field(default_factory=list)

    def update_code(self, code: str):
        new_hash = hashlib.md5(code.encode()).hexdigest()
        if new_hash != self.code_hash:
            self.code_hash = new_hash
            self.code_snapshot = code
            self.findings = []
            self.messages = []
        return new_hash


def trim_messages(messages: List[Dict], max_recent: int = 6) -> List[Dict]:
    if len(messages) <= max_recent + 2:
        return messages
    anchors = messages[:2]
    recent = messages[-max_recent:]
    if recent and recent[0].get("role") == "tool":
        recent = messages[-(max_recent + 1):]
    return anchors + recent


class MemoryStore:
    def __init__(self):
        self.preferences: Dict[str, List[str]] = {}

    def add_preference(self, user_id: str, rule: str):
        self.preferences.setdefault(user_id, []).append(rule)

    def get_preferences_text(self, user_id: str) -> str:
        prefs = self.preferences.get(user_id, [])
        if not prefs:
            return ""
        return "\n".join(f"- {p}" for p in prefs)