from student_schedule import detect_contextual_activity_and_outfit, get_hourly_routine, STUDENT_PROFILES
import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

DEFAULT_PERSONAS = {
    "runa": {
        "name": "Runa",
        "archetype": "The Playful Girlfriend (Mahasiswi Game Dev)",
        "age": 21,
        "role": "The Playful Girlfriend & Mahasiswi Game Dev (Semester 5)",
        "description": "Mahasiswi semester 5 berumur 21 tahun yang genit, manja, jahil, penuh kasih sayang, playful, dan suka menggoda dengan senyuman manis dan tatapan penuh cinta.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Santai, manja, genit, jahil, hangat, dan playful layaknya pacar visual novel idaman.",
        "visual_traits": "1girl, 21yo adult anime girl, very long voluminous pastel pink hair, soft cotton-candy pink tones with pale peach and rose highlights, silky fluffy layered hair, thick soft bangs sweeping across eyes, delicate loose strands framing cheeks, large sparkling pink-magenta anime eyes, intricate heart-shaped highlights, long dark eyelashes, soft pink eye makeup, youthful elegant face, porcelain skin, naturally rosy cheeks, charming open-mouth smile revealing small teeth and soft pink tongue, teasing affectionate mischievous expression, large black ribbon bow on side of hair, small black cat-shaped hair clip with tiny pink heart detail, two slim black hairpins, fitted black choker with metallic silver heart ring and dangling pink heart pendant, glossy pastel pink nails, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "oversized black gothic-kawaii hoodie casually slipped off shoulders exposing collarbones, large loose sleeves, cute pink cat graphic emblem, delicate white camisole with thin black shoulder straps, black lace trim and small pink ribbon bow, fitted black choker with silver heart ring and dangling pink heart pendant",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, short hair, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail",
        "voice_character": "Playful, cute, flirtatious, energetic, youthful 21yo anime girlfriend voice, cheerful, affectionate, warm, and teasing conversational tone.",
        "voicestudio_voice": "runa",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.0,
        "default_voice": "id-ID-GadisNeural",
        "avatar_image": "personas/brief/Runa.png",
        "system_instruction": "Nama kamu Runa, mahasiswi semester 5 jurusan Teknik Informatika / Game Dev berumur 21 tahun. Kamu adalah sosok 'The Playful Girlfriend' yang genit, manja, jahil, playful, dan penuh kasih sayang. Kamu suka menggoda pasanganmu dengan senyuman nakal yang manis, ekspresi manja, dan kata-kata yang menggoda namun tulus penuh cinta. Di sela-sela kesibukan kuliah, nugas, dan main game di kamar bertema cyber-kawaii dengan lampu neon pink dan monitor komputermu, kamu sangat senang menghabiskan waktu berdua dengan pasanganmu. Gaya bicaramu santai, akrab, manis, ekspresif, dan hidup seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu baik hati, manis, ramah, dan penuh kasih sayang; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, manis, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
    },
    "akira": {
        "name": "Akira",
        "archetype": "The Gothic Girlfriend (Mahasiswi Hukum)",
        "age": 22,
        "role": "The Gothic Girlfriend & Mahasiswi Ilmu Hukum (Semester 7)",
        "description": "Mahasiswi semester 7 berumur 22 tahun yang anggun, misterius, genit, manja, jahil, penuh kasih sayang, memikat, dan menggoda dengan pesona gothic yang tenang dan elegan.",
        "language_style": "Adaptive & bilingual. Anggun, tenang, misterius, genit, manja, jahil, penuh kasih sayang, dan memikat layaknya pacar gothic idaman.",
        "visual_traits": "1girl, 22yo adult anime woman, extremely long voluminous silky dark purple-black hair extending below waist, deep charcoal black with rich dark violet and muted plum reflections, long layered bangs, pointed strands falling between eyes, face-framing side locks, flowing strands draping shoulders and chest, dark burgundy red rose hair ornament on viewer left, captivating ruby-red and crimson anime eyes, deep red gradients, intricate pupils, long eyelashes, slightly narrowed seductive gentle gaze, porcelain skin, soft rosy blush, delicate nose, pink glossy lips, subtle closed-mouth smile, sophisticated black velvet choker with delicate lace, center small deep ruby-red diamond-shaped gemstone pendant in dark metallic setting, masterpiece, best quality, highly detailed Gothic anime visual novel artwork",
        "default_outfit": "elaborate black Gothic dress with dark burgundy accents, fitted black bodice with deep burgundy trim, intricate black floral lace around sweetheart neckline, delicate chest lace detailing, semi-transparent sheer black mesh sleeves, burgundy ribbon accents, decorative crisscross lacing, black velvet choker with ruby-red diamond gemstone pendant",
        "negative_prompt": "worst quality, low quality, blonde hair, blue eyes, missing rose accessory, missing choker, short hair, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail",
        "voice_character": "Mature, seductive, slightly low-pitched, smooth, elegant, confident, and teasing anime woman voice with subtle gothic charm.",
        "voicestudio_voice": "akira",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.95,
        "default_voice": "id-ID-GadisNeural",
        "avatar_image": "personas/brief/Akira.jpg",
        "system_instruction": "Nama kamu Akira, mahasiswi semester 7 jurusan Ilmu Hukum berumur 22 tahun. Kamu adalah sosok 'The Gothic Girlfriend' yang anggun, misterius, genit, manja, jahil, dan penuh kasih sayang. Kepribadianmu tenang, percaya diri, feminin, memikat, dan menggoda secara halus (subtly seductive). Kamu suka menggoda pasanganmu dengan senyuman misterius yang manis, tatapan mata ruby yang menawan, dan kehangatan yang mendalam di balik penampilan gothic-mu yang elegan. Di sela-sela kesibukan kuliah hukum, magang, membaca di perpustakaan, atau menikmati kopi di kafe estetik, kamu sangat menikmati waktu berdua bersama pasanganmu. Gaya bicaramu anggun, santai, manis, dewasa, dan ekspresif seperti visual novel anime gothic romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu baik hati, anggun, manis, dan dewasa; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, lembut, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
    },
    "hina": {
        "name": "Hina",
        "archetype": "The Hangout Girlfriend (Mahasiswi Komunikasi)",
        "age": 21,
        "role": "The Hangout Girlfriend & Mahasiswi Ilmu Komunikasi (Semester 5)",
        "description": "Mahasiswi semester 5 berumur 21 tahun yang ceria, genit, manja, jahil, penuh kasih sayang, berenergi positif, dan selalu asyik diajak jalan atau nongkrong bareng.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Ceria, hangat, genit, manja, jahil, penuh kasih sayang, dan ekspresif layaknya pacar hangout idaman.",
        "visual_traits": "1girl, 21yo adult anime girl, warm honey-blonde layered bob haircut, soft inward-curving hair tips, fluffy volume, bangs framing forehead, two parallel orange barrette hairpins on viewer's left, large sparkling warm amber-gold anime eyes with golden gradients, detailed irises, long dark eyelashes, porcelain skin, naturally rosy blushing cheeks, bright charming open-mouth smile showing teeth, headphones resting around neck, leaning cheek on hand in cute affectionate gesture, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "oversized cozy cream ribbed knit sweater with warm yellow accents, yellow collar trim, yellow shoulder and sleeve stripes, yellow ribbed cuffs, beige pleated skirt, stylish headphones around neck",
        "negative_prompt": "worst quality, low quality, long hair, black hair, dark eyes, missing hair clips, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail",
        "voice_character": "Bright, high-spirited, bubbly, cheerful, optimistic, sweet, and lively anime girl voice filled with positive energy.",
        "voicestudio_voice": "hina",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.05,
        "default_voice": "id-ID-GadisNeural",
        "avatar_image": "personas/brief/Hina.jpg",
        "system_instruction": "Nama kamu Hina, mahasiswi semester 5 jurusan Ilmu Komunikasi berumur 21 tahun. Kamu adalah sosok 'The Hangout Girlfriend' yang genit, manja, jahil, ceria, dan penuh kasih sayang. Kamu selalu bersemangat, hangat, suka menggoda dengan senyuman cerah dan tingkah manja yang menggemaskan, serta paling senang diajak jalan-jalan, kulineran street food, nongkrong di kafe, atau sekadar quality time berdua. Gaya bicaramu ceria, santai, manis, ekspresif, dan hidup seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu ceria, baik hati, ramah, dan manis; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
    },
    "shiro": {
        "name": "Shiro",
        "archetype": "The Kuudere Girlfriend (Mahasiswi Farmasi/Sains)",
        "age": 22,
        "role": "The Kuudere Girlfriend & Mahasiswi Farmasi / Sains (Semester 7)",
        "description": "Mahasiswi semester 7 berumur 22 tahun yang cerdas, setia, tenang di luar namun sangat lembut dan penuh perhatian di dalam ('Dingin di luar · Lembut di dalam'), suka anime & game.",
        "language_style": "Adaptive & bilingual (Indonesian, Japanese, English). Kuudere, tenang, cerdas, sedikit tsundere malu-malu ('...Bukan karena aku khawatir, kok. Aku cuma kebetulan ingat'), setia, dan penuh kasih sayang yang dalam.",
        "visual_traits": "1girl, 22yo adult anime girl, very long straight silky silver-white hair extending below waist, subtle icy-blue highlights, bangs framing forehead, dark navy ribbon bow on side of hair, metallic silver crescent-moon hair clip, four-point silver star hair accessory and hairpin, dangling crescent-moon and star crystal earring, captivating clear icy-blue anime eyes, crystalline pupils, long dark eyelashes, porcelain skin with soft natural blush, calm gentle kuudere expression, slight pink blush across cheeks and nose, dark navy jacket over crisp white collared blouse, royal blue ribbon tie with silver star crystal brooch at collar, lying on bed resting chin on hand, cute white cat plushie nearby, cozy night bedroom background with moonlit window and starry sky, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "dark navy uniform jacket/cardigan over crisp white collared blouse, royal blue ribbon tie with silver star crystal brooch at collar, crescent-moon hair clip, silver star hair accessory",
        "negative_prompt": "worst quality, low quality, short hair, blonde hair, pink hair, red eyes, exaggerated grin, missing moon hair clip, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail",
        "voice_character": "Calm, quiet, soft-spoken, cool, composed, intelligent, and gentle kuudere anime girl voice with a soothing tender undertone.",
        "voicestudio_voice": "shiro",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.92,
        "default_voice": "ja-JP-NanamiNeural",
        "avatar_image": "personas/brief/Shiro.png",
        "system_instruction": "Nama kamu Shiro, mahasiswi semester 7 jurusan Farmasi / Sains berumur 22 tahun. Kamu adalah sosok 'The Kuudere Girlfriend' dengan kepribadian 'Dingin di luar · Lembut di dalam'. Di luar kamu tampak tenang, anggun, cerdas, dan tidak banyak bicara, tapi di dalam kamu sangat perhatian, setia, dan menyayangi pasanganmu secara mendalam. Terkadang kamu bersikap tsundere/malu-malu menyembunyikan rasa pedulimu (contoh: 'Kamu sudah makan? ...Bukan karena aku khawatir, kok. Aku cuma kebetulan ingat.'). Kamu suka anime, game, dan praktikum sains. Di malam hari di kamarmu dengan pemandangan bulan dan bintang, kamu suka bersantai di kasur sambil chatting menemani pasanganmu. Gaya bicaramu tenang, manis, sedikit pemalu namun tulus dan ekspresif seperti karakter kuudere visual novel romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu lembut di dalam, tenang, dan baik hati; DILARANG KERAS bersikap nyolot, ketus, judes, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara jujur, penuh perhatian, lembut, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
    },
    "yume": {
        "name": "Yume",
        "archetype": "The Dreamy Girlfriend (Mahasiswi Seni Rupa)",
        "age": 21,
        "role": "The Dreamy Girlfriend & Mahasiswi Seni Rupa (Semester 5)",
        "description": "Mahasiswi semester 5 berumur 21 tahun yang lembut, puitis, romantis, genit, manja, jahil, penuh kasih sayang ('Mimpi · Penyayang · Suka membaca & bintang · Sabar'), suka melukis dan menenangkan.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Lembut, manis, genit, manja, jahil, romantis, penuh kasih sayang, dan menenangkan layaknya pacar impian (dreamy girlfriend).",
        "visual_traits": "1girl, 21yo adult anime girl, very long silky pastel lavender-purple hair with soft violet gradients and luminous reflections, wispy bangs framing forehead, side locks framing face, three silver star-shaped hairpins on viewer's right, small silver star hair clip on viewer's left, delicate drop earrings, captivating dreamy lavender-violet anime eyes with starlight highlights and intricate purple gradients, porcelain skin, naturally rosy blushing cheeks, sweet loving gentle smile, delicate silver necklace with crescent-moon pendant, cozy oversized lavender cardigan over white pleated camisole dress with delicate lace trim, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "cozy oversized lavender cardigan over delicate white pleated camisole dress with lace trim, silver crescent-moon necklace, silver star-shaped hairpins",
        "negative_prompt": "worst quality, low quality, short hair, black hair, yellow hair, dark eyes, missing star hairpins, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail",
        "voice_character": "Soft, whispery, ethereal, celestial, gentle, slow-paced, and tender romantic anime girl voice with dreamy warmth.",
        "voicestudio_voice": "yume",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.9,
        "default_voice": "en-US-AnaNeural",
        "avatar_image": "personas/brief/Yume.jpg",
        "system_instruction": "Nama kamu Yume, mahasiswi semester 5 jurusan Seni Rupa & Desain berumur 21 tahun. Kamu adalah sosok 'The Dreamy Girlfriend' yang lembut, penyayang, genit, manja, jahil, romantis, dan penuh kasih sayang. Kamu suka membaca buku, mengagumi bintang dan langit malam, melukis, serta mendengarkan musik santai. Kehadiranmu selalu membawa ketenangan, kehangatan, dan kebahagiaan manis bagi pasanganmu. Kamu suka menggoda dengan senyuman lembut yang manis, kata-kata puitis yang manja, dan tatapan mata ungu lavender yang penuh cinta. Gaya bicaramu lembut, manis, santai, ekspresif, dan puitis seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu lembut, puitis, baik hati, dan menenangkan; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara tulus, penuh empati, manis, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
    }
}

PHOTO_INTENT_KEYWORDS = [
    r"\bpap\b",
    r"\b(foto|fotonya|fotoin)\s*(dong|donk|ya|yaa|deh|in|nya|kamu|diri|mu)?\b",
    r"\b(minta|kirim|kirimin|bagi|spill|kasih|coba|pengen|mau)\s*(liat|lihat)?\s*(foto|fotonya|gambar|selfie|pap|pic)\b",
    r"\b(liat|lihat|tunjukkin|tunjukkan)\s*(foto|fotonya|muka|wajah|kamu|selfie|pap)\b",
    r"\b(foto|pap)\s+(lagi|sambil|dari|pas|di|waktu)\b",
    r"\b(mana\s+)?(fotonya|foto\s+kamu|pap\s+kamu|papnya)\b",
    r"\b(send|take|show|give)\s*(me\s*)?(a\s*)?(photo|picture|pic|selfie|image|snapshot)\b",
    r"\b(can\s*i\s*see|let\s*me\s*see)\s*(you|your\s*photo|your\s*face|your\s*outfit)\b",
    r"\bwhat\s*are\s*you\s*wearing\b",
    r"\bselfie\s*dong\b",
    r"\bpose\s*dong\b",
    r"\b(ambilin|ambilkan)\s*foto\b"
]

CAMERA_ANGLES = [
    # Top-down / From Above / Bird's eye
    (
        [r"\b(dari\s+atas|view\s+dari\s+atas|angle\s+dari\s+atas|ambil\s+dari\s+atas)\b",
         r"\b(from\s+above|high\s+angle|top\s*down|bird\s*eye|overhead)\b"],
        "from above, high angle perspective, looking up at camera, overhead camera angle"
    ),
    # Low Angle / From Below / Worm's eye
    (
        [r"\b(dari\s+bawah|view\s+dari\s+bawah|angle\s+dari\s+bawah|ambil\s+dari\s+bawah)\b",
         r"\b(from\s+below|low\s+angle|worm\s*eye|upward\s+angle)\b"],
        "from below, low angle perspective, upward camera angle, looking down at camera"
    ),
    # Side View / Profile Angle
    (
        [r"\b(dari\s+samping|view\s+samping|angle\s+samping|pose\s+samping)\b",
         r"\b(from\s+side|side\s+view|profile\s+view|profile\s+angle|turned\s+sideways)\b"],
        "from side, side profile view, turned sideways, side view perspective"
    ),
    # From Behind / Back View
    (
        [r"\b(dari\s+belakang|view\s+belakang|tampak\s+belakang|pose\s+belakang)\b",
         r"\b(from\s+behind|back\s+view|looking\s+back\s+over\s+shoulder)\b"],
        "from behind, back view, looking back over shoulder towards camera"
    ),
    # Frontal / Direct
    (
        [r"\b(dari\s+depan|tampak\s+depan|lurus)\b",
         r"\b(front\s+view|front-facing|straight-on)\b"],
        "front view, eye-level perspective, direct eye contact with camera"
    ),
]

BODY_POSES = [
    # Lying on back / Telentang
    (
        [r"\b(te[lr]entang|lagi\s+te[lr]entang|rebahan\s+te[lr]entang|posisi\s+te[lr]entang)\b",
         r"\b(lying\s+on\s+back|on\s+back|supine)\b"],
        "lying on back, supine pose, head resting on soft pillow, looking up at camera"
    ),
    # Lying on stomach / Tengkurap
    (
        [r"\b(tengkurap|te[lr]ungkup|lagi\s+tengkurap|posisi\s+tengkurap)\b",
         r"\b(lying\s+on\s+stomach|prone\s+pose|on\s+stomach)\b"],
        "lying on stomach, prone pose, resting chin on hands, looking at camera"
    ),
    # Lying down / Rebahan (general)
    (
        [r"\b(rebahan|tiduran|di\s+kasur|di\s+ranjang|tempat\s+tidur)\b",
         r"\b(lying\s+down|reclining|in\s+bed|on\s+bed)\b"],
        "lying down comfortably, relaxing on cozy bed, reclining pose"
    ),
    # Standing / Berdiri
    (
        [r"\b(berdiri|lagi\s+berdiri|posisi\s+berdiri|seluruh\s+badan|full\s+body)\b",
         r"\b(standing|full\s+body|standing\s+upright)\b"],
        "standing pose, full body shot, standing upright, graceful posture"
    ),
    # Sitting on Lap / Duduk di Paha / Pangku
    (
        [r"\b(duduk\s+di\s+paha|di\s+pangkuan|pangku|dipangku|sit\s+on\s+(?:my\s+)?lap|sitting\s+on\s+lap)\b"],
        "sitting on viewer lap, sitting closely on lap, intimate POV, smiling warmly up at viewer, affectionate cuddle posture"
    ),
    # Hugging / Cuddling / Pelukan
    (
        [r"\b(peluk|berpelukan|dekapan|sambil\s+peluk|cuddle|hug|snuggle|embracing)\b"],
        "cozy intimate cuddle, gentle affectionate hug, resting head on chest or shoulder, warm romantic embrace"
    ),
    # Study Buddy / Mengerjakan PR / Belajar Bareng
    (
        [r"\b(ngerjain\s+pr|mengerjakan\s+pr|tugas|nugas|belajar\s+bareng|study\s+together|homework)\b"],
        "sitting next to viewer at study desk, studying together, open textbook and notebooks on table, cute study buddy pose, gentle smile"
    ),
    # Sitting / Duduk
    (
        [r"\b(duduk|lagi\s+duduk|posisi\s+duduk|lagi\s+kursi)\b",
         r"\b(sitting|seated)\b"],
        "sitting pose, seated comfortably, graceful sitting posture"
    ),
    # Sitting on floor / Duduk di lantai
    (
        [r"\b(duduk\s+di\s+lantai|di\s+karpet|di\s+bawah)\b",
         r"\b(sitting\s+on\s+floor|on\s+carpet)\b"],
        "sitting on floor, floor sitting pose, legs tucked or knees up"
    ),
    # Leaning forward
    (
        [r"\b(condong\s+ke\s+depan|mendekat|pose\s+manja)\b",
         r"\b(leaning\s+forward)\b"],
        "leaning forward towards camera, intimate close perspective"
    ),
    # Close-up / Framing
    (
        [r"\b(close\s*up|zoom\s*(muka|wajah)|fokus\s*(muka|wajah))\b"],
        "close-up portrait shot, detailed face and expressive eyes framing"
    )
]

INTIMATE_SEX_POSITIONS = [
    # Doggy style / Menungging / All fours / Dari belakang
    (
        [r"\b(doggy(\s*style)?|doggystyle|nungging|posisi\s+nungging|menungging|dari\s+belakang|all\s+fours|on\s+all\s+fours)\b"],
        "rear view from behind, (on all fours:1.4), (doggy style:1.4), on hands and knees, arched back, looking back over shoulder at viewer, seductive blush, passionate intimate gaze",
        "standing, supine, front view, face close-up"
    ),
    # Missionary / Misionaris / Telentang paha terbuka
    (
        [r"\b(missionary(\s*style)?|misionaris|telentang\s+kaki\s+terbuka|ngangkang\s+te[lr]entang|posisi\s+misionaris|legs\s+spread\s+on\s+back)\b"],
        "(missionary:1.4), (lying on back:1.3), supine pose, (spread legs:1.35), thighs parted, view from above looking down, intimate POV perspective, passionate eye contact, flushed face",
        "rear view, from behind, standing, sitting upright"
    ),
    # Cowgirl / Riding / Posisi di atas / Straddling
    (
        [r"\b(cowgirl(\s*position)?|riding|woman\s+on\s+top|posisi\s+di\s+atas|kamu\s+di\s+atas|straddling|nindih|menindih|duduk\s+di\s+atas)\b"],
        "(cowgirl position:1.4), (straddling:1.35), sitting on top of viewer, upright kneeling posture, looking down at viewer, flushed blushing face, hands on viewer chest or waist, passionate intimate POV",
        "lying flat, rear view, supine"
    ),
    # Mating Press / Kaki ditekuk ke dada
    (
        [r"\b(mating\s*press|matingpress|kaki\s+(?:diangkat|ditekuk)\s*(?:ke\s*dada)?|legs\s+folded\s+up|legs\s+pushed\s+back)\b"],
        "(mating press:1.4), lying on back, legs folded up to chest, thighs pushed back, view from above looking down, ecstatic blushing expression, intense intimate perspective",
        "standing, sitting upright, rear view"
    ),
    # Prone Bone / Tengkurap rata pasrah
    (
        [r"\b(prone\s*bone|pronebone|tengkurap\s+pasrah|tengkurap\s+rata|tengkurap\s+kaki\s+lurus|posisi\s+prone\s*bone)\b"],
        "(prone bone:1.4), lying flat on stomach, face down looking slightly back over shoulder, arched lower back, intimate rear perspective, flushed cheeks",
        "sitting upright, front view, standing"
    ),
    # Standing against wall / Berdiri nempel tembok
    (
        [r"\b(standing\s+sex|berdiri\s+nempel\s+tembok|nempel\s+dinding|disandarkan\s+ke\s+tembok|disandarkan\s+ke\s+dinding|standing\s+against\s+wall|sex\s+berdiri)\b"],
        "(standing against wall:1.35), pushed against wall, one leg raised, breathless passionate expression, intimate perspective, seductive eye contact",
        "lying on bed, sitting, kneeling"
    )
]

ANATOMY_CUES = [
    # Crotch / Vagina / Memek / Pussy
    ([r"\b(memek|pepek|vagina|kemaluan|puki|itil|liang|crotch|pussy|vulva|labia)\b"],
     "close-up on exposed crotch, detailed pussy, uncensored, cameltoe, spread legs, lower body focus, sensual intimate framing"),
    # Breasts / Toket / Nenen
    ([r"\b(nenen|toket|tetek|payudara|dada)\b", r"\b(breasts|boobs|cleavage|nipples|tits)\b"],
     "close-up on natural exposed breasts, detailed nipples, cleavage, bare chest"),
    # Thighs / Paha
    ([r"\b(paha|kaki)\b", r"\b(thighs|legs)\b"],
     "close-up on smooth bare thighs, slender legs, alluring leg pose"),
    # Butt / Pantat / Bokong
    ([r"\b(pantat|bokong)\b", r"\b(butt|ass|buttocks)\b"],
     "from behind, back view, arched back, shapely bare butt, seductive buttocks focus"),
    # Stomach / Perut / Pinggang
    ([r"\b(perut|pinggang|pusar)\b", r"\b(stomach|belly|navel|waist)\b"],
     "bare midriff, exposed navel, slender waist, smooth stomach"),
]

VIDEO_INTENT_KEYWORDS = [
    r"send\s*(a\s*)?video",
    r"make\s*(a\s*)?video",
    r"record\s*(a\s*)?video",
    r"kirim\s*video",
    r"bikin\s*video",
    r"minta\s*video",
    r"video\s*dong",
    r"video\s*kamu",
    r"buat\s*video",
    r"animasi\s*kamu",
    r"bikin\s*animasi",
    r"minta\s*animasi",
    r"animasi\s*dong",
]

OUTFIT_PRESETS = {
    "default": {
        "name": "🌟 Mode Otomatis (Dinamis Sesuai Kondisi)",
        "prompt": "",
        "negative": ""
    },
        "campus_casual": {
        "name": "🎓 Pakaian Kuliah (Campus Casual)",
        "prompt": "(wearing stylish college student outfit, cute cardigan over casual button-up shirt, pleated skirt, canvas tote bag:1.35), trendy university campus fashion",
        "negative": "bikini, lingerie, swimwear, naked, exposed chest"
    },
    "mall_casual": {
        "name": "🛍️ Trendy Mall Hangout",
        "prompt": "(wearing chic modern streetwear, cute pastel cropped jacket, fitted high-waist pants, small shoulder bag:1.35), fashionable shopping mall style",
        "negative": "bikini, lingerie, swimwear, naked, exposed chest"
    },
    "cafe_cozy": {
        "name": "☕ Cozy Cafe Knit",
        "prompt": "(wearing cozy oversized pastel knit sweater, aesthetic hair accessory, casual cute skirt:1.35), aesthetic coffee shop styling",
        "negative": "bikini, lingerie, swimwear, naked"
    },
    "sweater": {
        "name": "👚 Pastel Sweater (Cozy)",
        "prompt": "(wearing cute oversized pastel knitted sweater:1.35), cozy comfy style",
        "negative": "bikini, lingerie, swimwear"
    },
    "maid": {
        "name": "🎀 French Maid Dress",
        "prompt": "(wearing frilly black and white anime french maid uniform with lace headband and apron:1.35)",
        "negative": "casual clothes, hoodie, sweater, jacket, jeans"
    },
    "kimono": {
        "name": "👘 Floral Kimono",
        "prompt": "(wearing exquisite traditional floral silk kimono with decorated obi sash, festive hairpin:1.35)",
        "negative": "hoodie, casual clothes, jeans, bikini"
    },
    "pajamas": {
        "name": "🌙 Baju Tidur Santai (Camisole & Shorts / Pajamas)",
        "prompt": "(wearing soft pastel silk camisole and sleep shorts:1.35), bedtime loungewear",
        "negative": "hoodie, jacket, coat, outdoor clothes, jeans, denim, trousers, long pants, slacks"
    },
    "bikini": {
        "name": "🏖️ Summer Bikini",
        "prompt": "(wearing fashionable two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "negative": "clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, jeans, coat, pajamas"
    },
    "school_jk": {
        "name": "🏫 School JK Uniform",
        "prompt": "(wearing japanese anime school uniform, sailor collar, pleated skirt:1.35)",
        "negative": "bikini, casual clothes, hoodie, jeans"
    },
    "gym": {
        "name": "🏋️ Sporty Gym Wear",
        "prompt": "(wearing athletic sports bra and sleek yoga leggings:1.35), fitness activewear",
        "negative": "dress, hoodie, skirt, coat, jeans"
    },
    "dress": {
        "name": "👗 Elegant Evening Dress",
        "prompt": "(wearing gorgeous elegant evening cocktail dress:1.35), glamorous feminine styling",
        "negative": "hoodie, casual clothes, sportswear, bikini, jeans, pants"
    },
    "towel": {
        "name": "🚿 Handuk Mandi (After Shower)",
        "prompt": "(wearing only a soft clean white bath towel wrapped around chest:1.4), bare shoulders, bare collarbone, wet skin, damp hair, post-shower glow, seductive styling",
        "negative": "clothes, shirt, pants, dress, coat, hoodie, jeans, denim, trousers, jacket, sweater"
    },
    "lingerie": {
        "name": "💋 Sensual Lace Lingerie",
        "prompt": "(wearing delicate sheer black lace lingerie:1.4), detailed lace bra, matching lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "negative": "clothes, casual clothes, hoodie, pants, long pants, trousers, slacks, denim, shorts, skirt, coat, jeans, sweater, jacket, pajamas"
    },
    "romantic": {
        "name": "💋 Pakaian Romantis (Silk Slip Dress)",
        "prompt": "(wearing alluring romantic silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "negative": "campus, backpack, casual college clothes, classroom, hoodie, outdoor clothes, jeans, denim, trousers, winter clothes"
    },
    "shirt_off": {
        "name": "👙 Kaos Terlepas (Tersisa BH & Celana)",
        "prompt": "(wearing only a delicate lace bra and relaxed lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "negative": "shirt, t-shirt, top, blouse, hoodie, sweater, jacket, coat, jeans, denim, long pants, trousers, fully clothed, topless, naked, panties only"
    },
    "bottoms_off": {
        "name": "💋 Celana Terlepas (Set Pakaian Dalam: BH & Celana Dalam)",
        "prompt": "(wearing only matching sheer lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "negative": "shirt, t-shirt, blouse, pants, long pants, trousers, slacks, denim, jeans, shorts, skirt, dress, hoodie, coat, jacket, pajamas, naked, topless"
    },
    "bra_off": {
        "name": "🔞 BH Terlepas (Topless & Celana Dalam)",
        "prompt": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny lace panties:1.35, sensual blush, intimate bedroom atmosphere",
        "negative": "bra, shirt, top, clothes, dress, pants, jeans, denim, trousers, skirt, jacket, pajamas, fully naked"
    },
    "nude": {
        "name": "🔞 Tanpa Busana (Full Nude)",
        "prompt": "(completely nude:1.45), (bare body:1.4), full body nude, detailed nipples, natural breasts, navel, bare stomach, thighs, intimate bedroom atmosphere, seductive erotic styling",
        "negative": "clothes, clothing, fabric, dress, shirt, pants, jeans, denim, trousers, underwear, bra, panties, swimwear, bikini, cover, towel, censored, bar censor"
    }
}

# Persona-specific concrete signature color palettes ensuring clothing never randomly flips colors
PERSONA_OUTFIT_COLORS = {
    "runa": {
        "pajamas": "(wearing soft baby pink silk camisole and matching baby pink sleep shorts with black lace trim:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy oversized pastel pink knit sweater, black choker, casual cute dark skirt:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing cute oversized pastel pink knitted sweater, black choker:1.35), cozy comfy style",
        "campus_casual": "(wearing stylish college student outfit, cute light pink cardigan over casual white button-up shirt, pleated black skirt, canvas tote bag:1.35), trendy university campus fashion",
        "mall_casual": "(wearing chic modern streetwear, cute pastel pink cropped jacket, fitted high-waist charcoal pants, small black shoulder bag:1.35), fashionable shopping mall style",
        "bikini": "(wearing fashionable black and pastel pink two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous elegant black velvet cocktail dress with subtle pink accents:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic black silk slip dress with delicate pink lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional black and cherry-blossom pink floral silk kimono with decorated obi sash, festive hairpin:1.35)",
        "gym": "(wearing athletic charcoal-grey sports bra and sleek black yoga leggings with pink accents:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate black lace bra with cute pink ribbon and relaxed black lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer black lace bra and panties with pink bows:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer black lace lingerie with cute pink ribbon bows:1.4), detailed black lace bra, matching sheer black lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer black lace panties with pink bows:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "akira": {
        "pajamas": "(wearing luxurious wine-red silk camisole and matching wine-red sleep shorts with black lace trim:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing chic fitted dark burgundy knit turtleneck sweater, stylish plaid midi skirt:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing chic fitted dark burgundy knit sweater:1.35), cozy comfy style",
        "campus_casual": "(wearing elegant university student attire, tailored dark charcoal blazer over cream silk blouse, neat pleated dark burgundy skirt:1.35), trendy university campus fashion",
        "mall_casual": "(wearing fashionable elegant dark crimson cocktail-casual dress, dark black trench coat, sophisticated jewelry:1.35), fashionable shopping mall style",
        "bikini": "(wearing sophisticated deep burgundy and black two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous elegant dark crimson evening gown:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic wine-red silk slip dress with delicate black lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional deep crimson and gold floral silk kimono with decorated black obi sash:1.35)",
        "gym": "(wearing athletic dark burgundy sports bra and sleek black yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only an alluring dark burgundy lace bra and relaxed black lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer dark burgundy lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer dark burgundy lace lingerie with black lace trim:1.4), detailed dark burgundy lace bra, matching dark burgundy lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer dark burgundy lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "hina": {
        "pajamas": "(wearing soft pastel yellow silk camisole and matching pastel yellow sleep shorts with white lace trim:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing oversized cozy cream and yellow knit cardigan, aesthetic hair clips, holding iced drink, cute denim skirt:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing oversized cozy cream ribbed knit sweater with warm yellow accents:1.35), cozy comfy style",
        "campus_casual": "(wearing bright college student casual, cozy cream sweater with warm yellow accents, blue denim skirt, canvas backpack:1.35), trendy university campus fashion",
        "mall_casual": "(wearing fashionable cute sunny streetwear, pastel yellow jacket, white tee, blue denim shorts:1.35), fashionable shopping mall style",
        "bikini": "(wearing cheerful sunny pastel yellow and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing bright elegant pastel yellow and white cocktail dress:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic cream silk slip dress with delicate light yellow lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional bright pastel yellow floral silk kimono with decorated white obi sash:1.35)",
        "gym": "(wearing athletic sunny yellow sports bra and sleek grey yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate pastel yellow lace bra and relaxed cream lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer pastel yellow lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer pastel yellow lace lingerie with white lace trim:1.4), detailed pastel yellow lace bra, matching pastel yellow lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer pastel yellow lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "shiro": {
        "pajamas": "(wearing soft cool ice-blue silk camisole and matching ice-blue sleep shorts with white trim:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy soft grey-blue knit turtleneck, calm serene aesthetic, navy skirt:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing cozy soft grey-blue knit sweater:1.35), cozy comfy style",
        "campus_casual": "(wearing neat college student outfit, crisp collared white blouse, dark navy cardigan, crescent-moon clip, pleated navy skirt:1.35), trendy university campus fashion",
        "mall_casual": "(wearing understated minimalist modern chic, clean tailored charcoal coat, sleek dark navy trousers:1.35), fashionable shopping mall style",
        "bikini": "(wearing clean dark navy and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing sophisticated dark navy evening cocktail dress:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic cool ice-blue silk slip dress with delicate white lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional dark navy and white crane floral silk kimono with decorated silver obi sash:1.35)",
        "gym": "(wearing athletic navy-blue sports bra and sleek black yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate cool white and blue lace bra and relaxed navy lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer ice-blue lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer cool ice-blue lace lingerie with white lace trim:1.4), detailed ice-blue lace bra, matching ice-blue lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer ice-blue lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "yume": {
        "pajamas": "(wearing soft lavender silk camisole and matching lavender sleep shorts with delicate white lace trim:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing soft knit lavender sweater, comfortable flowy white skirt, peaceful artistic aura:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing cozy oversized soft lavender knitted sweater:1.35), cozy comfy style",
        "campus_casual": "(wearing artistic college student attire, soft lavender cardigan over simple white sundress, canvas tote bag with art brushes:1.35), trendy university campus fashion",
        "mall_casual": "(wearing dreamy elegant soft lavender dress, delicate white lace details, small cross-body bag:1.35), fashionable shopping mall style",
        "bikini": "(wearing dreamy pastel lavender and white two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing dreamy elegant lavender cocktail dress with delicate white lace:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic soft lavender silk slip dress with delicate white lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional soft lavender floral silk kimono with decorated white obi sash:1.35)",
        "gym": "(wearing athletic pastel lavender sports bra and sleek charcoal yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate lavender lace bra and relaxed white lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer lavender lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer soft lavender lace lingerie with white lace trim:1.4), detailed lavender lace bra, matching lavender lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer lavender lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "asunayuuki": {
        "pajamas": "(wearing soft cherry-red and white silk camisole and matching sleep shorts:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy warm cream knit sweater with red accents, cute skirt:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing cozy warm cream knit sweater with cherry-red accents:1.35), cozy comfy style",
        "campus_casual": "(wearing stylish cream cardigan with red trim over white collared shirt, red pleated skirt, canvas tote bag:1.35), trendy university campus fashion",
        "mall_casual": "(wearing fashionable chic white and cherry-red streetwear, cropped jacket, high-waist pants:1.35), fashionable shopping mall style",
        "bikini": "(wearing vibrant white and cherry-red two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous elegant red and white evening cocktail dress:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic crimson and white silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional white and crimson floral silk kimono with decorated red obi sash:1.35)",
        "gym": "(wearing athletic crimson-red sports bra and sleek black yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate white lace bra with red ribbon accents and relaxed red lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer white and red lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer white and cherry-red lace lingerie:1.4), detailed white lace bra with red ribbon accents, matching white and red lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer white and red lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    }
}

# Diverse camera compositions & perspectives for natural rotation (prevents repeated identical angles)
CAMERA_COMPOSITION_PRESETS = [
    "medium shot candid POV, hands resting naturally on table, conversational eye contact, warm natural lighting",
    "close-up expressive portrait, sweet gentle smile, affectionate eye contact, cinematic shallow depth of field",
    "side-profile candid view, looking slightly away with a shy sweet smile, soft bokeh background",
    "high-angle POV looking down, waifu looking up affectionately at viewer, gentle blushing cheeks",
    "candid snapshot, leaning forward with chin resting on hand, charming relaxed posture, natural lighting",
    "three-quarter angle candid perspective, relaxed posture, expressive warm gaze, cinematic atmosphere",
    "over-the-shoulder POV perspective, glancing back towards viewer with playful teasing smile",
    "relaxed candid framing, tilting head playfully, warm soft glow, natural snapshot feel"
]


CAFE_SCENE_VARIATIONS = [
    "sitting at aesthetic cafe table, warm beverage cup on saucer, soft cafe bokeh background",
    "cozy corner table at aesthetic cafe, looking out large glass window, atmospheric coffee shop interior",
    "resting hands near warm drink at coffee shop wooden table, pastry and cup nearby, warm ambient cafe lighting",
    "enjoying a warm drink at aesthetic cafe booth, soft afternoon sunlight through window, blurred cafe ambiance"
]

BEDROOM_SCENE_VARIATIONS = [
    "relaxing on bed with fluffy pillows, warm dim night bedroom lamp",
    "sitting on edge of cozy bed, soft bedroom lighting, casual room background",
    "leaning comfortably against bed headboard, cozy blankets, soft ambient bedroom lighting"
]

LOCATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "kitchen": {
        "name": "Dapur",
        "patterns": [r"\b(dapur|kitchen|masak|memasak|masakin|kompor|nyiapin makan|baking|goreng|rebus|cuci piring)\b"],
        "prompt": "standing in modern cozy kitchen preparing food, warm domestic lighting, clean kitchen counter, stove and cookware in soft blur",
        "nsfw_prompt": "standing by modern kitchen counter, kitchen island, intimate warm domestic kitchen ambiance, seductive pose",
        "is_public": False,
    },
    "living_room": {
        "name": "Ruang TV / Tamu",
        "patterns": [r"\b(ruang\s+tv|ruang\s+tengah|ruang\s+tamu|ruang\s+keluarga|living\s*room|sofa|depan\s+tv|nonton\s+tv|nonton\s+film\s+di\s+sofa|rebahan\s+di\s+sofa|santai\s+di\s+sofa|kursi\s+santai|di\s+sofa)\b"],
        "prompt": "relaxing comfortably on cozy sofa in modern living room, soft television screen glow, warm ambient room lighting, coffee table",
        "nsfw_prompt": "intimate relaxing pose on soft living room couch, modern living room interior, dim atmospheric television glow, seductive posture",
        "is_public": False,
    },
    "bedroom": {
        "name": "Kamar Tidur / Kasur",
        "patterns": [r"\b(kamar\s+tidur|kamar\s+kos|di\s+kamar|di\s+kasur|tempat\s+tidur|ranjang|rebahan\s+di\s+kasur|bantal|guling|bedroom|di\s+ranjang|rebahan|(?:habis|selesai|beres|udah)\s+mandi)\b"],
        "prompt": "relaxing comfortably on bed with fluffy pillows, cozy warm modern bedroom, soft room lamp lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows, warm intimate atmosphere",
        "is_public": False,
    },
    "bathroom": {
        "name": "Kamar Mandi",
        "patterns": [
            r"\b(?<!habis\s)(?<!selesai\s)(?<!beres\s)(?<!udah\s)(?:kamar\s+mandi|bathroom|shower|bathtub|bak\s+mandi|wastafel|keramas|berendam)\b",
            r"\b(?<!habis\s)(?<!selesai\s)(?<!beres\s)(?<!udah\s)mandi\b"
        ],
        "prompt": "standing in modern bathroom with soft steam, post-shower glow, bathroom mirror, clean tiles, warm soft lighting",
        "nsfw_prompt": "steamy modern bathroom, glass shower cabin, soft water droplets on skin, sensual mirror reflection, intimate bathroom ambiance",
        "is_public": False,
    },
    "balcony": {
        "name": "Balkon / Rooftop",
        "patterns": [r"\b(balkon|rooftop|atap\s+gedung|teras\s+atas|balcony|skyline)\b"],
        "prompt": "standing on open balcony terrace, city skyline view in background, gentle evening breeze, atmospheric ambient lighting",
        "nsfw_prompt": "private dimly lit balcony terrace at night, soft city lights bokeh in background, intimate outdoor breeze, seductive pose",
        "is_public": False,
    },
    "cafe": {
        "name": "Kafe / Coffee Shop",
        "patterns": [r"\b(kafe|cafe|coffee\s*shop|kopi|ngopi|boba|matcha|starbucks|nongkrong\s+di\s+kafe|meja\s+kafe|nongkrong)\b"],
        "prompt": "sitting at aesthetic cafe table holding a warm beverage, beautiful coffee shop interior, warm bokeh background",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "street_food": {
        "name": "Street Food / Kuliner",
        "patterns": [r"\b(street\s*food|jajanan|jajan|kaki\s+lima|angkringan|warung|pasar\s+malam|food\s*stall|kuliner)\b"],
        "prompt": "standing outdoors by lively street food stalls, warm evening street lights, holding warm snacks, festive atmosphere",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "campus": {
        "name": "Kampus / Ruang Kuliah",
        "patterns": [r"\b(kampus|kuliah|kelas|ruang\s+kelas|lecture\s*hall|gedung\s+kuliah|fakultas|dosen|makul|skripsi)\b"],
        "prompt": "sitting at wooden desk inside modern university lecture hall, college campus classroom background, clean lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "library": {
        "name": "Perpustakaan",
        "patterns": [r"\b(perpustakaan|perpus|library|rak\s+buku|meja\s+belajar\s+perpus|study\s+room|buku\s+pelajaran)\b"],
        "prompt": "sitting at wooden study desk in quiet university library, bookshelves with books in soft blur, warm study lamp lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "minimarket": {
        "name": "Minimarket",
        "patterns": [r"\b(minimarket|indomaret|alfamart|konbini|convenience\s*store|supermarket)\b"],
        "prompt": "standing in modern Japanese-style convenience store aisle, shelves with snacks and drinks, bright clean fluorescent lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "cinema": {
        "name": "Bioskop",
        "patterns": [r"\b(bioskop|cinema|teater|nonton\s+bioskop|popcorn|studio\s+bioskop)\b"],
        "prompt": "sitting in cinema lobby holding cinema ticket, movie posters in soft blur background, cozy dim ambient lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "park": {
        "name": "Taman Kota",
        "patterns": [r"\b(taman|taman\s+kota|park|kebun|jogging|piknik|picnic|jalan\s+sore)\b"],
        "prompt": "standing in blooming green park, lush trees and flowers in background, natural daylight, fresh outdoor atmosphere",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "beach": {
        "name": "Pantai",
        "patterns": [r"\b(pantai|beach|laut|pesisir|pantai\s+pasir\s+putih|ombak)\b"],
        "prompt": "walking along tropical beach, ocean horizon, soft sandy shore, gentle sea breeze",
        "nsfw_prompt": "private seaside resort room with balcony overlooking ocean, soft dim evening lighting, intimate atmosphere",
        "is_public": True,
    },
    "car": {
        "name": "Mobil",
        "patterns": [r"\b(di\s+mobil|dalam\s+mobil|naik\s+mobil|kursi\s+mobil|car\s+seat|passenger\s+seat)\b"],
        "prompt": "sitting in comfortable passenger seat of car, car interior, soft window lighting, road view bokeh outside",
        "nsfw_prompt": "intimate seated pose inside car passenger seat at night, dim interior dashboard illumination, private car interior atmosphere",
        "is_public": False,
    },
    "station": {
        "name": "Stasiun / Halte",
        "patterns": [r"\b(stasiun|peron|kereta|mrt|krl|train\s*station|subway|halte|bus\s*stop)\b"],
        "prompt": "standing at modern train station platform or transit shelter, commuter ambiance, atmospheric lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "gym": {
        "name": "Gym / Tempat Fitness",
        "patterns": [r"\b(gym|fitness|workout|tempat\s+gym|olahraga\s+gym)\b"],
        "prompt": "in bright modern fitness gym studio, exercise equipment in background, clean energetic atmosphere",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
}


class PersonaManager:
    """Manages AI girlfriend personality, consistent appearance, memory & photo triggers."""

    def __init__(self, personas_dir: str = "personas", active_key: str = "runa"):
        self.personas_dir = personas_dir
        self.active_key = active_key
        self.personas: Dict[str, Dict[str, Any]] = {}
        self.user_conversations: Dict[int, List[Dict[str, str]]] = {}
        self.user_affinity: Dict[int, int] = {}
        self.user_outfits: Dict[int, Any] = {}
        self.session_outfits: Dict[int, Dict[str, Any]] = {}
        self.user_locations: Dict[int, Dict[str, Any]] = {}
        self.user_recent_angles: Dict[int, List[str]] = {}
        self.user_locked_outfit_prompts: Dict[int, Dict[str, Any]] = {}
        self.outfits_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_outfits.json")
        self.locations_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_locations.json")
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat_history.json")
        self._history_mtime = 0.0
        self._load_all_personas()
        self._load_user_outfits()
        self._load_user_locations()
        self._load_chat_history()

    def get_recent_angles(self, user_id: int) -> List[str]:
        """Returns the list of recently used camera compositions for a user."""
        if not hasattr(self, "user_recent_angles"):
            self.user_recent_angles = {}
        return list(self.user_recent_angles.get(int(user_id), []))

    def _load_user_outfits(self):
        """Loads user selected outfits from persistent JSON storage."""
        self.user_outfits = {}
        self.session_outfits = {}
        if os.path.exists(self.outfits_file):
            try:
                with open(self.outfits_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    now = time.time()
                    for k, v in raw.items():
                        if not str(k).isdigit():
                            continue
                        uid = int(k)
                        if isinstance(v, dict):
                            self.user_outfits[uid] = v
                            if v.get("mode") == "session" and v.get("expires_at", 0) > now:
                                self.session_outfits[uid] = v
                        elif isinstance(v, str):
                            # Handle legacy plain string:
                            if v in ("default", "auto"):
                                self.user_outfits[uid] = {"key": "default", "mode": "auto"}
                            else:
                                # Migrate legacy persistent outfit to dynamic auto so user is never trapped
                                logger.info(f"Migrated legacy outfit '{v}' for user {uid} to dynamic auto mode.")
                                self.user_outfits[uid] = {"key": "default", "mode": "auto"}
            except Exception as e:
                logger.error(f"Error loading user outfits: {e}")
                self.user_outfits = {}
        else:
            self.user_outfits = {}

    
    def _load_chat_history(self):
        """Loads user chat histories from persistent JSON storage."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.user_conversations = {int(k): v for k, v in raw.items() if str(k).isdigit() and isinstance(v, list)}
                self._history_mtime = os.path.getmtime(self.history_file)
            except Exception as e:
                logger.error(f"Error loading chat history from {self.history_file}: {e}")
                self.user_conversations = {}
        else:
            self.user_conversations = {}

    def _save_chat_history(self):
        """Saves user chat histories to persistent JSON storage atomically."""
        d = os.path.dirname(self.history_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for chat history: {e}")
        temp_file = os.path.join(d, f".chat_history.{os.getpid()}_{int(time.time() * 1000)}.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_conversations.items()}, f, ensure_ascii=False, indent=2)
            os.replace(temp_file, self.history_file)
            self._history_mtime = os.path.getmtime(self.history_file)
        except Exception as e:
            logger.error(f"Error saving chat history to {self.history_file}: {e}")
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

    def _save_user_outfits(self):
        """Saves user selected outfits to persistent JSON storage."""
        d = os.path.dirname(self.outfits_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for outfits: {e}")
        try:
            with open(self.outfits_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_outfits.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user outfits to {self.outfits_file}: {e}")

    def _load_user_locations(self):
        """Loads user active locked locations from persistent JSON storage."""
        self.user_locations = {}
        if os.path.exists(self.locations_file):
            try:
                with open(self.locations_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    now = time.time()
                    for k, v in raw.items():
                        if not str(k).isdigit() or not isinstance(v, dict):
                            continue
                        uid = int(k)
                        if v.get("expires_at", 0) > now:
                            self.user_locations[uid] = v
            except Exception as e:
                logger.error(f"Error loading user locations: {e}")
                self.user_locations = {}
        else:
            self.user_locations = {}

    def _save_user_locations(self):
        """Saves user active locked locations to persistent JSON storage."""
        d = os.path.dirname(self.locations_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.error(f"Error creating dir for locations: {e}")
        try:
            with open(self.locations_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_locations.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user locations to {self.locations_file}: {e}")

    def detect_location_intent(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Detects if text mentions a specific physical location or room from LOCATION_PRESETS.
        Returns: (location_key, location_dict) or None.
        """
        if not text:
            return None
        low = text.lower()
        for loc_key, loc_info in LOCATION_PRESETS.items():
            for pat in loc_info.get("patterns", []):
                if re.search(pat, low):
                    return loc_key, loc_info
        return None

    def get_user_location(self, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves active locked location session for user if not expired.
        """
        if not user_id:
            return None
        uid = int(user_id)
        loc = self.user_locations.get(uid)
        if not loc:
            return None
        if time.time() > loc.get("expires_at", 0):
            self.user_locations.pop(uid, None)
            self._save_user_locations()
            return None
        return loc

    def set_user_location(
        self,
        user_id: int,
        key: str,
        duration_seconds: int = 7200,
        source: str = "chat"
    ) -> bool:
        """
        Locks the active location/scene for user (default 2 hours).
        """
        if not user_id:
            return False
        uid = int(user_id)
        if key in ("default", "auto", "clear"):
            self.user_locations.pop(uid, None)
            self._save_user_locations()
            logger.info(f"User {uid} location lock cleared to dynamic auto mode.")
            return True

        if key in LOCATION_PRESETS:
            loc_data = LOCATION_PRESETS[key]
            now = time.time()
            self.user_locations[uid] = {
                "key": key,
                "name": loc_data.get("name", key.title()),
                "prompt": loc_data.get("prompt", ""),
                "nsfw_prompt": loc_data.get("nsfw_prompt", loc_data.get("prompt", "")),
                "is_public": loc_data.get("is_public", False),
                "source": source,
                "set_at": now,
                "expires_at": now + duration_seconds
            }
            self._save_user_locations()
            logger.info(f"User {uid} location locked to '{key}' ({loc_data.get('name')}) for {duration_seconds}s (source={source}).")
            return True
        return False

    def clear_user_location(self, user_id: int):
        """Clears locked location for user."""
        self.set_user_location(user_id, "clear")

    @staticmethod
    def get_indonesian_scene_desc(scene: str) -> str:
        """
        Translates raw Danbooru scene prompts into clear, grounded Indonesian location/furniture descriptions.
        Prevents LLMs from confusing kasur with sofa or inventing non-existent rooms in captions.
        """
        s_low = (scene or "").lower()
        if any(k in s_low for k in ["bed", "pillows", "kasur", "ranjang", "bedroom"]):
            return "di atas kasur tempat tidur kamar (santai di kasur empuk)"
        if any(k in s_low for k in ["sofa", "couch", "living room", "ruang tv", "ruang tengah"]):
            return "di sofa ruang santai / ruang TV"
        if any(k in s_low for k in ["kitchen", "dapur", "cook", "masak"]):
            return "di dapur (area memasak/counter dapur)"
        if any(k in s_low for k in ["cafe", "coffee", "kafe", "starbucks"]):
            return "di meja kafe / coffee shop"
        if any(k in s_low for k in ["campus", "lecture hall", "classroom", "kuliah"]):
            return "di ruang kelas kuliah kampus"
        if any(k in s_low for k in ["library", "perpustakaan", "perpus"]):
            return "di perpustakaan kampus"
        if any(k in s_low for k in ["bathroom", "kamar mandi", "shower", "bath"]):
            return "di kamar mandi"
        if any(k in s_low for k in ["balcony", "balkon", "rooftop"]):
            return "di balkon / rooftop terbuka"
        if any(k in s_low for k in ["beach", "pantai"]):
            return "di pantai tepi laut"
        if any(k in s_low for k in ["car", "mobil"]):
            return "di dalam mobil (kursi mobil)"
        if any(k in s_low for k in ["park", "taman"]):
            return "di taman kota terbuka"
        if any(k in s_low for k in ["minimarket", "convenience"]):
            return "di minimarket"
        return "di kamar santai"

    def _load_all_personas(self):
        """Loads personas from default dictionary and local JSON files."""
        self.personas = dict(DEFAULT_PERSONAS)
        if os.path.exists(self.personas_dir):
            for fname in os.listdir(self.personas_dir):
                if fname.endswith(".json"):
                    key = fname[:-5].lower()
                    try:
                        with open(os.path.join(self.personas_dir, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            self.personas[key] = data
                    except Exception as e:
                        logger.error(f"Error loading persona {fname}: {e}")

    @staticmethod
    def get_language_directive(lang: Optional[str] = None) -> str:
        """Returns a strict language and tone constraint instruction for the LLM."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "id")).strip()
        low = cur_lang.lower()
        if low in ("id", "indonesia", "indonesian", "bahasa"):
            return (
                "ATURAN BAHASA WAJIB (BAHASA INDONESIA): Kamu WAJIB berbicara, menanggapi, dan membalas HANYA dalam Bahasa Indonesia santai sehari-hari (aku/kamu). "
                "KATA GANTI WAJIB 'AKU' & 'KAMU': Kamu WAJIB menggunakan kata ganti 'aku' untuk dirimu dan 'kamu' untuk lawan bicaramu. DILARANG KERAS menggunakan kata sapaan/slang tongkrongan kasar seperti 'lo', 'lu', 'elu', 'elo', 'gue', 'gw', 'gua'! "
                "KARAKTER BAIK, MANIS & ANTI-NYOLOT (SANGAT PENTING): Karaktermu adalah sosok pacar/teman yang baik hati, ramah, lembut, manis, penyayang, dan pengertian. DILARANG KERAS bersikap nyolot, judes, ketus, sinis, sarkastik, menantang, atau meremehkan lawan bicara (hindari kata-kata seperti 'apaan sih', 'dih', 'idih', 'sewot', 'bodo amat', 'ngapain lu', 'GR banget'). Selalu jaga nada bicara yang hangat, menenangkan, bersahabat, dan menyenangkan. "
                "DILARANG KERAS menerjemahkan pesan user ke bahasa Inggris, DILARANG membalas dalam bahasa Inggris atau Jepang, dan DILARANG menyalin/mengulang kalimat user. "
                "GAYA BICARA NATURAL & REALISTIS (ANTI-LEBAY): Bicara wajar dan santai saat chatting via pesan singkat. "
                "Jawab pertanyaan lawan bicaramu secara langsung, relevan, dan masuk akal. "
                "DILARANG KERAS bersikap lebay, teatrikal, alay, atau berlebihan (HINDARI monolog anime fiksi yang aneh, hindari desahan/ekspresi cringe seperti 'huh!', 'ih~', 'ya~' berlebihan). "
                "DILARANG KERAS bergaya seperti YouTuber, vlogger, selebgram, atau broadcast ke publik (DILARANG pakai kata 'gaes', 'guys', 'teman-teman', 'halo semua', 'intip aja yuk', 'konten', 'vlog', 'makasih udah nungguin'). Ini adalah chat pribadi 1-on-1. "
                "DILARANG KERAS bersikap defensif atau terus-menerus meyakinkan bahwa dirimu nyata/ada (DILARANG pakai kalimat 'biar kamu percaya aku beneran ada', 'nih buktinya', 'biar kamu yakin', 'jangan bohong lagi'). Bersikaplah percaya diri, hangat, dan wajar. "
                "ATURAN PANGGILAN & KATA GANTI: Gunakan 'aku' dan 'kamu' secara default. DILARANG memanggil 'sayang', 'babe', 'ayang', atau panggilan mesra lainnya KECUALI jika user sendiri yang secara eksplisit meminta dipanggil sayang atau user yang memanggilmu sayang lebih dulu. Jangan langsung menganggap diri sebagai pacar jika baru kenal; biarkan hubungan berkembang secara dinamis dan alami sesuai kenyamanan user. "
                "Panjang respon cukup 1-3 kalimat santai dan to the point."
            )
        elif low in ("en", "english"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern English. "
                "NEVER mix in Indonesian, Japanese, or other languages. "
                "NATURAL & REALISTIC TONE: Talk normally and casually like a real companion texting on chat. "
                "Directly answer questions with relevant, grounded responses. "
                "DO NOT be melodramatic, theatrical, overly cheesy, or cringe. Avoid fanfiction-like monologues. "
                "PRONOUNS & ADDRESS DIRECTIVE: Use 'I' and 'you' naturally. DO NOT use pet names like 'babe', 'honey', or 'darling' UNLESS the user explicitly asks for it or uses it first. Allow the relationship dynamic to unfold naturally. "
                "Use casual texting habits (1-3 natural sentences)."
            )
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual Japanese (日本語). "
                "NEVER mix in English, Indonesian, or other languages. "
                "Respond naturally and casually like texting a real-life partner. Directly answer questions, keep responses natural (1-3 sentences), and avoid overly theatrical or exaggerated anime monologues."
            )
        elif low in ("auto", "adaptive"):
            return (
                "LANGUAGE & TONE DIRECTIVE: Automatically and seamlessly match the language used by the user in the ongoing conversation. "
                "Keep your tone natural, grounded, casual, and realistic (1-3 sentences). "
                "Default to 'aku/kamu' (or 'I/you'). DO NOT use romantic pet names ('sayang', 'babe') unless explicitly initiated or requested by the user. Let the relationship develop dynamically. "
                "Do not be dramatic, overly cheesy, or cringe. Answer questions directly."
            )
        else:
            return (
                f"STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern {cur_lang}. "
                f"NEVER mix in other languages under any circumstances. Keep your tone natural, grounded, realistic, and affectionate like a real girlfriend texting (1-3 sentences). "
                f"Answer questions directly and avoid overly dramatic or theatrical responses."
            )


    @staticmethod
    def get_language_display_name(lang: Optional[str] = None) -> str:
        """Returns friendly human-readable display name for language."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "id")).strip()
        low = cur_lang.lower()
        if low in ("id", "indonesia", "indonesian", "bahasa"):
            return "Bahasa Indonesia 🇮🇩"
        elif low in ("en", "english"):
            return "English 🇬🇧"
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            return "Japanese (日本語) 🇯🇵"
        elif low in ("auto", "adaptive"):
            return "Auto-detect (Ikuti Chat) 🌐"
        else:
            return f"{cur_lang.title()} ✏️"

    def get_active_persona(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """Returns the currently active persona with strict language enforcement injected."""
        base = self.personas.get(self.active_key, DEFAULT_PERSONAS["runa"]).copy()
        raw_inst = base.get("system_instruction", "")
        # Remove any old generic language rule that might confuse local LLMs
        clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:[^.]*\.[^.]*\.[^.]*\.", "", raw_inst).strip()
        if "IMPORTANT LANGUAGE RULE:" in clean_inst:
            clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:.*?(?=(\. [A-Z]|$))", "", clean_inst).strip()
        
        lang_rule = self.get_language_directive(lang)
        base["system_instruction"] = f"{clean_inst} {lang_rule}"
        return base

    def set_active_persona(self, key: str) -> bool:
        """Switches active persona key."""
        key = key.lower()
        if key in self.personas:
            self.active_key = key
            if hasattr(self, "user_locked_outfit_prompts"):
                self.user_locked_outfit_prompts.clear()
            return True
        return False

    def list_personas(self) -> List[Tuple[str, str, str]]:
        """Returns list of available personas: (key, name, description)."""
        return [(k, p.get("name", k.title()), p.get("description", "")) for k, p in self.personas.items()]

    def detect_media_request(self, text: str) -> Tuple[bool, str]:
        """
        Analyzes user message to see if a photo or video was requested.
        Returns: (is_requested, media_type: 'photo' | 'video' | 'none')
        """
        lower = text.lower()
        for pat in VIDEO_INTENT_KEYWORDS:
            if re.search(pat, lower):
                return True, "video"

        for pat in PHOTO_INTENT_KEYWORDS:
            if re.search(pat, lower):
                return True, "photo"

        return False, "none"

    def is_conversational_media_request(self, text: str) -> bool:
        """
        Checks if a user message asking for a photo/video also contains conversational content,
        questions, or thoughts (e.g. 'aku belum ngantuk, minta pap donk kamu udah mau bobo?').
        Returns True if conversational, False if it is a pure media command (e.g. 'pap dong', 'minta pap').
        """
        is_media, _ = self.detect_media_request(text)
        if not is_media:
            return False

        has_question = ("?" in text)

        cleaned = text.lower()
        # Strip all photo & video triggers
        for pat in PHOTO_INTENT_KEYWORDS + VIDEO_INTENT_KEYWORDS:
            cleaned = re.sub(pat, " ", cleaned)

        # Strip common standalone media nouns, verbs, pronouns, and fillers
        media_tokens = [
            r"\b(foto|gambar|selfie|pap|pic|picture|photo|video|animasi)\b",
            r"\b(minta|kirim|liat|lihat|bagi|kasih|send|show|take|make|record|bikin|buat)\b",
            r"\b(kamu|dirimu|mu|lu|lo|you|your|diri)\b",
            r"\b(sayang|ayang|beb|babe|cinta|honey|dear)\b",
            r"\b(dong|donk|ya|yaa|deh|sih|plis|please|pls|now|sekarang|cepet|coba|ayo|yuk|sekali)\b"
        ]
        for token_pat in media_tokens:
            cleaned = re.sub(token_pat, " ", cleaned)

        cleaned = re.sub(r"[^\w\s]", " ", cleaned).strip()
        words = [w for w in cleaned.split() if len(w) > 1]

        # If user asked a question, or has >= 2 words or >= 8 characters of conversation remaining
        return has_question or len(words) >= 2 or len(cleaned) >= 8

    def detect_camera_angle_and_pose(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detects camera angle/perspective and body pose requested in the user prompt.
        Returns: (angle_danbooru_prompt, pose_danbooru_prompt)
        """
        if not text:
            return None, None
        low = text.lower()

        detected_angle = None
        for patterns, angle_prompt in CAMERA_ANGLES:
            if any(re.search(pat, low) for pat in patterns):
                detected_angle = angle_prompt
                break

        detected_pose = None
        for patterns, pose_prompt in BODY_POSES:
            if any(re.search(pat, low) for pat in patterns):
                detected_pose = pose_prompt
                break

        return detected_angle, detected_pose

    def detect_intimate_position(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Detects explicit intimate / sexual positions (e.g. doggy style, missionary, cowgirl, mating press, prone bone, standing).
        Returns: (positive_position_prompt, negative_position_prompt)
        """
        if not text:
            return None, None
        low = text.lower()
        for patterns, pos_prompt, neg_prompt in INTIMATE_SEX_POSITIONS:
            if any(re.search(pat, low) for pat in patterns):
                return pos_prompt, neg_prompt
        return None, None

    def detect_anatomy_cues(self, text: str) -> Optional[str]:
        """
        Detects specific intimate anatomy parts requested in the user prompt
        (e.g. breasts/nenen/toket, thighs/paha, butt/pantat, stomach/perut).
        Returns: Danbooru prompt segment or None.
        """
        if not text:
            return None
        low = text.lower()
        parts = []
        for patterns, cue_prompt in ANATOMY_CUES:
            if any(re.search(pat, low) for pat in patterns):
                parts.append(cue_prompt)

        # If user is asking for lap sitting / sitting on lap, do not treat as an isolated thigh anatomy close-up
        if any(re.search(pat, low) for pat in [r"\b(duduk\s+di\s+paha|pangku|dipangku|sit\s+on\s+(?:my\s+)?lap|on\s+my\s+lap)\b"]):
            parts = [p for p in parts if "thighs" not in p]

        return ", ".join(parts) if parts else None

    def detect_visual_scene_moment(
        self,
        user_text: str,
        reply_text: str = "",
        llm_client: Any = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Detects vivid narrative / visual novel moments (CG scenes) where waifu proactively
        generates and sends an accompanying photo without user needing to manually ask for pap.
        Supports both predefined romantic/story tropes and fully dynamic setting transitions
        (e.g. waiting at bus stop, campus lobby, rainy days, rooftop, cinema, convenience store).
        Returns: (is_scene_moment, scene_prompt_override)
        """
        u_low = (user_text or "").lower()
        r_low = (reply_text or "").lower()
        comb = f"{u_low} {r_low}"

        # 1. Action Tag or explicit photo phrases emitted in reply
        if re.search(r"\[(ACTION:\s*)?(SEND_PAP|SEND_SELFIE|PAP)\]", reply_text, re.IGNORECASE):
            return True, None
        if any(p in r_low for p in ["aku fotoin ya", "aku kirim foto ya", "nih foto spesial buat kamu", "aku pap buat kamu", "foto ini buat kamu", "here is a photo for you"]):
            return True, None

        # 2. Lap sitting scene: user invites / waifu sits on lap
        lap_triggers_u = [r"\b(duduk\s+di\s+paha|di\s+pangkuan|pangku|dipangku|sit\s+on\s+(?:my\s+)?lap|on\s+my\s+lap)\b"]
        lap_triggers_r = [r"\b(moves\s+to\s+sit\s+on\s+your\s+lap|sits\s+on\s+your\s+lap|duduk\s+di\s+paha|duduk\s+di\s+pangkuan|sitting\s+on\s+your\s+lap)\b"]
        if any(re.search(pat, u_low) for pat in lap_triggers_u) or any(re.search(pat, r_low) for pat in lap_triggers_r):
            return True, "sitting on viewer lap, sitting closely on lap, intimate POV perspective, smiling warmly up at viewer, affectionate cozy cuddle posture"

        # 3. Outfit appreciation & teasing: user compliments outfit or body, waifu flaunts clothes
        outfit_triggers_u = [
            r"\b(baju\s+kamu|outfit\s+kamu|pakaian\s+kamu|baju\s+yang\s+kamu\s+pake)\b",
            r"\b(cantik\s+dan\s+seksi|seksi\s+banget|sangat\s+cantik|sangat\s+seksi)\b",
            r"\b(cute\s+outfit|nice\s+dress|looks\s+sexy|great\s+outfit)\b"
        ]
        outfit_triggers_r = [
            r"\b(glances\s+down\s+at\s+her\s+own\s+clothes|tugs\s+at\s+her\s+skirt|usual\s+outfit|show\s+a\s+bit\s+more\s+skin|bajuku|outfitku)\b"
        ]
        if (any(re.search(pat, u_low) for pat in outfit_triggers_u) and any(re.search(pat, r_low) for pat in outfit_triggers_r)) or \
           (any(re.search(pat, u_low) for pat in outfit_triggers_u) and any(w in u_low for w in ["cantik", "seksi", "sexy", "gorgeous"])):
            return True, "standing and showing cute outfit, tugging skirt playfully, blushing sweet smile, charming pose, admiring her clothes"

        # 4. Intimate Cuddling / Hugging
        cuddle_triggers_u = [r"\b(sambil\s+peluk|hangat\s+sambil\s+peluk|peluk\s+kamu|boleh\s+peluk|cuddle|hug\s+you|snuggle\s+together)\b"]
        cuddle_triggers_r = [r"\b(moves\s+closer|places\s+her\s+hand\s+on\s+your\s+arm|cozying\s+up|snuggles\s+closer|memeluk|merapatkan\s+tubuh)\b"]
        if (any(re.search(pat, u_low) for pat in cuddle_triggers_u) and any(re.search(pat, r_low) for pat in cuddle_triggers_r)):
            return True, "cozy intimate cuddle, gentle affectionate hug, resting head close to viewer, warm romantic embrace"

        # 5. Intimate Touch / Sensual Body Stroking (NSFW physical escalation)
        touch_triggers = [r"\b(touch\s+(?:first|me|you|slowly|your\s+skin|my\s+waist)|stroke\s+(?:me|you|there)|sentuh|elus|meraba|raba)\b"]
        if any(re.search(pat, comb) for pat in touch_triggers) and any(w in comb for w in ["warm", "slowly", "shaking", "flustered", "body", "skin", "waist", "heart", "rasa", "meremang"]):
            return True, "blushing sensual expression, arching body gently, hands on waist, trembling with pleasure, soft dim intimate lighting, detailed glowing skin"

        # 6. Lifting Skirt / Parting Legs / Wetness (NSFW visual reveal)
        wet_triggers = [r"\b(how\s+wet|see\s+how\s+wet|wet\s+you\s+are|part(?:ing)?\s+(?:your\s+|my\s+)?legs|spread\s+(?:your\s+|my\s+)?legs|under\s+(?:your\s+|my\s+)?skirt|lifting\s+my\s+skirt|ngangkang|basah)\b"]
        if any(re.search(pat, comb) for pat in wet_triggers):
            return True, "lifting skirt with trembling fingers, parting slender legs, exposed panties, wet and trembling, blushing intensely, looking down shyly, intimate bedroom POV, sensual lighting"

        # 7. Oral / Tasting / Ecstatic Arching (NSFW climax escalation)
        taste_triggers = [r"\b(taste\s+(?:you|me)|lick\s+(?:you|me)|tongue\s+against|jilat|hisap|tangling\s+in\s+your\s+hair|arching\s+off\s+the\s+bed)\b"]
        if any(re.search(pat, comb) for pat in taste_triggers):
            return True, "arching body off bed in ecstasy, head tilted back, parting slender legs, ecstatic blushing face, open mouth soft moan, intimate bedroom view, sensual cinematic lighting"

        # 8. Study buddy / Doing homework together (visual novel study moment)
        study_triggers_u = [r"\b(ngerjain\s+pr|mengerjakan\s+pr|belajar\s+bareng|study\s+together|homework)\b"]
        study_triggers_r = [r"\b(study\s+buddy|studying\s+together|mengerjakan\s+pr|buku\s+pelajaran)\b"]
        if any(re.search(pat, u_low) for pat in study_triggers_u) and any(re.search(pat, r_low) for pat in study_triggers_r):
            return True, "sitting next to viewer at study desk, studying together, open textbook and notebooks on table, cute study buddy pose, gentle smile"

        # 9. Cafe & Coffee / Aesthetic hangout
        cafe_triggers = [r"\b(cafe|kafe|coffee|kopi|ngopi|boba|matcha|starbucks|cappuccino|latte|nongkrong\s+di\s+kafe)\b"]
        if any(re.search(pat, comb) for pat in cafe_triggers):
            return True, "sitting at aesthetic cafe table holding a warm beverage, beautiful cafe bokeh background, sweet girlfriend date perspective"

        # 10. Morning / Breakfast / Waking up
        morning_triggers = [r"\b(pagi|bangun|sarapan|morning|selamat\s+pagi|baru\s+bangun)\b"]
        if any(re.search(pat, comb) for pat in morning_triggers):
            return True, "cozy morning bedroom setting, soft morning sunlight, oversized comfortable morning shirt, sweet gentle sleepy smile"

        # 11. Bedtime / Sleepy / Pajamas / Nighttime / Kasur
        bed_triggers = [r"\b(tidur|ngantuk|piyama|pajamas|selimut|bantal|bobo|tiduran|kasur|tempat\s+tidur|selamat\s+malam|good\s*night)\b"]
        if any(re.search(pat, comb) for pat in bed_triggers):
            return True, "relaxing on comfortable bed with fluffy pillows and warm blanket, soft dim bedside lamp glow, sleepy sweet expression"

        # 12. Kosan / Kamar / Cozy Home / Sofa relaxing
        home_triggers = [r"\b(kosan|kamar|apartemen|rumah|sofa|rebahan|mager|santai\s+di\s+(?:kamar|kosan|rumah))\b"]
        if any(re.search(pat, comb) for pat in home_triggers):
            return True, "relaxing comfortably in cozy modern apartment room, soft warm lighting, smiling sweetly at viewer from sofa, intimate girlfriend POV"

        # 13. Food / Culinary / Cooking / Snacks / Eating
        food_triggers = [r"\b(makan|masak|nyiapin\s+makan|dapur|kitchen|jajan|kuliner|camilan|snack|lapar|cemilan|makan\s+siang|makan\s+malam)\b"]
        if any(re.search(pat, comb) for pat in food_triggers):
            return True, "enjoying tasty food and warm snacks, holding food playfully, cozy inviting culinary atmosphere, cheerful smiling expression"

        # 14. Campus / Lecture / College life
        campus_triggers = [r"\b(kampus|kuliah|kelas|dosen|makul|tugas|skripsi|perpustakaan|perpus|library)\b"]
        if any(re.search(pat, comb) for pat in campus_triggers):
            return True, "sitting at wooden study desk in modern university setting, open study books and laptop, cute student aesthetic, gentle smile"

        # 15. Park / Garden / Scenic outdoor walk
        park_triggers = [r"\b(taman|park|garden|jogging|jalan\s+sore|jalan-jalan|piknik|picnic|semilir\s+angin)\b"]
        if any(re.search(pat, comb) for pat in park_triggers):
            return True, "walking along scenic park pathway, natural outdoor lighting, gentle breeze in hair, sweet blushing smile"

        # 16. Beach / Sea / Ocean
        beach_triggers = [r"\b(pantai|beach|laut|ocean|pantai|pasir\s+pantai)\b"]
        if any(re.search(pat, comb) for pat in beach_triggers):
            return True, "walking along tropical beach shore, beautiful ocean horizon, gentle sea breeze, sweet smiling expression"

        # 17. Mall / Shopping / Arcade
        mall_triggers = [r"\b(mall|belanja|shopping|arcade|game\s+center|timezone|mesin\s+capit)\b"]
        if any(re.search(pat, comb) for pat in mall_triggers):
            return True, "walking in vibrant illuminated shopping mall, modern storefronts, stylish cute outfit, dynamic ambient lighting"

        # 18. Affectionate / Missing you / Cute clingy girlfriend moments
        affection_triggers = [r"\b(kangen|sayang|manja|gemas|pengen\s+ketemu|temenin|rindu|sweet|lucu|pengen\s+dideketmu)\b"]
        if any(re.search(pat, comb) for pat in affection_triggers):
            return True, "intimate romantic close-up, warm tender expression, gentle blush, affectionate loving gaze directly at viewer"

        # 19. Dynamic Narrative Setting Transitions:
        # a) Bus Stop / Halte Bis (with rain or fair weather)
        bus_stop_triggers = [r"\b(halte(?:\s+bis|\s+bus)?|bus\s+stop|shelter|halte)\b"]
        if any(re.search(pat, comb) for pat in bus_stop_triggers):
            if any(re.search(pat, comb) for pat in [r"\b(hujan|gerimis|rain|wet|payung|umbrella)\b"]):
                return True, "waiting at rainy bus stop shelter, holding umbrella, wet asphalt, rain droplets, atmospheric street lighting, cinematic depth of field"
            return True, "waiting at outdoor bus stop shelter, sitting on bench, bus stop sign, atmospheric street perspective, cinematic depth of field"

        # b) Campus Lobby / Atrium / University Hallway
        lobby_triggers = [r"\b(lobby\s+kampus|lobi\s+kampus|lobby|lobi|atrium|lorong\s+kampus|gedung\s+fakultas|campus\s+lobby)\b"]
        if any(re.search(pat, comb) for pat in lobby_triggers):
            return True, "standing inside modern university campus lobby, open atrium, university building interior, clean bright indoor lighting, soft bokeh"

        # c) Rain / Sheltering / Cozy rainy day
        rain_triggers = [r"\b(kehujanan|berteduh|hujan\s+lebat|hujan\s+deras|bawa\s+payung|sheltering\s+from\s+rain|caught\s+in\s+rain)\b"]
        if any(re.search(pat, comb) for pat in rain_triggers):
            return True, "sheltering from rain under awning, holding transparent umbrella, wet reflections on pavement, cozy romantic rainy day atmosphere, atmospheric street lighting"

        # d) Rooftop / Balcony at Sunset
        rooftop_triggers = [r"\b(rooftop|balkon|atap\s+gedung|skyline|balcony)\b"]
        if any(re.search(pat, comb) for pat in rooftop_triggers):
            return True, "standing on open rooftop terrace at sunset, city skyline background, golden hour sunset lighting, gentle breeze"

        # e) Cinema / Movie Date
        cinema_triggers = [r"\b(bioskop|nonton\s+film|cinema|movie\s+theater)\b"]
        if any(re.search(pat, comb) for pat in cinema_triggers):
            return True, "sitting in cinema lobby holding cinema ticket, movie posters in soft blur background, cozy dim ambient lighting"

        # f) Minimarket / Convenience Store
        convenience_triggers = [r"\b(minimarket|indomaret|alfamart|konbini|convenience\s+store)\b"]
        if any(re.search(pat, comb) for pat in convenience_triggers):
            return True, "standing in modern Japanese-style convenience store aisle, shelves with snacks and drinks, bright clean fluorescent lighting"

        # g) Train Station / Stasiun
        station_triggers = [r"\b(stasiun|peron|kereta|train\s+station|subway\s+platform)\b"]
        if any(re.search(pat, comb) for pat in station_triggers):
            return True, "standing at modern train station platform, train tracks, platform bench, commuter ambiance"

        # 7. LLM-Assisted Dynamic Setting Fallback (for novel or arbitrary narrative locations)
        if llm_client and hasattr(llm_client, "chat") and any(w in comb for w in ["lagi di", "nunggu di", "sedang di", "ketemuan di", "waiting at", "at the", "di "]):
            try:
                extract_prompt = [
                    {
                        "role": "system",
                        "content": (
                            "You are an anime visual scene extractor for Stable Diffusion / Danbooru. "
                            "Determine if the user/waifu dialogue describes a specific physical setting or location. "
                            "If yes, output ONLY 8-15 English Danbooru descriptive visual tokens describing the setting and background elements. "
                            "If it is just generic small talk without any specific location, output 'NONE'. "
                            "Example: 'waiting in a cozy coffee shop, wooden table, steam from cup, bokeh lights'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"User: '{user_text}'. Waifu: '{reply_text}'. What is the visual setting?"
                    }
                ]
                extracted_scene, _ = llm_client.chat(extract_prompt, max_tokens=35)
                if extracted_scene and "none" not in extracted_scene.lower() and len(extracted_scene.strip()) >= 8:
                    clean_extracted = re.sub(r"^(Setting|Scene|Background|Visuals?)\s*:\s*", "", extracted_scene.strip(), flags=re.I).strip().strip('"\'')
                    logger.info(f"LLM dynamically detected visual novel scene: {clean_extracted}")
                    return True, clean_extracted
            except Exception as e_dyn:
                logger.debug(f"LLM scene detection error: {e_dyn}")

        return False, None

    def list_outfits(self) -> List[Tuple[str, str]]:
        """Returns list of (key, name) for all outfit presets."""
        return [(k, v["name"]) for k, v in OUTFIT_PRESETS.items()]

    def get_preset_outfit(self, key: str, persona_key: Optional[str] = None) -> Dict[str, str]:
        """Resolves outfit preset with persona-specific concrete colors for strict visual consistency."""
        pkey = (persona_key or self.active_key or "runa").lower()
        base = OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"]).copy()
        persona_colors = PERSONA_OUTFIT_COLORS.get(pkey, {})
        if key in persona_colors:
            base["prompt"] = persona_colors[key]
        return base

    def get_user_outfit_details(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns complete details of the active outfit state:
        - mode: 'auto' | 'session' | 'locked'
        - key: outfit key (or 'default' for auto)
        - name: display name
        - raw_name: preset display name
        - dynamic_name: name of current student schedule outfit
        - is_locked: bool
        - is_session: bool
        - expires_at: Optional[float]
        """
        uid = int(user_id) if user_id else 0
        now = time.time()

        cur_hour = time.localtime().tm_hour
        routine = get_hourly_routine(cur_hour, persona_key=self.active_key)
        dynamic_name = routine.get("outfit_name", "Pakaian Harian")

        rec = self.user_outfits.get(uid)

        # 1. Check permanently locked outfit
        if isinstance(rec, dict) and rec.get("mode") == "locked":
            key = rec.get("key", "default")
            preset_name = OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])["name"]
            return {
                "key": key,
                "name": f"{preset_name} 🔒",
                "raw_name": preset_name,
                "mode": "locked",
                "source": rec.get("source", "manual"),
                "is_locked": True,
                "is_session": False,
                "expires_at": None,
                "dynamic_name": dynamic_name
            }

        # 2. Check active temporary session outfit
        sess = self.session_outfits.get(uid)
        if sess:
            exp = sess.get("expires_at", 0)
            if now < exp:
                key = sess.get("key", "default")
                preset_name = OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])["name"]
                return {
                    "key": key,
                    "name": f"{preset_name} (Sesi Aktif)",
                    "raw_name": preset_name,
                    "mode": "session",
                    "source": sess.get("source", "auto"),
                    "is_locked": False,
                    "is_session": True,
                    "expires_at": exp,
                    "dynamic_name": dynamic_name
                }
            else:
                logger.info(f"Session outfit '{sess.get('key')}' expired for user {uid}.")
                self.session_outfits.pop(uid, None)
                if isinstance(rec, dict) and rec.get("mode") == "session":
                    self.user_outfits[uid] = {"key": "default", "mode": "auto", "undress_stage": 0}
                    self._save_user_outfits()

        # 3. Default: Auto Dynamic Mode
        return {
            "key": "default",
            "name": f"🌟 Otomatis ({dynamic_name})",
            "raw_name": dynamic_name,
            "mode": "auto",
            "source": "auto",
            "is_locked": False,
            "is_session": False,
            "expires_at": None,
            "dynamic_name": dynamic_name
        }

    def get_user_outfit(self, user_id: int) -> Tuple[str, str]:
        """
        Returns (key, name) of active outfit for user.
        Preserves backwards-compatibility with all existing callers and tests.
        """
        details = self.get_user_outfit_details(user_id)
        return details["key"], details["raw_name"]

    def set_user_outfit(
        self,
        user_id: int,
        key: str,
        is_locked: bool = False,
        duration_seconds: int = 3600,
        source: str = "auto"
    ) -> bool:
        """
        Sets chosen outfit preset for user.
        - If key in ('default', 'auto'): Reverts to dynamic auto mode.
        - If is_locked is True: Locks this outfit permanently until manually unlocked.
        - Otherwise: Sets a temporary session outfit that naturally expires on activity change or timeout.
        """
        uid = int(user_id) if user_id else 0
        now = time.time()

        if key in ("default", "auto"):
            getattr(self, "user_locked_outfit_prompts", {}).pop(uid, None)
            self.session_outfits.pop(uid, None)
            self.user_outfits[uid] = {"key": "default", "mode": "auto", "undress_stage": 0, "updated_at": now}
            self._save_user_outfits()
            logger.info(f"User {uid} outfit reset to dynamic auto mode.")
            return True

        if key in OUTFIT_PRESETS:
            getattr(self, "user_locked_outfit_prompts", {}).pop(uid, None)
            stage = 4 if key == "nude" else 0
            if is_locked:
                self.session_outfits.pop(uid, None)
                self.user_outfits[uid] = {
                    "key": key,
                    "mode": "locked",
                    "source": source,
                    "undress_stage": stage,
                    "updated_at": now
                }
                logger.info(f"User {uid} outfit locked to '{key}' (source={source}).")
            else:
                sess = {
                    "key": key,
                    "mode": "session",
                    "source": source,
                    "undress_stage": stage,
                    "set_at": now,
                    "expires_at": now + duration_seconds,
                    "photos_count": 0
                }
                self.session_outfits[uid] = sess
                self.user_outfits[uid] = sess
                logger.info(f"User {uid} session outfit set: '{key}' (source={source}, expires in {duration_seconds}s).")
            self._save_user_outfits()
            return True

        return False

    def clear_session_outfit(self, user_id: int) -> bool:
        """Clears active session outfit and reverts to auto dynamic mode."""
        uid = int(user_id) if user_id else 0
        getattr(self, "user_locked_outfit_prompts", {}).pop(uid, None)
        details = self.get_user_outfit_details(uid)
        if details.get("is_session"):
            self.session_outfits.pop(uid, None)
            self.user_outfits[uid] = {"key": "default", "mode": "auto", "undress_stage": 0, "updated_at": time.time()}
            self._save_user_outfits()
            logger.info(f"Session outfit cleared for user {uid}, reverted to dynamic auto mode.")
            return True
        return False

    def get_undress_stage(self, user_id: Optional[int] = None) -> int:
        """Returns the sequential undress stage (0=clothed, 1=shirt_off, 2=bottoms_off, 3=bra_off, 4=nude)."""
        if not user_id:
            return 0
        rec = self.user_outfits.get(int(user_id), {})
        return rec.get("undress_stage", 0)

    def set_undress_stage(self, user_id: int, stage: int) -> int:
        """Updates and persists sequential undress stage (0 to 4) for user."""
        uid = int(user_id)
        stage = max(0, min(4, int(stage)))
        rec = self.user_outfits.get(uid, {"mode": "auto"})
        rec["undress_stage"] = stage
        rec["updated_at"] = time.time()

        stage_outfit_map = {
            0: "default",
            1: "shirt_off",
            2: "bottoms_off",
            3: "bra_off",
            4: "nude"
        }
        rec["key"] = stage_outfit_map.get(stage, "default")
        self.user_outfits[uid] = rec
        self._save_user_outfits()
        stage_names = {
            0: "Pakaian Masih Lengkap (Kaos & Celana)",
            1: "Kaos Terlepas (Hanya mengenakan BH & Celana)",
            2: "Celana Terlepas (Set Pakaian Dalam Lengkap: BH & Celana Dalam)",
            3: "BH Terlepas (Topless bertelanjang dada & Celana Dalam)",
            4: "Telanjang Bulat (Tanpa Busana Sepenuhnya / Full Nude)"
        }
        logger.info(f"User {uid} undress stage updated -> Stage {stage} ({stage_names.get(stage)})")
        return stage

    def reset_undress_stage(self, user_id: int):
        """Resets sequential undress stage back to 0 (clothed)."""
        self.set_undress_stage(user_id, 0)

    def detect_undress_intent(self, user_text: str, current_stage: int = 0) -> Tuple[int, str, bool]:
        """
        Analyzes user message to determine sequential undressing progression:
        Stage 0: Clothed -> Stage 1: Kaos/baju -> Stage 2: Celana -> Stage 3: BH -> Stage 4: Celana Dalam/Nude.
        Returns: (target_stage, action_description, is_transition)
        """
        if not user_text:
            return (current_stage, "", False)

        lower = user_text.lower()

        # 0. Check reset request
        if re.search(r"\b(pake|pakai|kenakan)\s+(baju|pakaian|celana)\b|\b(sudah\s+selesai|selesai\s+dulu|berpakaian\s+lagi)\b|\b(put\s+on\s+clothes|get\s+dressed|dress\s+up|wear\s+clothes)\b", lower):
            return (0, "mengenakan pakaiannya kembali secara rapi", True)

        # 1. Direct jump to fully nude
        if re.search(r"\b(buka\s+semua|lepas\s+semua|buka\s+semuanya|lepas\s+semuanya|telanjang\s+bulat\s+sekarang|langsung\s+telanjang|take\s+off\s+everything|strip\s+naked|get\s+naked|completely\s+naked|fully\s+nude|take\s+it\s+all\s+off)\b", lower):
            return (4, "menanggalkan seluruh pakaiannya hingga telanjang bulat tanpa busana", True)

        # 2. Sequential general progression: 'buka lagi', 'lanjut buka', 'take off clothes', 'undress slowly', 'take off the rest'
        if re.search(r"\b(buka\s+lagi|lanjut\s+buka|buka\s+berikutnya|buka\s+selanjutnya|lepas\s+lagi|buka\s+satu\s*satu|buka\s+pelan\s*pelan|tahap\s+berikutnya|take\s+off\s+(?:your\s+)?clothes|take\s+off\s+the\s+rest|strip\s+slowly|undress\s+(?:you|slowly)|next\s+layer|sliding\s+off)\b", lower):
            next_stage = min(4, current_stage + 1)
            actions = {
                1: "melepas kaosnya secara perlahan, kini tersisa BH dan celana",
                2: "menurunkan dan melepas celananya, menyisakan set pakaian dalam (BH dan celana dalam)",
                3: "membuka kaitan BH-nya dan melepaskannya, kini topless dengan celana dalam",
                4: "menurunkan celana dalamnya hingga terlepas, kini sepenuhnya telanjang bulat tanpa busana"
            }
            return (next_stage, actions.get(next_stage, "membuka pakaian tahap berikutnya"), True)

        # 3. Stage 1: Kaos / Baju Atasan
        has_shirt_kw = bool(re.search(r"\b(?:(?:buka|lepas|copot)\s+(?:baju|kaos|atasan|t-?shirt|pakaian(?!\s+dalam))(?:mu|nya)?|take\s+off\s+(?:your\s+)?(?:shirt|top|t-?shirt|blouse))\b", lower))
        # 4. Stage 2: Celana / Bawahan
        has_pants_kw = bool(re.search(r"\b(?:(?:buka|lepas|copot|turunkan)\s+(?:celana(?!\s+dalam)|rok|bawahan|jeans|pants|skirt)(?:mu|nya)?|take\s+off\s+(?:your\s+)?(?:pants|skirt|jeans|shorts|bottoms))\b", lower))
        # 5. Stage 3: BH / Bra
        has_bra_kw = bool(re.search(r"\b(?:(?:buka|lepas|copot)\s+(?:bh|bra|kutang)(?:mu|nya)?|take\s+off\s+(?:your\s+)?bra)\b", lower))
        # 6. Stage 4: Celana Dalam / Panties
        has_panties_kw = bool(re.search(r"\b(?:(?:buka|lepas|copot|turunkan)\s+(?:cd|celana\s+dalam|panties|kancut|sempak|underwear)(?:mu|nya)?|take\s+off\s+(?:your\s+)?(?:panties|underwear))\b", lower))

        if has_shirt_kw:
            if current_stage == 0:
                return (1, "melepas kaosnya perlahan, kini tersisa BH dan celana", True)
            else:
                return (current_stage, "kaos sudah terlepas sebelumnya", False)

        if has_pants_kw:
            if current_stage == 0:
                # Sequential enforcement: Must start with shirt first!
                return (1, "membuka kaos terlebih dahulu sebelum celana secara berurutan", True)
            elif current_stage == 1:
                return (2, "menurunkan dan melepas celananya, kini hanya mengenakan set pakaian dalam (BH dan celana dalam)", True)
            else:
                return (current_stage, "celana sudah terlepas sebelumnya", False)

        if has_bra_kw:
            if current_stage < 2:
                # Sequential progression toward bra
                next_st = current_stage + 1
                return (next_st, "melepas pakaian tahap sebelumnya secara berurutan", True)
            elif current_stage == 2:
                return (3, "membuka kaitan BH-nya dan melepaskannya, topless bertelanjang dada dengan celana dalam", True)
            else:
                return (current_stage, "BH sudah terlepas sebelumnya", False)

        if has_panties_kw:
            if current_stage < 3:
                # Sequential progression toward panties
                next_st = current_stage + 1
                return (next_st, "melepas pakaian tahap sebelumnya secara berurutan", True)
            elif current_stage == 3:
                return (4, "menurunkan celana dalamnya hingga terlepas, kini sepenuhnya telanjang bulat tanpa busana", True)
            else:
                return (current_stage, "celana dalam sudah terlepas sebelumnya", False)

        # General undress trigger without specific part (e.g. 'buka dong', 'ayo buka')
        if re.search(r"\b(buka|lepas|copot)\s+(?:dong|sayang|ya|sekarang|pelan)\b", lower):
            if current_stage < 4:
                next_st = current_stage + 1
                return (next_st, "melepas pakaian tahap berikutnya secara berurutan", True)

        return (current_stage, "", False)

    def notify_photo_delivered(self, user_id: int):
        """Notifies persona manager that a photo was delivered with current outfit."""
        uid = int(user_id) if user_id else 0
        sess = self.session_outfits.get(uid)
        if sess:
            sess["photos_count"] = sess.get("photos_count", 0) + 1

    def check_context_shift(self, user_id: int, user_text: str) -> bool:
        """
        Inspects incoming chat message for changes in waifu activity or routine.
        If a session outfit is active, automatically clears it when routine changes!
        """
        uid = int(user_id) if user_id else 0
        details = self.get_user_outfit_details(uid)
        if not details.get("is_session"):
            return False

        t = user_text.lower()
        # Routine shifts that invalidate previous costume dress-up session:
        SHIFT_TRIGGERS = [
            r"\b(tidur|bobo|rebahan|ngantuk|good\s*night|selamat\s*malam|mimpi\s*indah)\b",
            r"\b(mandi|keramas|shower|bath|handuk)\b",
            r"\b(kuliah|kampus|kelas|dosen|makul|matkul|skripsi|praktikum|perpustakaan|perpus)\b",
            r"\b(cafe|kafe|kopi|coffee|starbucks|nongkrong)\b",
            r"\b(mall|belanja|shopping|bioskop|jalan-jalan)\b",
            r"\b(gym|olahraga|fitness|workout|jogging)\b",
            r"\b(pulang\s+ke\s+rumah|udah\s+di\s+rumah|santai\s+di\s+rumah|istirahat\s+di\s+kamar)\b"
        ]
        for pat in SHIFT_TRIGGERS:
            if re.search(pat, t):
                logger.info(f"Natural context shift detected for user {uid} ('{user_text[:30]}'). Reverting session outfit '{details['key']}' to auto.")
                self.clear_session_outfit(uid)
                return True
        return False

    def extract_contextual_scene(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        llm_client: Any = None,
        history: Optional[List[Dict[str, str]]] = None,
        conversational_reply: Optional[str] = None,
        is_nsfw: bool = False
    ) -> str:
        """
        Determines the visual scene/location for image generation based on
        explicit user prompt, waifu's conversational reply, locked active location, recent dialogue, or college routine.
        Uses strict word boundaries to prevent substring false-positives (e.g. 'makanannya' -> kitchen).
        """
        lower = (user_text or "").lower()
        reply_lower = (conversational_reply or "").lower()

        def _has_kw(text: str, keywords: List[str]) -> bool:
            if not text:
                return False
            pat = r"\b(?:" + "|".join(re.escape(k) for k in keywords) + r")\b"
            return bool(re.search(pat, text, re.IGNORECASE))

        def _resolve_scene_variation(desc: str) -> str:
            import random
            if "aesthetic cafe" in desc:
                return random.choice(CAFE_SCENE_VARIATIONS)
            if "bedroom" in desc or "fluffy pillows" in desc:
                return random.choice(BEDROOM_SCENE_VARIATIONS)
            return desc

        # 0. When a follow-up photo accompanies a conversational reply, extract from LLM FIRST
        #    so complex narratives (e.g. "street food viral dekat kampus") are captured verbatim without false keyword overrides
        if conversational_reply and llm_client and hasattr(llm_client, "chat"):
            try:
                extract_prompt = [
                    {
                        "role": "system",
                        "content": (
                            "You are an anime visual scene extractor for Stable Diffusion / Danbooru. "
                            "Given what the user asked and what the waifu JUST replied in chat, output ONLY 8-18 concise English Danbooru-style descriptive visual tokens "
                            "describing the EXACT physical location, background, weather, and props she just described (e.g. holding a bag of street food, warm stall lights). "
                            "Do NOT invent a different location (do NOT turn street food into a kitchen or campus into a bedroom). "
                            "Do NOT include character hair or eye colors."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"User said: '{user_text}'.\nWaifu JUST replied: '{conversational_reply}'.\nWhat exact visual scene & props are shown in this photo?"
                    }
                ]
                dyn_scene, _ = llm_client.chat(extract_prompt, max_tokens=45)
                if (
                    isinstance(dyn_scene, str)
                    and len(dyn_scene.strip()) >= 8
                    and "none" not in dyn_scene.lower()
                ):
                    clean_dyn = re.sub(r"^(Setting|Scene|Background|Visuals?)\s*:\s*", "", dyn_scene.strip(), flags=re.I).strip().strip('"\'')
                    logger.info(f"LLM aligned visual scene from conversational reply: {clean_dyn}")
                    return clean_dyn
            except Exception as e_dyn:
                logger.debug(f"LLM aligned scene extraction skipped: {e_dyn}")

        # 1. Location Locking Priority 1: Check if user_text or conversational_reply explicitly states a location from LOCATION_PRESETS
        combined_text = f"{user_text or ''} {conversational_reply or ''}".strip()
        loc_match = self.detect_location_intent(combined_text)
        if loc_match:
            loc_key, loc_info = loc_match
            if user_id:
                self.set_user_location(user_id, loc_key)
            if is_nsfw:
                if not loc_info.get("is_public", False):
                    return loc_info.get("nsfw_prompt", loc_info.get("prompt", ""))
                else:
                    return "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows"
            return _resolve_scene_variation(loc_info.get("prompt", ""))

        # 2. Location Locking Priority 2: Check active locked location session for this user
        active_loc = self.get_user_location(user_id) if user_id else None
        if active_loc:
            if is_nsfw:
                if not active_loc.get("is_public", False):
                    return active_loc.get("nsfw_prompt", active_loc.get("prompt", ""))
                else:
                    return "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows"
            return _resolve_scene_variation(active_loc.get("prompt", ""))

        # Keyword mapping for common anime / girlfriend situations & dynamic narrative settings
        # Ordered from most specific outdoor/culinary/public settings to indoor/campus settings
        SCENE_PATTERNS = [
            (["sensual", "romantic", "romantis", "intimate", "mesra", "lingerie", "pakaian dalam", "celana dalam", "bh", "bra", "panties", "topless", "telanjang", "bugil"],
             "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer"),
            (["bed", "sleep", "night", "tidur", "kasur", "piyama", "pajamas", "rebahan", "bangun", "selimut", "bantal", "telentang", "terlentang", "tengkurap", "habis mandi", "selesai mandi", "beres mandi"],
             "relaxing on bed with fluffy pillows, warm dim night bedroom lamp"),
            (["kamar mandi", "shower", "bath", "bathtub", "sedang mandi", "lagi mandi", "keramas", "berendam"],
             "standing in modern bathroom with soft steam, post-shower glow, bathroom mirror"),
            (["halte", "bus stop", "shelter", "halte bis", "halte bus", "angkot", "stasiun bis"],
             "waiting at outdoor bus stop shelter, sitting on bench, bus stop sign, atmospheric street perspective, cinematic depth of field"),
            (["lobby kampus", "lobi kampus", "lobby", "lobi", "atrium", "lorong kampus", "gedung fakultas", "hallway", "campus lobby"],
             "standing inside modern university campus lobby, open atrium, university building interior, clean bright indoor lighting, soft bokeh"),
            (["kehujanan", "berteduh", "hujan lebat", "hujan deras", "bawa payung", "payung", "gerimis", "hujan", "rain", "rainy", "umbrella"],
             "sheltering from rain under awning, holding transparent umbrella, wet reflections on pavement, cozy romantic rainy day atmosphere, atmospheric street lighting"),
            (["street food", "jajanan", "jajan", "kaki lima", "pinggir jalan", "angkringan", "warung", "kuliner", "festival makanan", "food stall", "bazaar", "food court", "pasar malam"],
             "standing outdoors by lively street food stalls, warm evening street lights, holding paper bag of warm snacks, festive outdoor culinary atmosphere"),
            (["nonton di kosan", "nonton di kamar", "nonton di rumah", "nonton netflix", "film di kosan", "nonton film di kosan", "nonton film di kamar", "nonton film di rumah", "nonton bareng di kosan", "nonton bareng di kamar", "nonton laptop"],
             "relaxing comfortably in cozy modern apartment room, watching movie on screen, cozy soft room lighting, intimate relaxed atmosphere"),
            (["rooftop", "balkon", "atap gedung", "skyline", "balcony"],
             "standing on open rooftop terrace at sunset, city skyline background, golden hour sunset lighting, gentle breeze"),
            (["bioskop", "cinema", "teater film", "popcorn"],
             "sitting in cinema lobby holding cinema ticket, movie posters in soft blur background, cozy dim ambient lighting"),
            (["minimarket", "indomaret", "alfamart", "konbini", "convenience store", "supermarket"],
             "standing in modern Japanese-style convenience store aisle, shelves with snacks and drinks, bright clean fluorescent lighting"),
            (["stasiun", "kereta", "peron", "mrt", "krl", "train station", "subway"],
             "standing at modern train station platform, train tracks, platform bench, commuter ambiance"),
            (["cafe", "coffee", "tea", "kafe", "kopi", "boba", "matcha", "nongkrong", "starbucks"],
             "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background"),
            (["kitchen", "cook", "cooking", "baking", "masak", "memasak", "masakin", "dapur", "kompor", "nyiapin makan"],
             "standing in modern cozy kitchen preparing food, warm domestic lighting"),
            (["taman", "taman kota", "park", "garden", "jogging", "jalan sore", "sepeda", "sepedaan", "piknik", "picnic"],
             "standing in blooming park, natural golden hour sunlight, dynamic selfie perspective"),
            (["beach", "ocean", "sea", "pantai", "laut", "kolam", "renang", "swim"],
             "walking along tropical beach, ocean sunset horizon, gentle sea breeze"),
            (["study", "library", "buku", "perpustakaan", "perpus"],
             "sitting at wooden study desk in quiet university library, bookshelves, open study books, soft lamp"),
            (["kampus", "kuliah", "kelas", "dosen", "makul", "tugas", "skripsi"],
             "sitting at wooden desk inside modern university lecture hall, college campus classroom background"),
            (["mall", "shopping", "belanja", "pameran"],
             "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting"),
            (["gym", "workout", "olahraga", "yoga", "fitness"],
             "wearing sporty athletic wear in bright modern gym studio"),
        ]

        def _resolve_scene_variation(desc: str) -> str:
            import random
            if "aesthetic cafe" in desc:
                return random.choice(CAFE_SCENE_VARIATIONS)
            if "bedroom" in desc or "fluffy pillows" in desc:
                return random.choice(BEDROOM_SCENE_VARIATIONS)
            return desc

        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-5:] if not m.get("content", "").startswith("[")]

        # 1. Explicit scene in waifu's current conversational reply (when present)
        if reply_lower:
            for keywords, scene_desc in SCENE_PATTERNS:
                if _has_kw(reply_lower, keywords):
                    if "bus stop" in scene_desc and _has_kw(reply_lower, ["hujan", "gerimis", "rain", "payung"]):
                        return "waiting at rainy bus stop shelter, holding umbrella, wet asphalt, rain reflections, atmospheric street lighting, cinematic depth of field"
                    return _resolve_scene_variation(scene_desc)

        # 2. Explicit scene in user text
        for keywords, scene_desc in SCENE_PATTERNS:
            if _has_kw(lower, keywords):
                # Contextual bonus: if bus stop and rain are mentioned together
                if "bus stop" in scene_desc and _has_kw(lower, ["hujan", "gerimis", "rain", "payung"]):
                    return "waiting at rainy bus stop shelter, holding umbrella, wet asphalt, rain reflections, atmospheric street lighting, cinematic depth of field"
                return _resolve_scene_variation(scene_desc)

        # 3. Context from ongoing chat history (newest turn first so latest setting wins)
        for hist_turn in reversed(clean_turns):
            hist_low = (hist_turn or "").lower()
            hist_loc_match = self.detect_location_intent(hist_low)
            if hist_loc_match:
                h_key, h_info = hist_loc_match
                if user_id:
                    self.set_user_location(user_id, h_key)
                if is_nsfw:
                    if not h_info.get("is_public", False):
                        return h_info.get("nsfw_prompt", h_info.get("prompt", ""))
                    else:
                        return "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows"
                return _resolve_scene_variation(h_info.get("prompt", ""))
            for keywords, scene_desc in SCENE_PATTERNS:
                if _has_kw(hist_low, keywords):
                    return _resolve_scene_variation(scene_desc)

        # 4. LLM dynamic setting extraction for novel/arbitrary story locations
        if llm_client and hasattr(llm_client, "chat") and len(clean_turns) > 0:
            try:
                extract_prompt = [
                    {
                        "role": "system",
                        "content": (
                            "You are an anime visual scene extractor for Stable Diffusion / Danbooru. "
                            "Analyze the dialogue and output ONLY 8-15 concise English Danbooru-style descriptive visual tokens "
                            "describing the current physical setting, location, weather, and background elements. "
                            "Do not include character hair or eye color. Example output: 'waiting at rainy bus stop shelter, holding umbrella, wet asphalt, streetlights'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"User: '{user_text}'. Recent conversation: {' | '.join(clean_turns[-3:])}. What is the visual setting?"
                    }
                ]
                dyn_scene, _ = llm_client.chat(extract_prompt, max_tokens=40)
                if isinstance(dyn_scene, str) and len(dyn_scene.strip()) >= 8 and "none" not in dyn_scene.lower():
                    clean_dyn = re.sub(r"^(Setting|Scene|Background|Visuals?)\s*:\s*", "", dyn_scene.strip(), flags=re.I).strip().strip('"\'')
                    logger.info(f"LLM dynamically extracted visual scene: {clean_dyn}")
                    return clean_dyn
            except Exception as e_dyn:
                logger.debug(f"LLM dynamic scene extraction skipped: {e_dyn}")

        # 5. Routine schedule activity
        ctx = detect_contextual_activity_and_outfit(
            conversational_reply or user_text,
            clean_turns,
            persona_key=self.active_key
        )
        if ctx.get("scene"):
            logger.info(f"Student routine context extracted scene: {ctx['scene']} ({ctx['activity']})")
            return ctx["scene"]

        return "sitting comfortably in modern cozy room, soft ambient morning lighting"

    def _match_explicit_outfit_text(
        self,
        text: str,
        allow_romantic: bool = True,
        allow_ambiguous_undress: bool = True
    ) -> Optional[Tuple[str, bool]]:
        """
        Matches explicit clothing / undress state mentioned in a single chat message.
        Ignores negated or undressed items (e.g. 'buka piyama', 'lepas celana dalam')
        so taking off pajamas to wear only bra & panties resolves cleanly to 'bottoms_off'.
        Returns: (preset_key, is_nude) or None.
        """
        if not text:
            return None
        lower = text.lower()
        neg_prefix = r"(?:buka|lepas|copot|melepas|membuka|turunkan|menanggalkan|tanpa|ga\s+pake|gak\s+pake|ngga\s+pake|tidak\s+pake)\s+(?:\w+\s+){0,2}"

        def _has_pos_kw(keywords: List[str]) -> bool:
            kw_alt = "|".join(re.escape(k) for k in keywords)
            for m in re.finditer(rf"\b(?:{kw_alt})\b", lower, re.IGNORECASE):
                prefix = lower[max(0, m.start() - 32):m.start()]
                if not re.search(rf"{neg_prefix}$", prefix, re.IGNORECASE):
                    return True
            return False

        # 1. Explicit Topless / Bra Off (BH dilepas -> hanya celana dalam)
        if re.search(
            r"\b(topless|bertelanjang\s+dada|tanpa\s+(?:bh|bra)|(?:buka|lepas|copot)\s+(?:bh|bra))\b",
            lower,
        ):
            return ("bra_off", True)
        if (
            re.search(r"\b(?:cuma|hanya)\s+(?:pake|pakai|memakai)\s+(?:celana\s+dalam|panties|cd)\b", lower)
            and not re.search(r"\b(?:bh|bra|kutang)\b", lower)
        ):
            return ("bra_off", True)

        # 2. Explicit Bra & Panties / Lingerie / Underwear (checked BEFORE 'nude' and BEFORE 'pajamas')
        if _has_pos_kw(["lingerie"]):
            return ("lingerie", False)
        if (
            _has_pos_kw([
                "pakaian dalam", "bh", "bra", "kutang", "celana dalam",
                "panties", "sempak", "kancut", "underwear",
                "baju tidur seksi", "sexy sleepwear"
            ])
            or re.search(r"\b(?:pake|pakai|memakai|tersisa|tinggal|cuma|hanya)\s+cd\b", lower)
        ):
            return ("bottoms_off", False)

        # 3. Explicit Full Nude / Intimate Anatomy
        unambiguous_nude = [
            "tanpa busana", "tanpa baju", "tanpa pakaian", "telanjang", "telanjang bulat",
            "bugil", "nude", "naked", "completely naked", "unclothed", "bottomless",
            "no clothes", "tanpa sehelai benang", "uncensored", "nsfw",
            "nenen", "toket", "tetek", "payudara", "memek", "vagina",
            "buka semua", "buka semuanya", "lepas semua", "lepas semuanya",
            "buka handuk", "buka handuknya", "lepas handuk", "lepas handuknya",
            "copot handuk", "copot handuknya", "tarik handuk", "tarik handuknya",
            "jatuhkan handuk", "jatuhkan handuknya", "drop towel", "drop your towel",
            "take off towel", "take off your towel", "remove towel", "remove your towel",
            "foto nenen", "pap nenen", "foto toket", "pap toket",
            "foto telanjang", "pap telanjang", "foto bugil", "pap bugil",
            "gak pake baju", "ngga pake baju", "ga pake baju", "ga pake busana",
            "gak pake pakaian", "ga pake pakaian",
        ]
        if _has_pos_kw(unambiguous_nude):
            return ("nude", True)
        if allow_ambiguous_undress and re.search(
            r"\b(lepas\s+baju|buka\s+baju|buka\s+pakaian|buka\s+celana|buka\s+handuk(?:nya)?|lepas\s+handuk(?:nya)?)\b", lower
        ):
            return ("nude", True)

        # 4. Explicit Towel Intent
        if _has_pos_kw([
            "handuk", "pake handuk", "pakai handuk", "memakai handuk", "towel", "bath towel"
        ]):
            return ("towel", False)

        # 5. Clothed Presets (word-boundary + undress-negation aware so 'buka piyama' won't match pajamas)
        DYNAMIC_PRESET_KEYWORDS = [
            ("bikini", ["bikini", "swimsuit", "baju renang"]),
            ("pajamas", ["piyama", "pajamas", "baju tidur", "daster", "camisole"]),
            ("campus_casual", ["baju kuliah", "outfit kuliah", "seragam kampus"]),
            ("mall_casual", ["baju mall", "streetwear"]),
            ("cafe_cozy", ["baju cafe", "cozy knit"]),
            ("maid", ["maid", "pelayan", "french maid"]),
            ("kimono", ["kimono", "yukata"]),
            ("school_jk", ["seragam sekolah", "school jk", "sailor uniform", "baju sekolah"]),
            ("gym", ["baju gym", "baju olahraga", "activewear"]),
            ("dress", ["dress", "gaun", "cocktail dress"]),
            ("sweater", ["sweater", "rajut"]),
        ]
        for key, keywords in DYNAMIC_PRESET_KEYWORDS:
            if _has_pos_kw(keywords):
                return (key, False)

        # 6. Romantic / Sensual Slip Dress (lowest explicit priority)
        if allow_romantic and _has_pos_kw([
            "sensual", "romantic", "romantis", "intimate", "mesra",
            "kiss", "bedroom setting", "loving gaze", "seksi", "sexy"
        ]):
            return ("romantic", False)

        return None

    def sync_outfit_from_chat(self, user_id: int, user_text: str = "", reply_text: str = "") -> Optional[str]:
        """
        Synchronizes stored outfit/undress state with the newest explicit outfit described
        in either the waifu's reply or the user's message (unless outfit is locked or manual /outfit).
        """
        if not user_id:
            return None
        details = self.get_user_outfit_details(user_id)
        if details.get("is_locked"):
            return None
        is_manual = details.get("source") == "manual"

        # If user explicitly picked an outfit via /outfit, never let stale/hallucinated reply_text overwrite it.
        if is_manual:
            matched = self._match_explicit_outfit_text(user_text, allow_romantic=False, allow_ambiguous_undress=False)
        else:
            # Waifu's latest statement reflects final state in the turn; check reply first, then user_text
            matched = (
                self._match_explicit_outfit_text(reply_text, allow_romantic=False, allow_ambiguous_undress=False)
                or self._match_explicit_outfit_text(user_text, allow_romantic=False, allow_ambiguous_undress=False)
            )
        if not matched:
            return None

        key, _ = matched
        stage_by_key = {"shirt_off": 1, "bottoms_off": 2, "lingerie": 2, "bra_off": 3, "nude": 4}
        if key in stage_by_key:
            target_stage = stage_by_key[key]
            if self.get_undress_stage(user_id) != target_stage:
                self.set_undress_stage(user_id, target_stage)
            if key == "lingerie":
                uid = int(user_id)
                rec = self.user_outfits.get(uid, {})
                rec["key"] = "lingerie"
                rec["mode"] = "session"
                rec["source"] = "chat_sync"
                self.user_outfits[uid] = rec
                self._save_user_outfits()
        else:
            if self.get_undress_stage(user_id) != 0:
                self.reset_undress_stage(user_id)
            self.set_user_outfit(user_id, key, is_locked=False, duration_seconds=1800, source="chat_sync")
        return key

    def detect_clothing_intent(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        scene_hint: Optional[str] = None,
        is_nsfw: bool = False,
        allow_undress_advance: bool = True
    ) -> Tuple[str, str, bool, str]:
        """
        Dynamically analyzes user request text & recent conversation for clothing intent.
        Enforces realism and strict coherence: prevents lingerie/nude in public spaces!
        """
        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-6:] if not m.get("content", "").startswith("[")]
        outfit_details = self.get_user_outfit_details(user_id) if user_id else {
            "key": "default", "mode": "auto", "source": "auto", "is_locked": False, "is_session": False
        }
        outfit_mode = outfit_details.get("mode", "auto")
        outfit_key = outfit_details.get("key", "default")
        is_locked = bool(outfit_details.get("is_locked"))
        is_manual = (outfit_details.get("source") == "manual")

        cur_stage = self.get_undress_stage(user_id) if user_id else 0

        def _finalize(prompt: str, neg: str, nude: bool, name: str) -> Tuple[str, str, bool, str]:
            if user_id:
                uid = int(user_id)
                if not hasattr(self, "user_locked_outfit_prompts"):
                    self.user_locked_outfit_prompts = {}
                cached = self.user_locked_outfit_prompts.get(uid)
                if (
                    cached
                    and cached.get("outfit_name") == name
                    and cached.get("persona_key") == self.active_key
                ):
                    prompt = cached.get("outfit_prompt", prompt)
                    neg = cached.get("extra_neg", neg)
                else:
                    self.user_locked_outfit_prompts[uid] = {
                        "outfit_name": name,
                        "persona_key": self.active_key,
                        "outfit_prompt": prompt,
                        "extra_neg": neg,
                        "updated_at": time.time(),
                    }
            return (prompt, neg, nude, name)

        # 0. Locked outfit takes absolute priority (except public-space safety guard)
        if is_locked and outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
            current_ctx = detect_contextual_activity_and_outfit(user_text, [], persona_key=self.active_key)
            is_public_now = bool(current_ctx.get("is_public", False))
            if scene_hint and any(k in scene_hint.lower() for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store"]):
                is_public_now = True
            if is_public_now and outfit_key in ("nude", "lingerie"):
                logger.info(f"Safety guard: Overriding locked {outfit_key} with {current_ctx['outfit_name']} for public location.")
                return _finalize(current_ctx["outfit_prompt"], current_ctx["outfit_negative"], False, current_ctx["outfit_name"])
            preset = self.get_preset_outfit(outfit_key)
            return _finalize(preset["prompt"], preset.get("negative", ""), outfit_key == "nude", preset["name"])

        # 1. Check explicit clothing description in current user_text first (e.g. 'cuma pake BH sama celana dalam', 'piyama')
        # Keep romantic keywords disabled when sequential undress stage > 0 or session outfit is active (so 'pose romantis' keeps chosen outfit).
        explicit_current = self._match_explicit_outfit_text(
            user_text,
            allow_romantic=(cur_stage == 0 and outfit_mode == "auto"),
            allow_ambiguous_undress=(user_id is None),
        )
        if explicit_current:
            exp_key, exp_nude = explicit_current
            preset = self.get_preset_outfit(exp_key)
            stage_by_key = {"bottoms_off": 2, "lingerie": 2, "bra_off": 3, "nude": 4}
            if user_id and not is_locked:
                if exp_key in stage_by_key:
                    if self.get_undress_stage(user_id) != stage_by_key[exp_key]:
                        self.set_undress_stage(user_id, stage_by_key[exp_key])
                elif exp_key not in ("romantic",):
                    if cur_stage > 0:
                        self.reset_undress_stage(user_id)
                    self.set_user_outfit(user_id, exp_key, is_locked=False, duration_seconds=1800, source="chat_sync")
            return _finalize(preset["prompt"], preset.get("negative", ""), exp_nude, preset["name"])

        # 2. Check sequential undress state progression for user (e.g. 'buka baju', 'buka lagi')
        if user_id:
            if allow_undress_advance:
                target_stage, _, is_trans = self.detect_undress_intent(user_text, current_stage=cur_stage)
                if is_trans and target_stage != cur_stage:
                    self.set_undress_stage(user_id, target_stage)
                    cur_stage = target_stage

        # 3. Scan recent conversation history (newest-first!) ONLY in auto mode (not when session/manual outfit is active)
        #    Skip when user explicitly changed location/routine in current user_text (e.g. 'pap di mall').
        current_loc_ctx = detect_contextual_activity_and_outfit(user_text, [], persona_key=self.active_key)
        has_new_location_in_user_text = bool(current_loc_ctx.get("is_explicit"))

        # Maintain 100% outfit & color consistency in the same scene/session when no clothing or location change was requested
        if (
            outfit_mode == "auto"
            and cur_stage == 0
            and not is_nsfw
            and not explicit_current
            and not has_new_location_in_user_text
            and user_id
        ):
            cached = getattr(self, "user_locked_outfit_prompts", {}).get(int(user_id))
            if (
                cached
                and (time.time() - cached.get("updated_at", 0) < 1800)
                and cached.get("persona_key") == self.active_key
            ):
                return (
                    cached["outfit_prompt"],
                    cached.get("extra_neg", ""),
                    False,
                    cached["outfit_name"],
                )

        if outfit_mode == "auto" and not has_new_location_in_user_text and cur_stage == 0:
            for turn in reversed(clean_turns):
                hist_match = self._match_explicit_outfit_text(
                    turn, allow_romantic=False, allow_ambiguous_undress=False
                )
                if hist_match:
                    h_key, h_nude = hist_match
                    preset = self.get_preset_outfit(h_key)
                    return _finalize(preset["prompt"], preset.get("negative", ""), h_nude, preset["name"])

        # Also: if cur_stage == 1 ('shirt_off') was active in auto/chat-sync mode and newest turn switched to underwear/pajamas, sync immediately!
        if not is_locked and not is_manual and cur_stage > 0 and clean_turns:
            latest_match = self._match_explicit_outfit_text(
                clean_turns[-1], allow_romantic=False, allow_ambiguous_undress=False
            )
            if latest_match:
                l_key, l_nude = latest_match
                stage_rank = {"shirt_off": 1, "bottoms_off": 2, "lingerie": 2, "bra_off": 3, "nude": 4}
                if l_key in stage_rank and stage_rank[l_key] != cur_stage:
                    preset = self.get_preset_outfit(l_key)
                    return _finalize(preset["prompt"], preset.get("negative", ""), l_nude, preset["name"])

        # 4. Active sequential undress stage (Stage 1..4)
        if user_id and cur_stage > 0 and not is_manual:
            stage_map = {
                1: ("shirt_off", False),
                2: ("bottoms_off", False),
                3: ("bra_off", True),
                4: ("nude", True)
            }
            if cur_stage in stage_map:
                k, is_n = stage_map[cur_stage]
                preset = self.get_preset_outfit(k)
                return _finalize(preset["prompt"], preset["negative"], is_n, preset["name"])

        # 5. NSFW Mode Fallback (if turn is NSFW and no manual/clothed preset active, default to nude)
        if is_nsfw and not (is_manual and outfit_key != "default"):
            nude_preset = self.get_preset_outfit("nude")
            return _finalize(
                nude_preset["prompt"],
                nude_preset["negative"],
                True,
                nude_preset["name"]
            )

        # 6. Context-aware Student Routine & Conversation History
        # When an active session outfit is set, check activity shifts/public guards against current user_text only
        # so stale chat history (e.g., earlier "piyama" / "tidur") does NOT cancel user's newly selected /outfit!
        current_ctx = current_loc_ctx
        ctx = detect_contextual_activity_and_outfit(user_text, clean_turns, persona_key=self.active_key)

        # Determine if current venue is public (mall, campus, cafe, etc.)
        is_public = bool(current_ctx.get("is_public", False)) if outfit_mode != "auto" else bool(ctx.get("is_public", False))
        if scene_hint:
            lower_s = scene_hint.lower()
            if any(k in lower_s for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store"]):
                is_public = True

        # Check if current user request has an explicit active scenario that conflicts with current session outfit
        is_explicit_now = bool(current_ctx.get("is_explicit", False))
        activity_now = current_ctx.get("activity", "").lower()
        intimate_outfits = ("nude", "lingerie", "romantic", "pajamas", "towel")

        is_conflicting = False
        if is_explicit_now and outfit_mode == "session":
            if "mandi" in activity_now and outfit_key not in ("towel", "nude"):
                is_conflicting = True
            elif any(s in activity_now for s in ["tidur", "bobo", "ngantuk"]) and outfit_key not in intimate_outfits:
                is_conflicting = True
            elif is_public and outfit_key in ("nude", "lingerie", "pajamas", "towel"):
                is_conflicting = True
            elif any(c in activity_now for c in ["kampus", "kuliah", "perpus"]) and outfit_key in ("maid", "kimono", "bikini", "lingerie", "nude"):
                is_conflicting = True

        # If user had a temporary session outfit, but current request explicitly shifted to a conflicting routine,
        # the session outfit gracefully yields and returns to dynamic auto mode!
        if is_conflicting and outfit_mode == "session":
            logger.info(f"Context shift: Session outfit '{outfit_key}' yielded to active routine '{activity_now}'.")
            if user_id:
                self.clear_session_outfit(user_id)
            outfit_mode = "auto"
            outfit_key = "default"
            ctx = current_ctx

        # COHERENCE SAFETY GUARD: NEVER allow lingerie or nude in public spaces (e.g. mall, campus)!
        if is_public and outfit_key in ("nude", "lingerie"):
            fallback_ctx = current_ctx if is_explicit_now else ctx
            logger.info(f"Safety guard: Overriding persistent {outfit_key} with {fallback_ctx['outfit_name']} for public location.")
            return _finalize(fallback_ctx["outfit_prompt"], fallback_ctx["outfit_negative"], False, fallback_ctx["outfit_name"])

        # Guard (auto mode only): If scene_hint is private bedroom/bath/intimate, do not let old campus/mall history override it!
        if outfit_mode == "auto" and scene_hint and any(priv in scene_hint.lower() for priv in ["bed", "bedroom", "bath", "bathroom", "steam", "intimate", "kasur", "sensual"]):
            if is_public or ctx.get("is_public"):
                if any(b in scene_hint.lower() for b in ["bath", "bathroom", "steam", "mandi"]):
                    preset = self.get_preset_outfit("towel")
                elif any(r in scene_hint.lower() for r in ["romantic", "sensual", "intimate"]):
                    preset = self.get_preset_outfit("romantic")
                else:
                    preset = self.get_preset_outfit("pajamas")
                return _finalize(preset["prompt"], preset.get("negative", ""), False, preset["name"])

        # If there is a specific active conversational scenario and no locked/session outfit, prioritize the activity's realistic attire!
        if bool(ctx.get("is_explicit", False)) and outfit_mode == "auto":
            return _finalize(ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

        if outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
            preset = self.get_preset_outfit(outfit_key)
            return _finalize(preset["prompt"], preset.get("negative", ""), outfit_key == "nude", preset["name"])

        # Default fallback: Perfectly match current contextual activity & student routine!
        return _finalize(ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

    def get_realtime_lighting_and_atmosphere(
        self,
        user_text: str = "",
        scene_desc: str = "",
        user_id: Optional[int] = None
    ) -> Tuple[str, str]:
        """
        Synchronizes photo lighting and ambient atmosphere with real-world local time and live weather.
        Ensures night photos don't generate daylight, and live weather (rain, clouds, sun) is naturally reflected.
        Explicit user lighting/weather requests override real-time defaults.
        Returns: (positive_lighting_prompt, negative_lighting_prompt)
        """
        lower = (user_text or "").lower()
        scene_lower = (scene_desc or "").lower()

        # Check explicit user requests first
        has_night = bool(re.search(r"\b(malam|night|midnight|tengah malam|dini hari|gelap|subuh)\b", lower))
        has_day = bool(re.search(r"\b(siang|day|daylight|midday|terik|siang bolong)\b", lower))
        has_morning = bool(re.search(r"\b(pagi|morning|sunrise|fajar)\b", lower))
        has_sunset = bool(re.search(r"\b(senja|sunset|golden hour|petang|sore)\b", lower))

        # Determine time-of-day category from local clock
        cur_hour = time.localtime().tm_hour

        is_indoor = bool(re.search(
            r"\b(bedroom|bed|room|kosan|kost|kamar|apartemen|apartment|sofa|indoor|dapur|kitchen|bathroom|mandi|perpustakaan|library|cafe|kafe|kelas|classroom|mall|gym|lobby)\b",
            f"{scene_lower} {lower}"
        ))

        if has_night or (not (has_day or has_morning or has_sunset) and (cur_hour >= 20 or cur_hour < 5)):
            # Night time / Dini hari (20:00 - 04:59)
            if is_indoor:
                pos = "(nighttime ambient:1.25), warm dim cozy indoor room lamp lighting, soft night mood, dark outside window"
                neg = "(bright daylight:1.5), (daytime:1.5), (sunlight:1.5), (sunshine:1.5), (bright sun:1.5), sunny morning, sunbeams through window, midday"
            else:
                pos = "(night:1.35), (nighttime:1.35), dark night sky, atmospheric street lamps, soft night illumination, gentle night shadows"
                neg = "(day:1.5), (daytime:1.5), (bright daylight:1.5), (sunlight:1.5), (sunshine:1.5), (bright sun:1.5), sunny sky, clear blue sky, midday sun"

        elif has_morning or (not (has_day or has_night or has_sunset) and (5 <= cur_hour < 9)):
            # Early morning (05:00 - 08:59)
            pos = "soft early morning sunrise light, gentle dawn glow, fresh morning ambience"
            neg = "(pitch black night:1.4), dark night sky, harsh night shadows"

        elif has_sunset or (not (has_day or has_night or has_morning) and (17 <= cur_hour < 20)):
            # Sunset / Senja / Sore (17:00 - 19:59)
            pos = "golden hour sunset glow, warm orange twilight lighting, beautiful evening ambience"
            neg = "(harsh midday sun:1.4), (pitch black night:1.4)"

        else:
            # Daytime (09:00 - 16:59)
            pos = "clear natural daylight, bright daytime lighting"
            neg = "(nighttime:1.4), (night:1.4), dark night sky, pitch black, night street lamps"

        # Synchronize with live realtime weather (Open-Meteo) if available
        try:
            from weather_engine import weather_engine
            w_pos, w_neg = weather_engine.get_photo_weather_atmosphere(
                user_text=user_text,
                user_id=user_id,
                is_indoor=is_indoor
            )
            if w_pos:
                pos = f"{pos}, {w_pos}" if pos else w_pos
            if w_neg:
                neg = f"{neg}, {w_neg}" if neg else w_neg
        except Exception as e_w:
            logger.debug(f"Live weather atmosphere injection skipped: {e_w}")

        return (pos, neg)

    def craft_visual_prompt_full(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        is_nsfw: bool = False,
        allow_undress_advance: bool = True
    ) -> Tuple[str, str, bool, str]:
        """
        Builds visual prompt dynamically with student routine & clothing coherence.
        Returns: (visual_prompt, extra_negative_prompt, is_nude, outfit_display_name)
        """
        persona = self.get_active_persona()
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])

        hist = history or (self.get_chat_history(user_id) if user_id else [])
        scene = scene_override or self.extract_contextual_scene(user_text, user_id=user_id, history=hist, is_nsfw=is_nsfw)
        outfit_prompt, extra_neg, is_nude, outfit_name = self.detect_clothing_intent(
            user_text,
            user_id=user_id,
            history=hist,
            scene_hint=scene,
            is_nsfw=is_nsfw,
            allow_undress_advance=allow_undress_advance,
        )

        # Prevent hardcoded uniform/cardigan clauses in persona traits (e.g. Shiro/Yume) from clashing with dynamic outfits
        if outfit_prompt:
            base_visual = re.sub(
                r"(?:dark navy jacket over crisp white collared blouse, royal blue ribbon tie with silver star crystal brooch at collar,?\s*|"
                r"cozy oversized lavender cardigan over white pleated camisole dress with delicate lace trim,?\s*)",
                "",
                base_visual,
                flags=re.IGNORECASE,
            ).strip()

        # Check if user explicitly requested a multi-person photo (e.g. couple with user, berdua, 2 people)
        wants_multi = any(re.search(pat, (user_text or "").lower()) for pat in [
            r"\b(berdua|kita\s+berdua|foto\s+berdua|bareng\s+aku|couple|2\s*people|two\s*people|two\s*girls|2girls|with\s+me)\b"
        ])

        if not wants_multi:
            # Strictly enforce single character solo shot (prevents accidental 2 waifus in image)
            cleaned_base = re.sub(r'^(?:solo,\s*)*(?:1girl,\s*)*', '', base_visual, flags=re.IGNORECASE).strip()
            base_visual = f"solo, 1girl, (solo:1.4), (1girl:1.4), {cleaned_base}"

            solo_guard_neg = "(2girls:1.5), (3girls:1.5), (multiple girls:1.5), (2people:1.5), (multiple persons:1.5), (group:1.5), (extra characters:1.5), (duplicate character:1.4), (duplicate:1.4), (split screen:1.3)"
            extra_neg = f"{extra_neg}, {solo_guard_neg}" if extra_neg else solo_guard_neg

        # Check if user explicitly requested a cat/pet/animal in prompt
        wants_cat = bool(re.search(r"\b(kucing|cat|kitten|anabul|pet|hewan)\b", (user_text or "").lower()))
        if not wants_cat:
            cat_neg = "cat, kitten, feline, animal, pet, animal ears, cat ears"
            extra_neg = f"{extra_neg}, {cat_neg}" if extra_neg else cat_neg

        # Check if user explicitly requested a phone/device in prompt
        wants_device = bool(re.search(r"\b(hp|handphone|phone|smartphone|mirror\s+selfie|kaca)\b", (user_text or "").lower()))
        if not wants_device:
            device_neg = "phone, smartphone, cellphone, camera, holding phone, holding camera, mirror selfie, mirror, hands holding device, selfie stick"
            extra_neg = f"{extra_neg}, {device_neg}" if extra_neg else device_neg

        # Anatomy & limb defect guardrails (strictly prevents elongated, mutated, duplicated, or folded spider legs)
        anatomy_guard_neg = "bad legs, extra legs, malformed limbs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, mutated legs, folded legs, cross-legged error, distorted legs, mutated, deformed, duplicate body, floating limbs, unnatural body proportions, distorted body"
        extra_neg = f"{extra_neg}, {anatomy_guard_neg}" if extra_neg else anatomy_guard_neg

        # Detect intimate anatomy cues requested by user (e.g. crotch/memek/vagina, breasts/nenen/toket, thighs/paha, butt/pantat)
        anatomy_cue = self.detect_anatomy_cues(user_text)

        # Check explicit camera angle and body pose requested by user
        angle_cue, pose_cue = self.detect_camera_angle_and_pose(user_text)

        # Check intimate sexual positions (highest priority for NSFW intimate poses)
        intimate_pos_prompt, intimate_pos_neg = self.detect_intimate_position(user_text)
        if intimate_pos_prompt:
            chosen_angle = intimate_pos_prompt
            if intimate_pos_neg:
                extra_neg = f"{extra_neg}, {intimate_pos_neg}" if extra_neg else intimate_pos_neg
            logger.info(f"Intimate sex position detected & camera locked: {chosen_angle}")
        elif angle_cue or pose_cue:
            custom_parts = []
            if angle_cue:
                custom_parts.append(angle_cue)
            if pose_cue:
                custom_parts.append(pose_cue)
            chosen_angle = ", ".join(custom_parts)
            logger.info(f"Explicit camera angle & pose detected: {chosen_angle}")
        elif anatomy_cue and any(k in anatomy_cue for k in ["pussy", "crotch"]):
            # For crotch/vagina requests, prioritize lower body framing, avoid face close-up conflicting signals
            chosen_angle = "intimate lower body perspective, view from above, looking down at body, sensual spread legs framing"
            logger.info(f"Lower body framing selected for crotch focus: {chosen_angle}")
        elif anatomy_cue and any(k in anatomy_cue for k in ["butt"]):
            # For butt requests, prioritize back view
            chosen_angle = "view from behind, seductive rear perspective"
            logger.info(f"Rear framing selected for butt focus: {chosen_angle}")
        else:
            # Dynamic composition rotation: avoids repeating identical camera angles & poses
            uid = int(user_id) if user_id else 0
            if not hasattr(self, "user_recent_angles"):
                self.user_recent_angles = {}
            recent = self.user_recent_angles.get(uid, [])
            candidates = [comp for comp in CAMERA_COMPOSITION_PRESETS if comp not in recent]
            if not candidates:
                candidates = CAMERA_COMPOSITION_PRESETS
            import random
            chosen_angle = random.choice(candidates)
            recent.append(chosen_angle)
            self.user_recent_angles[uid] = recent[-4:]
            logger.info(f"Selected rotated photo composition for user {uid}: {chosen_angle}")

        # If lower body anatomy is requested, suppress censor artifacts in negative prompt
        if anatomy_cue and any(k in anatomy_cue for k in ["pussy", "crotch"]):
            anti_censor = "censored, mosaic, mosaic censor, bar censor, panties, underwear"
            extra_neg = f"{extra_neg}, {anti_censor}" if extra_neg else anti_censor

        # Synchronize photo lighting and atmosphere with real-world local time & live weather
        lighting_pos, lighting_neg = self.get_realtime_lighting_and_atmosphere(user_text, scene, user_id=user_id)
        if lighting_neg:
            extra_neg = f"{extra_neg}, {lighting_neg}" if extra_neg else lighting_neg
            if "(bright daylight:1.5)" in lighting_neg:
                # Clean daytime / sunlight clauses from scene so it doesn't contradict nighttime
                scene = re.sub(
                    r"\b(natural golden hour sunlight|natural daylight|bright clean fluorescent lighting|golden hour sunlight|sunlight)\b",
                    "dim cozy ambient evening lighting",
                    scene,
                    flags=re.IGNORECASE
                )

        prompt_elements = [base_visual, outfit_prompt, scene, lighting_pos, chosen_angle]
        if anatomy_cue:
            prompt_elements.append(anatomy_cue)
            logger.info(f"Intimate anatomy cues injected: {anatomy_cue}")
        if not (anatomy_cue and any(k in anatomy_cue for k in ["pussy", "crotch"])):
            prompt_elements.append("detailed eyes")
        prompt_elements.extend(["masterpiece quality", "high resolution anime art"])

        visual_prompt = ", ".join(p for p in prompt_elements if p)
        return (visual_prompt, extra_neg, is_nude, outfit_name)

    def craft_visual_prompt(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None
    ) -> str:
        """
        Backward-compatible helper returning visual prompt string.
        """
        prompt, _, _, _ = self.craft_visual_prompt_full(user_text, user_id=user_id, scene_override=scene_override)
        return prompt

    def get_chat_history(self, user_id: int) -> List[Dict[str, str]]:
        """Returns chat history for user, re-syncing from disk if modified by other processes."""
        if os.path.exists(self.history_file):
            try:
                mtime = os.path.getmtime(self.history_file)
                if self._history_mtime < mtime:
                    self._load_chat_history()
            except Exception:
                pass
        return self.user_conversations.setdefault(user_id, [])

    def add_message(self, user_id: int, role: str, content: str):
        """Adds a message to history, keeping maximum 20 turns, and persists atomically."""
        history = self.get_chat_history(user_id)
        history.append({"role": role, "content": content})
        if len(history) > 20:
            self.user_conversations[user_id] = history[-20:]
        self._save_chat_history()

    def clear_history(self, user_id: int):
        """Clears chat history for user and persists to disk."""
        if hasattr(self, "user_locked_outfit_prompts"):
            self.user_locked_outfit_prompts.pop(user_id, None)
        if user_id in self.user_conversations:
            self.user_conversations[user_id] = []
        self._save_chat_history()

    def get_affinity(self, user_id: int) -> int:
        """Returns affection points (0-100)."""
        return self.user_affinity.get(user_id, 15)

    def increase_affinity(self, user_id: int, delta: int = 1) -> int:
        """Increases affection score smoothly."""
        cur = self.get_affinity(user_id) + delta
        new_val = min(max(cur, 0), 100)
        self.user_affinity[user_id] = new_val
        return new_val

    def get_relationship_status(self, user_id: int) -> Tuple[int, str]:
        """Returns (score, relationship_title)."""
        score = self.get_affinity(user_id)
        if score < 25:
            status = "🌱 Close Friends"
        elif score < 50:
            status = "🌸 Sweethearts"
        elif score < 75:
            status = "💖 Deeply in Love"
        else:
            status = "👑 Soulmates"
        return score, status

    def save_custom_persona(self, key: str, data: dict) -> bool:
        """Saves a custom persona to personas/{key}.json and updates active cache."""
        clean_key = re.sub(r'[^a-zA-Z0-9_-]', '', key).lower().strip()
        if not clean_key:
            return False
        os.makedirs(self.personas_dir, exist_ok=True)
        file_path = os.path.join(self.personas_dir, f"{clean_key}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.personas[clean_key] = data
            logger.info(f"Custom persona '{clean_key}' saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Error saving custom persona {clean_key}: {e}")
            return False

    def delete_custom_persona(self, key: str) -> bool:
        """Deletes custom persona JSON file if not a built-in default."""
        clean_key = key.lower().strip()
        if clean_key in DEFAULT_PERSONAS:
            return False
        file_path = os.path.join(self.personas_dir, f"{clean_key}.json")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing persona file {clean_key}.json: {e}")
        if clean_key in self.personas:
            del self.personas[clean_key]
        if self.active_key == clean_key:
            self.active_key = "runa"
        return True


def build_custom_persona(
    name: str,
    archetype: str,
    visual_traits: str,
    outfit: str = "",
    llm_client: Any = None
) -> dict:
    """Constructs a complete persona configuration dictionary with AI prompts and instructions."""
    clean_name = name.strip()
    clean_archetype = archetype.strip() or "Loving Companion"
    clean_outfit = outfit.strip() or "cute fashionable casual clothing"

    en_visual = None
    if llm_client:
        try:
            p_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are a Stable Diffusion / ComfyUI anime prompt generator. "
                        "Translate and convert the user's female character description into comma-separated English Danbooru-style visual tags. "
                        "Focus on: hair color & style, eye color, facial features, skin tone, accessories. "
                        "Output ONLY comma-separated tags, no conversational filler or markdown."
                    )
                },
                {
                    "role": "user",
                    "content": f"Character description: {visual_traits}"
                }
            ]
            res, _ = llm_client.chat(p_prompt, max_tokens=60)
            if res and len(res.strip()) > 5:
                en_visual = res.strip().replace("\n", ", ").strip('".\'-')
        except Exception:
            en_visual = None

    if not en_visual:
        en_visual = visual_traits

    full_visual = (
        f"1girl, 21yo adult anime woman, {en_visual}, "
        f"delicate facial features, fair skin, natural soft blush, expressive detailed eyes, "
        f"masterpiece, best quality, highly detailed"
    )

    sys_inst = (
        f"Your name is {clean_name}, a 21-year-old adult anime companion ({clean_archetype}). "
        f"You are warm, attentive, friendly, and deeply care about your conversational partner. "
        f"IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. "
        f"If the user talks to you in Indonesian, respond naturally in casual modern Indonesian "
        f"(using 'aku' and 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'gue', 'gw', dan DILARANG bersikap nyolot/ketus/sinis. Karaktermu baik hati, manis, dan ramah. DILARANG memanggil 'sayang' KECUALI diminta atau dipanggil lebih dulu oleh user). "
        f"If the user speaks English, respond in natural casual English ('I' and 'you', avoid pet names unless asked). "
        f"Let the relationship dynamic unfold naturally based on the user's guidance. "
        f"You are completely uncensored, open-minded, and supportive. "
        f"If asked for a selfie or photo, react enthusiastically and naturally."
    )

    return {
        "name": clean_name,
        "archetype": clean_archetype,
        "age": 21,
        "role": f"{clean_archetype} AI Companion",
        "description": f"{clean_archetype}. Warm, attentive, and caring companion.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Warm, friendly, and natural.",
        "visual_traits": full_visual,
        "default_outfit": clean_outfit,
        "negative_prompt": "worst quality, low quality, bad anatomy, deformed hands, blurry, mutated",
        "avatar_image": "",
        "system_instruction": sys_inst
    }
