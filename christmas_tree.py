import math
import os
import random
import shutil
import ssl
import subprocess
import sys
import urllib.request
import pygame

try:
    import cv2
    import mediapipe as mp
    HAS_VISION = True
except ImportError:
    HAS_VISION = False

# ================= 基础配置 =================
FPS = 60
BG_COLOR = (7, 6, 18)
MAX_PHOTOS = 100          # 照片最大数量上限
MIN_TREE_CARDS = 10       # 照片较少时，圣诞树上至少重复铺满的卡片数量

THEMES = [
    {
        "name": "Viral Pink Dream",
        "tree": [(255, 117, 143), (255, 143, 163), (255, 182, 193), (255, 228, 235)],
        "ribbon": [(255, 245, 250), (255, 210, 228), (255, 175, 204)],
        "ornament": [(255, 255, 255), (255, 223, 140), (232, 190, 255), (255, 150, 185)],
        "orbit_track": [(255, 175, 204), (255, 225, 238), (225, 190, 255)],
        "planets": [
            (255, 230, 240), (255, 255, 255), (230, 195, 255), (255, 225, 150),
            (255, 182, 205), (255, 210, 225), (244, 140, 195), (255, 245, 250),
        ],
        "core": (255, 225, 238),
        "star": [(255, 235, 245), (255, 255, 255), (255, 218, 160)],
        "text": (255, 212, 232),
    },
    {
        "name": "Cosmic Violet Galaxy",
        "tree": [(216, 180, 254), (243, 232, 255), (192, 132, 252), (255, 255, 255)],
        "ribbon": [(255, 255, 255), (238, 220, 255), (210, 175, 255)],
        "ornament": [(255, 255, 255), (244, 140, 200), (253, 230, 150)],
        "orbit_track": [(192, 132, 252), (233, 213, 255), (168, 85, 247)],
        "planets": [
            (255, 245, 230), (233, 213, 255), (244, 140, 200), (255, 255, 255),
            (192, 132, 252), (253, 230, 150), (216, 180, 254), (248, 250, 252),
        ],
        "core": (255, 235, 200),
        "star": [(255, 255, 255), (243, 232, 255), (253, 230, 150)],
        "text": (243, 232, 255),
    },
    {
        "name": "Frozen Ice Blue",
        "tree": [(56, 189, 248), (125, 211, 252), (186, 230, 253), (240, 249, 255)],
        "ribbon": [(255, 255, 255), (215, 242, 255), (180, 225, 255)],
        "ornament": [(255, 255, 255), (180, 195, 255), (253, 230, 138)],
        "orbit_track": [(125, 211, 252), (224, 242, 254), (165, 180, 252)],
        "planets": [
            (224, 242, 254), (255, 255, 255), (165, 180, 252), (125, 211, 252),
            (253, 230, 138), (186, 230, 253), (199, 210, 254), (240, 249, 255),
        ],
        "core": (215, 242, 255),
        "star": [(210, 242, 255), (255, 255, 255), (175, 215, 255)],
        "text": (210, 242, 255),
    },
]

FIREWORK_PALETTES = [
    [(255, 105, 145), (255, 210, 120), (255, 255, 255)],
    [(96, 195, 255), (150, 155, 255), (240, 249, 255)],
    [(244, 125, 190), (195, 140, 255), (253, 224, 110)],
    [(255, 155, 95), (255, 115, 130), (255, 240, 165)],
    [(255, 182, 210), (216, 180, 254), (255, 255, 255)],
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]


def convert_heic_in_folder(folder):
    """自动将文件夹内的苹果 .heic/.HEIC 照片转换为 .jpg"""
    if not os.path.isdir(folder):
        return
    for fname in os.listdir(folder):
        if fname.lower().endswith(".heic"):
            src = os.path.join(folder, fname)
            dst = os.path.join(folder, os.path.splitext(fname)[0] + ".jpg")
            try:
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", src, "--out", dst],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
                os.remove(src)
            except Exception:
                pass


class HandTracker:
    """智能双手甄别追踪器：过滤举手机的手，同时测量主控手离摄像头的远近尺寸"""

    def __init__(self):
        self.cam_enabled = False
        self.ai_ready = False
        self.status_msg = "Init Camera..."
        self.cap = None
        self.cam_index = 0
        self.detector = None
        self.use_legacy = False

        self.gesture = "NONE"
        self.hand_detected = False
        self.palm_x = 0.5
        self.palm_y = 0.5
        self.hand_size = 0.21
        self.prev_active_pos = None
        self.swipe_vx = 0.0
        self.is_pinching = False
        self.preview_surface = None
        self.hand_slots = []

        if not HAS_VISION:
            self.status_msg = "Missing cv2/mediapipe"
            return

        self._open_camera(0)
        self._init_mediapipe()

    def _open_camera(self, index):
        if self.cap is not None:
            self.cap.release()
        self.cam_index = index
        self.cap = cv2.VideoCapture(index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cam_enabled = self.cap.isOpened()
        if not self.cam_enabled:
            self.status_msg = f"Camera {index} Unavailable"

    def switch_camera(self):
        next_idx = 1 if self.cam_index == 0 else 0
        self._open_camera(next_idx)
        self.prev_active_pos = None
        self.hand_slots.clear()

    def _init_mediapipe(self):
        try:
            if hasattr(mp, "solutions") and hasattr(mp.solutions, "hands"):
                self.use_legacy = True
                self.detector = mp.solutions.hands.Hands(
                    static_image_mode=False,
                    max_num_hands=2,
                    model_complexity=0,
                    min_detection_confidence=0.55,
                    min_tracking_confidence=0.55,
                )
                self.ai_ready = True
                return

            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(script_dir, "hand_landmarker.task")

            if not os.path.exists(model_path) or os.path.getsize(model_path) < 100000:
                url = (
                    "https://storage.googleapis.com/mediapipe-models/"
                    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
                )
                ctx = ssl._create_unverified_context()
                req = urllib.request.urlopen(url, context=ctx, timeout=20)
                with open(model_path, "wb") as f:
                    f.write(req.read())

            base_options = mp_python.BaseOptions(model_asset_path=model_path)
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_hands=2,
                min_hand_detection_confidence=0.55,
                min_hand_presence_confidence=0.55,
                min_tracking_confidence=0.55,
            )
            self.detector = mp_vision.HandLandmarker.create_from_options(options)
            self.use_legacy = False
            self.ai_ready = True
        except Exception:
            self.ai_ready = False
            self.status_msg = "Model Load Error"

    def _measure_apparent_size(self, pts):
        ax, ay = 1.333, 1.0
        d_mid = math.hypot((pts[9].x - pts[0].x) * ax, (pts[9].y - pts[0].y) * ay)
        d_idx = math.hypot((pts[5].x - pts[0].x) * ax, (pts[5].y - pts[0].y) * ay)
        d_pnk = math.hypot((pts[17].x - pts[0].x) * ax, (pts[17].y - pts[0].y) * ay)
        d_width = math.hypot((pts[5].x - pts[17].x) * ax, (pts[5].y - pts[17].y) * ay)
        return ((d_mid + d_idx + d_pnk) / 3.0) * 0.65 + d_width * 0.35

    def _classify_single_hand(self, pts, currently_pinching=False):
        palm_scale = math.hypot(pts[9].x - pts[0].x, pts[9].y - pts[0].y) + 1e-5
        pinch_dist = math.hypot(pts[4].x - pts[8].x, pts[4].y - pts[8].y) / palm_scale

        finger_specs = [
            (8, 6, 5),
            (12, 10, 9),
            (16, 14, 13),
            (20, 18, 17),
        ]
        ext_flags = []
        for tip_i, pip_i, mcp_i in finger_specs:
            d_tip_wrist = math.hypot(pts[tip_i].x - pts[0].x, pts[tip_i].y - pts[0].y)
            d_pip_wrist = math.hypot(pts[pip_i].x - pts[0].x, pts[pip_i].y - pts[0].y)
            d_tip_mcp = math.hypot(pts[tip_i].x - pts[mcp_i].x, pts[tip_i].y - pts[mcp_i].y)
            d_pip_mcp = math.hypot(pts[pip_i].x - pts[mcp_i].x, pts[pip_i].y - pts[mcp_i].y)
            is_ext = (d_tip_wrist > d_pip_wrist * 1.08) and (d_tip_mcp > d_pip_mcp * 1.12)
            ext_flags.append(is_ext)

        extended_4 = sum(ext_flags)
        other_3_ext = sum(ext_flags[1:])
        thumb_spread = math.hypot(pts[4].x - pts[17].x, pts[4].y - pts[17].y) / palm_scale

        pinch_threshold = 0.50 if currently_pinching else 0.41
        if pinch_dist < pinch_threshold and (other_3_ext >= 1 or currently_pinching):
            return "PINCH", 1.35

        if extended_4 >= 4 or (extended_4 == 3 and thumb_spread > 0.90):
            return "OPEN", 1.30

        if extended_4 == 0 and thumb_spread < 0.95:
            return "FIST", 1.15

        return "NEUTRAL", 0.50

    def _draw_skeleton(self, rgb_frame, pts, is_primary=True):
        h, w, _ = rgb_frame.shape
        line_col = (255, 255, 255) if is_primary else (110, 115, 130)
        dot_col = (255, 145, 210) if is_primary else (90, 95, 110)
        for i1, i2 in HAND_CONNECTIONS:
            x1, y1 = int(pts[i1].x * w), int(pts[i1].y * h)
            x2, y2 = int(pts[i2].x * w), int(pts[i2].y * h)
            cv2.line(rgb_frame, (x1, y1), (x2, y2), line_col, 1, cv2.LINE_AA)
        for lm in pts:
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(rgb_frame, (cx, cy), 3 if is_primary else 2, dot_col, -1, cv2.LINE_AA)

    def update(self, render_preview=False):
        if not self.cam_enabled or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        all_hands_pts = []
        if self.ai_ready and self.detector is not None:
            try:
                if self.use_legacy:
                    res = self.detector.process(rgb)
                    if res.multi_hand_landmarks:
                        all_hands_pts = [h.landmark for h in res.multi_hand_landmarks]
                else:
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    res = self.detector.detect(mp_img)
                    if res.hand_landmarks:
                        all_hands_pts = list(res.hand_landmarks)
            except Exception:
                all_hands_pts = []

        if all_hands_pts:
            new_slots = []
            candidates = []

            for idx, pts in enumerate(all_hands_pts):
                cx, cy = pts[9].x, pts[9].y

                best_dist = 0.22
                matched_energy = 0.0
                for slot in self.hand_slots:
                    d = math.hypot(cx - slot["pos"][0], cy - slot["pos"][1])
                    if d < best_dist:
                        best_dist = d
                        matched_energy = slot["energy"]

                inst_speed = best_dist if matched_energy > 0 else 0.0
                energy = matched_energy * 0.80 + inst_speed * 2.2
                new_slots.append({"pos": (cx, cy), "energy": energy})

                is_prev_locked = False
                if self.prev_active_pos is not None:
                    if math.hypot(cx - self.prev_active_pos[0], cy - self.prev_active_pos[1]) < 0.18:
                        is_prev_locked = True

                gesture, intent_bonus = self._classify_single_hand(
                    pts, currently_pinching=(self.is_pinching and is_prev_locked)
                )

                dist_center = math.hypot(cx - 0.5, cy - 0.48)
                center_score = max(0.0, 1.0 - dist_center * 1.4)
                lock_bonus = 0.42 if is_prev_locked else 0.0
                total_score = intent_bonus + energy * 3.5 + center_score * 0.65 + lock_bonus
                candidates.append((total_score, idx, pts, cx, cy, gesture))

            self.hand_slots = new_slots
            candidates.sort(key=lambda item: item[0], reverse=True)
            _, best_idx, best_pts, bx, by, best_gesture = candidates[0]

            if render_preview:
                for idx, pts in enumerate(all_hands_pts):
                    self._draw_skeleton(rgb, pts, is_primary=(idx == best_idx))

            self.hand_detected = True
            self.gesture = best_gesture
            self.is_pinching = (best_gesture == "PINCH")

            raw_size = self._measure_apparent_size(best_pts)
            self.hand_size = self.hand_size * 0.80 + raw_size * 0.20

            if self.prev_active_pos is not None:
                raw_vx = bx - self.prev_active_pos[0]
                if abs(raw_vx) > 0.0035:
                    self.swipe_vx = self.swipe_vx * 0.45 + raw_vx * 0.55
                else:
                    self.swipe_vx *= 0.75
            else:
                self.swipe_vx = 0.0

            self.prev_active_pos = (bx, by)
            self.palm_x = bx
            self.palm_y = by
        else:
            self.hand_detected = False
            self.gesture = "NONE"
            self.is_pinching = False
            self.prev_active_pos = None
            self.hand_slots.clear()
            self.swipe_vx *= 0.82

        if render_preview:
            small = cv2.resize(rgb, (190, 142))
            self.preview_surface = pygame.surfarray.make_surface(small.swapaxes(0, 1))

    def release(self):
        if self.cap is not None:
            self.cap.release()
        if self.detector is not None and hasattr(self.detector, "close"):
            self.detector.close()


def make_cloud_point(spread_r=520.0, spread_y=360.0):
    theta = random.uniform(0, math.pi * 2)
    phi = math.acos(random.uniform(-1, 1))
    r = spread_r * (random.random() ** 0.45)
    cx = r * math.sin(phi) * math.cos(theta) * 1.35
    cy = r * math.cos(phi) * (spread_y / spread_r)
    cz = r * math.sin(phi) * math.sin(theta)
    return cx, cy, cz


class GlowCache:
    def __init__(self):
        self.cache = {}

    def get_sprite(self, color, radius, style="dot"):
        max_r = 26 if style in ("planet", "ornament") else 13
        radius = max(1, min(max_r, int(round(radius))))
        key = (color, radius, style)
        if key not in self.cache:
            glow_r = radius * (4 if style in ("planet", "ornament") else 3)
            surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            r, g, b = color
            if style == "planet":
                pygame.draw.circle(surf, (r, g, b, 22), (glow_r, glow_r), glow_r)
                pygame.draw.circle(surf, (r, g, b, 52), (glow_r, glow_r), int(glow_r * 0.65))
                pygame.draw.circle(surf, (r, g, b, 115), (glow_r, glow_r), int(radius * 1.45))
                pygame.draw.circle(surf, (r, g, b, 210), (glow_r, glow_r), radius)
                core = (min(255, r + 70), min(255, g + 70), min(255, b + 70), 245)
                pygame.draw.circle(surf, core, (glow_r, glow_r), max(2, int(radius * 0.65)))
            elif style == "ornament":
                pygame.draw.circle(surf, (r, g, b, 30), (glow_r, glow_r), glow_r)
                pygame.draw.circle(surf, (r, g, b, 90), (glow_r, glow_r), int(glow_r * 0.52))
                pygame.draw.circle(surf, (r, g, b, 235), (glow_r, glow_r), radius)
                hi_offset = max(1, radius // 3)
                pygame.draw.circle(
                    surf,
                    (255, 255, 255, 245),
                    (glow_r - hi_offset, glow_r - hi_offset),
                    max(1, int(radius * 0.42)),
                )
            elif style == "ribbon":
                pygame.draw.circle(surf, (r, g, b, 34), (glow_r, glow_r), glow_r)
                pygame.draw.circle(surf, (r, g, b, 110), (glow_r, glow_r), int(glow_r * 0.56))
                pygame.draw.circle(surf, (255, 255, 255, 235), (glow_r, glow_r), max(1, int(radius * 0.75)))
            else:
                pygame.draw.circle(surf, (r, g, b, 26), (glow_r, glow_r), glow_r)
                pygame.draw.circle(surf, (r, g, b, 75), (glow_r, glow_r), int(glow_r * 0.58))
                pygame.draw.circle(surf, (r, g, b, 215), (glow_r, glow_r), radius)
                core = (min(255, r + 95), min(255, g + 95), min(255, b + 95), 255)
                pygame.draw.circle(surf, core, (glow_r, glow_r), max(1, radius // 2))
            self.cache[key] = surf
        return self.cache[key]


class CelebrationSparkle3D:
    """添加照片时从圣诞树照片位置向四周迸发的 3D 星光粒子"""

    def __init__(self, x, y, z, color):
        self.x, self.y, self.z = x, y, z
        theta = random.uniform(0, math.pi * 2)
        phi = math.acos(random.uniform(-1, 1))
        speed = random.uniform(45.0, 165.0)
        self.vx = speed * math.sin(phi) * math.cos(theta)
        self.vy = speed * math.cos(phi) - 25.0
        self.vz = speed * math.sin(phi) * math.sin(theta)
        self.color = color
        self.size = random.uniform(2.2, 4.4)
        self.life = 1.0
        self.decay = random.uniform(0.55, 0.95)

    def update(self, dt):
        self.vx *= 0.95
        self.vy = self.vy * 0.95 + 22.0 * dt
        self.vz *= 0.95
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.z += self.vz * dt
        self.life -= self.decay * dt


class TreeParticle:
    def __init__(self, x, y, z, base_size):
        self.x, self.y, self.z = x, y, z
        self.cx, self.cy, self.cz = make_cloud_point(560.0, 380.0)
        self.base_size = base_size
        self.phase = random.uniform(0, math.pi * 2)
        self.twinkle_speed = random.uniform(1.6, 4.0)
        self.color = (255, 255, 255)

    def apply_theme(self, theme):
        self.color = random.choice(theme["tree"])


class TreeOrnament:
    def __init__(self, x, y, z, shape, base_size):
        self.x, self.y, self.z = x, y, z
        self.cx, self.cy, self.cz = make_cloud_point(500.0, 340.0)
        self.shape = shape
        self.base_size = base_size
        self.phase = random.uniform(0, math.pi * 2)
        self.color = (255, 255, 255)

    def apply_theme(self, theme):
        self.color = random.choice(theme["ornament"])


class RibbonNode:
    def __init__(self, x, y, z, progress, strand_idx, base_size):
        self.x, self.y, self.z = x, y, z
        self.cx, self.cy, self.cz = make_cloud_point(540.0, 360.0)
        self.progress = progress
        self.strand_idx = strand_idx
        self.base_size = base_size
        self.phase = random.uniform(0, math.pi * 2)
        self.color = (255, 255, 255)

    def apply_theme(self, theme):
        palette = theme["ribbon"]
        self.color = palette[self.strand_idx % len(palette)]


class PlanetaryTrackParticle:
    def __init__(self, radius, base_y, angle, speed, base_size):
        self.radius = radius
        self.base_y = base_y
        self.angle = angle
        self.speed = speed
        self.cx, self.cy, self.cz = make_cloud_point(620.0, 400.0)
        self.base_size = base_size
        self.phase = random.uniform(0, math.pi * 2)
        self.color = (255, 255, 255)

    def apply_theme(self, theme):
        self.color = random.choice(theme["orbit_track"])

    def update_and_get_pos(self, dt):
        self.angle += self.speed * dt
        x = self.radius * math.cos(self.angle)
        z = self.radius * math.sin(self.angle)
        y = self.base_y + math.sin(self.angle * 3.0 + self.phase) * 1.6
        return x, y, z


class PlanetOrb:
    def __init__(self, orbit_idx, radius, base_y, angle, speed, planet_size):
        self.orbit_idx = orbit_idx
        self.radius = radius
        self.base_y = base_y
        self.angle = angle
        self.speed = speed
        self.cx, self.cy, self.cz = make_cloud_point(480.0, 320.0)
        self.planet_size = planet_size
        self.phase = random.uniform(0, math.pi * 2)
        self.color = (255, 255, 255)

    def apply_theme(self, theme):
        palette = theme["planets"]
        self.color = palette[self.orbit_idx % len(palette)]

    def update_and_get_pos(self, dt):
        self.angle += self.speed * dt
        x = self.radius * math.cos(self.angle)
        z = self.radius * math.sin(self.angle)
        y = self.base_y - self.planet_size * 0.25
        return x, y, z


def build_polaroid_surface(img_surf):
    """根据照片原图横竖比例自适应构建拍立得相框，不拉伸不变形"""
    iw, ih = img_surf.get_size()
    if ih > iw:
        w, h = 212, 268
        inner_w, inner_h = w - 20, h - 42
    else:
        w, h = 260, 212
        inner_w, inner_h = w - 20, h - 42

    card = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(card, (255, 255, 255, 244), (0, 0, w, h), border_radius=8)
    pygame.draw.rect(card, (255, 200, 225, 255), (0, 0, w, h), 2, border_radius=8)

    scale = max(inner_w / max(1, iw), inner_h / max(1, ih))
    sw, sh = max(1, int(iw * scale)), max(1, int(ih * scale))
    scaled = pygame.transform.smoothscale(img_surf, (sw, sh))
    crop_x = (sw - inner_w) // 2
    crop_y = (sh - inner_h) // 2
    card.blit(scaled, (10, 10), (crop_x, crop_y, inner_w, inner_h))
    return card


class PhotoCard:
    def __init__(self, uid, card_surf, tree_pos, cloud_pos, size_factor, pop_timer=0.0):
        self.uid = uid
        self.card_surf = card_surf
        self.tx0, self.ty0, self.tz0 = tree_pos
        self.cx0, self.cy0, self.cz0 = cloud_pos
        self.size_factor = size_factor
        self.phase = random.uniform(0, math.pi * 2)
        self.pop_timer = pop_timer

    def get_3d_pos(self, t_sec, scatter, cloud_spread):
        ty = self.ty0 + math.sin(t_sec * 1.4 + self.phase) * 4.5

        orb_ang = t_sec * 0.14
        cos_a, sin_a = math.cos(orb_ang), math.sin(orb_ang)
        cx = (self.cx0 * cos_a - self.cz0 * sin_a) * cloud_spread
        cz = (self.cx0 * sin_a + self.cz0 * cos_a) * cloud_spread
        cy = (self.cy0 + math.sin(t_sec * 1.1 + self.phase) * 12.0) * cloud_spread

        x = self.tx0 * (1.0 - scatter) + cx * scatter
        y = ty * (1.0 - scatter) + cy * scatter
        z = self.tz0 * (1.0 - scatter) + cz * scatter
        return x, y, z


class AdaptivePhotoGallery:
    """自适应照片库：支持 1~100 张照片挂在圣诞树与星海中，支持热更新检测"""

    def __init__(self):
        self.has_photos = False
        self.unique_surfs = []
        self.cards = []
        self.deck_queue = []
        self.last_shown_uid = -1
        self.last_signature = None

        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.primary_dir = os.path.expanduser("~/Desktop/圣诞树照片库")
        os.makedirs(self.primary_dir, exist_ok=True)
        self.search_dirs = [
            self.primary_dir,
            os.path.join(script_dir, "photos"),
            os.path.expanduser("~/Desktop/photos"),
        ]
        self.reload(with_pop_effect=False)

    def _scan_files(self):
        valid_exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp")
        for folder in self.search_dirs:
            if os.path.isdir(folder):
                convert_heic_in_folder(folder)
                files = []
                for fname in sorted(os.listdir(folder)):
                    if fname.lower().endswith(valid_exts):
                        fpath = os.path.join(folder, fname)
                        try:
                            mtime = os.path.getmtime(fpath)
                            files.append((fpath, mtime))
                        except Exception:
                            pass
                        if len(files) >= MAX_PHOTOS:
                            break
                if files:
                    return folder, tuple(files)
        return None, ()

    def check_for_updates(self):
        """实时检测照片库变动：新增照片时返回 'ADDED'，删除照片返回 'REMOVED'"""
        _, sig = self._scan_files()
        if sig == self.last_signature:
            return "NONE"
        old_count = len(self.last_signature) if self.last_signature else 0
        new_count = len(sig)
        self.reload(with_pop_effect=(new_count > old_count))
        return "ADDED" if new_count > old_count else "REMOVED"

    def reload(self, with_pop_effect=True):
        _, sig = self._scan_files()
        self.last_signature = sig
        self.deck_queue.clear()

        raw_images = []
        for fpath, _ in sig:
            try:
                img = pygame.image.load(fpath).convert()
                raw_images.append(img)
            except Exception:
                pass

        if not raw_images:
            self.has_photos = False
            self.unique_surfs = []
            self.cards = []
            return

        self.has_photos = True
        self.unique_surfs = [build_polaroid_surface(img) for img in raw_images[:MAX_PHOTOS]]
        u_count = len(self.unique_surfs)

        display_count = max(MIN_TREE_CARDS, u_count)
        display_count = min(MAX_PHOTOS, display_count)

        if display_count <= 14:
            size_factor = 1.0
        elif display_count <= 35:
            size_factor = 0.84
        elif display_count <= 65:
            size_factor = 0.70
        else:
            size_factor = 0.58

        golden_angle = 2.39996323
        tree_height = 460.0
        max_radius = 192.0

        self.cards = []
        for i in range(display_count):
            uid = i % u_count
            surf = self.unique_surfs[uid]

            # 圣诞树表面黄金角螺旋坐标（直接挂在树身外层，与树一起自转）
            frac = (i + 0.5) / display_count
            t = 0.16 + 0.72 * frac
            ty = -tree_height / 2 + t * tree_height
            tr = (t ** 0.90) * max_radius * 1.03 + 11.0
            t_ang = i * golden_angle
            tx = tr * math.cos(t_ang)
            tz = tr * math.sin(t_ang)

            # 张开手掌散开时的 3D 斐波那契球面星云坐标
            y_norm = 1.0 - 2.0 * frac
            r_xy = math.sqrt(max(0.0, 1.0 - y_norm * y_norm))
            shell_r = 350.0 + (i % 3) * 65.0
            c_ang = i * golden_angle
            cx = shell_r * 1.32 * r_xy * math.cos(c_ang)
            cy = shell_r * 0.72 * y_norm
            cz = shell_r * 1.32 * r_xy * math.sin(c_ang)

            pop_t = 1.0 if with_pop_effect else 0.0
            self.cards.append(PhotoCard(uid, surf, (tx, ty, tz), (cx, cy, cz), size_factor, pop_timer=pop_t))

    def next_unique_photo(self):
        if not self.has_photos or not self.unique_surfs:
            return -1, None
        u_count = len(self.unique_surfs)
        if u_count == 1:
            self.last_shown_uid = 0
            return 0, self.unique_surfs[0]

        if not self.deck_queue:
            self.deck_queue = list(range(u_count))
            random.shuffle(self.deck_queue)
            if self.deck_queue[0] == self.last_shown_uid:
                self.deck_queue[0], self.deck_queue[-1] = self.deck_queue[-1], self.deck_queue[0]

        uid = self.deck_queue.pop(0)
        self.last_shown_uid = uid
        return uid, self.unique_surfs[uid]


class FireworkSpark:
    def __init__(self, x, y, vx, vy, color, size):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.color = color
        self.size = size
        self.life = 1.0
        self.decay = random.uniform(0.011, 0.019)
        self.trail = [(x, y)]

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.vx *= 0.965
        self.vy *= 0.965
        self.vy += 0.06
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay

    def draw(self, screen, glow_cache):
        if self.life <= 0:
            return
        if len(self.trail) >= 2:
            for i in range(len(self.trail) - 1):
                fade = (i + 1) / len(self.trail) * self.life
                c = (
                    int(self.color[0] * fade),
                    int(self.color[1] * fade),
                    int(self.color[2] * fade),
                )
                pygame.draw.line(screen, c, self.trail[i], self.trail[i + 1], max(1, int(self.size * fade)))

        radius = self.size * (0.4 + 0.8 * self.life)
        sprite = glow_cache.get_sprite(self.color, radius, "dot")
        w, h = sprite.get_size()
        screen.blit(sprite, (int(self.x) - w // 2, int(self.y) - h // 2))


class Firework:
    def __init__(self, screen_w, screen_h, delay=0.0, custom_x=None):
        self.delay = delay
        margin = max(70, int(screen_w * 0.08))
        left_max = max(margin + 50, int(screen_w * 0.34))
        right_min = min(screen_w - margin - 50, int(screen_w * 0.66))

        if custom_x is not None:
            self.x = custom_x
        elif random.random() < 0.5:
            self.x = random.uniform(margin, left_max)
        else:
            self.x = random.uniform(right_min, screen_w - margin)

        self.y = screen_h + 10
        self.vx = random.uniform(-1.0, 1.0)
        self.vy = -random.uniform(10.5, 14.2) * (screen_h / 900.0)
        self.target_y = random.uniform(screen_h * 0.08, screen_h * 0.34)
        self.palette = random.choice(FIREWORK_PALETTES)
        self.rocket_color = self.palette[0]
        self.exploded = False
        self.sparks = []
        self.rocket_trail = []

    def update(self, dt=0.016):
        if self.delay > 0:
            self.delay -= dt
            return
        if not self.exploded:
            self.rocket_trail.append((self.x, self.y))
            if len(self.rocket_trail) > 8:
                self.rocket_trail.pop(0)
            self.x += self.vx
            self.y += self.vy
            self.vy += 0.14
            if self.y <= self.target_y or self.vy >= -1.5:
                self.explode()
        else:
            for s in self.sparks:
                s.update()
            self.sparks = [s for s in self.sparks if s.life > 0]

    def explode(self):
        self.exploded = True
        count = random.randint(80, 110)
        shape = random.choice(["sphere", "double_ring", "starburst"])
        for i in range(count):
            if shape == "double_ring":
                angle = (2 * math.pi / count) * i
                speed = random.choice([3.0, 5.4]) + random.uniform(-0.4, 0.4)
            elif shape == "starburst":
                angle = (2 * math.pi / count) * i
                star_mod = 1.0 + 0.45 * math.cos(5 * angle)
                speed = random.uniform(2.3, 5.2) * star_mod
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(1.2, 5.8)

            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(self.palette)
            size = random.uniform(1.8, 3.2)
            self.sparks.append(FireworkSpark(self.x, self.y, vx, vy, color, size))

    def draw(self, screen, glow_cache):
        if self.delay > 0:
            return
        if not self.exploded:
            for i, pos in enumerate(self.rocket_trail):
                fade = (i + 1) / len(self.rocket_trail)
                c = (
                    int(self.rocket_color[0] * fade),
                    int(self.rocket_color[1] * fade),
                    int(self.rocket_color[2] * fade),
                )
                pygame.draw.circle(screen, c, (int(pos[0]), int(pos[1])), 2)
            sprite = glow_cache.get_sprite(self.rocket_color, 3, "dot")
            w, h = sprite.get_size()
            screen.blit(sprite, (int(self.x) - w // 2, int(self.y) - h // 2))
        else:
            for s in self.sparks:
                s.draw(screen, glow_cache)

    def is_dead(self):
        return self.delay <= 0 and self.exploded and len(self.sparks) == 0


def create_tree_elements():
    tree_particles = []
    ribbon_nodes = []
    ornaments = []

    tree_height = 460.0
    max_radius = 192.0

    layers = 9
    for layer in range(layers):
        t_start = layer / layers
        t_end = min(1.0, (layer + 1.15) / layers)
        dots_in_layer = 155 + layer * 26
        for _ in range(dots_in_layer):
            u = random.random()
            t = t_start + (t_end - t_start) * u
            y = -tree_height / 2 + t * tree_height
            branch_flare = 1.0 + 0.14 * math.sin(u * math.pi)
            r_max = (t ** 0.90) * max_radius * branch_flare
            r = r_max * (random.random() ** 0.35)
            a = random.uniform(0, math.pi * 2)
            x = r * math.cos(a)
            z = r * math.sin(a)
            y_jitter = y + random.uniform(-5, 5)
            tree_particles.append(TreeParticle(x, y_jitter, z, random.uniform(1.3, 2.5)))

    steps = 360
    total_turns = 5.5
    strand_offsets = [
        (0.0, 0.0, 3.2),
        (-4.5, 0.06, 2.1),
        (4.5, -0.06, 2.1),
    ]
    for i in range(steps):
        prog = i / (steps - 1)
        t_cone = 1.0 - prog
        base_y = -tree_height / 2 + t_cone * tree_height
        base_r = (t_cone ** 0.92) * (max_radius + 10.0) + 4.0
        base_angle = prog * total_turns * 2.0 * math.pi

        for s_idx, (dy, d_ang, sz) in enumerate(strand_offsets):
            ang = base_angle + d_ang
            r = base_r + math.sin(prog * 30.0 + s_idx) * 1.5
            x = r * math.cos(ang)
            z = r * math.sin(ang)
            y = base_y + dy
            ribbon_nodes.append(RibbonNode(x, y, z, prog, s_idx, sz))

    num_ornaments = 64
    for i in range(num_ornaments):
        t = 0.14 + 0.82 * (i / num_ornaments)
        y = -tree_height / 2 + t * tree_height + random.uniform(-6, 6)
        r = (t ** 0.90) * max_radius * random.uniform(0.86, 1.04)
        a = i * 2.39996 + random.uniform(-0.15, 0.15)
        x = r * math.cos(a)
        z = r * math.sin(a)
        shape = "pendant" if i % 3 == 0 else "bauble"
        size = random.uniform(4.2, 6.2) if shape == "bauble" else random.uniform(3.6, 5.0)
        ornaments.append(TreeOrnament(x, y, z, shape, size))

    return tree_particles, ribbon_nodes, ornaments


def create_star_particles():
    outer_r = 33.0
    inner_r = 13.5
    z_depth = 11.0

    vertices = []
    for i in range(10):
        r = outer_r if i % 2 == 0 else inner_r
        angle = -math.pi / 2 + i * math.pi / 5
        vertices.append((r * math.cos(angle), r * math.sin(angle), 0.0))

    front_apex = (0.0, 0.0, z_depth)
    back_apex = (0.0, 0.0, -z_depth)

    star_pts = []
    for i in range(10):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % 10]
        for step in range(12):
            u = step / 12.0
            x = p1[0] + (p2[0] - p1[0]) * u + random.uniform(-0.8, 0.8)
            y = p1[1] + (p2[1] - p1[1]) * u + random.uniform(-0.8, 0.8)
            z = random.uniform(-1.5, 1.5)
            star_pts.append([x, y, z, random.uniform(1.8, 3.0), random.uniform(0, math.pi * 2)])

    for v in vertices:
        for apex in (front_apex, back_apex):
            for step in range(1, 7):
                u = step / 7.0
                x = apex[0] + (v[0] - apex[0]) * u
                y = apex[1] + (v[1] - apex[1]) * u
                z = apex[2] + (v[2] - apex[2]) * u
                star_pts.append([x, y, z, random.uniform(1.5, 2.6), random.uniform(0, math.pi * 2)])

    return star_pts


def create_planetary_orbits():
    base_y = 236.0
    orbit_radii = [155, 205, 258, 312, 372, 435, 500, 565]
    planet_sizes = [6.5, 8.0, 8.5, 7.2, 13.5, 12.0, 9.5, 9.0]

    track_particles = []
    planets = []

    for idx, r in enumerate(orbit_radii):
        angular_speed = 0.46 / ((r / 155.0) ** 0.75)

        num_dots = int(r * 0.58)
        for i in range(num_dots):
            angle = (2 * math.pi / num_dots) * i + random.uniform(-0.02, 0.02)
            r_jitter = r + random.uniform(-5.5, 5.5)
            size = random.uniform(1.3, 2.6)
            track_particles.append(
                PlanetaryTrackParticle(r_jitter, base_y, angle, angular_speed, size)
            )

        if idx < len(orbit_radii) - 1:
            mid_r = (r + orbit_radii[idx + 1]) * 0.5
            for _ in range(40):
                angle = random.uniform(0, math.pi * 2)
                track_particles.append(
                    PlanetaryTrackParticle(
                        mid_r + random.uniform(-14, 14),
                        base_y + random.uniform(-2, 2),
                        angle,
                        angular_speed * 0.9,
                        random.uniform(1.0, 1.8),
                    )
                )

        init_angle = idx * 0.85 + random.uniform(-0.2, 0.2)
        planets.append(
            PlanetOrb(idx, r, base_y, init_angle, angular_speed * 1.12, planet_sizes[idx])
        )

    return track_particles, planets


def create_snowflakes(width, height):
    count = max(130, int((width * height) / 6800))
    snow = []
    for _ in range(count):
        snow.append(
            {
                "x": random.uniform(0, width),
                "y": random.uniform(0, height),
                "speed": random.uniform(0.6, 1.8),
                "radius": random.uniform(1.2, 3.0),
                "drift": random.uniform(0, math.pi * 2),
            }
        )
    return snow


def draw_glowing_title(screen, text, center_pos, font_size, color, alpha=1.0):
    if alpha <= 0.02:
        return
    font = pygame.font.SysFont("georgia", font_size, italic=True) or pygame.font.Font(None, font_size)
    c_main = (int(color[0] * alpha), int(color[1] * alpha), int(color[2] * alpha))
    glow_color = (max(0, c_main[0] // 3), max(0, c_main[1] // 3), max(0, c_main[2] // 3))
    glow_surf = font.render(text, True, glow_color)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)]:
        screen.blit(glow_surf, glow_surf.get_rect(center=(center_pos[0] + dx, center_pos[1] + dy)))

    main_surf = font.render(text, True, c_main)
    screen.blit(main_surf, main_surf.get_rect(center=center_pos))


def scale_color(color, factor):
    factor = max(0.0, min(1.0, factor))
    return (int(color[0] * factor), int(color[1] * factor), int(color[2] * factor))


def import_photos_via_dialog(target_dir):
    """调用 macOS 原生文件选择窗口导入照片（自动转换 HEIC）"""
    script = (
        'set chosenFiles to choose file of type {"public.image"} '
        'with prompt "选择要挂上圣诞树的照片（可按住 Command 多选）" '
        'with multiple selections allowed\n'
        'set outPaths to ""\n'
        'repeat with f in chosenFiles\n'
        'set outPaths to outPaths & POSIX path of f & linefeed\n'
        'end repeat\n'
        'return outPaths'
    )
    try:
        res = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if res.returncode != 0 or not res.stdout.strip():
            return 0
        paths = [p.strip() for p in res.stdout.strip().splitlines() if p.strip()]
        imported = 0
        os.makedirs(target_dir, exist_ok=True)
        for src in paths:
            if os.path.isfile(src):
                fname = os.path.basename(src)
                dst = os.path.join(target_dir, fname)
                if os.path.abspath(src) != os.path.abspath(dst):
                    shutil.copy2(src, dst)
                imported += 1
        if imported > 0:
            convert_heic_in_folder(target_dir)
        return imported
    except Exception:
        return 0


def main():
    pygame.init()
    tracker = HandTracker()

    info = pygame.display.Info()
    desktop_w, desktop_h = info.current_w, info.current_h

    is_fullscreen = True
    screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
    pygame.display.set_caption("3D Particle Christmas Tree")
    width, height = screen.get_size()

    clock = pygame.time.Clock()
    glow_cache = GlowCache()
    tree_particles, ribbon_nodes, ornaments = create_tree_elements()
    star_pts = create_star_particles()
    track_particles, planets = create_planetary_orbits()
    gallery = AdaptivePhotoGallery()
    snowflakes = create_snowflakes(width, height)
    fireworks = []
    cele_sparkles = []

    theme_idx = 0

    def apply_current_theme():
        theme = THEMES[theme_idx]
        for p in tree_particles:
            p.apply_theme(theme)
        for rn in ribbon_nodes:
            rn.apply_theme(theme)
        for orn in ornaments:
            orn.apply_theme(theme)
        for tp in track_particles:
            tp.apply_theme(theme)
        for pl in planets:
            pl.apply_theme(theme)

    apply_current_theme()

    rot_y = 0.0
    rot_vel = 0.0
    star_rot_y = 0.0
    auto_speed = 0.0075
    base_tilt_x = 0.25
    current_tilt_x = base_tilt_x
    dragging = False
    last_mouse_x = 0
    firework_timer = 0.0
    folder_watch_timer = 0.0
    intro_elapsed = 0.0
    star_burst_triggered = False
    star_burst = 0.0

    def trigger_photo_celebration():
        """添加照片时的专属特效：6朵连环烟花 + 树顶星芒 + 照片位星光迸发"""
        nonlocal star_burst
        star_burst = 1.25
        # 6 朵错峰升空的绚丽烟花
        x_positions = [
            width * 0.14,
            width * 0.86,
            width * 0.24,
            width * 0.76,
            width * 0.34,
            width * 0.66,
        ]
        for idx, fx in enumerate(x_positions):
            fireworks.append(Firework(width, height, delay=idx * 0.14, custom_x=fx))

        # 从每张挂在圣诞树上的照片周围迸发金色与樱花粉星光粒子
        spark_palette = [(255, 225, 130), (255, 165, 215), (255, 255, 255), (225, 185, 255)]
        for card in gallery.cards:
            for _ in range(10):
                cele_sparkles.append(
                    CelebrationSparkle3D(
                        card.tx0,
                        card.ty0,
                        card.tz0,
                        random.choice(spark_palette),
                    )
                )

    # 如果启动时已经放入了照片，开场结束时也送上一波欢迎烟花
    initial_photo_celebrated = not gallery.has_photos

    scatter = 0.0
    target_scatter = 0.0
    cloud_spread = 1.0
    target_cloud_spread = 1.0
    grabbed_uid = None
    grabbed_surf = None
    photo_hold_timer = 0.0
    prev_pinch_active = False
    zoom_blend = 0.0
    hand_streak = 0
    no_hand_duration = 0.0
    show_cam_preview = False
    hud_font = pygame.font.SysFont("helvetica", 14, bold=True)

    ascend_dur = 3.6
    pullback_dur = 2.0
    intro_total_dur = ascend_dur + pullback_dur

    while True:
        dt = clock.tick(FPS) / 1000.0
        t_sec = pygame.time.get_ticks() / 1000.0
        intro_elapsed += dt

        # 每隔 1 秒自动检查一次照片库文件夹是否有新照片拖入
        folder_watch_timer += dt
        if folder_watch_timer >= 1.0:
            folder_watch_timer = 0.0
            status = gallery.check_for_updates()
            if status == "ADDED":
                trigger_photo_celebration()
            elif status == "REMOVED" and not gallery.has_photos:
                grabbed_uid = None
                grabbed_surf = None

        tracker.update(render_preview=show_cam_preview)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                tracker.release()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.VIDEORESIZE and not is_fullscreen:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                snowflakes = create_snowflakes(width, height)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    theme_idx = (theme_idx + 1) % len(THEMES)
                    apply_current_theme()
                elif event.key == pygame.K_p:
                    # 按 P 键弹出 macOS 原生选图框（临时切窗口模式防止全屏遮挡系统弹窗）
                    was_full = is_fullscreen
                    if was_full:
                        safe_w = int(desktop_w * 0.84)
                        safe_h = int(desktop_h * 0.80)
                        screen = pygame.display.set_mode((safe_w, safe_h), pygame.RESIZABLE)
                        pygame.display.flip()
                    added = import_photos_via_dialog(gallery.primary_dir)
                    if was_full:
                        screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
                    width, height = screen.get_size()
                    snowflakes = create_snowflakes(width, height)
                    if added > 0:
                        gallery.reload(with_pop_effect=True)
                        trigger_photo_celebration()
                elif event.key == pygame.K_v:
                    show_cam_preview = not show_cam_preview
                elif event.key == pygame.K_f:
                    fireworks.append(Firework(width, height))
                elif event.key == pygame.K_c:
                    tracker.switch_camera()
                elif event.key == pygame.K_r:
                    intro_elapsed = 0.0
                    star_burst_triggered = False
                    star_burst = 0.0
                    target_scatter = 0.0
                    scatter = 0.0
                    cloud_spread = 1.0
                    target_cloud_spread = 1.0
                    grabbed_uid = None
                    grabbed_surf = None
                    hand_streak = 0
                    fireworks.clear()
                    cele_sparkles.clear()
                elif event.key in (pygame.K_TAB, pygame.K_RETURN):
                    is_fullscreen = not is_fullscreen
                    if is_fullscreen:
                        screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.FULLSCREEN)
                    else:
                        safe_w = int(desktop_w * 0.84)
                        safe_h = int(desktop_h * 0.80)
                        screen = pygame.display.set_mode((safe_w, safe_h), pygame.RESIZABLE)
                    width, height = screen.get_size()
                    snowflakes = create_snowflakes(width, height)
                elif event.key == pygame.K_ESCAPE:
                    tracker.release()
                    pygame.quit()
                    sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                dragging = True
                last_mouse_x = event.pos[0]
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx = event.pos[0] - last_mouse_x
                rot_y += dx * 0.007
                last_mouse_x = event.pos[0]

        # ================= 严格开场锁 + 智能手势交互 =================
        intro_finished = intro_elapsed >= intro_total_dur

        if not intro_finished:
            hand_streak = 0
            no_hand_duration = 0.0
            target_scatter = 0.0
            target_cloud_spread = 1.0
            grabbed_uid = None
            grabbed_surf = None
            prev_pinch_active = False
            target_tilt = base_tilt_x
        else:
            if not initial_photo_celebrated and gallery.has_photos:
                initial_photo_celebrated = True
                trigger_photo_celebration()

            if tracker.hand_detected and tracker.gesture != "NEUTRAL":
                hand_streak += 1
                no_hand_duration = 0.0
            else:
                hand_streak = 0
                no_hand_duration += dt

            pinch_now = tracker.hand_detected and (tracker.gesture == "PINCH")

            if hand_streak >= 3:
                if tracker.gesture == "OPEN":
                    target_scatter = 1.0
                    grabbed_uid = None
                    grabbed_surf = None
                    rot_vel += tracker.swipe_vx * 0.72

                    norm_near = max(0.0, min(1.0, (tracker.hand_size - 0.10) / (0.33 - 0.10)))
                    target_cloud_spread = 1.72 - norm_near * (1.72 - 0.42)

                elif tracker.gesture == "PINCH":
                    if gallery.has_photos and not prev_pinch_active:
                        uid, surf = gallery.next_unique_photo()
                        if surf is not None:
                            grabbed_uid = uid
                            grabbed_surf = surf
                            zoom_blend = 0.15
                    photo_hold_timer = 0.0

                elif tracker.gesture == "FIST":
                    if scatter > 0.15 or grabbed_uid is not None:
                        target_scatter = 0.0
                        target_cloud_spread = 1.0
                        grabbed_uid = None
                        grabbed_surf = None

                target_tilt = base_tilt_x + (tracker.palm_y - 0.5) * 0.28 * scatter
            else:
                target_tilt = base_tilt_x
                if grabbed_uid is not None:
                    photo_hold_timer += dt
                    if photo_hold_timer >= 3.0 or no_hand_duration >= 2.0:
                        grabbed_uid = None
                        grabbed_surf = None

                if no_hand_duration >= 2.0:
                    target_scatter = 0.0
                    target_cloud_spread = 1.0

            prev_pinch_active = pinch_now

        scatter += (target_scatter - scatter) * min(1.0, dt * 4.2)
        cloud_spread += (target_cloud_spread - cloud_spread) * min(1.0, dt * 4.5)
        current_tilt_x += (target_tilt - current_tilt_x) * min(1.0, dt * 5.0)
        target_zoom = 1.0 if grabbed_surf is not None else 0.0
        zoom_blend += (target_zoom - zoom_blend) * min(1.0, dt * 7.5)

        rot_y += rot_vel
        rot_vel *= 0.91

        # ================= 开场运镜与正常自转 =================
        if intro_elapsed < ascend_dur:
            u = intro_elapsed / ascend_dur
            smooth_u = u * u * (3.0 - 2.0 * u)
            ribbon_progress = smooth_u
            cam_zoom = 1.85 - 0.30 * smooth_u
            cam_look_y = 205.0 - 385.0 * smooth_u
            orbit_alpha = 0.0
            star_alpha = max(0.0, (u - 0.85) / 0.15)
            title_alpha = 0.0
            if not dragging:
                rot_y += auto_speed * 1.6
        elif intro_elapsed < intro_total_dur:
            if not star_burst_triggered:
                star_burst_triggered = True
                star_burst = 1.0
            v = (intro_elapsed - ascend_dur) / pullback_dur
            ease_v = 1.0 - (1.0 - v) ** 3
            ribbon_progress = 1.0
            cam_zoom = 1.55 - 0.55 * ease_v
            cam_look_y = -180.0 * (1.0 - ease_v)
            orbit_alpha = ease_v
            star_alpha = 1.0
            title_alpha = ease_v
            if not dragging:
                rot_y += auto_speed
        else:
            ribbon_progress = 1.0
            cam_zoom = 1.0
            cam_look_y = 0.0
            orbit_alpha = 1.0
            star_alpha = 1.0
            title_alpha = 1.0
            if not dragging:
                rot_y += auto_speed * (0.45 if scatter > 0.5 else 1.0)

        star_burst = max(0.0, star_burst - dt * 0.85)
        star_rot_y += 1.45 * dt

        if intro_elapsed > ascend_dur + 0.4:
            firework_timer += dt
            if firework_timer >= 1.15:
                firework_timer = 0.0
                if len(fireworks) < 8:
                    fireworks.append(Firework(width, height))

        screen.fill(BG_COLOR)

        scale_ratio = (height / 900.0) * cam_zoom
        fov = 720.0 * scale_ratio
        center_x = width // 2
        center_y = int(height * 0.44)

        for s in snowflakes:
            s["y"] += s["speed"]
            s["x"] += math.sin(t_sec * 1.3 + s["drift"]) * 0.4
            if s["y"] > height:
                s["y"] = -5
                s["x"] = random.uniform(0, width)
            pygame.draw.circle(screen, (215, 220, 248), (int(s["x"]), int(s["y"])), int(s["radius"]))

        for fw in fireworks:
            fw.update(dt)
            fw.draw(screen, glow_cache)
        fireworks = [fw for fw in fireworks if not fw.is_dead()]

        cos_y, sin_y = math.cos(rot_y), math.sin(rot_y)
        cos_x, sin_x = math.cos(current_tilt_x), math.sin(current_tilt_x)
        projected = []

        reveal_y_limit = 245.0 - ribbon_progress * 490.0
        density_size_mod = 1.0 - scatter * max(0.0, (1.0 - cloud_spread) * 0.25)

        for p in tree_particles:
            if p.y < reveal_y_limit - 35.0:
                continue
            fade = min(1.0, (p.y - (reveal_y_limit - 35.0)) / 75.0)
            if fade <= 0.05:
                continue

            px = p.x * (1.0 - scatter) + (p.cx * cloud_spread) * scatter
            py = p.y * (1.0 - scatter) + (p.cy * cloud_spread) * scatter
            pz = p.z * (1.0 - scatter) + (p.cz * cloud_spread) * scatter

            x1 = px * cos_y - pz * sin_y
            z1 = px * sin_y + pz * cos_y
            py_shifted = py - cam_look_y
            y2 = py_shifted * cos_x - z1 * sin_x
            z2 = py_shifted * sin_x + z1 * cos_x

            depth = fov + z2
            if depth > 60:
                scale = fov / depth
                sx = int(center_x + x1 * scale)
                sy = int(center_y + y2 * scale)
                twinkle = 0.78 + 0.30 * math.sin(t_sec * p.twinkle_speed + p.phase)
                radius = p.base_size * scale * twinkle * fade * (1.0 + 0.22 * scatter) * density_size_mod
                projected.append((z2, sx, sy, radius, scale_color(p.color, fade), "dot", None))

        for rn in ribbon_nodes:
            if rn.progress > ribbon_progress:
                continue
            dist_to_head = ribbon_progress - rn.progress
            is_head = dist_to_head < 0.035 and ribbon_progress < 0.995
            head_boost = 1.65 if is_head else 1.0

            rx = rn.x * (1.0 - scatter) + (rn.cx * cloud_spread) * scatter
            ry = rn.y * (1.0 - scatter) + (rn.cy * cloud_spread) * scatter
            rz = rn.z * (1.0 - scatter) + (rn.cz * cloud_spread) * scatter

            x1 = rx * cos_y - rz * sin_y
            z1 = rx * sin_y + rz * cos_y
            ry_shifted = ry - cam_look_y
            y2 = ry_shifted * cos_x - z1 * sin_x
            z2 = ry_shifted * sin_x + z1 * cos_x

            depth = fov + z2
            if depth > 60:
                scale = fov / depth
                sx = int(center_x + x1 * scale)
                sy = int(center_y + y2 * scale)
                pulse = 0.90 + 0.15 * math.sin(t_sec * 4.5 - rn.progress * 18.0 + rn.phase)
                radius = rn.base_size * scale * pulse * head_boost * density_size_mod
                col = (255, 255, 255) if is_head else rn.color
                projected.append((z2, sx, sy, radius, col, "ribbon", None))

        for orn in ornaments:
            if orn.y < reveal_y_limit - 15.0:
                continue
            fade = min(1.0, (orn.y - (reveal_y_limit - 15.0)) / 65.0)
            if fade <= 0.05:
                continue

            ox = orn.x * (1.0 - scatter) + (orn.cx * cloud_spread) * scatter
            oy = orn.y * (1.0 - scatter) + (orn.cy * cloud_spread) * scatter
            oz = orn.z * (1.0 - scatter) + (orn.cz * cloud_spread) * scatter

            x1 = ox * cos_y - oz * sin_y
            z1 = ox * sin_y + oz * cos_y
            oy_shifted = oy - cam_look_y
            y2 = oy_shifted * cos_x - z1 * sin_x
            z2 = oy_shifted * sin_x + z1 * cos_x

            depth = fov + z2
            if depth > 60:
                scale = fov / depth
                sx = int(center_x + x1 * scale)
                sy = int(center_y + y2 * scale)
                twinkle = 0.85 + 0.22 * math.sin(t_sec * 3.0 + orn.phase)
                radius = orn.base_size * scale * twinkle * fade * density_size_mod
                col = scale_color(orn.color, fade)
                projected.append((z2, sx, sy, radius, col, "ornament", None))

        if orbit_alpha > 0.02:
            core_fade = orbit_alpha * (1.0 - 0.75 * scatter)
            if core_fade > 0.02:
                core_y_shifted = 236.0 - cam_look_y
                core_y2 = core_y_shifted * cos_x
                core_z2 = core_y_shifted * sin_x
                if fov + core_z2 > 60:
                    core_scale = fov / (fov + core_z2)
                    core_sx = int(center_x)
                    core_sy = int(center_y + core_y2 * core_scale)
                    core_pulse = 18.0 * core_scale * (0.92 + 0.08 * math.sin(t_sec * 2.5)) * core_fade
                    projected.append(
                        (core_z2, core_sx, core_sy, core_pulse, scale_color(THEMES[theme_idx]["core"], core_fade), "planet", None)
                    )

            for tp in track_particles:
                tx0, ty0, tz0 = tp.update_and_get_pos(dt)
                tx = tx0 * (1.0 - scatter) + (tp.cx * cloud_spread) * scatter
                ty = ty0 * (1.0 - scatter) + (tp.cy * cloud_spread) * scatter
                tz = tz0 * (1.0 - scatter) + (tp.cz * cloud_spread) * scatter

                x1 = tx * cos_y - tz * sin_y
                z1 = tx * sin_y + tz * cos_y
                ty_shifted = ty - cam_look_y
                y2 = ty_shifted * cos_x - z1 * sin_x
                z2 = ty_shifted * sin_x + z1 * cos_x

                depth = fov + z2
                if depth > 60:
                    scale = fov / depth
                    sx = int(center_x + x1 * scale)
                    sy = int(center_y + y2 * scale)
                    twinkle = 0.78 + 0.30 * math.sin(t_sec * 3.5 + tp.phase)
                    radius = tp.base_size * scale * twinkle * orbit_alpha * density_size_mod
                    projected.append((z2, sx, sy, radius, scale_color(tp.color, orbit_alpha), "dot", None))

            for pl in planets:
                px0, py0, pz0 = pl.update_and_get_pos(dt)
                px = px0 * (1.0 - scatter) + (pl.cx * cloud_spread) * scatter
                py = py0 * (1.0 - scatter) + (pl.cy * cloud_spread) * scatter
                pz = pz0 * (1.0 - scatter) + (pl.cz * cloud_spread) * scatter

                x1 = px * cos_y - pz * sin_y
                z1 = px * sin_y + pz * cos_y
                py_shifted = py - cam_look_y
                y2 = py_shifted * cos_x - z1 * sin_x
                z2 = py_shifted * sin_x + z1 * cos_x

                depth = fov + z2
                if depth > 60:
                    scale = fov / depth
                    sx = int(center_x + x1 * scale)
                    sy = int(center_y + y2 * scale)
                    pulse = 0.92 + 0.10 * math.sin(t_sec * 2.8 + pl.phase)
                    radius = pl.planet_size * scale * pulse * orbit_alpha * density_size_mod
                    projected.append((z2, sx, sy, radius, scale_color(pl.color, orbit_alpha), "planet", None))

        # 只要放入了真实照片，无论是常态悬挂在圣诞树上还是散开星海均全程渲染
        if gallery.has_photos:
            for card in gallery.cards:
                if card.pop_timer > 0.0:
                    card.pop_timer = max(0.0, card.pop_timer - dt * 1.4)

                # 开场攀升阶段随灯带逐层点亮照片
                if scatter < 0.2 and card.ty0 < reveal_y_limit - 20.0:
                    continue
                tree_fade = 1.0 if scatter >= 0.2 else min(1.0, (card.ty0 - (reveal_y_limit - 20.0)) / 65.0)
                if tree_fade <= 0.05:
                    continue

                px, py, pz = card.get_3d_pos(t_sec, scatter, cloud_spread)
                x1 = px * cos_y - pz * sin_y
                z1 = px * sin_y + pz * cos_y
                py_shifted = py - cam_look_y
                y2 = py_shifted * cos_x - z1 * sin_x
                z2 = py_shifted * sin_x + z1 * cos_x

                depth = fov + z2
                if depth > 80:
                    scale = fov / depth
                    sx = int(center_x + x1 * scale)
                    sy = int(center_y + y2 * scale)
                    # 挂在树上时为精致小卡片 (0.155)，张开手掌散开星海时平滑放大 (0.29)
                    base_ratio = 0.155 + 0.135 * scatter
                    pop_boost = 1.0 + 0.42 * math.sin(card.pop_timer * math.pi) if card.pop_timer > 0 else 1.0
                    card_scale = scale * base_ratio * card.size_factor * tree_fade * pop_boost
                    projected.append((z2, sx, sy, card_scale, (255, 255, 255), "photo", card.card_surf))

        # 添加照片时的 3D 星光迸发特效粒子
        if cele_sparkles:
            for sp in cele_sparkles:
                sp.update(dt)
                if sp.life > 0:
                    x1 = sp.x * cos_y - sp.z * sin_y
                    z1 = sp.x * sin_y + sp.z * cos_y
                    py_shifted = sp.y - cam_look_y
                    y2 = py_shifted * cos_x - z1 * sin_x
                    z2 = py_shifted * sin_x + z1 * cos_x
                    depth = fov + z2
                    if depth > 60:
                        scale = fov / depth
                        sx = int(center_x + x1 * scale)
                        sy = int(center_y + y2 * scale)
                        radius = sp.size * scale * sp.life
                        projected.append((z2, sx, sy, radius, scale_color(sp.color, sp.life), "dot", None))
            cele_sparkles = [sp for sp in cele_sparkles if sp.life > 0]

        if star_alpha > 0.02:
            star_cos, star_sin = math.cos(star_rot_y), math.sin(star_rot_y)
            star_colors = THEMES[theme_idx]["star"]
            star_offset_y = -255.0
            burst_scale = 1.0 + 0.55 * star_burst

            for idx, (lx, ly, lz, base_sz, phase) in enumerate(star_pts):
                sx_rot = (lx * star_cos - lz * star_sin) * burst_scale
                sz_rot = (lx * star_sin + lz * star_cos) * burst_scale
                sy_rot = ly * burst_scale + star_offset_y - cam_look_y

                y2 = sy_rot * cos_x - sz_rot * sin_x
                z2 = sy_rot * sin_x + sz_rot * cos_x

                depth = fov + z2
                if depth > 60:
                    scale = fov / depth
                    sx = int(center_x + sx_rot * scale)
                    sy = int(center_y + y2 * scale)
                    twinkle = 0.82 + 0.32 * math.sin(t_sec * 4.5 + phase)
                    radius = base_sz * scale * twinkle * star_alpha * (1.0 + 0.4 * star_burst)
                    color = (255, 255, 255) if star_burst > 0.4 else scale_color(star_colors[idx % len(star_colors)], star_alpha)
                    projected.append((z2, sx, sy, radius, color, "dot", None))

        projected.sort(key=lambda item: item[0], reverse=True)
        for _, sx, sy, val, color, style, extra_surf in projected:
            if style == "photo" and extra_surf is not None:
                cw = max(8, int(extra_surf.get_width() * val))
                ch = max(8, int(extra_surf.get_height() * val))
                if -cw <= sx <= width + cw and -ch <= sy <= height + ch:
                    scaled_card = pygame.transform.smoothscale(extra_surf, (cw, ch))
                    screen.blit(scaled_card, (sx - cw // 2, sy - ch // 2))
            elif -50 <= sx <= width + 50 and -50 <= sy <= height + 50:
                sprite = glow_cache.get_sprite(color, val, style)
                w, h = sprite.get_size()
                screen.blit(sprite, (sx - w // 2, sy - h // 2))

        if gallery.has_photos and grabbed_surf is not None and zoom_blend > 0.02:
            sw, sh = grabbed_surf.get_size()
            aspect = sw / max(1, sh)
            max_box_w = min(width * 0.46, 480)
            max_box_h = min(height * 0.66, 520)

            if max_box_w / aspect <= max_box_h:
                base_w = max_box_w
                base_h = max_box_w / aspect
            else:
                base_h = max_box_h
                base_w = max_box_h * aspect

            anim_scale = 0.35 + 0.65 * zoom_blend
            target_w = int(base_w * anim_scale)
            target_h = int(base_h * anim_scale)

            if target_w > 10 and target_h > 10:
                glow_box = pygame.Surface((target_w + 36, target_h + 36), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_box,
                    (255, 190, 225, int(95 * zoom_blend)),
                    (0, 0, target_w + 36, target_h + 36),
                    border_radius=18,
                )
                screen.blit(glow_box, glow_box.get_rect(center=(center_x, center_y)))

                big_card = pygame.transform.smoothscale(grabbed_surf, (target_w, target_h))
                screen.blit(big_card, big_card.get_rect(center=(center_x, center_y)))

        title_size = max(28, int(44 * (height / 900.0)))
        draw_glowing_title(
            screen,
            "Merry Christmas",
            (center_x, height - int(46 * (height / 900.0))),
            title_size,
            THEMES[theme_idx]["text"],
            alpha=title_alpha,
        )

        # 按 V 键调试时显示左下角识别小窗（默认隐藏）
        if show_cam_preview and tracker.cam_enabled and tracker.preview_surface is not None:
            box_x, box_y = 22, height - 178
            pw, ph = tracker.preview_surface.get_size()
            pygame.draw.rect(screen, (255, 185, 220), (box_x - 2, box_y - 2, pw + 4, ph + 4), 2, border_radius=6)
            screen.blit(tracker.preview_surface, (box_x, box_y))

            if not intro_finished:
                label = "Intro Playing (Gestures Locked)"
            elif not tracker.ai_ready:
                label = tracker.status_msg
            else:
                pinch_hint = f"PINCH: Photo ({len(gallery.unique_surfs)})" if gallery.has_photos else "PINCH: No Photos"
                status_map = {
                    "OPEN": f"OPEN: Spread {cloud_spread:.2f}x",
                    "PINCH": pinch_hint,
                    "FIST": "FIST: Assemble Tree",
                    "NEUTRAL": "Hand Ready",
                    "NONE": f"Cam {tracker.cam_index} | Show Hand",
                }
                label = status_map.get(tracker.gesture if tracker.hand_detected else "NONE", "Show Hand")
            badge_surf = hud_font.render(label, True, (255, 225, 240))
            screen.blit(badge_surf, (box_x, box_y + ph + 6))

        pygame.display.flip()


if __name__ == "__main__":
    main()
