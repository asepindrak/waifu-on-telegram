"""
project_vault.py - Isolated Per-Project Memory Vault & Hierarchical Compaction
Manages persistent memory for each workspace project (.waifu/project_memory.json).
Tracks completed tasks, pending to-dos, architectural blueprints, cross-project relations,
and implements 3-tier memory compaction so context is never lost.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

DEFAULT_COMPACT_THRESHOLD_TASKS = 12
DEFAULT_RECENT_TASKS_RETAINED = 6


class ProjectVault:
    """Manages memory, tasks, and state isolation for individual projects."""

    def __init__(self, project_path: str, project_name: str, fallback_dir: Optional[str] = None):
        self.project_path = os.path.abspath(project_path)
        self.project_name = project_name.strip().lower()
        self.waifu_dir = os.path.join(self.project_path, ".waifu")
        self.memory_file = os.path.join(self.waifu_dir, "project_memory.json")
        self.fallback_dir = fallback_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "project_vaults")
        self.fallback_file = os.path.join(self.fallback_dir, f"{self.project_name}_memory.json")
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensures `.waifu` directory exists in project workspace or falls back to data/project_vaults."""
        try:
            os.makedirs(self.waifu_dir, exist_ok=True)
            self._target_file = self.memory_file
        except Exception as e:
            logger.warning(f"Cannot create .waifu in '{self.project_path}': {e}. Using fallback directory.")
            os.makedirs(self.fallback_dir, exist_ok=True)
            self._target_file = self.fallback_file

        if not os.path.exists(self._target_file):
            initial_data = self._create_empty_schema()
            self._write_memory(initial_data)

    def _create_empty_schema(self) -> Dict[str, Any]:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return {
            "version": "1.0.0",
            "project_name": self.project_name,
            "project_path": self.project_path,
            "created_at": now_iso,
            "updated_at": now_iso,
            "architecture": {
                "tech_stack": [],
                "summary": "Belum ada analisis arsitektur.",
                "architecture_doc": "ARCHITECTURE.md",
                "framework": "N/A",
                "database": "N/A"
            },
            "relations": [],  # List of {"target_project": str, "relation_type": str, "description": str}
            "tasks": {
                "completed": [],  # List of {"id": str, "description": str, "completed_at": str, "files": list}
                "pending": []     # List of {"id": str, "description": str, "priority": str, "created_at": str}
            },
            "compacted_milestones": [],  # Summarized historical milestones
            "context_stats": {
                "total_completed": 0,
                "compact_count": 0,
                "last_compact_at": None
            }
        }

    def load_memory(self) -> Dict[str, Any]:
        """Loads project memory JSON safely."""
        target = getattr(self, "_target_file", self.memory_file)
        if not os.path.exists(target):
            if os.path.exists(self.fallback_file):
                target = self.fallback_file
            else:
                return self._create_empty_schema()

        try:
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Ensure essential keys exist
                    data.setdefault("tasks", {"completed": [], "pending": []})
                    data.setdefault("relations", [])
                    data.setdefault("compacted_milestones", [])
                    data.setdefault("architecture", {})
                    data.setdefault("context_stats", {"total_completed": 0, "compact_count": 0, "last_compact_at": None})
                    return data
        except Exception as e:
            logger.error(f"Error loading project memory from '{target}': {e}")

        return self._create_empty_schema()

    def _write_memory(self, data: Dict[str, Any]) -> bool:
        """Saves memory to disk."""
        data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        target = getattr(self, "_target_file", self.memory_file)
        try:
            parent_dir = os.path.dirname(target)
            os.makedirs(parent_dir, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing project memory to '{target}': {e}")
            # Try writing to fallback
            try:
                os.makedirs(self.fallback_dir, exist_ok=True)
                with open(self.fallback_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self._target_file = self.fallback_file
                return True
            except Exception as e2:
                logger.error(f"Fallback write also failed: {e2}")
                return False

    def add_completed_task(
        self,
        description: str,
        files_touched: Optional[List[str]] = None,
        auto_compact: bool = True
    ) -> Dict[str, Any]:
        """Records a completed task, updates stats, and checks for compaction."""
        data = self.load_memory()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        completed_list = data["tasks"].setdefault("completed", [])

        task_id = f"task-{len(completed_list) + 1 + data['context_stats'].get('total_completed', 0)}"
        new_entry = {
            "id": task_id,
            "description": description.strip(),
            "completed_at": now_iso,
            "files": [f.strip() for f in files_touched] if files_touched else []
        }
        completed_list.append(new_entry)
        data["context_stats"]["total_completed"] = data["context_stats"].get("total_completed", 0) + 1

        # Also remove matching task from pending if exists
        desc_lower = description.lower()
        pending = data["tasks"].get("pending", [])
        data["tasks"]["pending"] = [
            p for p in pending
            if p.get("description", "").lower() not in desc_lower and desc_lower not in p.get("description", "").lower()
        ]

        self._write_memory(data)

        if auto_compact and len(completed_list) > DEFAULT_COMPACT_THRESHOLD_TASKS:
            self.compact_memory()

        return new_entry

    def add_pending_task(self, description: str, priority: str = "normal") -> Dict[str, Any]:
        """Adds a new to-do task to project pending list."""
        data = self.load_memory()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        pending_list = data["tasks"].setdefault("pending", [])

        # Avoid exact duplicates
        clean_desc = description.strip()
        for p in pending_list:
            if p.get("description", "").lower() == clean_desc.lower():
                return p

        task_id = f"todo-{len(pending_list) + 1}"
        new_entry = {
            "id": task_id,
            "description": clean_desc,
            "priority": priority.lower(),
            "created_at": now_iso
        }
        pending_list.append(new_entry)
        self._write_memory(data)
        return new_entry

    def remove_pending_task(self, identifier: str) -> bool:
        """Removes a task by ID or partial description match."""
        data = self.load_memory()
        pending_list = data["tasks"].get("pending", [])
        orig_len = len(pending_list)
        ident_lower = identifier.strip().lower()

        filtered = [
            p for p in pending_list
            if p.get("id", "").lower() != ident_lower and ident_lower not in p.get("description", "").lower()
        ]

        if len(filtered) < orig_len:
            data["tasks"]["pending"] = filtered
            self._write_memory(data)
            return True
        return False

    def update_architecture_info(
        self,
        tech_stack: Optional[List[str]] = None,
        summary: Optional[str] = None,
        framework: Optional[str] = None,
        database: Optional[str] = None,
        doc_path: Optional[str] = None
    ):
        """Updates architecture metadata in project memory."""
        data = self.load_memory()
        arch = data.setdefault("architecture", {})
        if tech_stack is not None:
            arch["tech_stack"] = tech_stack
        if summary is not None:
            arch["summary"] = summary
        if framework is not None:
            arch["framework"] = framework
        if database is not None:
            arch["database"] = database
        if doc_path is not None:
            arch["architecture_doc"] = doc_path
        self._write_memory(data)

    def add_relation(self, target_project: str, relation_type: str, description: str = ""):
        """Registers a cross-project dependency or relationship (ERP multi-module support)."""
        data = self.load_memory()
        relations = data.setdefault("relations", [])
        clean_target = target_project.strip().lower()

        # Update if exists, else append
        existing = next((r for r in relations if r.get("target_project", "").lower() == clean_target), None)
        if existing:
            existing["relation_type"] = relation_type
            existing["description"] = description
        else:
            relations.append({
                "target_project": clean_target,
                "relation_type": relation_type,
                "description": description
            })

        self._write_memory(data)

    def compact_memory(
        self,
        retain_recent: int = DEFAULT_RECENT_TASKS_RETAINED,
        force: bool = False
    ) -> Tuple[bool, str]:
        """
        Hierarchical 3-tier memory compaction:
        Tier 1 (Detailed Recent): Keeps the most recent `retain_recent` completed tasks.
        Tier 2 (Summarized Milestones): Old completed tasks are compacted into milestone bullets.
        Tier 3 (Core Blueprint): Architecture and relations are permanent and untouched.
        Memory is never lost!
        """
        data = self.load_memory()
        completed = data["tasks"].get("completed", [])

        if not force and len(completed) <= retain_recent:
            return False, f"Jumlah task ({len(completed)}) masih di bawah ambang batas ({retain_recent})."

        # Split into tasks to archive and tasks to retain
        to_compact = completed[:-retain_recent] if len(completed) > retain_recent else completed
        retained = completed[-retain_recent:] if len(completed) > retain_recent else []

        if not to_compact:
            return False, "Tidak ada task yang perlu dipadatkan."

        # Group and create milestone bullet summary
        date_start = to_compact[0].get("completed_at", "").split("T")[0]
        date_end = to_compact[-1].get("completed_at", "").split("T")[0]
        date_span = f"{date_start} s/d {date_end}" if date_start != date_end else date_start

        descriptions = [t.get("description", "") for t in to_compact if t.get("description")]
        compact_summary = (
            f"Milestone ({date_span} • {len(to_compact)} tasks): " +
            "; ".join(descriptions[:5]) +
            (f" ... (+{len(descriptions) - 5} lainnya)" if len(descriptions) > 5 else "")
        )

        milestones = data.setdefault("compacted_milestones", [])
        milestones.append(compact_summary)

        data["tasks"]["completed"] = retained
        data["context_stats"]["compact_count"] = data["context_stats"].get("compact_count", 0) + 1
        data["context_stats"]["last_compact_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        self._write_memory(data)
        logger.info(f"Project '{self.project_name}' memory compacted. {len(to_compact)} tasks compressed into milestone.")
        return True, compact_summary

    def get_prompt_context(self, max_chars: int = 15000) -> str:
        """
        Formats project memory into an enriched context string for LLM injection.
        Includes architecture blueprint summary, cross-project relations, completed milestones,
        recent tasks, and pending to-dos.
        """
        data = self.load_memory()
        arch = data.get("architecture", {})
        relations = data.get("relations", [])
        milestones = data.get("compacted_milestones", [])
        completed = data.get("tasks", {}).get("completed", [])
        pending = data.get("tasks", {}).get("pending", [])

        lines = [
            f"=== [PROJECT CONTEXT: {self.project_name.upper()}] ===",
            f"• Workspace Directory: {self.project_path}",
            f"• Framework / Language: {arch.get('framework', 'N/A')} ({', '.join(arch.get('tech_stack', [])) or 'General'})",
            f"• Database / Storage: {arch.get('database', 'N/A')}",
            f"• Architecture Overview: {arch.get('summary', 'Lihat ARCHITECTURE.md untuk detail.')}"
        ]

        if relations:
            lines.append("\n[CROSS-PROJECT RELATIONS & ERP DEPENDENCIES]:")
            for r in relations:
                lines.append(f"  - Modul '{r.get('target_project')}': {r.get('relation_type')} ({r.get('description') or 'No note'})")

        if milestones:
            lines.append("\n[HISTORICAL COMPACTED MILESTONES]:")
            for m in milestones[-4:]:  # Show last 4 milestones
                lines.append(f"  ✓ {m}")

        if completed:
            lines.append("\n[RECENTLY COMPLETED TASKS]:")
            for t in completed[-6:]:
                files_str = f" [Files: {', '.join(t.get('files', []))}]" if t.get("files") else ""
                lines.append(f"  ✓ {t.get('description')}{files_str}")

        if pending:
            lines.append("\n[PENDING TASKS & TO-DO LIST]:")
            for p in pending:
                prio_mark = "🔥 [HIGH]" if p.get("priority") == "high" else "📌"
                lines.append(f"  {prio_mark} {p.get('description')}")
        else:
            lines.append("\n[PENDING TASKS]: Tidak ada tugas tertunda (Semua beres!).")

        lines.append("=========================================\n")
        full_text = "\n".join(lines)
        if len(full_text) > max_chars:
            return full_text[:max_chars] + "\n... [Context Truncated for Safety]"
        return full_text


_VAULT_CACHE: Dict[str, ProjectVault] = {}


def get_project_vault(project_path: str, project_name: str) -> ProjectVault:
    """Singleton getter for ProjectVault instances by project path/name."""
    key = f"{project_name}:{os.path.abspath(project_path)}"
    if key not in _VAULT_CACHE:
        _VAULT_CACHE[key] = ProjectVault(project_path=project_path, project_name=project_name)
    return _VAULT_CACHE[key]
