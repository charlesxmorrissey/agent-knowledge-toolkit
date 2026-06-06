"""Initialize a personal knowledge base and record it in config."""
from pathlib import Path

from akt import config
from akt.index import write_index

_AGENTS_SEED = "# Global Rules\n\nGraduated patterns (personal, cross-repo). Generated entries carry provenance.\n"


def init_kb(kb_path, config_path=None):
    kb = Path(kb_path)
    (kb / "stories").mkdir(parents=True, exist_ok=True)
    agents = kb / "AGENTS.md"
    if not agents.exists():
        agents.write_text(_AGENTS_SEED)
    if not (kb / "INDEX.md").exists():
        write_index(kb, [])
    config.set_value("knowledge_base_path", str(kb), config_path)
    config.set_value("install_mode", "minimal", config_path)
    return kb
