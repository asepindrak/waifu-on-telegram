"""
architecture_generator.py - Automated Project Architecture Blueprint Generator
Inspects workspace directory manifests, code structures, and dependencies,
and generates or updates a standardized ARCHITECTURE.md blueprint.
Syncs high-level architecture insights into the project's memory vault.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

from project_vault import get_project_vault

logger = logging.getLogger(__name__)


class ArchitectureGenerator:
    """Scans project repository, deduces architecture, and generates ARCHITECTURE.md."""

    def __init__(self, workspace_path: str, project_name: str):
        self.workspace_path = os.path.abspath(workspace_path)
        self.project_name = project_name.strip().lower()
        self.arch_file = os.path.join(self.workspace_path, "ARCHITECTURE.md")
        self.vault = get_project_vault(self.workspace_path, self.project_name)

    def scan_and_generate(self, force_overwrite: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Inspects workspace, creates or updates ARCHITECTURE.md,
        and synchronizes metadata with project_vault.
        """
        if not os.path.isdir(self.workspace_path):
            return False, f"Direktori workspace '{self.workspace_path}' tidak ditemukan.", {}

        analysis = self.analyze_workspace()

        # If ARCHITECTURE.md already exists and force_overwrite is False, read and enhance
        if os.path.exists(self.arch_file) and not force_overwrite:
            try:
                with open(self.arch_file, "r", encoding="utf-8") as f:
                    content = f.read()
                # Update vault from existing doc if analysis is sparse
                self._sync_vault(analysis, content)
                return True, self.arch_file, analysis
            except Exception as e:
                logger.warning(f"Error reading existing ARCHITECTURE.md: {e}")

        # Generate new markdown content
        doc_content = self._render_architecture_markdown(analysis)

        try:
            with open(self.arch_file, "w", encoding="utf-8") as f:
                f.write(doc_content)
            self._sync_vault(analysis, doc_content)
            return True, self.arch_file, analysis
        except Exception as e:
            logger.error(f"Failed to write ARCHITECTURE.md: {e}")
            return False, str(e), analysis

    def analyze_workspace(self) -> Dict[str, Any]:
        """Examines files, package definitions, dependencies, and directory structures."""
        analysis: Dict[str, Any] = {
            "project_name": self.project_name,
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
            "entry_points": [],
            "directory_structure": [],
            "summary": "Project workspace umum."
        }

        # 1. Inspect manifest files
        manifest_checks = {
            "package.json": self._inspect_node,
            "requirements.txt": self._inspect_python_reqs,
            "pyproject.toml": self._inspect_pyproject,
            "go.mod": self._inspect_go,
            "Cargo.toml": self._inspect_rust,
            "composer.json": self._inspect_php,
            "pom.xml": self._inspect_java_maven,
            "docker-compose.yml": self._inspect_docker_compose,
            "Dockerfile": lambda p, a: a["tools"].append("Docker")
        }

        for fname, handler in manifest_checks.items():
            fpath = os.path.join(self.workspace_path, fname)
            if os.path.exists(fpath):
                try:
                    handler(fpath, analysis)
                except Exception as e:
                    logger.debug(f"Manifest inspection error on {fname}: {e}")

        # 2. Inspect root directory layout
        top_dirs = []
        try:
            for item in os.listdir(self.workspace_path):
                if item.startswith((".", "node_modules", "venv", "__pycache__", "dist", "build")):
                    continue
                full_item = os.path.join(self.workspace_path, item)
                if os.path.isdir(full_item):
                    top_dirs.append(item)
                elif item.endswith((".py", ".js", ".ts", ".go", ".rs", ".php", ".java", ".html")):
                    analysis["entry_points"].append(item)
        except Exception:
            pass

        analysis["directory_structure"] = sorted(top_dirs)

        # Remove duplicates
        for key in ["languages", "frameworks", "databases", "tools"]:
            analysis[key] = sorted(list(set(analysis[key])))

        # Compose summary
        fw_str = ", ".join(analysis["frameworks"]) or "Custom / Scripting"
        lang_str = ", ".join(analysis["languages"]) or "Multi-language"
        db_str = f" dengan storage {', '.join(analysis['databases'])}" if analysis["databases"] else ""
        analysis["summary"] = f"Aplikasi {lang_str} berbasis framework {fw_str}{db_str}."

        return analysis

    def _inspect_node(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("JavaScript/TypeScript")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                pj = json.load(f)
            deps = {**pj.get("dependencies", {}), **pj.get("devDependencies", {})}

            if "typescript" in deps:
                analysis["languages"].append("TypeScript")
            if "next" in deps:
                analysis["frameworks"].append("Next.js")
            if "react" in deps:
                analysis["frameworks"].append("React")
            if "vue" in deps or "nuxt" in deps:
                analysis["frameworks"].append("Vue/Nuxt")
            if "@nestjs/core" in deps:
                analysis["frameworks"].append("NestJS")
            elif "express" in deps:
                analysis["frameworks"].append("Express")
            elif "fastify" in deps:
                analysis["frameworks"].append("Fastify")

            if "prisma" in deps or "@prisma/client" in deps:
                analysis["databases"].append("Prisma ORM")
            if "typeorm" in deps:
                analysis["databases"].append("TypeORM")
            if "drizzle-orm" in deps:
                analysis["databases"].append("Drizzle ORM")
            if "mongoose" in deps:
                analysis["databases"].append("MongoDB")
            if "pg" in deps or "postgres" in deps:
                analysis["databases"].append("PostgreSQL")
            if "mysql2" in deps or "mysql" in deps:
                analysis["databases"].append("MySQL")
            if "ioredis" in deps or "redis" in deps:
                analysis["databases"].append("Redis")
        except Exception:
            pass

    def _inspect_python_reqs(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("Python")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            self._parse_python_deps(content, analysis)
        except Exception:
            pass

    def _inspect_pyproject(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("Python")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            self._parse_python_deps(content, analysis)
        except Exception:
            pass

    def _parse_python_deps(self, text: str, analysis: Dict[str, Any]):
        if "fastapi" in text:
            analysis["frameworks"].append("FastAPI")
        elif "django" in text:
            analysis["frameworks"].append("Django")
        elif "flask" in text:
            analysis["frameworks"].append("Flask")

        if "sqlalchemy" in text:
            analysis["databases"].append("SQLAlchemy")
        if "alembic" in text:
            analysis["tools"].append("Alembic")
        if "psycopg" in text or "asyncpg" in text:
            analysis["databases"].append("PostgreSQL")
        if "pymongo" in text:
            analysis["databases"].append("MongoDB")
        if "redis" in text:
            analysis["databases"].append("Redis")
        if "pytest" in text:
            analysis["tools"].append("Pytest")

    def _inspect_go(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("Go")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().lower()
            if "gin-gonic/gin" in text:
                analysis["frameworks"].append("Gin")
            elif "gofiber/fiber" in text:
                analysis["frameworks"].append("Fiber")
            if "gorm.io/gorm" in text:
                analysis["databases"].append("GORM")
        except Exception:
            pass

    def _inspect_rust(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("Rust")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().lower()
            if "actix-web" in text:
                analysis["frameworks"].append("Actix Web")
            elif "axum" in text:
                analysis["frameworks"].append("Axum")
            if "tokio" in text:
                analysis["tools"].append("Tokio Async")
        except Exception:
            pass

    def _inspect_php(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("PHP")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().lower()
            if "laravel" in text:
                analysis["frameworks"].append("Laravel")
        except Exception:
            pass

    def _inspect_java_maven(self, fpath: str, analysis: Dict[str, Any]):
        analysis["languages"].append("Java")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().lower()
            if "spring-boot" in text:
                analysis["frameworks"].append("Spring Boot")
        except Exception:
            pass

    def _inspect_docker_compose(self, fpath: str, analysis: Dict[str, Any]):
        analysis["tools"].append("Docker Compose")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read().lower()
            if "postgres" in text and "PostgreSQL" not in analysis["databases"]:
                analysis["databases"].append("PostgreSQL (Container)")
            if "mysql" in text and "MySQL" not in analysis["databases"]:
                analysis["databases"].append("MySQL (Container)")
            if "redis" in text and "Redis" not in analysis["databases"]:
                analysis["databases"].append("Redis (Container)")
        except Exception:
            pass

    def _render_architecture_markdown(self, analysis: Dict[str, Any]) -> str:
        """Renders comprehensive Markdown file with architecture guidelines and mermaid diagram."""
        tech_list = []
        if analysis["languages"]:
            tech_list.append(f"• **Language(s)**: {', '.join(analysis['languages'])}")
        if analysis["frameworks"]:
            tech_list.append(f"• **Framework(s)**: {', '.join(analysis['frameworks'])}")
        if analysis["databases"]:
            tech_list.append(f"• **Database / Storage**: {', '.join(analysis['databases'])}")
        if analysis["tools"]:
            tech_list.append(f"• **DevOps & Tools**: {', '.join(analysis['tools'])}")

        tech_block = "\n".join(tech_list) if tech_list else "• Tech stack belum terdefinisi secara spesifik."

        dir_block = "\n".join([f"├── {d}/" for d in analysis["directory_structure"][:15]]) or "├── (Root flat structure)"

        # Mermaid flow diagram
        fw_label = analysis["frameworks"][0] if analysis["frameworks"] else "Application Core"
        db_label = analysis["databases"][0] if analysis["databases"] else "Data Storage"

        mermaid_diag = (
            "```mermaid\n"
            "flowchart TD\n"
            "    Client[\"Client / External Request\"] --> Gateway[\"API Gateway / Entrypoint\"]\n"
            f"    Gateway --> Core[\"{fw_label}\"]\n"
            f"    Core --> DB[(\"{db_label}\")]\n"
            "    Core -. Cross Relations .-> OtherServices[\"ERP / Microservice Modules\"]\n"
            "```\n"
        )

        return (
            f"# Architecture Blueprint: {self.project_name.upper()}\n\n"
            f"> Auto-generated by Waifu Project Architecture Engine.\n"
            f"> Source of truth for code structure, architectural patterns, and module dependencies.\n\n"
            f"## 1. Executive Summary\n"
            f"{analysis['summary']}\n\n"
            f"## 2. Technology Stack\n"
            f"{tech_block}\n\n"
            f"## 3. Directory Layout\n"
            f"```text\n"
            f"{self.workspace_path}\n"
            f"{dir_block}\n"
            f"```\n\n"
            f"## 4. Architectural Diagram\n"
            f"{mermaid_diag}\n"
            f"## 5. Module & Cross-Project Dependencies\n"
            f"Project ini beroperasi dalam ekosistem multi-project. Setiap integrasi dengan servis lain "
            f"(misalnya autentikasi, database terdistribusi, atau reporting) didokumentasikan di sini dan "
            f"disinkronkan dengan memory vault `.waifu/project_memory.json`.\n\n"
            f"## 6. Coding & Quality Standards\n"
            f"1. **Clean Code & Modularity**: Setiap fungsi harus memiliki tanggung jawab tunggal (SRP).\n"
            f"2. **Documentation**: Perubahan endpoint atau schema harus memperbarui file ini.\n"
            f"3. **Zero-Regression**: Selalu verifikasi kompatibilitas dengan service yang bergantung pada project ini.\n"
        )

    def _sync_vault(self, analysis: Dict[str, Any], doc_content: str):
        """Syncs key findings into .waifu/project_memory.json."""
        tech_all = analysis["languages"] + analysis["frameworks"] + analysis["databases"]
        fw = analysis["frameworks"][0] if analysis["frameworks"] else (analysis["languages"][0] if analysis["languages"] else "N/A")
        db = ", ".join(analysis["databases"]) or "N/A"

        self.vault.update_architecture_info(
            tech_stack=tech_all,
            summary=analysis["summary"],
            framework=fw,
            database=db,
            doc_path="ARCHITECTURE.md"
        )


def ensure_project_architecture(workspace_path: str, project_name: str, force: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    """Helper to inspect project workspace and ensure ARCHITECTURE.md and memory are in sync."""
    gen = ArchitectureGenerator(workspace_path=workspace_path, project_name=project_name)
    return gen.scan_and_generate(force_overwrite=force)

