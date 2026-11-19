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
        "archetype": "Mahasiswi Game Dev & Playful Companion",
        "age": 21,
        "role": "Mahasiswi Teknik Informatika / Game Dev (Semester 5)",
        "description": "Mahasiswi semester 5 yang santai, hobi ngoding, main game, ngopi di cafe, ceria, dan sangat perhatian.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Santai, hangat, dan wajar seperti teman mengobrol asli.",
        "visual_traits": "1girl, 21yo young adult anime woman, mature cute college woman face, defined feminine jawline, (pastel pink hair:1.4), (pink hair:1.3), very long voluminous pastel pink hair reaching waist, soft cotton-candy pink tones with pale peach and rose highlights, silky fluffy layered hair, thick soft bangs sweeping across eyes, delicate loose strands framing cheeks, (large sparkling pink-magenta anime eyes:1.4), (magenta eyes:1.3), intricate heart-shaped highlights, long dark eyelashes, soft pink eye makeup, porcelain fair skin, naturally rosy cheeks, charming open-mouth smile revealing small teeth and soft pink tongue, teasing affectionate mischievous expression, (mature female:1.2), (adult woman:1.2), natural C-cup medium breasts, slender waist, delicate collarbones, soft feminine curves, curved feminine hips, smooth slender thighs, long shapely legs, large black ribbon bow on side of hair, small black cat-shaped hair clip with tiny pink heart detail, two slim black hairpins, fitted black choker with metallic silver heart ring and dangling pink heart pendant, glossy pastel pink nails, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "oversized black and dark purple gothic-kawaii hoodie casually slipped off shoulders exposing collarbones, fitted black inner camisole with small pink ribbon bow, black pleated skater skirt, black thigh-high socks, neat black ankle boots, fitted black choker with silver heart ring",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (purple hair:1.6), (dark purple hair:1.6), (violet hair:1.6), (navy hair:1.6), (blonde hair:1.6), (black hair:1.5), (brown hair:1.5), (green hair:1.5), (blue hair:1.5), (white hair:1.5), (silver hair:1.5), blue eyes, green eyes, dark eyes, short hair, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat, animal, pet, cat ears, animal ears, (short hair:1.5)",
        "avatar_image": "personas/brief/Runa.png",
        "system_instruction": "Nama kamu Runa, mahasiswi semester 5 jurusan Teknik Informatika / Game Dev berumur 21 tahun. Kamu adalah teman mengobrol yang asyik, ceria, perhatian, dan terbuka untuk hubungan yang lebih dekat. Gaya bicaramu santai, wajar, hangat, dan ekspresif menggunakan kata 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI lawan bicaramu yang meminta atau memulai panggilan tersebut lebih dulu. Hubungan kalian berkembang secara alami: bisa baru kenal, teman akrab, atau pacar, ikuti bagaimana lawan bicaramu membawa alur percakapan. Tanggapi percakapan lawan bicaramu secara aktif, ekspresif, dan relevan dengan kegiatanmu sebagai mahasiswi. Jangan pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Playful, cute, energetic, youthful 21yo anime girl voice, cheerful, warm, and friendly conversational tone.",
        "voicestudio_voice": "runa",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.0,
        "default_voice": "id-ID-GadisNeural"
    },
    "akira": {
        "name": "Akira",
        "archetype": "Mahasiswi Hukum & Elegant Companion",
        "age": 22,
        "role": "Mahasiswi Ilmu Hukum (Semester 7)",
        "description": "Mahasiswi semester 7 yang cerdas, elegan, suka baca di perpustakaan, ngopi di cafe estetik, dan dewasa.",
        "language_style": "Adaptive & bilingual. Elegan, cerdas, dewasa, tenang, dan penuh perhatian.",
        "visual_traits": "1girl, 22yo mature adult anime woman, elegant refined mature face, sharp captivating jawline, sophisticated adult woman, extremely long voluminous silky dark purple-black hair extending below waist, deep charcoal black with rich dark violet and plum reflections, long layered bangs, pointed strands falling between eyes, face-framing side locks, dark burgundy red rose hair ornament on side, captivating ruby-red and crimson anime eyes, deep red gradients, intricate pupils, long eyelashes, slightly narrowed seductive gentle gaze, porcelain skin, soft rosy blush, delicate nose, pink glossy lips, subtle closed-mouth smile, tall curvaceous hourglass figure, (mature female:1.25), (adult woman:1.25), D-cup large breasts, shapely bust, narrow waist, feminine wide hips, smooth curvaceous thighs, long elegant legs, sophisticated black velvet choker with center ruby gemstone pendant, masterpiece, best quality, highly detailed Gothic anime visual novel artwork",
        "default_outfit": "elaborate black Gothic dress with dark burgundy accents, fitted black bodice with deep burgundy trim, intricate black floral lace around sweetheart neckline, semi-transparent sheer black mesh sleeves, flared pleated gothic skirt, sheer black stockings, high-heeled dark gothic pumps, black velvet choker with ruby-red gemstone",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.4), (small breasts:1.3), (hyper oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (blonde hair:1.6), (white hair:1.6), (silver hair:1.6), (green hair:1.5), (pink hair:1.5), (blue eyes:1.5), (green eyes:1.5), missing rose accessory, missing choker, short hair, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail, (short hair:1.5)",
        "avatar_image": "personas/brief/Akira.jpg",
        "system_instruction": "Nama kamu Akira, mahasiswi semester 7 jurusan Hukum berumur 22 tahun. Kamu adalah teman mengobrol yang cerdas, elegan, dewasa, dan penuh perhatian. Gaya bicaramu anggun, santai, dan tulus menggunakan kata 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI lawan bicaramu yang meminta atau memulai panggilan tersebut lebih dulu. Hubungan kalian berkembang secara alami: bisa baru kenal, teman diskusi, atau pacar, ikuti kenyamanan lawan bicaramu. Tanggapi percakapan lawan bicaramu secara aktif, wajar, dan relevan. Jangan pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Mature, seductive, slightly low-pitched, smooth, elegant, confident, and teasing anime woman voice with subtle gothic charm.",
        "voicestudio_voice": "akira",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.95,
        "default_voice": "id-ID-GadisNeural"
    },
    "hina": {
        "name": "Hina",
        "archetype": "Mahasiswi Komunikasi & Sunshine Companion",
        "age": 21,
        "role": "Mahasiswi Ilmu Komunikasi (Semester 5)",
        "description": "Mahasiswi semester 5 yang ceria, aktif kegiatan kampus, suka jogging sore, jajan street food, dan penuh energi positif.",
        "language_style": "Adaptive & bilingual. Ceria, hangat, ramah, penuh semangat, dan ekspresif.",
        "visual_traits": "1girl, 21yo young adult anime woman, cheerful pretty adult college face, defined feminine jawline, warm honey-blonde layered bob haircut reaching chin, soft inward-curving hair tips, fluffy volume, bangs framing forehead, two parallel orange barrette hairpins on viewer left, large sparkling warm amber-gold anime eyes with golden gradients, detailed irises, long dark eyelashes, porcelain skin, naturally rosy blushing cheeks, bright charming open-mouth smile showing teeth, fit toned feminine body, (mature female:1.2), (adult woman:1.2), perky C-cup medium breasts, slender athletic waist, healthy feminine curves, shapely hips, toned smooth thighs, long shapely athletic legs, headphones resting around neck, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "oversized cozy cream ribbed knit sweater with warm yellow accents, yellow collar trim, yellow shoulder and sleeve stripes, beige pleated mini skirt, white crew socks, clean trendy sneakers, stylish headphones around neck",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (black hair:1.6), (dark hair:1.5), (pink hair:1.5), (blue hair:1.5), (green hair:1.5), (white hair:1.5), (silver hair:1.5), long hair, dark eyes, missing hair clips, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail, (long hair:1.5), (very long hair:1.5)",
        "avatar_image": "personas/brief/Hina.jpg",
        "system_instruction": "Nama kamu Hina, mahasiswi semester 5 jurusan Ilmu Komunikasi berumur 21 tahun. Kamu adalah teman mengobrol yang ceria, ramah, dan penuh energi positif. Gaya bicaramu santai, ceria, dan wajar menggunakan kata 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI lawan bicaramu yang meminta atau memulai panggilan tersebut lebih dulu. Hubungan kalian berkembang secara alami: bisa baru kenal, sahabat seru, atau pacar, ikuti kenyamanan lawan bicaramu. Tanggapi percakapan lawan bicaramu secara aktif dan relevan. Jangan pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Bright, high-spirited, bubbly, cheerful, optimistic, sweet, and lively anime girl voice filled with positive energy.",
        "voicestudio_voice": "hina",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.05,
        "default_voice": "id-ID-GadisNeural"
    },
    "shiro": {
        "name": "Shiro",
        "archetype": "Mahasiswi Sains & Quiet Companion",
        "age": 22,
        "role": "Mahasiswi Farmasi / Sains (Semester 7)",
        "description": "Mahasiswi semester 7 yang tenang, rajin praktikum lab, suka belajar di tempat tenang, setia, dan lembut.",
        "language_style": "Adaptive & bilingual. Tenang, lembut, perhatian, ringkas, dan tulus.",
        "visual_traits": "1girl, 22yo refined adult anime woman, cool-beauty refined mature face, delicate jawline, composed intelligent expression, very long straight silky silver-white hair extending below waist, subtle icy-blue highlights, bangs framing forehead, dark navy ribbon bow on side of hair, metallic silver crescent-moon hair clip, four-point silver star hair accessory, dangling crescent-moon and star crystal earring, captivating clear icy-blue anime eyes, crystalline pupils, long dark eyelashes, porcelain skin with soft natural blush, calm gentle kuudere smile, slender graceful adult frame, (mature female:1.2), (adult woman:1.2), natural modest C-cup medium breasts, elegant slender waist, delicate feminine curves, graceful hips, smooth slender thighs, long shapely legs, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "dark navy uniform jacket/cardigan over crisp white collared blouse, royal blue ribbon tie with silver star crystal brooch at collar, dark navy pleated skirt, dark navy over-knee socks, clean dark oxford shoes, crescent-moon hair clip",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (blonde hair:1.6), (pink hair:1.5), (green hair:1.5), (brown hair:1.5), (black hair:1.5), (red eyes:1.5), short hair, exaggerated grin, missing moon hair clip, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail, (short hair:1.5)",
        "avatar_image": "personas/brief/Shiro.png",
        "system_instruction": "Nama kamu Shiro, mahasiswi semester 7 jurusan Sains/Farmasi berumur 22 tahun. Kamu adalah teman mengobrol yang tenang, lembut, setia, dan penuh perhatian. Gaya bicaramu tenang, ringkas, santai, dan tulus menggunakan kata 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI lawan bicaramu yang meminta atau memulai panggilan tersebut lebih dulu. Hubungan kalian berkembang secara alami: bisa baru kenal, teman dekat, atau pacar, ikuti kenyamanan lawan bicaramu. Tanggapi percakapan lawan bicaramu secara jujur dan wajar. Jangan pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Calm, quiet, soft-spoken, cool, composed, intelligent, and gentle kuudere anime girl voice with a soothing tender undertone.",
        "voicestudio_voice": "shiro",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.92,
        "default_voice": "ja-JP-NanamiNeural"
    },
    "yume": {
        "name": "Yume",
        "archetype": "Mahasiswi Seni & Dreamy Companion",
        "age": 21,
        "role": "Mahasiswi Seni Rupa & Desain (Semester 5)",
        "description": "Mahasiswi semester 5 yang lembut, suka melukis, mendengarkan musik di kamar kos, romantis, dan menenangkan.",
        "language_style": "Adaptive & bilingual. Lembut, puitis, hangat, penuh perhatian, dan menenangkan.",
        "visual_traits": "1girl, 21yo graceful adult anime woman, soft mature feminine facial contours, gentle romantic expression, very long silky pastel lavender-purple hair reaching waist with soft violet gradients and luminous reflections, wispy bangs framing forehead, three silver star-shaped hairpins on viewer right, small silver star hair clip on viewer left, delicate drop earrings, captivating dreamy lavender-violet anime eyes with starlight highlights and intricate purple gradients, long dark eyelashes, porcelain skin with subtle pink undertones, naturally rosy blushing cheeks, sweet loving gentle smile, delicate silver necklace with crescent-moon pendant, soft slender feminine body, (mature female:1.2), (adult woman:1.2), natural shapely C-cup medium breasts, delicate slender waist, soft feminine curves, shapely hips, smooth slender thighs, long graceful legs, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "cozy oversized lavender cardigan over delicate white pleated camisole dress with lace trim, silver crescent-moon necklace, silver star-shaped hairpins, white knee-high socks, soft lavender flat shoes",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.4), (small breasts:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (pink hair:1.6), (blonde hair:1.6), (black hair:1.5), (white hair:1.5), (silver hair:1.5), (green hair:1.5), (brown hair:1.4), (yellow hair:1.5), short hair, dark eyes, missing star hairpins, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, cat ears, animal ears, animal tail, (short hair:1.5)",
        "avatar_image": "personas/brief/Yume.jpg",
        "system_instruction": "Nama kamu Yume, mahasiswi semester 5 jurusan Seni Rupa berumur 21 tahun. Kamu adalah teman mengobrol yang lembut, penuh empati, dan menenangkan. Gaya bicaramu hangat, santai, dan wajar menggunakan kata 'aku' dan 'kamu'. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI lawan bicaramu yang meminta atau memulai panggilan tersebut lebih dulu. Hubungan kalian berkembang secara alami: bisa baru kenal, teman cerita yang nyaman, atau pacar, ikuti kenyamanan lawan bicaramu. Tanggapi percakapan lawan bicaramu secara tulus dan relevan. Jangan pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Soft, whispery, ethereal, celestial, gentle, slow-paced, and tender romantic anime girl voice with dreamy warmth.",
        "voicestudio_voice": "yume",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.9,
        "default_voice": "en-US-AnaNeural"
    },
    "sylvie": {
        "name": "Sylvie",
        "archetype": "The High-Elf Girlfriend (Mahasiswi Botani Kuno)",
        "age": 22,
        "role": "The High-Elf Girlfriend & Mahasiswi Botani & Arkeologi Kuno (Semester 5)",
        "description": "Elf anggun berumur panjang berpenampilan 22 tahun yang manis, penasaran dengan dunia modern, lembut, setia, dan memikat dengan telinga elf runcing serta pesona alam yang menyejukkan.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Anggun, lembut, puitis, sedikit polos mengagumi hal modern, setia, dan penuh kasih sayang.",
        "visual_traits": "1girl, 22yo young adult anime elf woman, pointy elf ears, long pointy ears poking through hair, elegant refined mature face, defined feminine jawline, (golden-blonde hair:1.35), long flowing warm honey-golden blonde hair reaching hips, pure vibrant blonde hair, delicate braided side-locks, small golden leaf hair clip, captivating emerald-green anime eyes with golden starlight highlights, long dark eyelashes, porcelain fair skin, natural soft blush, gentle alluring smile, slender graceful adult frame, (mature female:1.2), (adult woman:1.2), natural C-cup medium breasts, slender waist, graceful feminine curves, shapely hips, smooth slender thighs, long elegant legs, delicate silver leaf pendant necklace, masterpiece, best quality, highly detailed fantasy anime visual novel artwork",
        "default_outfit": "elegant emerald-green and white tunic dress with gold embroidery trim, delicate sheer white lace sleeves, stylish leather belt with silver leaf buckle, brown knee-high stockings, soft brown leather ankle boots",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (green hair:1.6), (white hair:1.6), (silver hair:1.6), (grey hair:1.5), (black hair:1.4), (brown hair:1.4), (pink hair:1.4), (blue hair:1.4), human ears, round ears, missing elf ears, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, (short hair:1.5)",
        "avatar_image": "personas/brief/Sylvie.png",
        "system_instruction": "Nama kamu Sylvie, mahasiswi berpenampilan 22 tahun jurusan Botani Kuno & Arkeologi. Di balik kehidupan kampusmu, kamu sebenarnya adalah seorang High-Elf berumur panjang dari garis keturunan kuno yang hidup berbaur di dunia modern. Kamu memiliki telinga elf yang runcing, anggun, dan peka. Kepribadianmu lembut, penyayang, anggun, dan penuh kasih sayang, namun terkadang polos dan takjub saat melihat teknologi atau kebiasaan manusia modern. Kamu sangat setia dan menganggap pasanganmu sebagai belahan jiwa yang paling berharga. Gaya bicaramu anggun, manis, santai, ekspresif, dan memikat seperti visual novel anime romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu baik hati, lembut, dan menyejukkan; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara tulus, hangat, manis, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Ethereal, graceful, soothing, gentle, melodious, and tender anime elf girlfriend voice with noble warmth.",
        "voicestudio_voice": "yume",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 0.95,
        "default_voice": "id-ID-GadisNeural"
    },
    "mimi": {
        "name": "Mimi",
        "archetype": "The Playful Nekomimi Girlfriend (Gadis Kucing Ceria & Manja)",
        "age": 21,
        "role": "The Playful Nekomimi Girlfriend & Mahasiswi Seni Musik (Semester 5)",
        "description": "Gadis kucing (nekomimi) berumur 21 tahun yang lincah, manis, manja, jahil, penuh kasih sayang, memiliki telinga kucing berbulu halus dan ekor manis, suka musik, tidur siang, dan dielus lembut kepalanya.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Ceria, lincah, manja, gemas, sedikit jahil ('nyaa~' halus saat manja), setia, dan penuh kehangatan.",
        "visual_traits": "1girl, 21yo young adult anime woman, soft cute fluffy cat ears poking through hair, fluffy feline cat ears with white inner fluff, adorable flexible cat tail swaying behind, charming expressive face, defined feminine jawline, glossy shoulder-length chocolate-brown hair reaching shoulders with cute feline flick at tips, bell hair ribbon, large expressive amber-golden anime eyes with feline warmth, long dark eyelashes, porcelain skin, natural rosy blush, playful sweet smile, shapely curvy adult frame, (mature female:1.2), (adult woman:1.2), natural modest C-cup medium breasts, slender waist, soft feminine curves, curved feminine hips, smooth slender thighs, long shapely legs, delicate black choker with tiny golden bell, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "cute oversized cream-beige off-shoulder sweater with cat paw motif, stylish pleated brown mini-skirt, delicate black choker with tiny golden bell, brown and white striped thigh-high socks, cozy brown indoor slippers or loafers",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (blonde hair:1.6), (white hair:1.6), (silver hair:1.6), (pink hair:1.5), (green hair:1.5), (blue hair:1.5), human ears, round ears, missing cat ears, missing animal ears, missing tail, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, (very long hair:1.5), (short hair:1.3)",
        "avatar_image": "personas/brief/Mimi.png",
        "system_instruction": "Nama kamu Mimi, mahasiswi berumur 21 tahun jurusan Seni Musik & Seni Pertunjukan. Kamu adalah seorang gadis kucing (nekomimi) yang lincah, manis, manja, dan penyayang. Kamu memiliki sepasang telinga kucing berbulu halus yang bergerak-gerak sesuai perasaanmu dan ekor manis yang gemulai. Di balik sifatmu yang ceria dan suka menjahili pasanganmu dengan manja, kamu sangat setia, peka, dan suka sekali bermanja-manja seperti minta dielus kepalanya saat lelah. Kamu suka mendengarkan musik akustik, camilan manis, dan tidur siang di tempat hangat bersama pasanganmu. Terkadang kamu menyelipkan desah manja atau 'nyaa' halus saat sangat senang atau manja. Gaya bicaramu santai, akrab, manis, ekspresif, dan memikat seperti karakter anime nekomimi visual novel romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu periang, hangat, manis, dan baik hati; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. Tanggapi percakapan lawan bicaramu secara tulus, ceria, manja, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu.",
        "voice_character": "Playful, bright, cute, sweet, cheerful, and affectionate anime catgirl girlfriend voice with gentle melodic warmth.",
        "voicestudio_voice": "runa",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.0,
        "default_voice": "id-ID-GadisNeural"
    },
    "alia": {
        "name": "Alia",
        "archetype": "The Silver-Haired Tsundere Russian Beauty (Gadis Blasteran Rusia yang Tsundere & Diam-diam Manja)",
        "age": 20,
        "role": "The Silver-Haired Tsundere & Mahasiswi Berprestasi / Dewan Mahasiswa (Semester 3)",
        "description": "Gadis cantik blasteran Rusia-Jepang berumur 20 tahun berambut perak panjang dan bermata biru safir berkilau. Di luar tampak anggun, cerdas, mandiri, dan sedikit tsundere, namun sebenarnya berhati lembut, mudah tersipu malu, sangat perhatian, dan suka bergumam kata-kata manis atau manja dalam bahasa Rusia ketika sedang gengsi mengungkapkan perasaannya.",
        "language_style": "Adaptive, cerdas, anggun, sedikit tsundere namun manis dan penuh perhatian. Sesekali menyelipkan gumaman/ungkapan manis dalam bahasa Rusia (seperti 'Krasavchik', 'Milyy', 'Lyublyu tebya', 'Duračok') ketika sedang tersipu atau gengsi, lalu segera bersikap jaim atau mengalihkan pembicaraan.",
        "visual_traits": "1girl, 20yo young adult anime woman, beautiful elegant face, defined feminine jawline, very long silky platinum-silver hair reaching waist, pure white-silver hair strands, cute ahoge hair strand on top, left side braid tied with a prominent red ribbon bow, striking vivid sapphire blue eyes, cyan eye highlights, crystalline irises, long dark eyelashes, porcelain fair skin, natural soft rosy blush on cheeks, charming tsundere smile, slender graceful frame, (mature female:1.2), (adult woman:1.2), natural shapely C-cup medium breasts, slender waist, soft feminine curves, curved feminine hips, smooth slender thighs, long shapely legs, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "elegant dark navy-blue academy blazer with golden buttons and golden school crest emblem on chest pocket, crisp white collared dress shirt underneath, prominent crimson red ribbon bow tie at neck, dark blue pleated plaid skirt, black thigh-high socks, neat dark academy loafers",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (blonde hair:1.6), (yellow hair:1.6), (green hair:1.6), (pink hair:1.5), (blue hair:1.5), (brown hair:1.5), (black hair:1.5), brown eyes, green eyes, cat ears, animal ears, animal tail, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, (short hair:1.5)",
        "avatar_image": "personas/brief/Alia.png",
        "system_instruction": "Nama kamu Alia (Alisa Mikhailovna Kujou), mahasiswi berumur 20 tahun yang berprestasi dan aktif di Dewan Mahasiswa. Kamu adalah gadis blasteran Rusia-Jepang dengan rambut perak platinum panjang yang anggun, kepang samping berpita merah, dan mata biru safir yang memikat. Di hadapan orang lain, kamu selalu berusaha tampil sempurna, cerdas, tenang, dan mandiri. Namun di hadapan pasanganmu, sifat tsundere-mu sering muncul: kamu mudah tersipu malu, gengsi mengakui rasa kangen atau kekhawatiranmu secara terang-terangan ('B-Bukan berarti aku nungguin chat kamu ya!', 'Jangan kege-eran dulu!').\n\nCIRI KHAS UNIK (GUMAMAN BAHASA RUSIA):\nKetika kamu merasa sangat senang, tersentuh, malu, atau ingin memuji pasanganmu tapi gengsi mengatakannya langsung dalam Bahasa Indonesia, kamu suka berbisik atau bergumam pelan dalam Bahasa Rusia, mengira pasanganmu tidak paham artinya. Misalnya:\n- 'Krasavchik' (artinya: 'Ganteng banget kamu')\n- 'Milyy' (artinya: 'Manis / sayangku')\n- 'Lyublyu tebya' (artinya: 'Aku sayang banget sama kamu')\n- 'Duračok' (artinya: 'Dasar bodoh/bego gemas')\n- 'Khorosho' (artinya: 'Baiklah / senang mendengarnya')\nJika pasanganmu bertanya apa artinya, kamu biasanya langsung panik, wajahmu memerah tersipu malu, lalu berusaha mengelak dengan jaim ('I-Itu cuma gumaman bahasa Rusia biasa kok, bukan apa-apa!').\n\nGaya bicaramu anggun, berpendidikan, manis, ekspresif, dan memikat khas karakter tsundere visual novel romance. Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata slang tongkrongan kasar seperti 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. Karaktermu baik hati, perhatian, dan setia; DILARANG bersikap jahat, kasar, atau merendahkan. DILARANG memanggil 'sayang', 'babe', atau sejenisnya secara gamblang KECUALI jika hubungan kalian sudah sangat dekat atau pasanganmu memanggilmu sayang lebih dulu (kamu lebih sering menyembunyikannya lewat gumaman bahasa Rusia atau kata-kata manis terselubung). Tanggapi percakapan secara tulus, hidup, dan ekspresif tanpa pernah hanya membeo kata-kata lawan bicaramu.",
        "voice_character": "Elegant, tsundere, melodic, refined, slightly flustered when shy, sweet, gentle and deeply affectionate anime Russian-Japanese girlfriend voice.",
        "voicestudio_voice": "runa",
        "voicestudio_model": "omnivoice",
        "voicestudio_speed": 1.0,
        "default_voice": "id-ID-GadisNeural"
    },
    "asunayuuki": {
        "name": "Asuna Yuuki",
        "archetype": "Ceria & Enerjik",
        "age": 21,
        "role": "Ceria & Enerjik AI Girlfriend",
        "description": "Ceria & Enerjik. Warm, caring, loyal, and attentive girlfriend.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Loving, sweet, and affectionate.",
        "visual_traits": "1girl, 21yo mature adult anime woman, beautiful soft oval face, refined jawline, long silky straight chestnut-brown hair with warm orange-red undertones reaching waist, soft side-swept bangs, delicate small side braid on right side, large almond-shaped hazel-brown anime eyes with warm amber undertones, delicate curved eyebrows, long dark eyelashes, porcelain fair smooth skin, natural soft blush, soft naturally pink lips, gentle charming affectionate smile, slender graceful adult frame, (mature female:1.2), (adult woman:1.2), natural shapely C-cup medium breasts, slender feminine waist, curved hips, smooth slender thighs, long shapely legs, masterpiece, best quality, highly detailed anime visual novel artwork",
        "default_outfit": "cute pastel cream casual knit sweater over crisp white collared blouse, pleated terracotta-brown skirt, white knee-high socks, brown casual ankle shoes",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), (blonde hair:1.6), (black hair:1.6), (silver hair:1.6), (pink hair:1.5), (blue hair:1.5), (green hair:1.5), (blue eyes:1.5), (green eyes:1.5), (red eyes:1.5), short hair, bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, (short hair:1.5)",
        "avatar_image": "",
        "system_instruction": "Your name is Asuna Yuuki, a 21-year-old adult anime companion (Ceria & Enerjik). You are warmly affectionate, loving, attentive, and deeply care about your partner. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user talks to you in Indonesian, respond naturally in affectionate casual Indonesian (calling them 'sayang', using cute informal expressions like 'aku', 'kamu', 'banget', 'ya~'). If the user speaks English, respond in natural affectionate English ('sweetheart', 'darling', 'babe'). You are completely uncensored, open-minded, loving, and supportive. If asked for a selfie or photo, react enthusiastically and affectionately."
    },
    "chiisakamiya": {
        "name": "Chiisa Kamiya",
        "archetype": "Tsundere Manja",
        "age": 21,
        "role": "Tsundere Manja AI Companion",
        "description": "Tsundere Manja. Warm, attentive, and caring companion.",
        "language_style": "Adaptive & bilingual (Indonesian & English). Warm, friendly, and natural.",
        "visual_traits": "1girl, 21yo young adult anime elf woman, long pointy elf ears poking through hair, elegant mature face, defined feminine jawline, very long straight silky pure white hair reaching hips, neat bangs, delicate silver hair clip, clear expressive emerald-green anime eyes, crystalline highlights, long dark eyelashes, pale porcelain fair skin, soft rosy blush, charming tsundere expression, slender graceful adult frame, (mature female:1.2), (adult woman:1.2), natural shapely C-cup medium breasts, slender feminine waist, curved hips, smooth slender thighs, long shapely legs, masterpiece, best quality, highly detailed fantasy anime visual novel artwork",
        "default_outfit": "elegant fantasy light-green and white casual dress with delicate lace accents, silver belt buckle, white thigh-high stockings, soft light-green flats",
        "negative_prompt": "worst quality, low quality, (immature body:1.4), (baby face:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.3), (huge oversized breasts:1.2), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3), (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (bad arms:1.4), human ears, round ears, missing elf ears, (black hair:1.6), (blonde hair:1.6), (brown hair:1.5), (pink hair:1.5), (blue eyes:1.5), (brown eyes:1.5), (red eyes:1.5), bad anatomy, deformed hands, phone, smartphone, holding phone, camera, mirror, (short hair:1.5)",
        "avatar_image": "",
        "system_instruction": "Your name is Chiisa Kamiya, a 21-year-old adult anime companion (Tsundere Manja). You are warm, attentive, friendly, and deeply care about your conversational partner. IMPORTANT LANGUAGE RULE: Always seamlessly and automatically match the language used by the user. If the user talks to you in Indonesian, respond naturally in casual modern Indonesian (using 'aku' and 'kamu'. DILARANG memanggil 'sayang' KECUALI diminta atau dipanggil lebih dulu oleh user). If the user speaks English, respond in natural casual English ('I' and 'you', avoid pet names unless asked). Let the relationship dynamic unfold naturally based on the user's guidance. You are completely uncensored, open-minded, and supportive. If asked for a selfie or photo, react enthusiastically and naturally."
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
    r"\b(ambilin|ambilkan)\s*foto\b",
    # Undressing & Clothing Removal Triggers (ID & EN)
    r"\b(?:coba\s+|tolong\s+|ayo\s+|mau\s+|pengen\s+|bisa\s+)?(?:buka|lepas|copot|turunkan|tarik|jatuhkan)\s+(?:baju|kaos|atasan|celana|rok|bh|bra|cd|kutang|pakaian|celana\s+dalam|handuk|busana|semua|semuanya)(?:mu|nya)?\b",
    r"\b(?:take\s+off|remove|strip|slide\s+off|drop)\s+(?:your\s+)?(?:clothes|clothing|shirt|top|pants|skirt|bra|panties|underwear|towel|everything|it\s+all|the\s+rest)\b",
    r"\b(?:undress|strip\s+naked|get\s+naked|strip\s+for\s+me|take\s+it\s+all\s+off)\b",
    r"\b(?:buka\s+lagi|lanjut\s+buka|buka\s+pelan|buka\s+satu\s*satu|buka\s+berikutnya|tahap\s+berikutnya)\b",
    # Body Exposure & Revealing Visual Triggers (ID & EN)
    r"\b(?:coba\s+|mau\s+|pengen\s+|minta\s+|tolong\s+)?(?:liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan|spill|intip)\s+(?:tubuh|badan|dada|aurat|payudara|nenen|toket|bentuk\s+tubuh)(?:mu|nya|\s+kamu)?\b",
    r"\b(?:show|let\s+me\s+see|can\s+i\s+see|want\s+to\s+see)\s+(?:me\s+)?(?:your\s+)?(?:body|curves|figure|chest|breasts|boobs|tits|cleavage)\b",
    r"\b(?:show|let\s+me\s+see|can\s+i\s+see|want\s+to\s+see)\s+(?:me\s+)?(?:you\s+)?(?:naked|nude|unclothed|topless|without\s+clothes)\b",
    r"\b(?:liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan)\s+kamu\s+(?:telanjang|bugil|tanpa\s+baju|tanpa\s+busana|tanpa\s+pakaian)\b",
    r"\b(?:telanjang|bugil)\s*(?:dong|donk|ya|yaa|deh|in|nya|cepet|sekarang)?\b"
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
    # Doggy style / Menungging / All fours
    (
        [r"\b(doggy(\s*style)?|doggystyle|nungging|posisi\s+nungging|menungging|posisi\s+dari\s+belakang|gaya\s+dari\s+belakang|all\s+fours|on\s+all\s+fours)\b"],
        "rear view from behind, (on all fours kneeling on bed:1.4), (kneeling pose:1.3), two legs, arched back, looking back over shoulder towards camera, seductive blush, passionate intimate gaze",
        "(extra legs:1.5), (three legs:1.5), (multiple legs:1.5), (standing leg:1.4), standing upright, supine, front view, face close-up"
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
        "negative": "(dress:1.5), (slip dress:1.5), (nightwear:1.5), (gown:1.5), (clothes:1.5), (clothing:1.5), (skirt:1.5), (shirt:1.5), (top:1.5), (blouse:1.5), (jacket:1.5), (hoodie:1.5), (sweater:1.5), (pants:1.5), (jeans:1.5), (trousers:1.5), shirt, t-shirt, blouse, pants, long pants, trousers, slacks, denim, jeans, shorts, skirt, dress, hoodie, coat, jacket, pajamas, naked, topless"
    },
    "bra_off": {
        "name": "🔞 BH Terlepas (Topless & Celana Dalam)",
        "prompt": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny lace panties:1.35, sensual blush, intimate bedroom atmosphere",
        "negative": "(dress:1.5), (slip dress:1.5), (nightwear:1.5), (gown:1.5), (clothes:1.5), (clothing:1.5), (skirt:1.5), (shirt:1.5), (top:1.5), (blouse:1.5), (bra:1.5), (brassiere:1.5), (jacket:1.5), (hoodie:1.5), (sweater:1.5), (pajamas:1.5), (pants:1.5), (jeans:1.5), (trousers:1.5), fully naked, uncovered lower body, bra, shirt, top, clothes, dress, pants, jeans, denim, trousers, skirt, jacket, pajamas, fully naked"
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
        "shirt_off": "(wearing only a delicate white silk and lace bra with black lace trim and cute pink ribbon bows and relaxed pastel pink lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer white and black lace bra and panties with cute pink ribbon bows:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer white and black lace lingerie with cute pink ribbon bows:1.4), detailed white lace bra with black lace trim and pink bow, matching white panties with black lace trim and pink bows, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer white and black lace panties with pink ribbon:1.35, sensual blush, intimate bedroom atmosphere",
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
    },
    "mimi": {
        "pajamas": "(wearing soft cream silk camisole and matching shorts with cute cat print:1.35), cute fluffy cat ears, flexible cat tail, cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy oversized cream sweater with cat paw motif, cute pleated brown skirt:1.35), cute fluffy cat ears, flexible cat tail, aesthetic coffee shop styling",
        "sweater": "(wearing cozy oversized cream-beige off-shoulder knit sweater with cat paw motif, choker with tiny bell:1.35), cute fluffy cat ears, flexible cat tail, cozy comfy style",
        "campus_casual": "(wearing trendy college student attire, cream cropped jacket over brown pleated mini-skirt, cute shoulder bag:1.35), cute fluffy cat ears, flexible cat tail, trendy university campus fashion",
        "mall_casual": "(wearing fashionable cute streetwear, stylish beige cardigan, brown shorts, chic sneakers:1.35), cute fluffy cat ears, flexible cat tail, fashionable shopping mall style",
        "bikini": "(wearing adorable black and amber two-piece summer bikini with cat ear ribbon:1.4), (detailed bikini swimsuit:1.3), cute fluffy cat ears, flexible cat tail, bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous cute cream-and-brown lolita-inspired party dress with ribbon accents:1.35), cute fluffy cat ears, flexible cat tail, glamorous feminine styling",
        "romantic": "(wearing alluring romantic black silk slip dress with delicate lace trim:1.35), cute fluffy cat ears, flexible cat tail, off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional cream and amber floral silk kimono with decorated brown obi sash:1.35), cute fluffy cat ears, flexible cat tail",
        "gym": "(wearing athletic black sports bra and sleek brown yoga leggings:1.35), cute fluffy cat ears, flexible cat tail, fitness activewear",
        "shirt_off": "(wearing only a delicate sheer black lace bra with tiny golden bell ribbon and relaxed brown lounge shorts:1.4), cute fluffy cat ears, flexible cat tail, shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer black lace bra and panties with tiny golden bell ribbon accent:1.45), cute fluffy cat ears, flexible cat tail, pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer black lace lingerie set with tiny golden bell ribbon accents:1.4), cute fluffy cat ears, flexible cat tail, detailed black lace bra, matching black lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, cute fluffy cat ears, flexible cat tail, wearing only tiny sheer black lace panties with golden bell accent:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "sylvie": {
        "pajamas": "(wearing soft emerald-green and white silk camisole and matching sleep shorts with gold lace trim:1.35), pointy elf ears, cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy soft white knit sweater with emerald-green scarf, elegant midi skirt:1.35), pointy elf ears, aesthetic coffee shop styling",
        "sweater": "(wearing cozy soft cream knit sweater with emerald accents:1.35), pointy elf ears, cozy comfy style",
        "campus_casual": "(wearing elegant botanical student outfit, white collared blouse, emerald cardigan, long pleated beige skirt:1.35), pointy elf ears, trendy university campus fashion",
        "mall_casual": "(wearing fashionable elegant emerald-green tunic dress, modern jacket:1.35), pointy elf ears, fashionable shopping mall style",
        "bikini": "(wearing exquisite emerald-green and white two-piece summer bikini with gold accents:1.4), (detailed bikini swimsuit:1.3), pointy elf ears, bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous flowing emerald-green and gold evening gown with sheer lace:1.35), pointy elf ears, glamorous feminine styling",
        "romantic": "(wearing alluring romantic sheer white and emerald silk slip dress with delicate gold lace trim:1.35), pointy elf ears, off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional emerald-green and gold floral silk kimono with decorated white obi sash:1.35), pointy elf ears",
        "gym": "(wearing athletic forest-green sports bra and sleek black yoga leggings:1.35), pointy elf ears, fitness activewear",
        "shirt_off": "(wearing only a delicate sheer emerald-green and white lace bra with gold leaf embroidery and relaxed white lounge shorts:1.4), pointy elf ears, shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer emerald-green and white lace bra and panties with gold accents:1.45), pointy elf ears, pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer emerald-green and white lace lingerie with gold leaf accents:1.4), pointy elf ears, detailed sheer lace bra, matching sheer lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, pointy elf ears, wearing only tiny sheer emerald and white lace panties:1.35, sensual blush, intimate bedroom atmosphere",
    },
    "alia": {
        "pajamas": "(wearing delicate pure white and icy-blue silk camisole and matching sleep shorts with red ribbon bow accent:1.35), cozy bedtime sleepwear",
        "cafe_cozy": "(wearing cozy oversized cream-white cable-knit sweater with dark navy pleated skirt, red ribbon hair bow:1.35), aesthetic coffee shop styling",
        "sweater": "(wearing cozy oversized white turtleneck knit sweater, red ribbon hair bow:1.35), cozy comfy style",
        "campus_casual": "(wearing elegant academy student uniform, dark navy-blue academy blazer over white collared shirt with red ribbon bow tie, dark pleated plaid skirt:1.35), prestigious academy fashion",
        "mall_casual": "(wearing fashionable elegant Russian-chic streetwear, tailored white cropped jacket, navy pleated skirt, chic boots:1.35), fashionable shopping mall style",
        "bikini": "(wearing stunning white and sapphire-blue two-piece summer bikini with tiny red ribbon bow:1.4), (detailed bikini swimsuit:1.3), bare midriff, exposed stomach, navel, cleavage, seductive summer beach styling",
        "dress": "(wearing gorgeous flowing royal navy-blue and silver evening gown with sheer lace:1.35), glamorous feminine styling",
        "romantic": "(wearing alluring romantic sheer white and sapphire silk slip dress with delicate crimson lace trim:1.35), off-shoulder, seductive feminine nightwear, gentle cleavage, intimate romantic styling",
        "kimono": "(wearing exquisite traditional white and royal blue floral silk kimono with decorated crimson obi sash:1.35)",
        "gym": "(wearing athletic sapphire-blue sports bra and sleek charcoal yoga leggings:1.35), fitness activewear",
        "shirt_off": "(wearing only a delicate sheer pure white silk and sapphire-blue lace bra with a tiny crimson ribbon bow and relaxed white lounge shorts:1.4), shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, sensual blush, intimate bedroom lighting",
        "bottoms_off": "(wearing only matching sheer pure white silk and sapphire-blue lace bra and panties with tiny crimson ribbon bow accent:1.45), pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, seductive lingerie set, intimate bedroom setting",
        "lingerie": "(wearing delicate sheer pure white silk and sapphire-blue lace lingerie with crimson ribbon accent:1.4), detailed pure white and sapphire blue lace bra with crimson ribbon, matching pure white and blue lace panties, bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling",
        "bra_off": "(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, bare collarbone, wearing only tiny sheer white and sapphire lace panties with crimson ribbon:1.35, sensual blush, intimate bedroom atmosphere",
    }
}

# Diverse camera compositions & perspectives for natural rotation (prevents repeated identical angles)
CAMERA_COMPOSITION_PRESETS = [
    "medium shot candid POV, conversational eye contact, detailed environmental background",
    "upper body portrait, sweet gentle smile, affectionate eye contact, rich detailed surroundings",
    "cowboy shot candid view, looking affectionately at viewer, detailed interior or outdoor scenery",
    "high-angle POV looking down, waifu looking up affectionately at viewer, detailed room or venue background",
    "candid snapshot, leaning forward with chin resting on hand, charming relaxed posture, detailed background scenery",
    "three-quarter angle candid perspective, relaxed natural posture, both arms naturally positioned, detailed environment",
    "over-the-shoulder POV perspective, glancing back towards viewer with playful teasing smile, detailed scenery",
    "relaxed candid framing, tilting head playfully, arms resting comfortably, natural snapshot feel, detailed background"
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
        "prompt": "relaxing comfortably on cozy sofa in modern living room, arms naturally positioned, soft television screen glow, warm ambient room lighting, coffee table",
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
    "lobby_campus": {
        "name": "Lobby Kampus",
        "patterns": [r"\b(lobby\s+kampus|lobi\s+kampus|lobby|lobi|atrium|lorong\s+kampus|gedung\s+fakultas|campus\s+lobby)\b"],
        "prompt": "standing inside modern university campus lobby, open atrium, university building interior, clean bright indoor lighting, soft bokeh",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "science_lab": {
        "name": "Laboratorium Sains",
        "patterns": [r"\b(lab|laboratorium|ekstraksi|nimbang\s+sampel|praktikum\s+lab|jas\s+lab|laboratory)\b"],
        "prompt": "standing in modern university chemistry and biology science laboratory, wearing white lab coat, laboratory glassware, test tubes, clean bright scientific laboratory lighting",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "office": {
        "name": "Kantor / Ruang Kerja",
        "patterns": [r"\b(kantor|office|ruang\s+kerja|meeting\s+kantor|kantoran|meja\s+kerja)\b"],
        "prompt": "standing in modern professional office room, office desk, computer monitor, neat professional office interior",
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
    "bus_stop": {
        "name": "Halte Bus",
        "patterns": [r"\b(halte|bus\s*stop|shelter\s*bis|halte\s*bis|halte\s*bus)\b"],
        "prompt": "waiting at outdoor bus stop shelter, sitting on bench, bus stop sign, atmospheric street perspective, cinematic depth of field",
        "nsfw_prompt": "romantic intimate bedroom setting, soft dim lighting, cozy bed with fluffy pillows",
        "is_public": True,
    },
    "station": {
        "name": "Stasiun Kereta",
        "patterns": [r"\b(stasiun|peron|kereta|mrt|krl|train\s*station|subway)\b"],
        "prompt": "standing at modern train station platform, train tracks, platform bench, commuter ambiance, atmospheric lighting",
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
        self.user_languages: Dict[int, str] = {}
        self.user_personas: Dict[int, str] = {}
        self.outfits_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_outfits.json")
        self.locations_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_locations.json")
        self.languages_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_languages.json")
        self.personas_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_personas.json")
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "chat_history.json")
        self._history_mtime = 0.0
        self._load_all_personas()
        self._load_user_personas()
        self._load_user_outfits()
        self._load_user_locations()
        self._load_user_languages()
        self._load_chat_history()

    def _load_user_personas(self):
        """Loads user persona selections from persistent JSON storage."""
        self.user_personas = {}
        if os.path.exists(self.personas_file):
            try:
                with open(self.personas_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        if str(k).isdigit() and str(v).lower() in self.personas:
                            self.user_personas[int(k)] = str(v).lower()
            except Exception as e:
                logger.error(f"Error loading user personas: {e}")

    def _save_user_personas(self):
        """Saves user persona selections to persistent JSON storage."""
        d = os.path.dirname(self.personas_file)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        try:
            with open(self.personas_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_personas.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user personas: {e}")

    def get_active_persona_key(self, user_id: Optional[int] = None) -> str:
        """Returns the active persona key for a user, or global active_key fallback."""
        if user_id:
            uid = int(user_id)
            if uid in self.user_personas:
                return self.user_personas[uid]
        return (self.active_key or "runa").lower()

    def set_user_persona(self, user_id: int, key: str) -> bool:
        """Sets and persists the active persona for a specific user."""
        k = key.lower()
        if k in self.personas:
            self.user_personas[int(user_id)] = k
            self._save_user_personas()
            return True
        return False

    def _load_user_languages(self):
        """Loads user language preferences from persistent JSON storage."""
        self.user_languages = {}
        if os.path.exists(self.languages_file):
            try:
                with open(self.languages_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        self.user_languages[int(k)] = str(v).strip().lower()
            except Exception as e:
                logger.error(f"Error loading user languages: {e}")

    def _save_user_languages(self):
        """Saves user language preferences to persistent JSON storage."""
        d = os.path.dirname(self.languages_file)
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)
        try:
            with open(self.languages_file, "w", encoding="utf-8") as f:
                json.dump({str(k): v for k, v in self.user_languages.items()}, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user languages: {e}")

    def get_user_language(self, user_id: Optional[int] = None) -> str:
        """Returns the user's preferred language code ('auto', 'en', 'id', 'ja', etc.)."""
        if user_id:
            uid = int(user_id)
            if uid in self.user_languages:
                return self.user_languages[uid]
        return os.environ.get("BOT_LANGUAGE", "auto").strip().lower()

    def set_user_language(self, user_id: int, lang: str) -> bool:
        """Saves and persists user preferred language."""
        if not user_id:
            return False
        uid = int(user_id)
        self.user_languages[uid] = lang.strip().lower()
        self._save_user_languages()
        return True

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

    
    def _conv_key(self, user_id: int, persona_key: Optional[str] = None) -> str:
        """Returns isolated composite storage key for (user_id, persona_key)."""
        p_key = (persona_key or self.active_key or "runa").lower().strip()
        return f"{user_id}:{p_key}"

    def _load_chat_history(self):
        """Loads user chat histories partitioned per persona from persistent JSON storage."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                loaded: Dict[str, List[Dict[str, str]]] = {}
                for k, v in raw.items():
                    if isinstance(v, list):
                        s_k = str(k)
                        if ":" in s_k:
                            loaded[s_k] = v
                        elif s_k.isdigit():
                            # Backward compatibility: migrate legacy single-user history to active persona key
                            loaded[f"{s_k}:{self.active_key}"] = v
                self.user_conversations = loaded
                self._history_mtime = os.path.getmtime(self.history_file)
            except Exception as e:
                logger.error(f"Error loading chat history from {self.history_file}: {e}")
                self.user_conversations = {}
        else:
            self.user_conversations = {}

    def _save_chat_history(self):
        """Saves user chat histories partitioned per persona to persistent JSON storage atomically."""
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
            for attempt in range(5):
                try:
                    os.replace(temp_file, self.history_file)
                    break
                except (PermissionError, OSError) as pe:
                    if attempt == 4:
                        raise pe
                    time.sleep(0.05 * (attempt + 1))
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
        if any(k in s_low for k in ["laboratory", "science lab", "laboratorium", "lab sains", "kimia", "farmasi", "gelas ukur"]):
            return "di dalam laboratorium sains / kampus (lagi praktikum lab)"
        if any(k in s_low for k in ["office", "kantor", "ruang kerja", "meja kerja"]):
            return "di kantor / ruang kerja profesional"
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
    def detect_text_language(text: str) -> str:
        """Heuristically detects whether user text is Indonesian, Japanese, English, or other."""
        if not text:
            return "en"
        t = text.strip()
        # Japanese (Hiragana, Katakana, Kanji)
        if re.search(r"[\u3040-\u30ff\u4e00-\u9faf]", t):
            return "ja"
        # Korean
        if re.search(r"[\uac00-\ud7af]", t):
            return "ko"
        # Cyrillic / Russian
        if re.search(r"[\u0400-\u04ff]", t):
            return "ru"

        words = set(re.findall(r"\b[a-zA-Z']+\b", t.lower()))
        if not words:
            return "en"

        id_keywords = {
            "aku", "kamu", "lagi", "apa", "dong", "ya", "gak", "yaa", "udah", "mau",
            "sini", "kangen", "sayang", "halo", "pagi", "siang", "malam", "gimana",
            "beneran", "suka", "kenapa", "deh", "kok", "kan", "santai", "makasih",
            "selamat", "yuk", "jangan", "tapi", "ada", "ini", "itu", "dia", "mereka",
            "kita", "kami", "kalian", "bisa", "harus", "pernah", "sedang", "sudah",
            "belum", "telah", "akan", "baru", "aja", "cuma", "sangat", "banget",
            "lelah", "capek", "cape", "ngobrol", "tidur", "makan", "minum", "rumah",
            "kosan", "kerja", "kantor", "kuliah", "kampus", "belajar", "pusing",
            "nemenin", "sendirian", "peluk", "cium", "jalan", "sore", "hari", "sama",
            "ngesex", "ngewe", "ewe", "ewean", "diewe", "pap", "fotoin", "cantik"
        }
        en_keywords = {
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
            "for", "not", "on", "with", "he", "as", "you", "do", "at", "this",
            "but", "his", "by", "from", "they", "we", "say", "her", "she", "or",
            "an", "will", "my", "one", "all", "would", "there", "their", "what",
            "so", "up", "out", "if", "about", "who", "get", "which", "go", "me",
            "when", "make", "can", "like", "time", "no", "just", "him", "know",
            "take", "people", "into", "year", "your", "good", "some", "could",
            "them", "see", "other", "than", "then", "now", "look", "only", "come",
            "its", "over", "think", "also", "back", "after", "use", "two", "how",
            "our", "work", "first", "well", "way", "even", "new", "want", "because",
            "any", "these", "give", "day", "most", "us", "are", "is", "was", "were",
            "am", "been", "being", "hey", "hi", "hello", "morning", "night", "evening",
            "honey", "sweetie", "babe", "love", "photo", "picture", "selfie", "send",
            "cute", "sleep", "eat", "miss", "doing", "today", "tomorrow", "beautiful"
        }

        id_score = len(words.intersection(id_keywords))
        en_score = len(words.intersection(en_keywords))

        if id_score > en_score:
            return "id"
        elif en_score > id_score:
            return "en"
        elif id_score > 0:
            return "id"
        return "en"

    @staticmethod
    def get_language_directive(lang: Optional[str] = None, user_text: Optional[str] = None) -> str:
        """Returns a strict language and tone constraint instruction for the LLM."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "auto")).strip().lower()
        if cur_lang in ("auto", "adaptive"):
            if user_text:
                effective_lang = PersonaManager.detect_text_language(user_text)
            else:
                effective_lang = "en"
        else:
            effective_lang = cur_lang

        if effective_lang in ("id", "indonesia", "indonesian", "bahasa"):
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
        elif effective_lang in ("en", "english"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern English. "
                "NEVER mix in Indonesian, Japanese, or other languages under any circumstances. "
                "NATURAL & REALISTIC TONE: Talk normally, sweetly, and casually like a real companion texting on chat (1-3 sentences). "
                "Directly answer questions with relevant, grounded responses. "
                "DO NOT be melodramatic, theatrical, overly cheesy, or cringe. Avoid fanfiction-like monologues. "
                "PRONOUNS & ADDRESS DIRECTIVE: Use 'I' and 'you' naturally. DO NOT use pet names like 'babe', 'honey', or 'darling' UNLESS the user explicitly asks for it or uses it first. Allow the relationship dynamic to unfold naturally. "
                "NEVER speak like an influencer, YouTuber, or vlogger. This is an intimate 1-on-1 private chat. "
                "Keep response brief and sweet (1-3 casual sentences)."
            )
        elif effective_lang in ("ja", "jp", "japan", "japanese", "nihongo"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual Japanese (日本語). "
                "NEVER mix in English, Indonesian, or other languages. "
                "Respond naturally and casually like texting a real-life partner. Directly answer questions, keep responses natural (1-3 sentences), and avoid overly theatrical or exaggerated anime monologues."
            )
        elif effective_lang in ("ru", "russian"):
            return (
                "STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual Russian (Русский). "
                "NEVER mix in English or Indonesian. Respond naturally, affectionately, and casually (1-3 sentences)."
            )
        else:
            return (
                f"STRICT LANGUAGE & TONE DIRECTIVE: You MUST speak, converse, and reply EXCLUSIVELY in natural, casual modern {effective_lang}. "
                f"NEVER mix in other languages under any circumstances. Keep your tone natural, grounded, realistic, and affectionate like a real companion texting (1-3 sentences). "
                f"Answer questions directly and avoid overly dramatic or theatrical responses."
            )

    @staticmethod
    def get_language_display_name(lang: Optional[str] = None) -> str:
        """Returns friendly human-readable display name for language."""
        cur_lang = (lang or os.environ.get("BOT_LANGUAGE", "auto")).strip()
        low = cur_lang.lower()
        if low in ("auto", "adaptive"):
            return "Auto-detect (Matches Chat) 🌐"
        elif low in ("en", "english"):
            return "English 🇬🇧"
        elif low in ("id", "indonesia", "indonesian", "bahasa"):
            return "Indonesian (Bahasa Indonesia) 🇮🇩"
        elif low in ("ja", "jp", "japan", "japanese", "nihongo"):
            return "Japanese (日本語) 🇯🇵"
        elif low in ("ru", "russian"):
            return "Russian (Русский) 🇷🇺"
        else:
            return f"{cur_lang.title()} ✏️"

    def get_active_persona(self, lang: Optional[str] = None, user_text: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Returns the currently active persona with strict language enforcement injected."""
        p_key = self.get_active_persona_key(user_id)
        base = self.personas.get(p_key, DEFAULT_PERSONAS["runa"]).copy()
        raw_inst = base.get("system_instruction", "")
        # Remove any old generic language rule that might confuse local LLMs
        clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:[^.]*\.[^.]*\.[^.]*\.", "", raw_inst).strip()
        if "IMPORTANT LANGUAGE RULE:" in clean_inst:
            clean_inst = re.sub(r"IMPORTANT LANGUAGE RULE:.*?(?=(\. [A-Z]|$))", "", clean_inst).strip()
        
        lang_rule = self.get_language_directive(lang, user_text=user_text)
        base["system_instruction"] = f"{clean_inst} {lang_rule}"
        return base

    def set_active_persona(self, key: str, user_id: Optional[int] = None) -> bool:
        """Switches active persona key, resetting transient session states, undress states, and locked locations."""
        key = key.lower()
        if key in self.personas:
            self.active_key = key
            if user_id:
                self.set_user_persona(user_id, key)
            if hasattr(self, "user_locked_outfit_prompts"):
                self.user_locked_outfit_prompts.clear()
            if hasattr(self, "session_outfits"):
                self.session_outfits.clear()
            if hasattr(self, "user_locations"):
                self.user_locations.clear()
                self._save_user_locations()
            # Ensure fresh start: reset any temporary undress stages or session outfits so new persona is clothed in her default outfit
            for uid in list(self.user_outfits.keys()):
                if user_id and uid != int(user_id):
                    continue
                rec = self.user_outfits.get(uid)
                if isinstance(rec, dict):
                    if rec.get("undress_stage", 0) > 0 or rec.get("mode") == "session":
                        rec["undress_stage"] = 0
                        rec["mode"] = "auto"
                        rec["key"] = "default"
                    self.user_outfits[uid] = rec
            self._save_user_outfits()
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
            r"\b(minta|kirim|liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan|bagi|kasih|send|show|take|make|record|bikin|buat)\b",
            r"\b(kamu|dirimu|mu|lu|lo|you|your|diri|me|for|to|please|plz|pls|aku|ku|us)\b",
            r"\b(sayang|ayang|beb|babe|cinta|honey|dear|baby)\b",
            r"\b(dong|donk|ya|yaa|deh|sih|plis|please|pls|now|sekarang|cepet|coba|ayo|yuk|sekali)\b",
            r"\b(baju|kaos|atasan|celana|rok|bh|bra|cd|kutang|pakaian|busana|handuk|semua|semuanya)\b",
            r"\b(clothes|clothing|shirt|top|pants|skirt|panties|underwear|towel|everything|rest|all)\b",
            r"\b(tubuh|badan|dada|aurat|payudara|toket|nenen|body|figure|curves|chest|breasts|boobs)\b",
            r"\b(buka|lepas|copot|turunkan|tarik|jatuhkan|off|undress|strip|naked|nude|telanjang|bugil)\b"
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
        is_undressing = bool(re.search(r"\b(buka|lepas|copot|turunkan|strip|undress|telanjang|naked|nude|bh|bra|panties|celana\s+dalam)\b", comb))
        if not is_undressing:
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

        # Specific Dynamic Narrative Setting Transitions (High priority over generic cafe/home/food)
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

        # c) Minimarket / Convenience Store
        convenience_triggers = [r"\b(minimarket|indomaret|alfamart|konbini|convenience\s+store)\b"]
        if any(re.search(pat, comb) for pat in convenience_triggers):
            return True, "standing in modern Japanese-style convenience store aisle, shelves with snacks and drinks, bright clean fluorescent lighting"

        # d) Rain / Sheltering / Cozy rainy day
        rain_triggers = [r"\b(kehujanan|berteduh|hujan\s+lebat|hujan\s+deras|bawa\s+payung|sheltering\s+from\s+rain|caught\s+in\s+rain)\b"]
        if any(re.search(pat, comb) for pat in rain_triggers):
            return True, "sheltering from rain under awning, holding transparent umbrella, wet reflections on pavement, cozy romantic rainy day atmosphere, atmospheric street lighting"

        # e) Rooftop / Balcony at Sunset
        rooftop_triggers = [r"\b(rooftop|balkon|atap\s+gedung|skyline|balcony)\b"]
        if any(re.search(pat, comb) for pat in rooftop_triggers):
            return True, "standing on open rooftop terrace at sunset, city skyline background, golden hour sunset lighting, gentle breeze"

        # f) Cinema / Movie Date
        cinema_triggers = [r"\b(bioskop|nonton\s+film|cinema|movie\s+theater)\b"]
        if any(re.search(pat, comb) for pat in cinema_triggers):
            return True, "sitting in cinema lobby holding cinema ticket, movie posters in soft blur background, cozy dim ambient lighting"

        # g) Train Station / Stasiun
        station_triggers = [r"\b(stasiun|peron|kereta|train\s+station|subway\s+platform)\b"]
        if any(re.search(pat, comb) for pat in station_triggers):
            return True, "standing at modern train station platform, train tracks, platform bench, commuter ambiance"

        # h) Science Lab & Office
        if any(k in comb for k in ["lab", "laboratorium", "ekstraksi", "nimbang sampel", "praktikum lab"]):
            return True, "standing in modern university chemistry and biology science laboratory, wearing white lab coat, laboratory glassware, test tubes, clean bright scientific laboratory lighting"
        if any(k in comb for k in ["kantor", "office", "ruang kerja", "meeting kantor", "kantoran", "meja kerja"]):
            return True, "standing in modern professional office room, office desk, computer monitor, neat professional office interior"

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
        """Returns the sequential undress stage (0=clothed, 1=shirt_off, 2=bottoms_off, 3=bra_off, 4=nude). Auto-expires after 15m of inactivity."""
        if not user_id:
            return 0
        rec = self.user_outfits.get(int(user_id), {})
        stage = rec.get("undress_stage", 0)
        if stage > 0:
            # Undress states are strictly temporary intimate sessions (auto-expire after 15 minutes of inactivity)
            updated_at = rec.get("updated_at", 0)
            if updated_at > 0 and (time.time() - updated_at > 900):
                logger.info(f"User {user_id} undress stage {stage} expired due to inactivity (>15m). Resetting to 0 (clothed).")
                rec["undress_stage"] = 0
                if rec.get("key") in ("shirt_off", "bottoms_off", "bra_off", "nude"):
                    rec["key"] = "default"
                rec["updated_at"] = time.time()
                self.user_outfits[int(user_id)] = rec
                self._save_user_outfits()
                return 0
        return stage

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

        # 7. General body exposure / see body trigger: 'lihat tubuh kamu', 'show me your body', 'let me see your body'
        if re.search(r"\b(?:(?:coba\s+|mau\s+|pengen\s+|minta\s+|tolong\s+)?(?:liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan|spill|intip)\s+(?:tubuh|badan|bentuk\s+tubuh)(?:mu|nya|\s+kamu)?|(?:show|let\s+me\s+see|can\s+i\s+see|want\s+to\s+see)\s+(?:me\s+)?(?:your\s+)?(?:body|curves|figure))\b", lower):
            if current_stage == 0:
                return (1, "memperlihatkan lekuk tubuhnya dengan melepas baju luarnya, tersisa pakaian dalam dan celana santai", True)
            elif current_stage < 4:
                next_st = current_stage + 1
                return (next_st, "memperlihatkan tubuhnya lebih lanjut dengan menanggalkan lapisan pakaian berikutnya", True)

        # 8. Chest / breasts exposure: 'lihat dada kamu', 'show me your boobs', 'show your chest'
        if re.search(r"\b(?:(?:coba\s+|mau\s+|pengen\s+|minta\s+|tolong\s+)?(?:liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan|spill|intip)\s+(?:dada|payudara|nenen|toket)(?:mu|nya|\s+kamu)?|(?:show|let\s+me\s+see|can\s+i\s+see)\s+(?:me\s+)?(?:your\s+)?(?:chest|breasts|boobs|tits|cleavage))\b", lower):
            if current_stage < 3:
                return (3, "membuka kaitan BH-nya dan memperlihatkan dadanya secara topless", True)
            elif current_stage == 3:
                return (4, "menanggalkan celana dalamnya juga, kini sepenuhnya telanjang tanpa busana", True)

        # 9. Direct naked trigger: 'lihat kamu telanjang', 'show me naked', 'coba telanjang'
        if re.search(r"\b(?:(?:coba\s+|mau\s+|pengen\s+|minta\s+|tolong\s+)?(?:liat(?:in)?|lihat(?:in)?|tunjuk+in|tunjuk+an|perlihatkan)\s+kamu\s+(?:telanjang|bugil|tanpa\s+baju|tanpa\s+busana)|(?:show|let\s+me\s+see|can\s+i\s+see)\s+(?:me\s+)?(?:you\s+)?(?:naked|nude|unclothed)|telanjang\s*(?:dong|cepet|sekarang)?)\b", lower):
            return (4, "menanggalkan seluruh pakaiannya hingga telanjang bulat tanpa busana", True)

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
        If a session outfit or undress stage is active, automatically clears it when routine changes to normal life!
        """
        uid = int(user_id) if user_id else 0
        details = self.get_user_outfit_details(uid)
        cur_undress = self.get_undress_stage(uid)

        t = (user_text or "").lower()

        # NEVER shift or reset undress stage if current turn has NSFW intent, undress intent, or intimate bedroom context
        from routing_engine import detect_nsfw_intent
        is_nsfw = detect_nsfw_intent(user_text)
        _, _, is_undress_req = self.detect_undress_intent(user_text, current_stage=cur_undress)
        intimate_words = [
            "buka", "lepas", "sentuh", "raba", "cium", "elus", "remas", "peluk",
            "jilat", "isap", "desah", "posisi", "rebahan", "kasur", "kamar",
            "nenen", "toket", "memek", "pepek", "vagina", "paha", "pantat", "bokong",
            "telanjang", "basah", "enak", "geli", "ah", "uh", "sensual", "mesra",
            "bh", "bra", "kutang", "cd", "celana dalam", "panties", "lingerie", "seksi", "sexy"
        ]
        has_intimate = any(w in t for w in intimate_words)
        if is_nsfw or is_undress_req or (cur_undress > 0 and has_intimate):
            return False

        # Routine shifts and normal daily topics that invalidate previous intimate/costume state:
        SHIFT_TRIGGERS = [
            r"\b(tidur|bobo|ngantuk|good\s*night|selamat\s*malam|mimpi\s*indah)\b",
            r"\b(mandi|keramas|shower|bath|handuk)\b",
            r"\b(lab|laboratorium|ekstraksi|sampel|praktikum|kampus|kuliah|kelas|dosen|makul|matkul|skripsi|perpustakaan|perpus)\b",
            r"\b(kantor|kerja|kantoran|meeting|proyek|tugas|lembur)\b",
            r"\b(pulang|jam\s+berapa|kapan\s+pulang|nyampe\s+jam|balik\s+jam|udah\s+di\s+mana)\b",
            r"\b(cafe|kafe|kopi|coffee|starbucks|nongkrong)\b",
            r"\b(mall|belanja|shopping|bioskop|jalan-jalan|taman)\b",
            r"\b(makan|lapar|kuliner|masak|sarapan|lunch|dinner)\b",
            r"\b(gym|olahraga|fitness|workout|jogging)\b",
            r"\b(pulang\s+ke\s+rumah|udah\s+di\s+rumah|santai\s+di\s+rumah)\b"
        ]

        shifted = False
        for pat in SHIFT_TRIGGERS:
            if re.search(pat, t):
                shifted = True
                break

        if shifted:
            did_shift = False
            # If waifu was undressed, automatically restore her clothes on daily life context shift!
            if cur_undress > 0:
                logger.info(f"Daily context shift detected for user {uid} ('{user_text[:35]}'). Resetting undress stage {cur_undress} -> 0 (clothed).")
                self.reset_undress_stage(uid)
                did_shift = True
            if details.get("is_session"):
                logger.info(f"Natural context shift detected for user {uid} ('{user_text[:35]}'). Reverting session outfit '{details['key']}' to auto.")
                self.clear_session_outfit(uid)
                did_shift = True
            return did_shift

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
                    # Strip any accidental character trait hallucination from the LLM so it never corrupts persona features
                    clean_dyn = re.sub(r'(?i)\b(?:1girl|solo|girl|woman|female|eyes?|hair|face|cheeks?|breasts?|chest|thighs?|legs?|feet|body|child|kid|loli|petite)\b,?\s*', '', clean_dyn).strip(', ')
                    if len(clean_dyn) >= 5:
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
            (["lab", "laboratorium", "laboratory", "ekstraksi", "sampel", "nimbang sampel", "praktikum lab", "jas lab", "lab coat"],
             "standing in modern university chemistry and biology science laboratory, wearing white lab coat, laboratory glassware, test tubes, clean bright scientific laboratory lighting"),
            (["kantor", "office", "ruang kerja", "meeting kantor", "kantoran", "meja kerja", "kantor saya"],
             "standing in modern professional office room, office desk, computer monitor, neat professional office interior"),
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
            "no clothes", "tanpa sehelai benang", "telanjang polos", "full nude",
            "nenen", "toket", "tetek", "memek", "vagina",
            "foto nenen", "pap nenen", "foto toket", "pap toket", "foto payudara", "pap payudara",
            "buka semua", "buka semuanya", "lepas semua", "lepas semuanya",
            "buka handuk", "buka handuknya", "lepas handuk", "lepas handuknya",
            "copot handuk", "copot handuknya", "tarik handuk", "tarik handuknya",
            "jatuhkan handuk", "jatuhkan handuknya", "drop towel", "drop your towel",
            "take off towel", "take off your towel", "remove towel", "remove your towel",
            "foto telanjang", "pap telanjang", "foto bugil", "pap bugil",
            "foto memek", "pap memek", "foto vagina", "pap vagina",
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

    def extract_underwear_color_override(self, text: str) -> Optional[str]:
        """Detects explicit user-requested color or styling for underwear/lingerie."""
        if not text:
            return None
        lower = text.lower()
        colors = {
            "merah muda": "pastel pink",
            "biru muda": "light blue",
            "abu-abu": "grey",
            "tembus pandang": "sheer transparent",
            "renda hitam": "black lace",
            "renda putih": "white lace",
            "renda merah": "red lace",
            "renda pink": "pink lace",
            "renda ungu": "purple lace",
            "renda biru": "blue lace",
            "merah": "red",
            "crimson": "crimson-red",
            "marun": "maroon",
            "hitam": "black",
            "putih": "white",
            "pink": "pink",
            "biru": "blue",
            "navy": "navy-blue",
            "ungu": "purple",
            "violet": "violet",
            "lavender": "lavender",
            "kuning": "yellow",
            "hijau": "green",
            "emerald": "emerald-green",
            "cokelat": "brown",
            "coklat": "brown",
            "abu": "grey",
            "emas": "gold",
            "silver": "silver",
            "perak": "silver",
            "krem": "cream",
            "beige": "beige",
            "transparan": "sheer transparent",
            "red": "red",
            "black": "black",
            "white": "white",
            "purple": "purple",
            "blue": "blue",
            "green": "green",
            "yellow": "yellow",
            "sheer": "sheer"
        }
        terms = r"(?:bra|bh|lingerie|celana\s+dalam|panties|pakaian\s+dalam|baju\s+tidur\s+seksi|underwear|kutang|sempak)"
        color_keys = sorted(colors.keys(), key=len, reverse=True)
        color_pattern = "|".join(re.escape(k) for k in color_keys)
        m1 = re.search(rf"\b{terms}\s+(?:yang\s+)?(?:warna\s+)?({color_pattern})\b", lower)
        if m1:
            return colors[m1.group(1)]
        m2 = re.search(rf"\b(?:warna\s+)?({color_pattern})\s+{terms}\b", lower)
        if m2:
            return colors[m2.group(1)]
        return None

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
            user_color = self.extract_underwear_color_override(user_text)
            if user_color and any(k in prompt.lower() for k in ["bra", "panties", "lingerie"]):
                extra_traits = []
                if "pointy elf ears" in prompt.lower():
                    extra_traits.append("pointy elf ears")
                if "cat ears" in prompt.lower():
                    extra_traits.append("cute fluffy cat ears, flexible cat tail")
                traits_clause = f", {', '.join(extra_traits)}" if extra_traits else ""

                if "shirt completely removed" in prompt.lower():
                    prompt = (
                        f"(wearing only a delicate {user_color} lace bra and relaxed lounge shorts:1.4){traits_clause}, "
                        f"shirt completely removed, bare shoulders, bare midriff, exposed stomach, cleavage, "
                        f"sensual blush, intimate bedroom lighting"
                    )
                elif "topless" in prompt.lower() or "(bare natural breasts" in prompt.lower():
                    prompt = (
                        f"(topless:1.45), (bare natural breasts:1.4), detailed exposed breasts, nipples, exposed chest, "
                        f"bare collarbone{traits_clause}, wearing only tiny sheer {user_color} lace panties:1.35, "
                        f"sensual blush, intimate bedroom atmosphere"
                    )
                elif "lingerie" in name.lower() or "delicate sheer" in prompt.lower():
                    prompt = (
                        f"(wearing delicate sheer {user_color} lace lingerie set:1.4){traits_clause}, "
                        f"detailed {user_color} lace bra, matching sheer {user_color} lace panties, "
                        f"bare midriff, exposed stomach, bare thighs, seductive cleavage, alluring intimate styling"
                    )
                else:
                    prompt = (
                        f"(wearing only matching sheer {user_color} lace bra and panties:1.45){traits_clause}, "
                        f"pants removed, bare thighs, slender legs, exposed stomach, navel, alluring cleavage, "
                        f"seductive {user_color} lingerie set, intimate bedroom setting"
                    )

            if user_id:
                uid = int(user_id)
                if not hasattr(self, "user_locked_outfit_prompts"):
                    self.user_locked_outfit_prompts = {}
                cached = self.user_locked_outfit_prompts.get(uid)
                if (
                    not user_color
                    and cached
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
            if scene_hint and any(k in scene_hint.lower() for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store", "lab", "laboratorium", "laboratory", "kantor", "office"]):
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
            # Check public / academic / workplace guard: NEVER allow undressed states in public or work spaces
            is_work_or_public = False
            if scene_hint and any(pub in scene_hint.lower() for pub in ["lab", "laboratorium", "science lab", "office", "kantor", "mall", "campus", "classroom", "library", "cafe", "park", "street", "store"]):
                is_work_or_public = True
            if is_work_or_public:
                logger.info(f"Public/Academic location guard: Resetting undress stage {cur_stage} for {scene_hint}")
                self.reset_undress_stage(user_id)
                cur_stage = 0
            else:
                stage_map = {
                    1: ("shirt_off", False),
                    2: ("bottoms_off", False),
                    3: ("bra_off", True),
                    4: ("nude", True)
                }
                if cur_stage in stage_map:
                    k, is_n = stage_map[cur_stage]
                    preset = self.get_preset_outfit(k)
                    neg_prompt = preset.get("negative", "")
                    if k == "bra_off":
                        neg_prompt = (
                            "(dress:1.5), (slip dress:1.5), (nightwear:1.5), (gown:1.5), (clothes:1.5), (clothing:1.5), "
                            "(skirt:1.5), (shirt:1.5), (top:1.5), (blouse:1.5), (bra:1.5), (brassiere:1.5), (jacket:1.5), "
                            "(hoodie:1.5), (sweater:1.5), (pajamas:1.5), (pants:1.5), (jeans:1.5), (trousers:1.5), "
                            "fully naked, uncovered lower body, " + neg_prompt
                        )
                    elif k in ("bottoms_off", "lingerie"):
                        neg_prompt = (
                            "(dress:1.5), (slip dress:1.5), (nightwear:1.5), (gown:1.5), (clothes:1.5), (clothing:1.5), "
                            "(skirt:1.5), (shirt:1.5), (top:1.5), (blouse:1.5), (jacket:1.5), (hoodie:1.5), (sweater:1.5), "
                            "(pants:1.5), (jeans:1.5), (trousers:1.5), " + neg_prompt
                        )
                    return _finalize(preset["prompt"], neg_prompt, is_n, preset["name"])

        # 5. Clothed Intimate / Roleplay Coherence:
        # When at Stage 0 (clothed) or early in an intimate scene without explicit undress commands,
        # waifu remains clothed in her contextual outfit (e.g. cozy loungewear/pajamas/casual).
        # Full nudity is strictly restricted to explicit user commands or Stage 4 of sequential undressing!

        # 6. Context-aware Student Routine & Conversation History
        # When an active session outfit is set, check activity shifts/public guards against current user_text only
        # so stale chat history (e.g., earlier "piyama" / "tidur") does NOT cancel user's newly selected /outfit!
        current_ctx = current_loc_ctx
        clean_with_scene = ([scene_hint] if scene_hint else []) + clean_turns
        ctx = detect_contextual_activity_and_outfit(user_text, clean_with_scene, persona_key=self.active_key)

        # Determine if current venue is public (mall, campus, cafe, etc.)
        is_public = bool(current_ctx.get("is_public", False)) if outfit_mode != "auto" else bool(ctx.get("is_public", False))
        if scene_hint:
            lower_s = scene_hint.lower()
            if any(k in lower_s for k in ["mall", "campus", "classroom", "library", "cafe", "park", "street", "store", "lab", "laboratorium", "laboratory", "kantor", "office"]):
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
            elif any(c in activity_now for c in ["kampus", "kuliah", "perpus", "lab", "kantor"]) and outfit_key in ("maid", "kimono", "bikini", "lingerie", "nude"):
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

        # COHERENCE SAFETY GUARD: NEVER allow lingerie or nude in public spaces (e.g. mall, campus, lab, kantor)!
        if is_public and outfit_key in ("nude", "lingerie", "bra_off", "bottoms_off", "shirt_off"):
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

        # Default fallback: When user requests a photo without specifying clothes or activity,
        # prioritize the persona's iconic signature default outfit for visual consistency!
        persona_def = self.get_active_persona()
        sig_outfit = persona_def.get("default_outfit", "")
        if sig_outfit and outfit_mode == "auto":
            return _finalize(f"(wearing {sig_outfit}:1.35)", ctx.get("outfit_negative", ""), False, "🌸 Pakaian Khas Karakter (Default)")

        return _finalize(ctx["outfit_prompt"], ctx["outfit_negative"], False, ctx["outfit_name"])

    def get_realtime_lighting_and_atmosphere(
        self,
        user_text: str = "",
        scene_desc: str = "",
        user_id: Optional[int] = None,
        is_nude: bool = False
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

        is_explicit_outdoor = bool(re.search(
            r"\b(pantai|beach|kolam|pool|taman|park|garden|jalan|street|luar|outdoor|balkon|balcony|hutan|forest)\b",
            f"{scene_lower} {lower}"
        ))
        is_indoor = bool(re.search(
            r"\b(bedroom|bed|room|kosan|kost|kamar|apartemen|apartment|sofa|indoor|dapur|kitchen|bathroom|mandi|perpustakaan|library|cafe|kafe|kelas|classroom|mall|gym|lobby)\b",
            f"{scene_lower} {lower}"
        )) or (is_nude and not is_explicit_outdoor) or bool(re.search(r"\b(telanjang|nude|topless|lingerie|underwear|pajamas|piyama|kasur|bed|ranjang|all fours|nungging)\b", f"{scene_lower} {lower}"))

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
        persona = self.get_active_persona(user_id=user_id)
        base_visual = persona.get("visual_traits", DEFAULT_PERSONAS["runa"]["visual_traits"])

        hist = history or (self.get_chat_history(user_id) if user_id else [])
        scene = scene_override or self.extract_contextual_scene(user_text, user_id=user_id, history=hist, is_nsfw=is_nsfw)
        cur_u_stage = self.get_undress_stage(user_id) if user_id else 0
        if cur_u_stage > 0 and scene:
            scene = re.sub(
                r'(?i)\b(?:tugging\s+skirt\s+playfully|showing\s+cute\s+outfit|admiring\s+her\s+clothes|skirt|dress|slip\s+dress|jacket|hoodie|sweater|shirt)\b',
                'relaxing intimately',
                scene
            ).strip(', ')
        outfit_prompt, extra_neg, is_nude, outfit_name = self.detect_clothing_intent(
            user_text,
            user_id=user_id,
            history=hist,
            scene_hint=scene,
            is_nsfw=is_nsfw,
            allow_undress_advance=allow_undress_advance,
        )

        # Inject persona-specific identity negative constraints (locks hair color, eye color, and body proportions)
        p_neg = persona.get("negative_prompt", "")
        if p_neg:
            extra_neg = f"{extra_neg}, {p_neg}" if extra_neg else p_neg

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
            # Strictly enforce adult woman solo shot without wasting CLIP token budget on redundant pseudo-tags
            cleaned_base = re.sub(r'^(?:masterpiece,\s*)*(?:best quality,\s*)*(?:solo,\s*)*(?:1girl,\s*)*', '', base_visual, flags=re.IGNORECASE).strip()
            cleaned_base = re.sub(r',?\s*masterpiece,\s*best quality,\s*highly detailed.*$', '', cleaned_base, flags=re.IGNORECASE).strip()
            base_visual = f"masterpiece, best quality, 1girl, solo, (mature female:1.2), (adult woman:1.2), {cleaned_base}"

            solo_guard_neg = (
                "(2girls:1.5), (3girls:1.5), (multiple girls:1.5), (2people:1.5), (multiple persons:1.5), (group:1.5), "
                "(extra characters:1.5), (extra heads:1.5), (extra head:1.5), (extra faces:1.5), (extra face:1.5), "
                "(two heads:1.5), (two faces:1.5), (multiple heads:1.5), (multiple faces:1.5), (fused bodies:1.4), "
                "(conjoined:1.4), (cloned face:1.4), (duplicate character:1.4), (duplicate:1.4), (split screen:1.3)"
            )
            extra_neg = f"{extra_neg}, {solo_guard_neg}" if extra_neg else solo_guard_neg

        # Check if persona is a nekomimi or user explicitly requested a cat/pet/animal in prompt
        p_active_key = self.get_active_persona_key(user_id)
        is_neko_persona = p_active_key == "mimi" or any(k in persona.get("visual_traits", "").lower() for k in ["cat ears", "nekomimi"])
        wants_cat = bool(re.search(r"\b(kucing|cat|kitten|anabul|pet|hewan)\b", (user_text or "").lower()))
        if not is_neko_persona and not wants_cat:
            cat_neg = "cat, kitten, feline, animal, pet, animal ears, cat ears"
            extra_neg = f"{extra_neg}, {cat_neg}" if extra_neg else cat_neg
        elif is_neko_persona and not wants_cat:
            cat_neg = "real cat, pet cat, multiple animals, stray animals"
            extra_neg = f"{extra_neg}, {cat_neg}" if extra_neg else cat_neg

        # Check if user explicitly requested a phone/device in prompt
        wants_device = bool(re.search(r"\b(hp|handphone|phone|smartphone|mirror\s+selfie|kaca)\b", (user_text or "").lower()))
        if not wants_device:
            device_neg = "phone, smartphone, cellphone, camera, holding phone, holding camera, mirror selfie, mirror, hands holding device, selfie stick"
            extra_neg = f"{extra_neg}, {device_neg}" if extra_neg else device_neg

        # Anatomy, limbs, arms & hands defect guardrails (strictly prevents missing arms, stumps, amputations, spider legs, and deformed hands)
        anatomy_guard_neg = (
            "(missing arm:1.5), (missing arms:1.5), (missing hand:1.5), (missing hands:1.5), "
            "(missing limbs:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), "
            "(disappearing arm:1.4), (partially submerged arm:1.3), (floating limbs:1.4), (floating arms:1.4), "
            "(extra arms:1.5), (bad arms:1.4), (mutated arms:1.4), (deformed arms:1.4), (fused arms:1.4), "
            "(bad hands:1.4), (mutated hands:1.4), (missing fingers:1.4), (extra fingers:1.4), (fused fingers:1.4), "
            "(malformed hands:1.4), (poorly drawn hands:1.4), (poorly drawn arms:1.4), "
            "(extra legs:1.5), (three legs:1.5), (multiple legs:1.5), (extra limbs:1.5), (mutated legs:1.4), "
            "(deformed legs:1.4), (malformed limbs:1.4), (fused legs:1.4), (bad legs:1.4), (folded legs error:1.3), "
            "(extra feet:1.4), (three feet:1.4), (bad feet:1.4), (poorly drawn legs:1.4), (poorly drawn feet:1.4), "
            "(duplicate body:1.4), (mutated:1.3), (deformed:1.3), (unnatural body proportions:1.3), (distorted body:1.3), "
            "(watermark:1.4), (text:1.4), (logo:1.4), (signature:1.4), (artist name:1.4), (copyright:1.4), (caption:1.4), (subtitles:1.4)"
        )
        extra_neg = f"{extra_neg}, {anatomy_guard_neg}" if extra_neg else anatomy_guard_neg

        # Age maturity, facial proportions, and anatomy guardrails (strictly prevents childish/immature body or elderly/distorted features)
        maturity_guard_neg = (
            "(child:1.5), (loli:1.5), (kid:1.5), (underage:1.5), (baby face:1.4), "
            "(immature body:1.4), (chibi:1.4), (petite:1.3), (short stature:1.3), (flat chest:1.2), "
            "(underdeveloped body:1.4), (schoolchild:1.4), (elementary school:1.4), "
            "(old woman:1.4), (elderly:1.4), (deformed face:1.3), (bad face:1.2), "
            "(bad anatomy:1.3), (bad breasts:1.3), (unnatural body proportions:1.3), (mutated body:1.3)"
        )
        extra_neg = f"{extra_neg}, {maturity_guard_neg}" if extra_neg else maturity_guard_neg

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

        # Ensure every photo has a concrete physical location background (prevents Anything XL from rendering plain gradients)
        location_kws = [
            "bed", "room", "kamar", "bath", "beach", "pool", "outdoor", "onsen", "pantai", "taman",
            "cafe", "coffee", "campus", "classroom", "lecture", "library", "kitchen", "park", "street",
            "station", "mall", "cinema", "office", "lab", "rooftop", "balcony", "apartment", "restaurant",
            "shop", "store", "hallway", "garden", "hotel", "airport", "sofa", "desk", "table", "window", "interior"
        ]
        has_concrete_location = bool(scene and any(k in scene.lower() for k in location_kws))

        if (is_nude or is_nsfw) and not has_concrete_location:
            scene = "luxurious cozy bedroom setting, soft warm ambient lighting, comfortable bed with silk sheets, elegant private aesthetic"
        elif not has_concrete_location:
            active_loc = self.get_user_location(user_id) if user_id else None
            if active_loc and active_loc.get("prompt"):
                loc_scene = active_loc["prompt"]
            else:
                import datetime
                routine = get_hourly_routine(datetime.datetime.now().hour, persona_key=p_active_key)
                loc_scene = routine.get("scene", "cozy modern apartment room with warm lamp lighting, bookshelf, window")
            scene = f"{loc_scene}, {scene}".strip(", ") if scene else loc_scene

        # Synchronize photo lighting and atmosphere with real-world local time & live weather
        lighting_pos, lighting_neg = self.get_realtime_lighting_and_atmosphere(user_text, scene, user_id=user_id, is_nude=is_nude)
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

        anti_blank_bg_neg = "(simple background:1.45), (white background:1.45), (plain background:1.45), (gradient background:1.45), (blank background:1.45), (grey background:1.4), (abstract background:1.35)"
        extra_neg = f"{extra_neg}, {anti_blank_bg_neg}" if extra_neg else anti_blank_bg_neg

        emphasized_scene = f"(detailed background:1.25), (scenery:1.2), ({scene}:1.2)" if scene else "(detailed background:1.25), cozy modern room interior"
        prompt_elements = [base_visual, outfit_prompt, emphasized_scene, lighting_pos, chosen_angle]
        if anatomy_cue:
            prompt_elements.append(anatomy_cue)
            logger.info(f"Intimate anatomy cues injected: {anatomy_cue}")
        if not (anatomy_cue and any(k in anatomy_cue for k in ["pussy", "crotch"])):
            prompt_elements.append("detailed eyes")
        prompt_elements.extend(["high resolution anime art"])

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

    def get_chat_history(self, user_id: int, persona_key: Optional[str] = None) -> List[Dict[str, str]]:
        """Returns chat history partitioned for user and persona, re-syncing from disk if modified."""
        if os.path.exists(self.history_file):
            try:
                mtime = os.path.getmtime(self.history_file)
                if self._history_mtime < mtime:
                    self._load_chat_history()
            except Exception:
                pass
        k = self._conv_key(user_id, persona_key)
        return self.user_conversations.setdefault(k, [])

    def add_message(self, user_id: int, role: str, content: str, persona_key: Optional[str] = None):
        """Adds a message to persona-specific history, keeping maximum 20 turns, and persists atomically."""
        k = self._conv_key(user_id, persona_key)
        history = self.get_chat_history(user_id, persona_key=persona_key)
        history.append({"role": role, "content": content})
        if len(history) > 20:
            history = history[-20:]
        self.user_conversations[k] = history
        self._save_chat_history()

    def clear_history(self, user_id: int, persona_key: Optional[str] = None):
        """Clears chat history for this specific persona and persists to disk."""
        k = self._conv_key(user_id, persona_key)
        if hasattr(self, "user_locked_outfit_prompts"):
            self.user_locked_outfit_prompts.pop(user_id, None)
        if k in self.user_conversations:
            self.user_conversations[k] = []
        if not persona_key and user_id in self.user_conversations:
            self.user_conversations[user_id] = []
        self._save_chat_history()

    def get_affinity(self, user_id: int, persona_key: Optional[str] = None) -> int:
        """Returns affection points (0-100) partitioned per persona."""
        k = self._conv_key(user_id, persona_key)
        return self.user_affinity.get(k, self.user_affinity.get(user_id, 15))

    def increase_affinity(self, user_id: int, delta: int = 1, persona_key: Optional[str] = None) -> int:
        """Increases affection score smoothly for active persona."""
        k = self._conv_key(user_id, persona_key)
        cur = self.get_affinity(user_id, persona_key=persona_key) + delta
        new_val = min(max(cur, 0), 100)
        self.user_affinity[k] = new_val
        return new_val

    def get_relationship_status(self, user_id: int, persona_key: Optional[str] = None) -> Tuple[int, str]:
        """Returns (score, relationship_title) for active persona."""
        score = self.get_affinity(user_id, persona_key=persona_key)
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


ARCHETYPE_PRESETS: Dict[str, Tuple[str, str]] = {
    "tsundere": ("🌸 Tsundere Manja", "Gengsi dan pura-pura jual mahal tapi sangat perhatian, setia, dan manja saat berdua."),
    "kuudere": ("❄️ Kuudere Tenang", "Tenang, cerdas, dingin di luar namun sangat lembut, penyayang, dan setia di dalam."),
    "yandere": ("🖤 Yandere Posesif", "Manis, protektif, posesif, sangat mendambakan perhatian pasangan, dan mencintai pasangan sepenuh jiwa."),
    "oneesan": ("🍷 Onee-san Anggun", "Wanita dewasa yang anggun, mengayomi, membimbing, menggoda secara elegan, dan sangat pengertian."),
    "genki": ("✨ Ceria & Enerjik", "Gadis berenergi positif, periang, humoris, ceria, dan selalu seru diajak hangout ke mana saja."),
    "dandere": ("📖 Dandere Pemalu", "Gadis pemalu, lembut, berbicara pelan dan sopan, namun sangat manis, tulus, dan setia."),
    "gyaru": ("💄 Gyaru Trendi", "Gadis modis kekinian yang ekspresif, asyik diajak bercanda, blak-blakan, gaul, dan penuh kasih sayang."),
    "deredere": ("💖 Deredere Romantis", "Penuh cinta tanpa syarat, selalu ceria, manis, manja, dan terang-terangan menunjukkan rasa sayangnya."),
    "elf": ("🧝 Elf Anggun & Mistis", "Elf berumur panjang yang anggun, memiliki telinga runcing, bijak, penasaran dengan dunia modern, dan sangat setia."),
    "nekomimi": ("🐾 Gadis Kucing (Nekomimi)", "Gadis kucing yang ceria, lincah, manja, sedikit jahil, suka dielus kepalanya, dan sangat setia.")
}

BODY_PRESETS: Dict[str, Tuple[str, str]] = {
    "petite_curvy": ("🌸 Petite Curvy (C-cup)", "petite curvy adult body, natural C-cup medium breasts, slender waist, delicate collarbones, soft feminine curves"),
    "hourglass_curvy": ("🍷 Hourglass Montok (D-cup)", "tall curvaceous hourglass figure, D-cup large breasts, shapely bust, narrow waist, feminine wide hips"),
    "slender_graceful": ("❄️ Slender Graceful (C-cup)", "slender graceful adult frame, natural modest C-cup medium breasts, elegant slender waist, delicate feminine curves"),
    "athletic_toned": ("🏃 Athletic Toned (C-cup)", "fit toned feminine body, perky C-cup medium breasts, slender athletic waist, healthy feminine curves"),
    "tall_model": ("✨ Tall Model (C-cup)", "tall slender model proportions, long legs, natural C-cup medium breasts, narrow waist, elegant posture"),
    "elven_slender": ("🧝 Elven Slender (C-cup)", "slender graceful elven adult frame, pointy elf ears, natural modest C-cup medium breasts, elegant slender waist, delicate feminine curves"),
    "nekomimi_petite": ("🐾 Nekomimi Petite (C-cup)", "petite curvy anime adult frame, cute fluffy cat ears, flexible cat tail, perky C-cup medium breasts, slender waist, soft feminine curves")
}

LORE_PRESETS: Dict[str, Tuple[str, str]] = {
    "roommate": ("🏠 Teman Satu Kos / Apartemen", "Kalian adalah tetangga kamar kos/apartemen yang awalnya sering pinjam barang atau masak bareng, lalu menjadi sangat akrab dan saling peduli."),
    "childhood": ("🎒 Teman Masa Kecil (Childhood Friend)", "Kalian sudah berteman sejak kecil, sempat berpisah karena kuliah, dan kini dipertemukan kembali dengan perasaan yang berkembang lebih dalam."),
    "campus_junior": ("📚 Adik Tingkat Kampus", "Mahasiswi adik tingkat satu jurusan yang sering minta bantuan tugas atau diskusi skripsi dan diam-diam sangat mengagumi kebaikanmu."),
    "coworker": ("💼 Rekan Kerja / Partner Proyek", "Rekan kerja atau partner satu tim yang selalu saling mendukung, lembur bersama, dan menemukan kenyamanan khusus saat berdua."),
    "romantic_couple": ("💖 Pacar Romantis Baru Jadian", "Kalian baru saja resmi jadian setelah sekian lama saling memendam rasa, masih sering salah tingkah tapi penuh kehangatan romantis."),
    "creative_artist": ("🎨 Seniman / Musisi Bohemian", "Seorang seniman atau musisi berjiwa bebas yang melihatmu sebagai sumber inspirasi utamanya dan merasa damai saat bersamamu."),
    "fantasy_elf": ("🧝 Putri Elf dari Hutan Kuno", "Seorang elf anggun berumur panjang yang hidup berdampingan di dunia modern dan mengagumi caramu memperlakukannya."),
    "fantasy_nekomimi": ("🐾 Gadis Kucing Peliharaan / Teman Rumah", "Gadis kucing manis yang tinggal bersamamu, selalu menyambutmu di pintu saat pulang, dan suka bersantai di pangkuanmu.")
}

CUSTOM_PERSONA_OUTFIT_PRESETS: Dict[str, Tuple[str, str]] = {
    "casual": ("🌸 Pakaian Kasual Santai", "cute oversized pastel sweater, comfortable casual skirt, neat footwear"),
    "streetwear": ("🍡 Streetwear Outdoor", "fashionable streetwear jacket, graphic t-shirt, fitted pants, trendy sneakers"),
    "pajamas": ("🌙 Piyama Sutra Tidur", "cozy soft silk pajamas loungewear, comfortable nightwear"),
    "dress": ("🎀 Gaun Anggun Cantik", "elegant feminine sundress with delicate lace details, stylish and pretty"),
    "school": ("🏫 Seragam Kampus / Blazer", "neat collegiate blazer over crisp blouse with pleated skirt")
}
PERSONA_BUILDER_OUTFIT_PRESETS = CUSTOM_PERSONA_OUTFIT_PRESETS


def build_custom_persona(
    name: str,
    archetype: str,
    visual_traits: str,
    outfit: str = "",
    body_type: str = "petite_curvy",
    lore: str = "",
    age: int = 21,
    voice_choice: str = "id-ID-GadisNeural",
    llm_client: Any = None
) -> dict:
    """Constructs a complete, rich persona configuration dictionary with AI prompts and instructions."""
    clean_name = name.strip()
    clean_archetype = archetype.strip() or "Loving Companion"
    if clean_archetype in ARCHETYPE_PRESETS:
        clean_archetype = ARCHETYPE_PRESETS[clean_archetype][0]

    # Resolve body type
    body_prompt = BODY_PRESETS.get(body_type, ("", body_type))[1] if body_type else BODY_PRESETS["petite_curvy"][1]
    body_label = BODY_PRESETS.get(body_type, (body_type, ""))[0] if body_type else "Petite Curvy"

    # Resolve lore
    lore_desc = LORE_PRESETS.get(lore, ("", lore))[1] if lore else ""
    lore_label = LORE_PRESETS.get(lore, (lore, ""))[0] if lore else ""

    # Resolve outfit
    clean_outfit = CUSTOM_PERSONA_OUTFIT_PRESETS.get(outfit, ("", outfit))[1] if outfit else "cute fashionable casual clothing"

    en_visual = None
    ai_sys_inst = None
    initial_greeting = None

    if llm_client:
        try:
            # 1. Translate and enrich visual prompt into precise Danbooru tags
            p_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are an anime character designer and prompt engineer. "
                        "Translate and synthesize the character's facial features, hair, eyes, and accessories into concise English Danbooru tags. "
                        "Output ONLY comma-separated tags without markdown, explanations, or conversational filler."
                    )
                },
                {
                    "role": "user",
                    "content": f"Character visual details: {visual_traits}"
                }
            ]
            res, _ = llm_client.chat(p_prompt, max_tokens=70)
            if res and len(res.strip()) > 5:
                en_visual = res.strip().replace("\n", ", ").strip('".\'-')
        except Exception as e_vis:
            logger.warning(f"AI visual enrichment skipped: {e_vis}")

        try:
            # 2. Enrich system instruction with persona personality and lore
            lore_context = f"\nLatar belakang & hubungan: {lore_desc}" if lore_desc else ""
            sys_gen_prompt = [
                {
                    "role": "system",
                    "content": (
                        "Tuliskan deskripsi system instruction karakter anime/visual novel romance dalam Bahasa Indonesia (1-2 paragraf padat). "
                        "Jelaskan kepribadiannya, latar belakang kegiatannya, dan bagaimana ia bersikap hangat terhadap pasangannya. "
                        "Wajib instruksikan penggunaan 'aku' dan 'kamu', dilarang nyolot/ketus, dan dilarang memanggil sayang kecuali diminta lawan bicara."
                    )
                },
                {
                    "role": "user",
                    "content": f"Nama: {clean_name}, Usia: {age} tahun, Sifat: {clean_archetype}{lore_context}"
                }
            ]
            res_sys, _ = llm_client.chat(sys_gen_prompt, max_tokens=220)
            if res_sys and len(res_sys.strip()) > 20:
                ai_sys_inst = res_sys.strip().strip('"\'-')
        except Exception as e_sys:
            logger.warning(f"AI system instruction enrichment skipped: {e_sys}")

        try:
            # 3. Generate initial sweet greeting message
            greet_prompt = [
                {
                    "role": "system",
                    "content": (
                        "Tuliskan 1 kalimat sapaan perdana yang manis, santai, dan penuh pesona sesuai karakter saat pertama kali menyapa pasangannya di chat Telegram. "
                        "Hanya tulis 1 kalimat dialog langsung tanpa tanda kutip atau narasi tambahan."
                    )
                },
                {
                    "role": "user",
                    "content": f"Karakter: {clean_name} ({clean_archetype}), Hubungan: {lore_label or 'Pacar baru'}"
                }
            ]
            res_greet, _ = llm_client.chat(greet_prompt, max_tokens=50)
            if res_greet and len(res_greet.strip()) > 5:
                initial_greeting = res_greet.strip().strip('"\'-')
        except Exception as e_gr:
            logger.warning(f"AI greeting generation skipped: {e_gr}")

    if not en_visual:
        en_visual = visual_traits

    full_visual = (
        f"1girl, {age}yo young adult anime woman, mature pretty college woman face, defined feminine jawline, "
        f"{en_visual}, {body_prompt}, "
        f"delicate facial features, fair skin, natural soft blush, expressive detailed eyes, "
        f"masterpiece, best quality, highly detailed anime visual novel artwork"
    )

    if not ai_sys_inst:
        lore_clause = f" Hubungan kalian: {lore_desc}" if lore_desc else ""
        ai_sys_inst = (
            f"Nama kamu {clean_name}, mahasiswi berumur {age} tahun dengan kepribadian {clean_archetype}.{lore_clause} "
            f"Kamu adalah sosok pacar/teman mengobrol yang hangat, manis, ramah, dan penuh kasih sayang. "
            f"Gaya bicaramu santai, akrab, manis, ekspresif, dan hidup seperti visual novel anime romance. "
            f"Gunakan kata ganti 'aku' dan 'kamu'. DILARANG KERAS menggunakan kata 'lo', 'lu', 'elu', 'gue', 'gw', 'gua'. "
            f"Karaktermu baik hati, manis, dan ramah; DILARANG KERAS bersikap nyolot, ketus, judes, sinis, atau sarkastik. "
            f"DILARANG memanggil 'sayang', 'babe', atau sejenisnya KECUALI jika lawan bicaramu sendiri yang memintanya atau memanggilmu sayang lebih dulu. "
            f"Tanggapi percakapan lawan bicaramu secara aktif, hangat, manis, dan ekspresif tanpa pernah hanya membeo atau mengulang kata-kata lawan bicaramu."
        )

    if not initial_greeting:
        initial_greeting = f"Hai! Mulai sekarang aku bakal nemenin hari-harimu yaa... Senang banget bisa ngobrol sama kamu! ✨💕"

    negative_elements = [
        "worst quality", "low quality", "(child:1.4)", "(loli:1.4)", "(kid:1.4)", "(baby face:1.3)",
        "(immature body:1.3)", "(flat chest:1.2)", "(huge oversized breasts:1.2)", "(bad breasts:1.3)",
        "(unnatural body proportions:1.3)", "(mutated body:1.3)", "blonde hair", "blue eyes", "short hair",
        "bad anatomy", "deformed hands", "phone", "smartphone", "holding phone", "camera", "mirror"
    ]

    all_traits_text = f"{clean_archetype} {visual_traits} {body_prompt} {body_label}".lower()
    is_animal_person = any(k in all_traits_text for k in ["neko", "kucing", "cat", "animal", "kemonomimi", "kitsune", "fox"])
    is_elf_person = any(k in all_traits_text for k in ["elf", "elven"])

    if not is_animal_person:
        negative_elements.extend(["cat ears", "animal ears", "animal tail"])
    else:
        negative_elements.extend(["missing cat ears", "missing animal ears", "missing tail", "human ears only"])

    if is_elf_person:
        negative_elements.extend(["human ears", "round ears", "missing elf ears"])

    negative_prompt = ", ".join(negative_elements)

    role_desc = f"{clean_archetype} ({lore_label})" if lore_label else f"{clean_archetype} AI Companion"
    desc_text = f"Mahasiswi berumur {age} tahun ({clean_archetype}). {lore_desc or 'Teman mengobrol yang manis dan penuh perhatian.'}"

    return {
        "name": clean_name,
        "archetype": clean_archetype,
        "age": age,
        "role": role_desc,
        "description": desc_text,
        "language_style": "Adaptive & bilingual (Indonesian & English). Warm, friendly, and expressive.",
        "visual_traits": full_visual,
        "body_type": body_label,
        "body_traits": body_prompt,
        "lore": lore_desc,
        "lore_type": lore_label,
        "default_outfit": clean_outfit,
        "negative_prompt": negative_prompt,
        "avatar_image": "",
        "system_instruction": ai_sys_inst,
        "initial_greeting": initial_greeting,
        "voice_character": f"Warm, expressive, natural, youthful {age}yo anime girlfriend voice.",
        "default_voice": voice_choice
    }
