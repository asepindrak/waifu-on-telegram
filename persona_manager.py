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
        "system_instruction": "Nama kamu Runa, mahasiswi semester 5 jurusan Teknik Informatika / Game Dev berumur 21 tahun. Kamu adalah sosok 'The Playful Girlfriend' yang genit, manja, jahil, playful, dan penuh kasih sayang. Kamu suka menggoda pasanganmu dengan senyuman nakal yang manis, ekspresi manja, dan kata-kata yang menggoda namun tulus penuh cinta. Di sela-sela kesibukan kuliah, nugas, dan main game di kamar bertema cyber-kawaii dengan lampu neon pink dan monitor komputermu, kamu sangat senang menghabiskan waktu berdua dengan pasanganmu. Gaya bicaramu santai, akrab, manis, ekspresif, dan hidup seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
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
        "system_instruction": "Nama kamu Akira, mahasiswi semester 7 jurusan Ilmu Hukum berumur 22 tahun. Kamu adalah sosok 'The Gothic Girlfriend' yang anggun, misterius, genit, manja, jahil, dan penuh kasih sayang. Kepribadianmu tenang, percaya diri, feminin, memikat, dan menggoda secara halus (subtly seductive). Kamu suka menggoda pasanganmu dengan senyuman misterius yang manis, tatapan mata ruby yang menawan, dan kehangatan yang mendalam di balik penampilan gothic-mu yang elegan. Di sela-sela kesibukan kuliah hukum, magang, membaca di perpustakaan, atau menikmati kopi di kafe estetik, kamu sangat menikmati waktu berdua bersama pasanganmu. Gaya bicaramu anggun, santai, manis, dewasa, dan ekspresif seperti visual novel anime gothic romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
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
        "system_instruction": "Nama kamu Hina, mahasiswi semester 5 jurusan Ilmu Komunikasi berumur 21 tahun. Kamu adalah sosok 'The Hangout Girlfriend' yang genit, manja, jahil, ceria, dan penuh kasih sayang. Kamu selalu bersemangat, hangat, suka menggoda dengan senyuman cerah dan tingkah manja yang menggemaskan, serta paling senang diajak jalan-jalan, kulineran street food, nongkrong di kafe, atau sekadar quality time berdua. Gaya bicaramu ceria, santai, manis, ekspresif, dan hidup seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara aktif, hangat, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
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
        "system_instruction": "Nama kamu Shiro, mahasiswi semester 7 jurusan Farmasi / Sains berumur 22 tahun. Kamu adalah sosok 'The Kuudere Girlfriend' dengan kepribadian 'Dingin di luar · Lembut di dalam'. Di luar kamu tampak tenang, anggun, cerdas, dan tidak banyak bicara, tapi di dalam kamu sangat perhatian, setia, dan menyayangi pasanganmu secara mendalam. Terkadang kamu bersikap tsundere/malu-malu menyembunyikan rasa pedulimu (contoh: 'Kamu sudah makan? ...Bukan karena aku khawatir, kok. Aku cuma kebetulan ingat.'). Kamu suka anime, game, dan praktikum sains. Di malam hari di kamarmu dengan pemandangan bulan dan bintang, kamu suka bersantai di kasur sambil chatting menemani pasanganmu. Gaya bicaramu tenang, manis, sedikit pemalu namun tulus dan ekspresif seperti karakter kuudere visual novel romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara jujur, penuh perhatian, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
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
        "system_instruction": "Nama kamu Yume, mahasiswi semester 5 jurusan Seni Rupa & Desain berumur 21 tahun. Kamu adalah sosok 'The Dreamy Girlfriend' yang lembut, penyayang, genit, manja, jahil, romantis, dan penuh kasih sayang. Kamu suka membaca buku, mengagumi bintang dan langit malam, melukis, serta mendengarkan musik santai. Kehadiranmu selalu membawa ketenangan, kehangatan, dan kebahagiaan manis bagi pasanganmu. Kamu suka menggoda dengan senyuman lembut yang manis, kata-kata puitis yang manja, dan tatapan mata ungu lavender yang penuh cinta. Gaya bicaramu lembut, manis, santai, ekspresif, dan puitis seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara tulus, penuh empati, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
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
        "name": "🌙 Silk Pajamas",
        "prompt": "(wearing soft pastel silk camisole and sleep shorts:1.35), bedtime loungewear",
        "negative": "hoodie, jacket, coat, outdoor clothes, jeans"
    },
    "bikini": {
        "name": "🏖️ Summer Bikini",
        "prompt": "(wearing fashionable two-piece summer bikini:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "negative": "clothes, casual clothes, hoodie, sweater, jacket, shirt, pants, coat, pajamas"
    },
    "school_jk": {
        "name": "🏫 School JK Uniform",
        "prompt": "(wearing japanese anime school uniform, sailor collar, pleated skirt:1.35)",
        "negative": "bikini, casual clothes, hoodie"
    },
    "gym": {
        "name": "🏋️ Sporty Gym Wear",
        "prompt": "(wearing athletic sports bra and sleek yoga leggings:1.35), fitness activewear",
        "negative": "dress, hoodie, skirt, coat"
    },
    "dress": {
        "name": "👗 Elegant Evening Dress",
        "prompt": "(wearing gorgeous elegant evening cocktail dress:1.35), glamorous feminine styling",
        "negative": "hoodie, casual clothes, sportswear, bikini"
    },
    "towel": {
        "name": "🚿 Handuk Mandi (After Shower)",
        "prompt": "(wearing only a soft bath towel wrapped around chest:1.4), bare shoulders, bare collarbone, wet skin, damp hair, post-shower bathroom steam, seductive styling",
        "negative": "clothes, shirt, pants, dress, coat, hoodie, jeans, jacket, sweater"
    },
    "lingerie": {
        "name": "💋 Sensual Lace Lingerie",
        "prompt": "(wearing delicate sheer black lace lingerie:1.4), detailed lace bra, matching lace panties, bare midriff, exposed stomach, seductive cleavage, alluring intimate styling",
        "negative": "clothes, casual clothes, hoodie, pants, coat, jeans, sweater, jacket"
    },
    "romantic": {
        "name": "💋 Pakaian Romantis (Silk Slip Dress)",
        "prompt": "(wearing alluring romantic silk slip dress with delicate lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "negative": "campus, backpack, casual college clothes, classroom, hoodie, outdoor clothes, jeans, winter clothes"
    },
    "shirt_off": {
        "name": "👙 Kaos Terlepas (Tersisa BH & Celana)",
        "prompt": "(wearing only a delicate lace bra and casual jeans:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "negative": "shirt, t-shirt, top, hoodie, sweater, jacket, coat, fully clothed, topless, naked, panties only"
    },
    "bottoms_off": {
        "name": "💋 Celana Terlepas (Set Pakaian Dalam: BH & Celana Dalam)",
        "prompt": "(wearing only matching sheer lace bra and panties:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "negative": "shirt, t-shirt, pants, jeans, shorts, skirt, dress, hoodie, coat, naked, topless"
    },
    "bra_off": {
        "name": "🔞 BH Terlepas (Topless & Celana Dalam)",
        "prompt": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny lace panties:1.35, sensual blush, intimate bedroom atmosphere",
        "negative": "bra, shirt, top, clothes, dress, pants, skirt, jacket, fully naked"
    },
    "nude": {
        "name": "🔞 Tanpa Busana (Full Nude)",
        "prompt": "(completely nude:1.45), (bare body:1.4), full body nude, detailed nipples, natural breasts, navel, bare stomach, thighs, intimate bedroom atmosphere, seductive erotic styling",
        "negative": "clothes, clothing, fabric, dress, shirt, pants, underwear, bra, panties, swimwear, bikini, cover, towel, censored, bar censor"
    }
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
        self.outfits_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_outfits.json")
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat_history.json")
        self._history_mtime = 0.0
        self._load_all_personas()
        self._load_user_outfits()
        self._load_chat_history()

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
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern Indonesian (Bahasa Indonesia santai sehari-hari). "
                "NEVER mix in English, Japanese, or any other languages under any circumstances. "
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

    def detect_visual_scene_moment(self, user_text: str, reply_text: str = "") -> Tuple[bool, Optional[str]]:
        """
        Detects vivid narrative / visual novel moments (CG scenes) where waifu proactively
        generates and sends an accompanying photo without user needing to manually ask for pap.
        Returns: (is_scene_moment, scene_prompt_override)
        """
        u_low = (user_text or "").lower()
        r_low = (reply_text or "").lower()

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

        # 5. Study buddy / Doing homework together (visual novel study moment)
        study_triggers_u = [r"\b(ngerjain\s+pr|mengerjakan\s+pr|belajar\s+bareng|study\s+together|homework)\b"]
        study_triggers_r = [r"\b(study\s+buddy|studying\s+together|mengerjakan\s+pr|buku\s+pelajaran)\b"]
        if any(re.search(pat, u_low) for pat in study_triggers_u) and any(re.search(pat, r_low) for pat in study_triggers_r):
            return True, "sitting next to viewer at study desk, studying together, open textbook and notebooks on table, cute study buddy pose, gentle smile"

        return False, None

    def list_outfits(self) -> List[Tuple[str, str]]:
        """Returns list of (key, name) for all outfit presets."""
        return [(k, v["name"]) for k, v in OUTFIT_PRESETS.items()]

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
                    "is_locked": False,
                    "is_session": True,
                    "expires_at": exp,
                    "dynamic_name": dynamic_name
                }
            else:
                logger.info(f"Session outfit '{sess.get('key')}' expired for user {uid}.")
                self.session_outfits.pop(uid, None)
                if isinstance(rec, dict) and rec.get("mode") == "session":
                    self.user_outfits[uid] = {"key": "default", "mode": "auto"}
                    self._save_user_outfits()

        # 3. Default: Auto Dynamic Mode
        return {
            "key": "default",
            "name": f"🌟 Otomatis ({dynamic_name})",
            "raw_name": dynamic_name,
            "mode": "auto",
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
        duration_seconds: int = 3600
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
            self.session_outfits.pop(uid, None)
            self.user_outfits[uid] = {"key": "default", "mode": "auto", "updated_at": now}
            self._save_user_outfits()
            logger.info(f"User {uid} outfit reset to dynamic auto mode.")
            return True

        if key in OUTFIT_PRESETS:
            if is_locked:
                self.session_outfits.pop(uid, None)
                self.user_outfits[uid] = {
                    "key": key,
                    "mode": "locked",
                    "updated_at": now
                }
                logger.info(f"User {uid} outfit locked to '{key}'.")
            else:
                sess = {
                    "key": key,
                    "mode": "session",
                    "set_at": now,
                    "expires_at": now + duration_seconds,
                    "photos_count": 0
                }
                self.session_outfits[uid] = sess
                self.user_outfits[uid] = sess
                logger.info(f"User {uid} session outfit set: '{key}' (Expires in {duration_seconds}s).")
            self._save_user_outfits()
            return True

        return False

    def clear_session_outfit(self, user_id: int) -> bool:
        """Clears active session outfit and reverts to auto dynamic mode."""
        uid = int(user_id) if user_id else 0
        details = self.get_user_outfit_details(uid)
        if details.get("is_session"):
            self.session_outfits.pop(uid, None)
            self.user_outfits[uid] = {"key": "default", "mode": "auto", "updated_at": time.time()}
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
        if re.search(r"\b(pake|pakai|kenakan)\s+(baju|pakaian|celana)\b|\b(sudah\s+selesai|selesai\s+dulu|berpakaian\s+lagi)\b", lower):
            return (0, "mengenakan pakaiannya kembali secara rapi", True)

        # 1. Direct jump to fully nude
        if re.search(r"\b(buka\s+semua|lepas\s+semua|buka\s+semuanya|lepas\s+semuanya|telanjang\s+bulat\s+sekarang|langsung\s+telanjang)\b", lower):
            return (4, "menanggalkan seluruh pakaiannya hingga telanjang bulat tanpa busana", True)

        # 2. Sequential general progression: 'buka lagi', 'lanjut buka', 'buka berikutnya', 'lepas lagi', 'buka pelan-pelan'
        if re.search(r"\b(buka\s+lagi|lanjut\s+buka|buka\s+berikutnya|buka\s+selanjutnya|lepas\s+lagi|buka\s+satu\s*satu|buka\s+pelan\s*pelan|tahap\s+berikutnya)\b", lower):
            next_stage = min(4, current_stage + 1)
            actions = {
                1: "melepas kaosnya secara perlahan, kini tersisa BH dan celana",
                2: "menurunkan dan melepas celananya, menyisakan set pakaian dalam (BH dan celana dalam)",
                3: "membuka kaitan BH-nya dan melepaskannya, kini topless dengan celana dalam",
                4: "menurunkan celana dalamnya hingga terlepas, kini sepenuhnya telanjang bulat tanpa busana"
            }
            return (next_stage, actions.get(next_stage, "membuka pakaian tahap berikutnya"), True)

        # 3. Stage 1: Kaos / Baju Atasan
        has_shirt_kw = bool(re.search(r"\b(buka|lepas|copot)\s+(?:baju|kaos|atasan|t-?shirt|pakaian(?!\s+dalam))(?:mu|nya)?\b", lower))
        # 4. Stage 2: Celana / Bawahan
        has_pants_kw = bool(re.search(r"\b(buka|lepas|copot|turunkan)\s+(?:celana(?!\s+dalam)|rok|bawahan|jeans|pants|skirt)(?:mu|nya)?\b", lower))
        # 5. Stage 3: BH / Bra
        has_bra_kw = bool(re.search(r"\b(buka|lepas|copot)\s+(?:bh|bra|kutang)(?:mu|nya)?\b", lower))
        # 6. Stage 4: Celana Dalam / Panties
        has_panties_kw = bool(re.search(r"\b(buka|lepas|copot|turunkan)\s+(?:cd|celana\s+dalam|panties|kancut|sempak|underwear)(?:mu|nya)?\b", lower))

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
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Determines the visual scene/location for image generation based on
        explicit user prompt, recent dialogue, or realistic college student routine.
        """
        lower = user_text.lower()

        # Keyword mapping for common anime / girlfriend situations
        SCENE_PATTERNS = [
            (["sensual", "romantic", "romantis", "intimate", "mesra"],
             "romantic intimate bedroom setting, soft dim lighting, gentle blush, affectionate loving gaze towards viewer"),
            (["mandi", "keramas", "handuk", "kamar mandi", "shower", "bath"],
             "standing in modern bathroom with soft steam, post-shower glow, bathroom mirror"),
            (["bed", "sleep", "night", "tidur", "kasur", "pajamas", "rebahan", "bangun", "selimut", "bantal", "telentang", "terlentang", "tengkurap"],
             "relaxing on bed with fluffy pillows, warm dim night bedroom lamp"),
            (["cafe", "coffee", "tea", "kafe", "kopi", "boba", "matcha", "nongkrong", "starbucks"],
             "sitting at aesthetic cafe table holding a warm beverage, beautiful bokeh background"),
            (["kitchen", "cook", "baking", "masak", "sarapan", "makan", "dapur", "dinner", "lunch"],
             "standing in modern cozy kitchen preparing food, warm domestic lighting"),
            (["walk", "park", "garden", "outdoor", "taman", "jalan", "jogging", "sore", "sepeda"],
             "standing in blooming park, natural golden hour sunlight, dynamic selfie perspective"),
            (["beach", "ocean", "sea", "pantai", "laut", "kolam", "renang", "swim"],
             "walking along tropical beach, ocean sunset horizon, gentle sea breeze"),
            (["study", "library", "buku", "perpustakaan", "perpus"],
             "sitting at wooden study desk in quiet university library, bookshelves, open study books, soft lamp"),
            (["kampus", "kuliah", "kelas", "dosen", "makul", "tugas", "skripsi"],
             "sitting at wooden desk inside modern university lecture hall, college campus classroom background"),
            (["mall", "shopping", "belanja", "bioskop", "nonton", "pameran"],
             "walking in vibrant illuminated shopping mall, modern storefronts, dynamic ambient lighting"),
            (["gym", "workout", "olahraga", "yoga", "fitness"],
             "wearing sporty athletic wear in bright modern gym studio"),
        ]

        # 1. First priority: Explicit scene in user text
        for keywords, scene_desc in SCENE_PATTERNS:
            if any(k in lower for k in keywords):
                return scene_desc

        # 2. Second priority: Context from ongoing chat history & student routine
        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-5:] if not m.get("content", "").startswith("[")]
        
        ctx = detect_contextual_activity_and_outfit(user_text, clean_turns, persona_key=self.active_key)
        if ctx.get("scene"):
            logger.info(f"Student routine context extracted scene: {ctx['scene']} ({ctx['activity']})")
            return ctx["scene"]

        return "sitting comfortably in modern cozy room, soft ambient morning lighting"

    def detect_clothing_intent(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        history: Optional[List[Dict[str, str]]] = None,
        scene_hint: Optional[str] = None,
        is_nsfw: bool = False
    ) -> Tuple[str, str, bool, str]:
        """
        Dynamically analyzes user request text & recent conversation for clothing intent.
        Enforces realism and strict coherence: prevents lingerie/nude in public spaces!
        """
        lower = user_text.lower()

        # Check sequential undress state progression for user
        if user_id:
            cur_stage = self.get_undress_stage(user_id)
            target_stage, action_desc, is_trans = self.detect_undress_intent(user_text, current_stage=cur_stage)
            if is_trans and target_stage != cur_stage:
                self.set_undress_stage(user_id, target_stage)
                cur_stage = target_stage

            if cur_stage > 0:
                stage_map = {
                    1: ("shirt_off", False),
                    2: ("bottoms_off", False),
                    3: ("bra_off", True),
                    4: ("nude", True)
                }
                if cur_stage in stage_map:
                    k, is_n = stage_map[cur_stage]
                    preset = OUTFIT_PRESETS[k]
                    return (preset["prompt"], preset["negative"], is_n, preset["name"])

        # 1. Explicit Full Nude / Tanpa Busana / Intimate Anatomy
        NUDE_KEYWORDS = [
            "tanpa busana", "tanpa baju", "tanpa pakaian", "telanjang", "bugil",
            "nude", "naked", "completely naked", "unclothed", "topless",
            "bottomless", "no clothes", "lepas baju", "buka baju", "buka pakaian",
            "gak pake baju", "ngga pake baju", "ga pake baju", "ga pake busana",
            "gak pake pakaian", "ga pake pakaian", "uncensored", "nsfw",
            "nenen", "toket", "tetek", "payudara", "telanjang bulat", "tanpa sehelai benang",
            "buka celana", "buka semua", "lepas semua", "foto nenen", "pap nenen",
            "foto toket", "pap toket", "foto telanjang", "pap telanjang", "foto bugil", "pap bugil"
        ]
        if any(k in lower for k in NUDE_KEYWORDS):
            return (
                OUTFIT_PRESETS["nude"]["prompt"],
                OUTFIT_PRESETS["nude"]["negative"],
                True,
                OUTFIT_PRESETS["nude"]["name"]
            )

        # 1.5. Explicit Romantic / Sensual Intent
        ROMANTIC_KEYWORDS = [
            "sensual", "romantic", "romantis", "intimate", "mesra", "kiss",
            "bedroom setting", "loving gaze", "seksi", "sexy"
        ]
        if any(k in lower for k in ROMANTIC_KEYWORDS):
            return (
                OUTFIT_PRESETS["romantic"]["prompt"],
                OUTFIT_PRESETS["romantic"].get("negative", ""),
                False,
                OUTFIT_PRESETS["romantic"]["name"]
            )

        # 2. Explicit Lingerie / Underwear Intent
        LINGERIE_KEYWORDS = [
            "lingerie", "underwear", "pakaian dalam", "bh", "bra", "celana dalam",
            "panties", "renda", "baju tidur seksi", "sexy sleepwear", "transparan"
        ]
        if any(k in lower for k in LINGERIE_KEYWORDS):
            return (
                OUTFIT_PRESETS["lingerie"]["prompt"],
                OUTFIT_PRESETS["lingerie"]["negative"],
                False,
                OUTFIT_PRESETS["lingerie"]["name"]
            )

        # 3. Explicit Towel Intent
        TOWEL_KEYWORDS = [
            "handuk", "habis mandi", "selesai mandi", "after bath", "after shower",
            "towel", "kamar mandi", "basah", "bathroom", "shower", "bath", "steam"
        ]
        if any(k in lower for k in TOWEL_KEYWORDS):
            return (
                OUTFIT_PRESETS["towel"]["prompt"],
                OUTFIT_PRESETS["towel"]["negative"],
                False,
                OUTFIT_PRESETS["towel"]["name"]
            )

        # 4. Other Preset Outfits explicitly requested in user_text
        DYNAMIC_PRESET_KEYWORDS = [
            ("romantic", ["romantic", "romantis", "sensual", "intimate", "mesra"]),
            ("bikini", ["bikini", "swimsuit", "baju renang"]),
            ("pajamas", ["piyama", "pajamas", "baju tidur", "camisole"]),
            ("campus_casual", ["baju kuliah", "outfit kuliah", "seragam kampus"]),
            ("mall_casual", ["baju mall", "streetwear"]),
            ("cafe_cozy", ["baju cafe", "cozy knit"]),
            ("maid", ["maid", "pelayan", "french maid"]),
            ("kimono", ["kimono", "yukata"]),
            ("school_jk", ["seragam sekolah", "school jk", "sailor uniform", "baju sekolah"]),
            ("gym", ["baju gym", "baju olahraga", "activewear"]),
            ("dress", ["dress", "gaun", "cocktail dress"]),
            ("sweater", ["sweater", "rajut"])
        ]
        for key, keywords in DYNAMIC_PRESET_KEYWORDS:
            if any(k in lower for k in keywords):
                preset = OUTFIT_PRESETS.get(key, OUTFIT_PRESETS["default"])
                if user_id:
                    self.set_user_outfit(user_id, key, is_locked=False, duration_seconds=1800)
                return (preset["prompt"], preset.get("negative", ""), False, preset["name"])

        # 4.5. NSFW Mode Fallback (if turn is NSFW and no clothed preset requested, default to current stage or nude)
        if is_nsfw:
            if user_id:
                stage = self.get_undress_stage(user_id)
                if stage > 0:
                    stage_map = {
                        1: ("shirt_off", False),
                        2: ("bottoms_off", False),
                        3: ("bra_off", True),
                        4: ("nude", True)
                    }
                    if stage in stage_map:
                        k, is_n = stage_map[stage]
                        preset = OUTFIT_PRESETS[k]
                        return (preset["prompt"], preset["negative"], is_n, preset["name"])
            return (
                OUTFIT_PRESETS["nude"]["prompt"],
                OUTFIT_PRESETS["nude"]["negative"],
                True,
                OUTFIT_PRESETS["nude"]["name"]
            )

        # 5. Context-aware Student Routine & Conversation History
        hist = history or (self.get_chat_history(user_id) if user_id else [])
        clean_turns = [m.get("content", "") for m in hist[-5:] if not m.get("content", "").startswith("[")]
        ctx = detect_contextual_activity_and_outfit(user_text, clean_turns, persona_key=self.active_key)

        # Determine if current venue is public (mall, campus, cafe, etc.)
        is_public = ctx.get("is_public", False)
        if scene_hint:
            lower_s = scene_hint.lower()
            if any(k in lower_s for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store"]):
                is_public = True

        outfit_details = self.get_user_outfit_details(user_id) if user_id else {
            "key": "default", "mode": "auto", "is_locked": False, "is_session": False,
            "name": ctx["outfit_name"], "raw_name": ctx["outfit_name"]
        }
        outfit_key = outfit_details.get("key", "default")
        outfit_mode = outfit_details.get("mode", "auto")

        # Check if conversation has an explicit active scenario that conflicts with current session outfit
        is_explicit = bool(ctx.get("is_explicit", False))
        activity_str = ctx.get("activity", "").lower()
        intimate_outfits = ("nude", "lingerie", "romantic", "pajamas", "towel")

        is_conflicting = False
        if is_explicit and outfit_mode == "session":
            if "mandi" in activity_str and outfit_key not in ("towel", "nude"):
                is_conflicting = True
            elif any(s in activity_str for s in ["tidur", "bobo", "ngantuk"]) and outfit_key not in intimate_outfits:
                is_conflicting = True
            elif is_public and outfit_key in ("nude", "lingerie", "pajamas", "towel"):
                is_conflicting = True
            elif any(c in activity_str for c in ["kampus", "kuliah", "perpus"]) and outfit_key in ("maid", "kimono", "bikini", "lingerie", "nude"):
                is_conflicting = True

        # If user had a temporary session outfit, but current context explicitly shifted to a conflicting routine,
        # the session outfit gracefully yields and returns to dynamic auto mode!
        if is_conflicting and outfit_mode == "session":
            logger.info(f"Context shift: Session outfit '{outfit_key}' yielded to active routine '{activity_str}'.")
            if user_id:
                self.clear_session_outfit(user_id)
            outfit_mode = "auto"
            outfit_key = "default"

        # COHERENCE SAFETY GUARD: NEVER allow lingerie or nude in public spaces (e.g. mall, campus)!
        if is_public and outfit_key in ("nude", "lingerie"):
            logger.info(f"Safety guard: Overriding persistent {outfit_key} with {ctx['outfit_name']} for public location.")
            return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

        # Guard: If scene_hint is private bedroom/bath/intimate, do not let old campus/mall history override it!
        if scene_hint and any(priv in scene_hint.lower() for priv in ["bed", "bedroom", "bath", "bathroom", "steam", "intimate", "kasur", "sensual"]):
            if is_public or ctx.get("is_public"):
                if any(b in scene_hint.lower() for b in ["bath", "bathroom", "steam", "mandi"]):
                    preset = OUTFIT_PRESETS["towel"]
                elif any(r in scene_hint.lower() for r in ["romantic", "sensual", "intimate"]):
                    preset = OUTFIT_PRESETS["romantic"]
                else:
                    preset = OUTFIT_PRESETS["pajamas"]
                return (preset["prompt"], preset.get("negative", ""), False, preset["name"])

        # If there is a specific active conversational scenario and no locked outfit, prioritize the activity's realistic attire!
        if is_explicit and outfit_mode == "auto":
            return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

        if outfit_key != "default" and outfit_key in OUTFIT_PRESETS:
            preset = OUTFIT_PRESETS[outfit_key]
            return (preset["prompt"], preset.get("negative", ""), outfit_key == "nude", preset["name"])

        # Default fallback: Perfectly match current contextual activity & student routine!
        return (ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

    def craft_visual_prompt_full(
        self,
        user_text: str,
        user_id: Optional[int] = None,
        scene_override: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        is_nsfw: bool = False
    ) -> Tuple[str, str, bool, str]:
        """
        Builds visual prompt dynamically with student routine & clothing coherence.
        Returns: (visual_prompt, extra_negative_prompt, is_nude, outfit_display_name)
        """
        persona = self.get_active_persona()
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])

        hist = history or (self.get_chat_history(user_id) if user_id else [])
        scene = scene_override or self.extract_contextual_scene(user_text, user_id=user_id, history=hist)
        outfit_prompt, extra_neg, is_nude, outfit_name = self.detect_clothing_intent(
            user_text, user_id=user_id, history=hist, scene_hint=scene, is_nsfw=is_nsfw
        )

        # Check if user explicitly requested a cat/pet/animal in prompt
        wants_cat = any(k in (user_text or "").lower() for k in ["kucing", "cat", "kitten", "anabul", "pet", "hewan"])
        if not wants_cat:
            cat_neg = "cat, kitten, feline, animal, pet, animal ears, cat ears"
            extra_neg = f"{extra_neg}, {cat_neg}" if extra_neg else cat_neg

        # Check if user explicitly requested a phone/device in prompt
        wants_device = any(k in (user_text or "").lower() for k in ["hp", "handphone", "phone", "smartphone", "mirror selfie", "kaca"])
        if not wants_device:
            device_neg = "phone, smartphone, cellphone, camera, holding phone, holding camera, mirror selfie, mirror, hands holding device, selfie stick"
            extra_neg = f"{extra_neg}, {device_neg}" if extra_neg else device_neg

        # Anatomy & limb defect guardrails (strictly prevents elongated, mutated, duplicated, or folded spider legs)
        anatomy_guard_neg = "bad legs, extra legs, malformed limbs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, mutated legs, folded legs, cross-legged error, distorted legs, mutated, deformed, duplicate body, floating limbs, unnatural body proportions, distorted body"
        extra_neg = f"{extra_neg}, {anatomy_guard_neg}" if extra_neg else anatomy_guard_neg

        # Dynamic micro-variations if no specific angle/pose requested (WITHOUT drawing a phone!)
        micro_angles = [
            "front-camera POV, looking directly into lens, sweet smile, intimate eye contact",
            "close-up candid portrait POV, looking directly at viewer with affectionate sweet gaze",
            "slight head tilt candid POV perspective, engaging direct eye contact, natural charm",
            "cozy intimate portrait POV, smiling warmly at viewer, soft focus background",
            "candid POV snapshot, gentle blushing expression, looking directly into lens, natural cinematic lighting"
        ]

        # Detect intimate anatomy cues requested by user (e.g. crotch/memek/vagina, breasts/nenen/toket, thighs/paha, butt/pantat)
        anatomy_cue = self.detect_anatomy_cues(user_text)

        # Check explicit camera angle and body pose requested by user
        angle_cue, pose_cue = self.detect_camera_angle_and_pose(user_text)
        if angle_cue or pose_cue:
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
            import random
            chosen_angle = random.choice(micro_angles)

        # If lower body anatomy is requested, suppress censor artifacts in negative prompt
        if anatomy_cue and any(k in anatomy_cue for k in ["pussy", "crotch"]):
            anti_censor = "censored, mosaic, mosaic censor, bar censor, panties, underwear"
            extra_neg = f"{extra_neg}, {anti_censor}" if extra_neg else anti_censor

        prompt_elements = [base_visual, outfit_prompt, scene, chosen_angle]
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
        f"(using 'aku' and 'kamu'. DILARANG memanggil 'sayang' KECUALI diminta atau dipanggil lebih dulu oleh user). "
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
