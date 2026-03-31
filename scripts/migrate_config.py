from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from novel_generator.config.config_manager import ConfigManager
from novel_generator.config.generation_config import DEFAULT_CONFIG
from novel_generator.config.session import SessionState


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _merge_generation(source: Dict[str, Any]) -> Dict[str, Any]:
    merged = {
        "version": source.get("version", DEFAULT_CONFIG.get("version", "1.0")),
        "generation": dict(DEFAULT_CONFIG.get("generation", {})),
        "roles": dict(DEFAULT_CONFIG.get("roles", {})),
        "providers": dict(DEFAULT_CONFIG.get("providers", {})),
        "quality_check": dict(DEFAULT_CONFIG.get("quality_check", {})),
    }
    merged["generation"].update(source.get("generation", {}))
    merged["roles"].update(source.get("roles", {}))
    merged["providers"].update(source.get("providers", {}))
    merged["quality_check"].update(source.get("quality_check", {}))
    return merged


def _merge_session(source: Dict[str, Any], generation: Dict[str, Any]) -> Dict[str, Any]:
    state = SessionState.from_dict(source)
    gen_cfg = generation.get("generation", {})
    roles = generation.get("roles", {})

    state.generation_config.batch_size = gen_cfg.get(
        "batch_size", state.generation_config.batch_size
    )
    state.generation_config.context_chapters = gen_cfg.get(
        "context_chapters", state.generation_config.context_chapters
    )
    state.generation_config.default_word_count = gen_cfg.get(
        "default_word_count", state.generation_config.default_word_count
    )
    if roles:
        state.ai_roles = state.ai_roles.from_dict(roles)
    return state.to_dict()


def migrate(
    project_root: Path,
    session_path: Path,
    generation_path: Path,
    dry_run: bool,
    write: bool,
) -> int:
    if not session_path.exists():
        raise FileNotFoundError(f"session file not found: {session_path}")
    if not generation_path.exists():
        raise FileNotFoundError(f"generation file not found: {generation_path}")

    session_data = _load_json(session_path)
    generation_data = _load_json(generation_path)

    merged_generation = _merge_generation(generation_data)
    merged_session = _merge_session(session_data, merged_generation)

    if dry_run:
        print("[dry-run] migration preview")
        print(
            json.dumps(
                {
                    "generation": {
                        "generation": merged_generation.get("generation", {}),
                        "roles": merged_generation.get("roles", {}),
                    },
                    "session": {
                        "api_config": merged_session.get("api_config", {}),
                        "generation_config": merged_session.get("generation_config", {}),
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    if write:
        _write_json(generation_path, merged_generation)
        _write_json(session_path, merged_session)
        manager = ConfigManager(str(project_root))
        manager.load()
        if not manager.save():
            raise RuntimeError("save through ConfigManager failed")
        print(f"migration completed: {generation_path} and {session_path}")
    else:
        print("no files written; use --write to persist")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=str, default=".")
    parser.add_argument("--session", type=str, default="05_script/session.json")
    parser.add_argument("--generation", type=str, default="05_script/generation_config.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    session_path = project_root / args.session
    generation_path = project_root / args.generation

    return migrate(
        project_root=project_root,
        session_path=session_path,
        generation_path=generation_path,
        dry_run=args.dry_run,
        write=args.write,
    )


if __name__ == "__main__":
    raise SystemExit(main())
