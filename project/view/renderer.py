# project/view/renderer.py
# FINAL — UQM spawn only (no circles/rings for ships) + glow
# UPDATED 2025-09-16: Yehat shield integration
import os
import math
import weakref
import pygame

# ---- Optional: suppress noisy "[shield]" logs without touching other files ----
import builtins as _bltins
DISABLE_SHIELD_LOG = True
_orig_print = _bltins.print
def _filtered_print(*args, **kwargs):
    if DISABLE_SHIELD_LOG and args and isinstance(args[0], str) and args[0].startswith("[shield] "):
        return
    return _orig_print(*args, **kwargs)
_bltins.print = _filtered_print


from project.model.utils import world_to_screen
from project.config import (
    ROTATION_STEP_DEGREES,
    SPAWN_PHANTOM_FADE_TIME, SPAWN_PHANTOM_MAX_ALPHA, SPAWN_PHANTOM_MIN_ALPHA,
    SPAWN_PHANTOM_OVERLAP, SPAWN_PHANTOM_ALPHA_FLOOR,
    SPAWN_PHANTOM_GLOW_PASSES, SPAWN_PHANTOM_GLOW_SCALE, SPAWN_PHANTOM_GLOW_INTENSITY, SPAWN_PHANTOM_CORE_ADD
)
from project.entities.forward_shot import ForwardShot

# ----------------------------------------------------------------------------------------------
# Paths (robust discovery)
HERE = os.path.abspath(os.path.dirname(__file__))

def _find_project_root(start_dir):
    cur = os.path.abspath(start_dir)
    for _ in range(8):  # walk up to 8 levels
        cand = os.path.join(cur, 'project')
        if os.path.isdir(cand) and os.path.isdir(os.path.join(cand, 'assets')):
            return cand
        cur = os.path.abspath(os.path.join(cur, os.pardir))
    # fallback to HERE/project if exists, else HERE
    fb = os.path.join(start_dir, 'project')
    return fb if os.path.isdir(os.path.join(fb, 'assets')) else start_dir

PROJECT_ROOT = _find_project_root(HERE)
ASSETS_ROOT = os.path.join(PROJECT_ROOT, 'assets')
SHIPS_ROOT       = os.path.join(ASSETS_ROOT, 'ships')
ASTEROIDS_ROOT   = os.path.join(ASSETS_ROOT, 'asteroids')
EFFECTS_ROOT     = os.path.join(ASSETS_ROOT, 'effects')
PLANETS_ROOT     = os.path.join(ASSETS_ROOT, 'planets')
PROJECTILES_ROOT = os.path.join(ASSETS_ROOT, 'projectiles')
print(f"[renderer] PROJECT_ROOT={PROJECT_ROOT}")
print(f"[renderer] PROJECTILES_ROOT={PROJECTILES_ROOT}")

# Ship → asset folder mapping
ASSET_KEY_MAPPING = {
    'shipa': 'cruiser',
    'shipb': 'kohr_ah',
    'shipterminator': 'yehat',
    'ship_terminator': 'yehat',
}

ANIM_TYPES = ['ship', 'missile', 'mine', 'buzzsaw', 'plasmoid', 'shield']
ZOOM_KEY = 'big'

# Storage
animations = {}
asteroid_anims = {}
planet_anims = {}
effect_defs = {}
effect_anims = {}
# [2026-03-29] Reason: fixed-location UQM Kohr-Ah buzzsaw visuals for primary projectile.
KOHRAH_BUZZSAW_FRAMES = []

# Trail behavior
TRAIL_GRACE_MS = 180
_particle_seen_tick = weakref.WeakKeyDictionary()

# ---------------------- SPAWN (UQM phantom params) ----------------------
PHANTOM_COUNT_DEFAULT = 4
PHANTOM_FADE_TIME = SPAWN_PHANTOM_FADE_TIME
PHANTOM_ALPHA_MAX = SPAWN_PHANTOM_MAX_ALPHA
PHANTOM_ALPHA_MIN = SPAWN_PHANTOM_MIN_ALPHA

def _ease_out_cubic(x: float) -> float:
    x = 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
    return 1 - (1 - x) ** 3


# ---------------- .ani readers ----------------
def _parse_simple_ani(ani_path: str):
    frames = []
    try:
        with open(ani_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                img_path = os.path.join(os.path.dirname(ani_path), parts[0])
                if not os.path.isfile(img_path):
                    continue
                surf = pygame.image.load(img_path)
                try:
                    surf = surf.convert_alpha()
                except Exception:
                    pass
                frames.append(surf)
    except Exception as e:
        print(f"[Renderer] ERROR parsing ani {ani_path}: {e}")
    return {'frames': frames, 'frame_count': len(frames)}


def _parse_shield_body_ani(ani_path: str):
    frames = []
    try:
        with open(ani_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts or parts[0].startswith('#'):
                    continue
                img_path = os.path.join(os.path.dirname(ani_path), parts[0])
                if os.path.isfile(img_path):
                    surf = pygame.image.load(img_path)
                    try:
                        surf = surf.convert_alpha()
                    except Exception:
                        pass
                    frames.append(surf)
    except Exception as e:
        print(f"[Renderer] ERROR parsing shield ani {ani_path}: {e}")
    return frames


def _parse_blast_ani(ani_path: str):
    groups = {0: [], 1: [], 2: [], 3: []}
    max_i = -1
    try:
        with open(ani_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                if len(parts) < 5:
                    png, dx, dy, g = parts[0], 0, 0, 0
                    i = len(groups[g])
                else:
                    png, dx, dy, g, i = parts[0], int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                img_path = os.path.join(os.path.dirname(ani_path), png)
                if not os.path.isfile(img_path):
                    continue
                surf = pygame.image.load(img_path)
                try:
                    surf = surf.convert_alpha()
                except Exception:
                    pass
                entry = {'img': surf, 'dx': dx, 'dy': dy}
                lst = groups.get(g, groups[0])
                while len(lst) <= i:
                    lst.append(None)
                lst[i] = entry
                max_i = max(max_i, i)
    except Exception as e:
        print(f"[Renderer] ERROR parsing blast ani {ani_path}: {e}")
    for g in groups:
        seq = groups[g]
        last = None
        for idx, val in enumerate(seq):
            if val is None:
                seq[idx] = last
            else:
                last = val
        groups[g] = [fr for fr in seq if fr is not None]
    return {'groups': groups, 'frame_count': max(0, max_i + 1)}


# ---------------- Loaders ----------------
def load_ship_animations():
    if not os.path.isdir(SHIPS_ROOT):
        print(f"[Renderer] WARNING: ships dir not found: {SHIPS_ROOT}")
        return
    for cls_name, folder in ASSET_KEY_MAPPING.items():
        ship_dir = os.path.join(SHIPS_ROOT, folder)
        if not os.path.isdir(ship_dir):
            print(f"[Renderer] WARNING: no assets for '{cls_name}' in {ship_dir}")
            continue
        animations.setdefault(folder, {})
        for fname in sorted(os.listdir(ship_dir)):
            if not fname.lower().endswith(f"-{ZOOM_KEY}.ani"):
                continue
            base = fname[:-4]
            parts = base.rsplit('-', 1)
            if len(parts) != 2:
                continue
            anim_name, _ = parts
            key = anim_name if anim_name in ANIM_TYPES else 'ship'
            frames = []
            ani_path = os.path.join(ship_dir, fname)
            with open(ani_path, 'r', encoding='utf-8') as f:
                for line in f:
                    img_file = line.strip().split()[0]
                    img_path = os.path.join(ship_dir, img_file)
                    if os.path.isfile(img_path):
                        surf = pygame.image.load(img_path)
                        try:
                            surf = surf.convert_alpha()
                        except Exception:
                            pass
                        frames.append(surf)
            animations[folder][key] = frames

def _load_projectile_animations():
    if not os.path.isdir(PROJECTILES_ROOT):
        print(f"[Renderer] WARNING: projectiles dir not found: {PROJECTILES_ROOT}")
        return
    for cls_name, folder in ASSET_KEY_MAPPING.items():
        proj_dir_name = 'ship_terminator' if cls_name == 'shipterminator' else cls_name
        proj_dir = os.path.join(PROJECTILES_ROOT, proj_dir_name)
        if not os.path.isdir(proj_dir):
            continue
        animations.setdefault(folder, {})['missile'] = []
        ani_file = os.path.join(proj_dir, 'missile-big.ani')
        if os.path.isfile(ani_file):
            with open(ani_file, 'r', encoding='utf-8') as f_ani:
                for l in f_ani:
                    img = l.strip().split()[0]
                    img_path = os.path.join(proj_dir, img)
                    if os.path.isfile(img_path):
                        surf = pygame.image.load(img_path)
                        try:
                            surf = surf.convert_alpha()
                        except Exception:
                            pass
                        animations[folder]['missile'].append(surf)


def _load_kohrah_buzzsaw_frames():
    # [2026-03-29] Reason: load original UQM buzzsaw sequence from fixed shared asset folder.
    buzzsaw_dir = os.path.join(PROJECTILES_ROOT, 'kohrah_buzzsaw')
    names = [f"buzzsaw-big-00{i}.png" for i in range(8)]
    KOHRAH_BUZZSAW_FRAMES.clear()
    for name in names:
        img_path = os.path.join(buzzsaw_dir, name)
        if not os.path.isfile(img_path):
            continue
        surf = pygame.image.load(img_path)
        try:
            surf = surf.convert_alpha()
        except Exception:
            pass
        KOHRAH_BUZZSAW_FRAMES.append(surf)
    if KOHRAH_BUZZSAW_FRAMES:
        animations.setdefault('kohr_ah', {})['buzzsaw'] = KOHRAH_BUZZSAW_FRAMES
    print(f"[projectiles] kohr-ah buzzsaw loaded: {len(KOHRAH_BUZZSAW_FRAMES)} frames from {buzzsaw_dir}")


# NEW 2025-09-16: load Yehat shield body frames from projectiles folder
def _load_shield_animations():
    if not os.path.isdir(PROJECTILES_ROOT):
        return
    proj_dir = os.path.join(PROJECTILES_ROOT, 'ship_terminator')
    if not os.path.isdir(proj_dir):
        print(f"[shield-assets] WARN: no dir {proj_dir}")
        return
    ani_path = os.path.join(proj_dir, 'shield-big.ani')
    if not os.path.isfile(ani_path):
        print(f"[shield-assets] WARN: no shield-big.ani at {ani_path}")
        return
    frames = _parse_shield_body_ani(ani_path)
    animations.setdefault('yehat', {})['shield'] = frames
    print(f"[shield-assets] yehat frames: {len(frames)} from {ani_path}")


def load_asteroid_animations():
    if not os.path.isdir(ASTEROIDS_ROOT):
        print(f"[Renderer] WARNING: asteroids dir not found: {ASTEROIDS_ROOT}")
        return
    for fname in sorted(os.listdir(ASTEROIDS_ROOT)):
        if not fname.lower().endswith(f"-{ZOOM_KEY}.ani"):
            continue
        base = fname[:-4]
        parts = base.rsplit('-', 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        frames = []
        ani_path = os.path.join(ASTEROIDS_ROOT, fname)
        with open(ani_path, 'r', encoding='utf-8') as f:
            for line in f:
                img_file = line.strip().split()[0]
                img_path = os.path.join(ASTEROIDS_ROOT, img_file)
                if os.path.isfile(img_path):
                    surf = pygame.image.load(img_path)
                    try:
                        surf = surf.convert_alpha()
                    except Exception:
                        pass
                    frames.append(surf)
        if len(frames) > 4:
            rotate_frames = frames[:-4][:16]
            asteroid_anims[key] = {'rotate': rotate_frames, 'destroy': frames[-4:]}
        else:
            asteroid_anims[key] = {'rotate': frames, 'destroy': []}


def _load_effects_for_shipkey(ship_key: str):
    base_dir = os.path.join(EFFECTS_ROOT, ship_key)
    if not os.path.isdir(base_dir):
        base_dir = os.path.join(EFFECTS_ROOT, "default")
    defs = {}
    blast_ani = os.path.join(base_dir, "blast-med.ani")
    boom_ani = os.path.join(base_dir, "boom-big.ani")
    if os.path.isfile(blast_ani):
        defs['blast'] = _parse_blast_ani(blast_ani)
    if os.path.isfile(boom_ani):
        defs['boom'] = _parse_simple_ani(boom_ani)
    return defs


def load_effects_animations():
    effect_defs['default'] = _load_effects_for_shipkey("default")
    for folder in set(ASSET_KEY_MAPPING.values()):
        effect_defs[folder] = _load_effects_for_shipkey(folder)
    bl = effect_defs.get('default', {}).get('blast')
    if bl:
        frames = [entry['img'] for entry in bl['groups'].get(0, []) if entry]
        if frames:
            effect_anims['blast'] = frames
    for k, defs in effect_defs.items():
        _ = defs.get('blast'), defs.get('boom')


# ---------------- PLANETS (big-only) ----------------
def _discover_planets_big_only():
    out = {}
    if not os.path.isdir(PLANETS_ROOT):
        return out
    for fname in os.listdir(PLANETS_ROOT):
        if not fname.endswith("-big.ani"):
            continue
        skin = fname[:-8]
        out[skin] = os.path.join(PLANETS_ROOT, fname)
    return out


def load_planet_animations():
    found = _discover_planets_big_only()
    for skin, ani_path in found.items():
        meta = _parse_simple_ani(ani_path)
        planet_anims.setdefault(skin, {})['big'] = meta.get('frames', [])

# ---------------- helpers ----------------
def _scale_surface(surf, zoom):
    w, h = surf.get_size()
    sw, sh = int(w * zoom), int(h * zoom)
    try:
        return pygame.transform.smoothscale(surf, (max(1, sw), max(1, sh)))
    except Exception:
        return pygame.transform.scale(surf, (max(1, sw), max(1, sh)))


def _tint_red_with_alpha(surface: pygame.Surface, alpha: int) -> pygame.Surface:
    s = surface.copy()
    try:
        s.fill((255, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        a = max(0, min(255, int(alpha)))
        s.fill((255, 255, 255, a), special_flags=pygame.BLEND_RGBA_MULT)
    except Exception:
        s.set_alpha(max(0, min(255, int(alpha))))
    return s


# ---------------- draw: planet ----------------
def draw_planet(screen, planet, cam, zoom):
    sx, sy = world_to_screen(planet.x, planet.y, cam.x, cam.y, zoom)
    if not planet_anims:
        pygame.draw.circle(screen, planet.color, (int(sx), int(sy)), max(1, int(planet.radius * zoom)))
        return
    if not hasattr(planet, "_skin") or planet._skin not in planet_anims:
        import random
        skins = [k for k, v in planet_anims.items() if v.get('big')]
        if not skins:
            pygame.draw.circle(screen, planet.color, (int(sx), int(sy)), max(1, int(planet.radius * zoom)))
            return
        planet._skin = random.choice(skins)
        planet._t0 = pygame.time.get_ticks()
    frames = planet_anims.get(planet._skin, {}).get('big', [])
    if not frames:
        pygame.draw.circle(screen, planet.color, (int(sx), int(sy)), max(1, int(planet.radius * zoom)))
        return
    elapsed = (pygame.time.get_ticks() - getattr(planet, "_t0", 0)) / 1000.0
    idx = int(elapsed / (1.0 / 12.0)) % len(frames)
    img = frames[idx]
    diameter = max(1, int(2 * planet.radius * zoom))
    try:
        img_s = pygame.transform.smoothscale(img, (diameter, diameter))
    except Exception:
        img_s = pygame.transform.scale(img, (diameter, diameter))
    screen.blit(img_s, (int(sx - img_s.get_width() / 2), int(sy - img_s.get_height() / 2)))


# ---------------- draw: asteroid ----------------
def draw_asteroid(screen, asteroid, cam, zoom):
    anim = asteroid_anims.get('asteroid')
    if anim:
        if getattr(asteroid, 'is_destroying', False):
            frames = anim['destroy']
            idx = getattr(asteroid, 'destroy_frame_index', 0)
            if 0 <= idx < len(frames):
                img = frames[idx]
                img_s = _scale_surface(img, zoom)
                w, h = img_s.get_size()
                sx, sy = world_to_screen(asteroid.x, asteroid.y, cam.x, cam.y, zoom)
                screen.blit(img_s, (sx - w / 2, sy - h / 2))
            return
        frames = anim.get('rotate', [])
        if frames:
            idx = int((asteroid.angle % 360) / 360 * len(frames))
            img = frames[idx]
            img_s = _scale_surface(img, zoom)
            w, h = img_s.get_size()
            sx, sy = world_to_screen(asteroid.x, asteroid.y, cam.x, cam.y, zoom)
            screen.blit(img_s, (sx - w / 2, sy - h / 2))
            return
    ax, ay = world_to_screen(asteroid.x, asteroid.y, cam.x, cam.y, zoom)
    half = asteroid.radius * zoom
    rad = math.radians(asteroid.angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    pts = [(ax + dx * cos_a - dy * sin_a, ay + dx * sin_a + dy * cos_a)
           for dx, dy in [(-half, -half), (half, -half), (half, half), (-half, half)]]
    pygame.draw.polygon(screen, asteroid.color, pts)


# ---------------- draw: ship ----------------
def draw_ship(screen, ship, cam, zoom):
    sx, sy = world_to_screen(ship.x, ship.y, cam.x, cam.y, zoom)
    now = pygame.time.get_ticks()

    # Track last engine-on time (для трейла)
    if getattr(ship, "engine_on", False) or getattr(ship, "thrust", False) or getattr(ship, "accelerating", False):
        ship._engine_last_on = now
    last_on = getattr(ship, "_engine_last_on", 0)

    # Exhaust trail (particles only)
    if hasattr(ship, "particles") and ship.particles:
        cutoff = last_on + TRAIL_GRACE_MS
        for p in ship.particles:
            if hasattr(p, "birth_time") and p.birth_time is not None:
                p_birth = int(p.birth_time)
            else:
                if p not in _particle_seen_tick:
                    _particle_seen_tick[p] = now
                p_birth = _particle_seen_tick.get(p, now)
            if not (getattr(ship, "engine_on", False) or getattr(ship, "thrust", False) or getattr(ship, "accelerating", False)):
                if p_birth > cutoff:
                    continue
            try:
                alpha = int(max(0, min(255, p.alpha())))
            except Exception:
                alpha = 128
            if alpha <= 0:
                continue
            sx_p, sy_p = world_to_screen(p.x, p.y, cam.x, cam.y, zoom)
            size = max(1, int(getattr(p, "size", 2) * zoom))
            point_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            color = getattr(p, "color", (255, 140, 0))
            r, g, b = color[:3] if isinstance(color, (list, tuple)) else (255, 140, 0)
            point_surf.fill((r, g, b, alpha))
            screen.blit(point_surf, (int(sx_p - size / 2), int(sy_p - size / 2)))

    # Ship body frames
    cls = ship.__class__.__name__.lower()
    folder = ASSET_KEY_MAPPING.get(cls) or getattr(ship, 'asset_key', None)
    if folder is None and animations:
        try:
            folder = next(iter(animations.keys()))
        except Exception:
            folder = None

    frames_ship = animations.get(folder, {}).get('ship') if folder else None
    frames_shield = animations.get(folder, {}).get('shield') if folder else None
    use_shield = bool(getattr(ship, 'shield_active', False) and frames_shield)

    if use_shield:
        print(f"[draw] ShipTerminator shield_on=True ship_frames={len(frames_ship) if frames_ship else 0} shield_frames={len(frames_shield)} using=shield")
    else:
        if getattr(ship, 'shield_active', False) and not frames_shield:
            print("[draw] WARN: shield_active but no shield frames loaded for folder:", folder)

    frames = frames_shield if use_shield else frames_ship

    # UQM-style phantom spawn
    supports_uqm = (
        hasattr(ship, "is_spawning") and
        hasattr(ship, "spawn_timer") and
        hasattr(ship, "warp_entry_dir") and
        hasattr(ship, "spawn_phantom_offsets")
    )

    if supports_uqm and getattr(ship, "is_spawning", False):
        if frames:
            if not hasattr(ship, "_spawn_total"):
                ship._spawn_total = max(0.01, float(getattr(ship, "spawn_timer", 0.6)))
            t_total = max(0.01, float(getattr(ship, "_spawn_total", 0.6)))
            t_passed = t_total - float(getattr(ship, "spawn_timer", 0.0))
            phantom_count = max(1, len(getattr(ship, "spawn_phantom_offsets", [])) or PHANTOM_COUNT_DEFAULT)
            step = t_total / phantom_count
            dx, dy = getattr(ship, "warp_entry_dir", (0.0, 1.0))

            for idx_off, off in enumerate(getattr(ship, "spawn_phantom_offsets", [])):
                off *= SPAWN_PHANTOM_OVERLAP
                t_birth = step * idx_off
                if t_passed < t_birth:
                    continue
                life = PHANTOM_FADE_TIME
                age = t_passed - t_birth
                fade = 1.0 - max(0.0, min(1.0, age / life))
                if fade <= 0.0:
                    continue
                k_dist = 1.0 - (idx_off / max(1, phantom_count - 1)) if phantom_count > 1 else 1.0
                a_max = PHANTOM_ALPHA_MIN + (PHANTOM_ALPHA_MAX - PHANTOM_ALPHA_MIN) * k_dist
                alpha = int(a_max * fade)
                if alpha < SPAWN_PHANTOM_ALPHA_FLOOR:
                    alpha = SPAWN_PHANTOM_ALPHA_FLOOR

                wx = ship.x + dx * off
                wy = ship.y + dy * off
                fx, fy = world_to_screen(wx, wy, cam.x, cam.y, zoom)

                idx = int(ship.angle / ROTATION_STEP_DEGREES) % len(frames)
                img = frames[idx]
                img_s = _scale_surface(img, zoom)

                halo_alpha = int(alpha * SPAWN_PHANTOM_GLOW_INTENSITY)
                if halo_alpha < SPAWN_PHANTOM_ALPHA_FLOOR:
                    halo_alpha = SPAWN_PHANTOM_ALPHA_FLOOR
                img_halo = _tint_red_with_alpha(img_s, halo_alpha)
                try:
                    img_halo = img_halo.convert_alpha()
                except Exception:
                    try: img_halo = img_halo.convert()
                    except Exception: pass
                try:
                    scale = float(SPAWN_PHANTOM_GLOW_SCALE)
                except Exception:
                    scale = 1.12
                if scale != 1.0:
                    w0, h0 = img_halo.get_size()
                    try:
                        img_halo = pygame.transform.smoothscale(img_halo, (max(1, int(w0 * scale)), max(1, int(h0 * scale))))
                    except Exception:
                        img_halo = pygame.transform.scale(img_halo, (max(1, int(w0 * scale)), max(1, int(h0 * scale))))
                w_h, h_h = img_halo.get_size()
                passes = max(0, int(SPAWN_PHANTOM_GLOW_PASSES))
                for _ in range(passes):
                    screen.blit(img_halo, (int(fx - w_h / 2), int(fy - h_h / 2)), special_flags=pygame.BLEND_ADD)

                img_core = _tint_red_with_alpha(img_s, alpha)
                try:
                    img_core = img_core.convert_alpha()
                except Exception:
                    pass
                w, h = img_core.get_size()
                if SPAWN_PHANTOM_CORE_ADD:
                    screen.blit(img_core, (int(fx - w / 2), int(fy - h / 2)), special_flags=pygame.BLEND_ADD)
                else:
                    screen.blit(img_core, (int(fx - w / 2), int(fy - h / 2)))
        return

    # Normal ship draw
    if frames:
        idx = int(ship.angle / ROTATION_STEP_DEGREES) % len(frames)
        img = frames[idx]
        img_s = _scale_surface(img, zoom)
        w, h = img_s.get_size()
        screen.blit(img_s, (int(sx - w / 2), int(sy - h / 2)))

    for tx, ty, _ in getattr(ship, 'active_lasers', []):
        ex, ey = world_to_screen(tx, ty, cam.x, cam.y, zoom)
        pygame.draw.line(screen, (255, 0, 0), (int(sx), int(sy)), (int(ex), int(ey)), 2)

# ---------------- draw: generic projectile ----------------
def draw_projectile(screen, proj, cam, zoom):
    def _is_missile_like(o):
        name = o.__class__.__name__.lower() if hasattr(o, '__class__') else ''
        if name in ('missile', 'cruisermissile'):
            return True
        return hasattr(o, 'launch_time') and hasattr(o, 'vx') and hasattr(o, 'vy') and hasattr(o, 'radius')
    if isinstance(proj, ForwardShot) or _is_missile_like(proj):
        draw_missile(screen, proj, cam, zoom)
        return
    sx, sy = world_to_screen(proj.x, proj.y, cam.x, cam.y, zoom)
    pygame.draw.circle(screen, (255,255,255), (int(sx), int(sy)), max(1, int(getattr(proj, 'radius', 2) * zoom)))


# ---------------- draw: missile ----------------
def draw_missile(screen, missile, cam, zoom):
    sx, sy = world_to_screen(missile.x, missile.y, cam.x, cam.y, zoom)
    cls = missile.owner.__class__.__name__.lower() if getattr(missile, 'owner', None) else ''
    folder = ASSET_KEY_MAPPING.get(cls)
    frames = animations.get(folder, {}).get('missile') if folder else None

    if folder == 'cruiser' and frames and len(frames) >= 16:
        if getattr(missile, 'exploding', False):
            age = float(getattr(missile, 'explosion_age', 0.0))
            fps = float(getattr(missile, 'explosion_fps', 14.0))
            idx = int(age * fps)
            seq = frames[16:25]
            if idx >= len(seq):
                missile.active = False
                return
            img = seq[idx]
        else:
            idx = getattr(missile, 'frame_index', 0) % 16
            img = frames[idx]

        img_s = _scale_surface(img, zoom)
        w, h = img_s.get_size()
        screen.blit(img_s, (int(sx - w/2), int(sy - h/2)))
        return

    # fallback
    if frames:
        idx = getattr(missile, 'frame_index', 0) % len(frames)
        img = frames[idx]
        img_s = _scale_surface(img, zoom)
        w, h = img_s.get_size()
        screen.blit(img_s, (int(sx - w/2), int(sy - h/2)))
    else:
        pygame.draw.circle(screen, (255,255,0), (int(sx), int(sy)),
                           max(1, int(getattr(missile, 'radius', 2) * zoom)))


# ---------------- draw: mine ----------------
def draw_mine(screen, mine, cam, zoom):
    sx, sy = world_to_screen(mine.x, mine.y, cam.x, cam.y, zoom)
    cls = mine.owner.__class__.__name__.lower() if getattr(mine, 'owner', None) else ''
    folder = ASSET_KEY_MAPPING.get(cls)
    # [2026-03-29] Reason: prefer fixed Kohr-Ah buzzsaw frames; fallback to existing ship-linked mine animation.
    fixed_buzzsaw = KOHRAH_BUZZSAW_FRAMES if cls == 'shipb' and KOHRAH_BUZZSAW_FRAMES else None
    key = 'buzzsaw' if folder and 'buzzsaw' in animations.get(folder, {}) else 'mine'
    frames = fixed_buzzsaw or (animations.get(folder, {}).get(key) if folder else None)
    if frames:
        # [2026-03-29] Reason: animate spinning by time, and run one-shot sequence while mine is dying.
        anim_time = float(getattr(mine, 'anim_time', 0.0))
        anim_fps = 24.0
        if getattr(mine, 'state', '') == 'dying':
            idx = min(len(frames) - 1, int(anim_time * anim_fps))
        else:
            idx = int(anim_time * anim_fps) % len(frames)
        img = frames[idx]
        img_s = _scale_surface(img, zoom)
        w, h = img_s.get_size()
        screen.blit(img_s, (int(sx - w / 2), int(sy - h / 2)))
    else:
        pygame.draw.circle(screen, (255, 0, 0), (int(sx), int(sy)), max(1, int(getattr(mine, 'radius', 3) * zoom)))


# ---------------- draw: plasmoid ----------------
def draw_plasmoid(screen, plasmoid, cam, zoom):
    sx, sy = world_to_screen(plasmoid.x, plasmoid.y, cam.x, cam.y, zoom)
    cls = plasmoid.owner.__class__.__name__.lower() if getattr(plasmoid, 'owner', None) else ''
    folder = ASSET_KEY_MAPPING.get(cls)
    key = 'shield' if folder and 'shield' in animations.get(folder, {}) else 'plasmoid'
    frames = animations.get(folder, {}).get(key) if folder else None
    if frames:
        angle = math.degrees(math.atan2(getattr(plasmoid, 'vy', 0.0), getattr(plasmoid, 'vx', 0.0)))
        idx = int((angle % 360) / ROTATION_STEP_DEGREES) % len(frames)
        img = frames[idx]
        img_s = _scale_surface(img, zoom)
        w, h = img_s.get_size()
        screen.blit(img_s, (int(sx - w / 2), int(sy - h / 2)))
    else:
        pygame.draw.circle(screen, (0, 255, 255), (int(sx), int(sy)),
                           max(1, int(getattr(plasmoid, 'radius', 3) * zoom)))


# ---------------- draw: effect ----------------
def draw_effect(screen, eff, cam, zoom):
    sx, sy = world_to_screen(eff.x, eff.y, cam.x, cam.y, zoom)
    ship_key = eff.ship_key if getattr(eff, 'ship_key', None) in effect_defs else 'default'
    defs = effect_defs.get(ship_key) or effect_defs.get('default') or {}

    if eff.key == 'blast':
        bl = defs.get('blast')
        if not bl:
            rad = max(2, int(4 * zoom))
            pygame.draw.circle(screen, (255, 230, 160), (int(sx), int(sy)), rad)
            pygame.draw.circle(screen, (255, 120, 0), (int(sx), int(sy)), max(1, rad // 2))
            eff.active = (eff.age < 0.3)
            return
        idx = int(eff.age / getattr(eff, 'frame_time', 0.05))
        idx = min(idx, max(0, bl['frame_count'] - 1))
        group = getattr(eff, "group", 0) % 4
        frames = bl['groups'].get(group, [])
        if not frames:
            rad = max(2, int(4 * zoom))
            pygame.draw.circle(screen, (255, 230, 160), (int(sx), int(sy)), rad)
            pygame.draw.circle(screen, (255, 120, 0), (int(sx), int(sy)), max(1, rad // 2))
            eff.active = (eff.age < 0.3)
            return
        entry = frames[idx] if idx < len(frames) else frames[-1]
        img = entry['img']
        if hasattr(eff, 'angle') and eff.angle is not None:
            try:
                img = pygame.transform.rotate(img, -eff.angle)
            except Exception:
                pass
        img_s = _scale_surface(img, zoom)
        if getattr(eff, "use_offsets", False):
            ox = int(entry['dx'] * zoom)
            oy = int(entry['dy'] * zoom)
        else:
            ox = oy = 0
        screen.blit(img_s, (int(sx - img_s.get_width() / 2 + ox), int(sy - img_s.get_height() / 2 + oy)))
        if eff.age >= getattr(eff, 'frame_time', 0.05) * max(1, bl['frame_count']):
            eff.active = False

    elif eff.key == 'boom':
        bm = defs.get('boom')
        if not bm:
            life = max(1, int(getattr(eff, 'loops', 1))) * 0.7
            t = (eff.age % 0.7) / 0.7
            rr = max(8, int((10 + 20 * t) * zoom))
            pygame.draw.circle(screen, (255, 180, 0), (int(sx), int(sy)), rr, 2)
            eff.active = (eff.age < life)
            return
        frames = bm.get('frames', [])
        if not frames:
            return
        loops = max(1, int(getattr(eff, "loops", 1)))
        total = len(frames) * loops
        idx_total = int(eff.age / getattr(eff, 'frame_time', 0.06))
        if idx_total >= total:
            eff.active = False
            idx_total = total - 1
        idx = idx_total % len(frames)
        img_s = _scale_surface(frames[idx], zoom)
        screen.blit(img_s, (int(sx - img_s.get_width() / 2), int(sy - img_s.get_height() / 2)))

def _load_cruiser_saturn_human():
    human_dir = os.path.join(PROJECTILES_ROOT, 'human')
    ani = os.path.join(human_dir, 'saturn-big.ani')
    if not (os.path.isdir(human_dir) and os.path.isfile(ani)):
        print(f"[projectiles] WARN: saturn not found at {ani}")
        return
    frames = []
    try:
        with open(ani, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                img = parts[0]
                img_path = os.path.join(human_dir, img)
                if os.path.isfile(img_path):
                    surf = pygame.image.load(img_path)
                    try:
                        surf = surf.convert_alpha()
                    except Exception:
                        pass
                    frames.append(surf)
    except Exception as e:
        print(f"[projectiles] ERROR reading {ani}: {e}")
        return
    animations.setdefault('cruiser', {})['missile'] = frames
    print(f"[projectiles] cruiser/saturn loaded: {len(frames)} frames from {ani}")


# ----------------------------------------------------------------------------------------------
# Load assets on import
load_ship_animations()
_load_projectile_animations()
_load_cruiser_saturn_human()
_load_shield_animations()  # NEW 2025-09-16
_load_kohrah_buzzsaw_frames()  # [2026-03-29] Reason: fixed folder override for Kohr-Ah primary buzzsaw frames.
load_asteroid_animations()
load_effects_animations()
load_planet_animations()
