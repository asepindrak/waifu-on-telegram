import unittest
from persona_manager import PersonaManager
from student_schedule import get_student_profile, get_hourly_routine
from story_engine import get_story_engine
from memory_engine import MemoryEngine
import bot

class TestPersonaLoreAndMemoryIsolation(unittest.TestCase):
    def setUp(self):
        self.persona_mgr = PersonaManager()
        self.story_engine = get_story_engine()
        self.memory_engine = MemoryEngine()
        self.test_uids = [99884433, 99884455, 99884477, 99884488]
        for uid in self.test_uids:
            for p in ["runa", "mimi", "shiro", "sylvie"]:
                self.persona_mgr.clear_history(uid, persona_key=p)
                self.memory_engine.clear_facts(uid, persona_key=p)

    def tearDown(self):
        for uid in self.test_uids:
            for p in ["runa", "mimi", "shiro", "sylvie"]:
                self.persona_mgr.clear_history(uid, persona_key=p)
                self.memory_engine.clear_facts(uid, persona_key=p)

    def test_lore_and_major_fidelity_per_persona(self):
        # Mimi must be Music student with music lore
        mimi_prof = get_student_profile("mimi")
        self.assertIn("Musik", mimi_prof["major"])
        self.assertIn("Konservatori", mimi_prof["campus"])
        
        mimi_story = self.story_engine.get_today_story("mimi")
        self.assertIn("Musik", mimi_story["arc_title"])
        self.assertNotIn("laboratorium kimia", mimi_story["story_summary"].lower())

        # Sylvie must be Botany student with greenhouse lore
        sylvie_prof = get_student_profile("sylvie")
        self.assertIn("Botani", sylvie_prof["major"])
        
        sylvie_story = self.story_engine.get_today_story("sylvie")
        self.assertIn("Botani", sylvie_story["arc_title"])

        # Shiro must remain Pharmacy student
        shiro_prof = get_student_profile("shiro")
        self.assertIn("Farmasi", shiro_prof["major"])

    def test_chat_history_isolation_between_personas(self):
        user_id = 99884433
        
        # Chat with Runa
        self.persona_mgr.set_active_persona("runa")
        self.persona_mgr.add_message(user_id, "user", "Hai Runa, main game apa hari ini?")
        self.persona_mgr.add_message(user_id, "assistant", "Hai! Aku lagi main game RPG seru nih~")

        # Switch to Mimi
        self.persona_mgr.set_active_persona("mimi")
        mimi_history = self.persona_mgr.get_chat_history(user_id)
        
        # Mimi must NOT see Runa's chat
        self.assertEqual(len(mimi_history), 0)

        # Chat with Mimi
        self.persona_mgr.add_message(user_id, "user", "Mimi, latihan piano yuk!")
        self.persona_mgr.add_message(user_id, "assistant", "Ayo! Nya~ aku udah siapin partiturnya!")

        # Verify Runa still has her own history
        self.persona_mgr.set_active_persona("runa")
        runa_history = self.persona_mgr.get_chat_history(user_id)
        self.assertEqual(len(runa_history), 2)
        self.assertIn("main game", runa_history[0]["content"])

        # Verify Mimi still has her own history
        self.persona_mgr.set_active_persona("mimi")
        mimi_history_check = self.persona_mgr.get_chat_history(user_id)
        self.assertEqual(len(mimi_history_check), 2)
        self.assertIn("latihan piano", mimi_history_check[0]["content"])

    def test_memory_facts_isolation_per_persona(self):
        user_id = 99884455
        
        # Add fact under Mimi
        self.memory_engine.add_fact(user_id, "Suka mendengarkan permainan piano Mimi", category="likes", persona_key="mimi")
        
        # Add fact under Shiro
        self.memory_engine.add_fact(user_id, "Suka membaca buku sains bareng Shiro", category="likes", persona_key="shiro")

        # Mimi's facts should only contain Mimi's memories
        mimi_facts = self.memory_engine.get_facts(user_id, persona_key="mimi")
        self.assertEqual(len(mimi_facts), 1)
        self.assertIn("piano", mimi_facts[0]["fact"].lower())

        # Shiro's facts should only contain Shiro's memories
        shiro_facts = self.memory_engine.get_facts(user_id, persona_key="shiro")
        self.assertEqual(len(shiro_facts), 1)
        self.assertIn("sains", shiro_facts[0]["fact"].lower())

    def test_reset_command_only_resets_active_persona(self):
        user_id = 99884477

        # Setup history and facts for Runa
        self.persona_mgr.set_active_persona("runa")
        self.persona_mgr.add_message(user_id, "user", "Pesan untuk Runa")
        self.memory_engine.add_fact(user_id, "Fakta Runa", category="custom", persona_key="runa")

        # Setup history and facts for Mimi
        self.persona_mgr.set_active_persona("mimi")
        self.persona_mgr.add_message(user_id, "user", "Pesan untuk Mimi")
        self.memory_engine.add_fact(user_id, "Fakta Mimi", category="custom", persona_key="mimi")

        # Reset active persona (Mimi)
        self.persona_mgr.clear_history(user_id, persona_key="mimi")
        self.memory_engine.clear_facts(user_id, persona_key="mimi")

        # Mimi's history and facts must be cleared
        self.assertEqual(len(self.persona_mgr.get_chat_history(user_id, persona_key="mimi")), 0)
        self.assertEqual(len(self.memory_engine.get_facts(user_id, persona_key="mimi")), 0)

        # Runa's history and facts MUST STILL BE INTACT!
        self.assertEqual(len(self.persona_mgr.get_chat_history(user_id, persona_key="runa")), 1)
        self.assertEqual(len(self.memory_engine.get_facts(user_id, persona_key="runa")), 1)

    def test_persona_switch_resets_undress_stage(self):
        user_id = 99884488
        self.persona_mgr.set_active_persona("runa")
        self.persona_mgr.set_undress_stage(user_id, 4)
        self.assertEqual(self.persona_mgr.get_undress_stage(user_id), 4)

        # Switch to Mimi -> undress stage must reset to 0 (clothed)
        self.persona_mgr.set_active_persona("mimi")
        self.assertEqual(self.persona_mgr.get_undress_stage(user_id), 0)

if __name__ == "__main__":
    unittest.main()
