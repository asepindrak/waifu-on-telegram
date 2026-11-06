"""
project_intent_router.py - Conversational Project Intent Router & God-View Coordinator
Enables zero-command conversational switching, natural project creation,
task management (done/todo), cross-project relations (ERP multi-module),
executive multi-project overview (God View), and background server execution with Tailscale port opening.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any

from project_manager import get_project_manager, ProjectManager
from project_vault import get_project_vault, ProjectVault
from architecture_generator import ensure_project_architecture
from project_runner import get_project_runner, ProjectRunner

logger = logging.getLogger(__name__)


class ProjectIntentResult:
    """Encapsulates the detected intent and associated parameters."""

    def __init__(
        self,
        intent_type: str,
        target_project: Optional[str] = None,
        extracted_task: Optional[str] = None,
        relation_target: Optional[str] = None,
        relation_type: Optional[str] = None,
        custom_port: Optional[int] = None,
        cleaned_text: Optional[str] = None
    ):
        self.intent_type = intent_type  # SWITCH, CREATE, GOD_VIEW, STATUS, ADD_TODO, MARK_DONE, ADD_RELATION, RUN_PROJECT, STOP_PROJECT, SERVER_STATUS, SERVER_LOGS, NONE
        self.target_project = target_project
        self.extracted_task = extracted_task
        self.relation_target = relation_target
        self.relation_type = relation_type
        self.custom_port = custom_port
        self.cleaned_text = cleaned_text or ""

    def __repr__(self):
        return f"<ProjectIntentResult intent={self.intent_type} target={self.target_project} port={self.custom_port}>"


class ProjectIntentRouter:
    """Analyzes user messages for natural project interactions without requiring slash commands."""

    def __init__(self, project_manager: Optional[ProjectManager] = None):
        self.pm = project_manager or get_project_manager()

    def route_intent(self, message: str, user_id: int) -> ProjectIntentResult:
        """
        Parses user message and determines if it intends to switch project,
        spawn a new one, view God-View, manage memory/tasks, or run with Tailscale port.
        """
        raw_text = message.strip()
        lower = raw_text.lower()
        active_proj = self.pm.get_active_project(user_id)
        projs = self.pm.list_projects()

        # 1. Check Server Logs
        if re.search(r'\b(log\s+(?:server|project)|lihat\s+log|cek\s+log)\b', lower):
            return ProjectIntentResult(intent_type="SERVER_LOGS", target_project=active_proj)

        # 2. Check Server Status / Open Ports
        if re.search(r'\b(status\s+server|cek\s+server|server\s+apa\s+aja|port\s+yang\s+(?:lagi\s+)?kebuka|list\s+server)\b', lower):
            return ProjectIntentResult(intent_type="SERVER_STATUS")

        # 3. Check Stop Project / Server
        stop_pattern = r'\b(stop\s+(?:project|server|app)|matikan\s+(?:project|server|aplikasi)|hentikan\s+(?:project|server|app)|kill\s+server|close\s+port|tutup\s+port)\b'
        if re.search(stop_pattern, lower):
            target_p = None
            for p_name in projs.keys():
                if p_name != "general" and re.search(r'\b' + re.escape(p_name) + r'\b', lower):
                    target_p = p_name
                    break
            return ProjectIntentResult(intent_type="STOP_PROJECT", target_project=target_p or active_proj)

        # 4. Check Run Project / Open Port (Tailscale dev server)
        # e.g.: "run project", "jalankan project", "buka port", "start server", "running project di port 5000"
        run_pattern = r'\b(run\s+(?:project|server|app)|jalankan\s+(?:project|server|aplikasi)|start\s+(?:project|server|app)|buka\s+port|open\s+port|running\s+project|serve\s+project)\b'
        if re.search(run_pattern, lower):
            # Extract port if specified
            port_match = re.search(r'\b(?:port|ke\s+port)\s+(\d+)\b', lower)
            custom_port = int(port_match.group(1)) if port_match else None
            # Check if user mentioned another specific project
            target_p = None
            for p_name in projs.keys():
                if p_name != "general" and re.search(r'\b' + re.escape(p_name) + r'\b', lower):
                    target_p = p_name
                    break
            return ProjectIntentResult(
                intent_type="RUN_PROJECT",
                target_project=target_p or active_proj,
                custom_port=custom_port
            )

        # 5. Check God View / Overview of all projects
        god_view_patterns = [
            r'\b(god\s*view|peta\s*dewa)\b',
            r'\b(semua\s*project|seluruh\s*project|list\s*project|daftar\s*project)\b',
            r'\b(project\s*apa\s*aja|ada\s*project\s*apa|sedang\s*ngerjain\s*project\s*apa)\b',
            r'\b(status\s*semua\s*project|rekap\s*project|overview\s*project)\b'
        ]
        for pat in god_view_patterns:
            if re.search(pat, lower):
                return ProjectIntentResult(intent_type="GOD_VIEW")

        # 6. Check Project Status / Memory of active project
        status_patterns = [
            r'\b(status\s*project(\s*ini)?|progres\s*project(\s*ini)?)\b',
            r'\b(ingatan\s*project|memory\s*project|catatan\s*project)\b',
            r'\b(apa\s*aja\s*yang\s*(sudah|udah)\s*dikerjakan)\b',
            r'\b(to\s*do\s*project|rencana\s*project|list\s*tugas\s*project)\b'
        ]
        for pat in status_patterns:
            if re.search(pat, lower):
                return ProjectIntentResult(intent_type="STATUS", target_project=active_proj)

        # 7. Check Cross-Project Relation (ERP Dependencies)
        rel_pattern = r'\b(?:project|modul)\s+([a-zA-Z0-9_\-]+)\s+(?:ada\s+relasi\s+ke|butuh\s+api\s+dari|konek\s+ke|bergantung\s+pada)\s+([a-zA-Z0-9_\-]+)\b'
        m_rel = re.search(rel_pattern, lower)
        if m_rel:
            source_p = m_rel.group(1).strip()
            target_p = m_rel.group(2).strip()
            return ProjectIntentResult(
                intent_type="ADD_RELATION",
                target_project=source_p,
                relation_target=target_p,
                relation_type="dependency"
            )

        # 8. Check Add To-Do / Pending Task
        todo_pattern = r'\b(?:catat\s+to\s*do|tambah\s+to\s*do|tambah\s+task|nanti\s+tolong)\s*[:\-]?\s*(.+)$'
        m_todo = re.search(todo_pattern, raw_text, re.IGNORECASE)
        if m_todo:
            task_desc = m_todo.group(1).strip()
            return ProjectIntentResult(intent_type="ADD_TODO", target_project=active_proj, extracted_task=task_desc)

        # 9. Check Mark Task Done
        done_pattern = r'\b(?:tandai\s+selesai|task\s+(?:sudah|udah)\s+selesai|selesai\s+ngerjain)\s*[:\-]?\s*(.+)$'
        m_done = re.search(done_pattern, raw_text, re.IGNORECASE)
        if m_done:
            task_desc = m_done.group(1).strip()
            return ProjectIntentResult(intent_type="MARK_DONE", target_project=active_proj, extracted_task=task_desc)

        # 10. Check Create New Project
        create_pattern = r'\b(?:buat|bikin|spawn|create)\s+project\s+(?:baru\s+)?([a-zA-Z0-9_\-]+)'
        m_create = re.search(create_pattern, lower)
        if m_create:
            proj_name = m_create.group(1).strip()
            if proj_name not in ["baru", "ini", "itu", "dong"]:
                return ProjectIntentResult(intent_type="CREATE", target_project=proj_name)

        # 11. Check Switch Project (Explicit switch phrasing)
        switch_pattern = r'\b(?:switch\s+(?:ke\s+)?(?:project\s+)?|pindah\s+(?:ke\s+)?(?:project\s+)?|buka\s+project\s+|fokus\s+(?:ke\s+)?(?:project\s+)?|kerjain\s+project\s+)([a-zA-Z0-9_\-]+)'
        m_switch = re.search(switch_pattern, lower)
        if m_switch:
            candidate = m_switch.group(1).strip()
            matched = self._match_project_name(candidate, projs)
            if matched:
                return ProjectIntentResult(intent_type="SWITCH", target_project=matched)

        # 12. Check Contextual Mention in Coding Request
        context_pattern = r'\bdi\s+project\s+([a-zA-Z0-9_\-]+)\b'
        m_ctx = re.search(context_pattern, lower)
        if m_ctx:
            candidate = m_ctx.group(1).strip()
            matched = self._match_project_name(candidate, projs)
            if matched and matched != active_proj:
                return ProjectIntentResult(intent_type="SWITCH", target_project=matched)

        # Check exact existing project name when discussing coding tasks
        for p_name in projs.keys():
            if p_name != "general" and p_name != active_proj:
                if re.search(r'\b' + re.escape(p_name) + r'\b', lower):
                    if any(w in lower for w in ["update", "cek", "bikin", "fix", "tambah", "kerjain", "buka", "edit"]):
                        return ProjectIntentResult(intent_type="SWITCH", target_project=p_name)

        return ProjectIntentResult(intent_type="NONE")

    def _match_project_name(self, candidate: str, projs: Dict[str, str]) -> Optional[str]:
        """Fuzzy matches candidate against registered projects."""
        clean = candidate.lower().replace(" ", "-")
        if clean in projs:
            return clean

        for k in projs.keys():
            if k.lower() == clean or k.lower().replace("-", "") == clean.replace("-", ""):
                return k

        if len(clean) >= 3:
            for k in projs.keys():
                if clean in k.lower() or k.lower() in clean:
                    return k
        return None

    def handle_project_intent(
        self,
        intent: ProjectIntentResult,
        user_id: int,
        persona_name: str = "Akira"
    ) -> Tuple[bool, str]:
        """
        Executes the required project operation (switch, create, update, query, or run/stop server).
        Returns: (handled_successfully, formatted_response_message)
        """
        runner = get_project_runner()

        if intent.intent_type == "RUN_PROJECT":
            target_p = intent.target_project or self.pm.get_active_project(user_id)
            projs = self.pm.list_projects()
            p_path = projs.get(target_p, self.pm.get_active_project_path(user_id))

            res = runner.start_project(
                project_name=target_p,
                project_path=p_path,
                custom_port=intent.custom_port
            )
            if not res.get("success"):
                return False, f"⚠️ Gagal menjalankan project `{target_p}`: {res.get('error')}"

            entry = res["entry"]
            port = entry["port"]
            ts_url = entry.get("tailscale_url")
            magic_url = entry.get("magic_dns_url")
            https_url = entry.get("https_serve_url")
            local_url = entry.get("local_url")
            peers = entry.get("peer_devices", [])
            peers_str = ", ".join([f"`{p}`" for p in peers]) if peers else "Perangkat di akun Tailscale kamu"

            lines = [
                f"🚀 **Project `{target_p}` Berhasil Dijalankan!** ✨",
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"📂 **Workspace:** `{p_path}`",
                f"⚡ **Command:** `{entry['command']}`",
                f"🔌 **Port Aktif:** `{port}` (PID: `{entry['pid']}`)",
                f"📡 **Status Tailscale:** 🟢 Online ({entry.get('tailscale_ip') or 'Terhubung'})\n",
                f"🌐 **AKSES TAILSCALE (HP & Perangkat Lain):**"
            ]
            if ts_url:
                lines.append(f"👉 **IP URL:** {ts_url}")
            if magic_url:
                lines.append(f"👉 **MagicDNS:** {magic_url}")
            if https_url:
                lines.append(f"🔒 **HTTPS Serve:** {https_url}")
            lines.append(f"💻 **Lokal:** {local_url}\n")

            lines.append(f"📱 **Siap dibuka dari perangkatmu:** {peers_str}")
            lines.append(f"💡 *Pastikan HP / perangkat lain sudah terhubung ke aplikasi Tailscale yaa!*")
            lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"Ketik _'stop server'_ jika mau mematikan project ini.")
            return True, "\n".join(lines)

        elif intent.intent_type == "STOP_PROJECT":
            target_p = intent.target_project or self.pm.get_active_project(user_id)
            ok, stop_msg = runner.stop_project(target_p)
            return ok, f"🛑 {stop_msg}"

        elif intent.intent_type == "SERVER_STATUS":
            active_servers = runner.list_running()
            if not active_servers:
                return True, (
                    "ℹ️ Saat ini belum ada server project yang aktif di background.\n\n"
                    "💡 Ketik *'run project'* atau *'buka port'* untuk menjalankan project dan membukanya di Tailscale! 🚀"
                )

            lines = [
                f"🖥️ **Daftar Server Project yang Sedang Aktif**",
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]
            for name, srv in active_servers.items():
                lines.append(f"🟢 **`{name}`** (Port: `{srv['port']}` • PID: `{srv['pid']}`)")
                lines.append(f"   📂 `{srv['project_path']}`")
                lines.append(f"   🌐 Tailscale: {srv.get('tailscale_url') or 'N/A'}")
                lines.append(f"   📱 MagicDNS : {srv.get('magic_dns_url') or 'N/A'}")
                lines.append(f"   💻 Local    : {srv.get('local_url')}")
                lines.append("")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("Ketik _'stop server'_ untuk menghentikan server.")
            return True, "\n".join(lines)

        elif intent.intent_type == "SERVER_LOGS":
            target_p = intent.target_project or self.pm.get_active_project(user_id)
            logs = runner.get_server_logs(target_p, lines=25)
            msg = (
                f"📄 **Log Server: `{target_p}`**\n"
                f"```text\n{logs}\n```"
            )
            return True, msg

        elif intent.intent_type == "GOD_VIEW":
            return True, self.render_god_view(user_id=user_id, persona_name=persona_name)

        elif intent.intent_type == "STATUS":
            active_p = intent.target_project or self.pm.get_active_project(user_id)
            p_path = self.pm.get_active_project_path(user_id)
            vault = get_project_vault(p_path, active_p)
            ensure_project_architecture(p_path, active_p)
            return True, self.render_project_status(vault, persona_name=persona_name)

        elif intent.intent_type == "SWITCH":
            target_p = intent.target_project
            if not target_p:
                return False, "Project target tidak spesifik."

            ok, p_path = self.pm.set_active_project(user_id, target_p)
            if not ok:
                return False, f"⚠️ Gagal berpindah: {p_path}"

            ensure_project_architecture(p_path, target_p)
            vault = get_project_vault(p_path, target_p)
            mem = vault.load_memory()

            completed_cnt = len(mem.get("tasks", {}).get("completed", []))
            pending_cnt = len(mem.get("tasks", {}).get("pending", []))
            arch = mem.get("architecture", {})
            fw = arch.get("framework", "General")

            msg = (
                f"🔀 **Fokus Workspace Dialihkan ke `{target_p}`!** 💼✨\n\n"
                f"📁 **Path:** `{p_path}`\n"
                f"🛠️ **Stack / Framework:** {fw}\n"
                f"📋 **Memory Progres:** {completed_cnt} task selesai • {pending_cnt} to-do tertunda.\n\n"
                f"Ingatan dan blueprint arsitektur project ini sudah aktif. Mau kita kerjakan apa sekarang, sayang? 🥰"
            )
            return True, msg

        elif intent.intent_type == "CREATE":
            target_p = intent.target_project
            if not target_p:
                return False, "Nama project tidak boleh kosong."

            ok, clean_name, p_path = self.pm.spawn_project(name=target_p, switch_user_id=user_id)
            if not ok:
                return False, f"⚠️ Gagal membuat project: {p_path}"

            ensure_project_architecture(p_path, clean_name, force=True)
            vault = get_project_vault(p_path, clean_name)
            vault.add_completed_task(f"Inisialisasi workspace dan pembuatan ARCHITECTURE.md untuk project {clean_name}")

            msg = (
                f"🌱 **Project Baru `{clean_name}` Berhasil Dibuat!** 🎉🚀\n\n"
                f"📁 **Workspace:** `{p_path}`\n"
                f"📄 **Blueprint:** `ARCHITECTURE.md` otomatis diinisialisasi.\n"
                f"🧠 **Vault:** `.waifu/project_memory.json` siap menyimpan riwayat pekerjaan.\n\n"
                f"Fokus kita sudah otomatis dialihkan ke project ini. Ada modul atau file awal yang mau kita bikin sekarang? 💕"
            )
            return True, msg

        elif intent.intent_type == "ADD_TODO":
            active_p = self.pm.get_active_project(user_id)
            p_path = self.pm.get_active_project_path(user_id)
            vault = get_project_vault(p_path, active_p)
            entry = vault.add_pending_task(intent.extracted_task or "Tugas baru")
            msg = (
                f"📌 **To-Do Berhasil Dicatat di Project `{active_p}`!** ✨\n\n"
                f"• Task: *{entry['description']}*\n"
                f"• ID: `{entry['id']}`\n\n"
                f"Aku simpan di ingatan project ya, nanti pas senggang tinggal bilang aja untuk kerjain! 🥰"
            )
            return True, msg

        elif intent.intent_type == "MARK_DONE":
            active_p = self.pm.get_active_project(user_id)
            p_path = self.pm.get_active_project_path(user_id)
            vault = get_project_vault(p_path, active_p)
            entry = vault.add_completed_task(intent.extracted_task or "Task selesai")
            msg = (
                f"🎉 **Hebat! Task di Project `{active_p}` Ditandai Selesai!** 💖\n\n"
                f"✓ *{entry['description']}*\n"
                f"• Waktu: `{entry['completed_at']}`\n\n"
                f"Riwayat ini sudah aku simpan aman di memory vault project. Mau lanjut ke task berikutnya? 🚀"
            )
            return True, msg

        elif intent.intent_type == "ADD_RELATION":
            source_p = intent.target_project
            target_p = intent.relation_target
            projs = self.pm.list_projects()
            if source_p in projs and target_p in projs:
                p_path = projs[source_p]
                vault = get_project_vault(p_path, source_p)
                vault.add_relation(
                    target_project=target_p,
                    relation_type=intent.relation_type or "dependency",
                    description=f"Relasi modul ERP: {source_p} terhubung ke {target_p}"
                )
                msg = (
                    f"🔗 **Relasi Antar-Project Terhubung!** 🌐\n\n"
                    f"Modul `{source_p}` sekarang aware dan terhubung dengan `{target_p}`.\n"
                    f"Waifu akan memperhitungkan dependensi ini setiap kali mengedit kode atau API! 💡"
                )
                return True, msg
            else:
                return False, f"⚠️ Salah satu project (`{source_p}` atau `{target_p}`) belum terdaftar di sistem."

        return False, "Intent tidak dikenali."

    def render_god_view(self, user_id: int, persona_name: str = "Akira") -> str:
        """Generates the executive God View dashboard for all registered projects."""
        projs = self.pm.list_projects()
        active_p = self.pm.get_active_project(user_id)

        lines = [
            f"👑 **{persona_name} - Project Coordinator (God View Dashboard)**",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 Total Terpantau: **{len(projs)} Project** • Aktif: **`{active_p}`**\n"
        ]

        all_relations = []

        for p_name, p_path in projs.items():
            is_active = (p_name == active_p)
            status_badge = "🟢 **[AKTIF]**" if is_active else "📁"

            vault = get_project_vault(p_path, p_name)
            mem = vault.load_memory()
            arch = mem.get("architecture", {})
            completed = mem.get("tasks", {}).get("completed", [])
            pending = mem.get("tasks", {}).get("pending", [])
            relations = mem.get("relations", [])

            for r in relations:
                all_relations.append(f"`{p_name}` ➔ `{r.get('target_project')}` ({r.get('relation_type')})")

            fw = arch.get("framework", "General")
            last_task = completed[-1].get("description", "Belum ada riwayat") if completed else "Baru diinisialisasi"

            lines.append(f"{status_badge} **`{p_name}`** (`{fw}`)")
            lines.append(f"   📂 `{p_path}`")
            lines.append(f"   ✓ Selesai: **{len(completed)}** | 📌 To-Do: **{len(pending)}**")
            lines.append(f"   📝 Terakhir: _{last_task[:50]}_")
            lines.append("")

        if all_relations:
            lines.append("🌐 **Relasi Antar Modul / ERP Network:**")
            for rel in set(all_relations):
                lines.append(f"   • {rel}")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 *Tinggal ngobrol dengan Waifu untuk pindah project, buat modul baru, atau cek to-do!*")
        return "\n".join(lines)

    def render_project_status(self, vault: ProjectVault, persona_name: str = "Akira") -> str:
        """Renders comprehensive status and memory of an individual project."""
        mem = vault.load_memory()
        p_name = mem.get("project_name", vault.project_name)
        p_path = mem.get("project_path", vault.project_path)
        arch = mem.get("architecture", {})
        relations = mem.get("relations", [])
        milestones = mem.get("compacted_milestones", [])
        completed = mem.get("tasks", {}).get("completed", [])
        pending = mem.get("tasks", {}).get("pending", [])
        stats = mem.get("context_stats", {})

        lines = [
            f"📋 **Status & Memory Vault: `{p_name}`**",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📂 **Path:** `{p_path}`",
            f"🛠️ **Framework:** {arch.get('framework', 'N/A')} ({', '.join(arch.get('tech_stack', [])) or 'General'})",
            f"🗄️ **Storage / DB:** {arch.get('database', 'N/A')}",
            f"📄 **Blueprint:** `{arch.get('architecture_doc', 'ARCHITECTURE.md')}`\n"
        ]

        if relations:
            lines.append("🌐 **Relasi Modul (ERP Dependencies):**")
            for r in relations:
                lines.append(f"   • Terhubung ke `{r.get('target_project')}` ({r.get('relation_type')})")
            lines.append("")

        if milestones:
            lines.append("🏛️ **Milestone Terpadatkan (Permanent Memory):**")
            for m in milestones[-3:]:
                lines.append(f"   ✓ {m}")
            lines.append("")

        lines.append(f"✅ **Pekerjaan Selesai ({len(completed)} tasks • Total historis: {stats.get('total_completed', len(completed))}):**")
        if completed:
            for t in completed[-5:]:
                lines.append(f"   ✓ {t.get('description')}")
        else:
            lines.append("   _(Belum ada task selesai tercatat)_")

        lines.append("")
        lines.append(f"📌 **Rencana / To-Do List ({len(pending)} tasks):**")
        if pending:
            for p in pending:
                prio = "🔥 [HIGH]" if p.get("priority") == "high" else "•"
                lines.append(f"   {prio} `{p.get('id')}`: {p.get('description')}")
        else:
            lines.append("   _(Tidak ada tugas tertunda, semua bersih! 🎉)_")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)


# Global singleton
_GLOBAL_INTENT_ROUTER: Optional[ProjectIntentRouter] = None


def get_project_intent_router() -> ProjectIntentRouter:
    global _GLOBAL_INTENT_ROUTER
    if _GLOBAL_INTENT_ROUTER is None:
        _GLOBAL_INTENT_ROUTER = ProjectIntentRouter()
    return _GLOBAL_INTENT_ROUTER
