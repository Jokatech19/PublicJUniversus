# Juniversus_public.py
# JUniversus — Public Simulator: official vs community players
# - Differentiates official players (protected) from community-created players
# - Community players are tier-capped to B
# - Adds Multisport Best-of-5 match mode (first to 3 sports wins)
# - Players limited to playing at most 2 sports in a Multisport match (encourages collecting)
# - Adds a simple avatar canvas showing player initials and sport icon during play

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import random, time, threading, json, os, datetime

# ---------------------------
# Files: official roster (protected) and community players (editable)
# ---------------------------
OFFICIAL_PLAYERS_FILE = "official_players.json"
PLAYERS_FILE = "players.json"   # community players

# ---------------------------
# Tier system & ranges
# ---------------------------
TIER_RANGES = {
    "D": (1, 4),
    "B": (5, 7),
    "A": (7, 9),
    "S": (9, 10)
}
TIER_ORDER = ["D", "B", "A", "S"]

def stat_value_within_tier(tier):
    lo, hi = TIER_RANGES.get(tier, (1, 10))
    return random.randint(lo, hi)

def tier_index_of(tier):
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 1  # default B

def tier_up(tier):
    idx = tier_index_of(tier)
    if idx < len(TIER_ORDER)-1:
        return TIER_ORDER[idx+1]
    return tier

def tier_down(tier):
    idx = tier_index_of(tier)
    if idx > 0:
        return TIER_ORDER[idx-1]
    return tier

# ---------------------------
# Stats & specializations
# ---------------------------
STAT_KEYS = ["power", "speed", "stamina", "accuracy", "defense", "clutch", "teamwork"]

WEIGHT_CLASSES = ["Flyweight", "Lightweight", "Middleweight", "Light-Heavy", "Heavyweight"]
WEIGHT_CLASS_MOD = {
    "Flyweight": 0.95,
    "Lightweight": 0.98,
    "Middleweight": 1.00,
    "Light-Heavy": 1.03,
    "Heavyweight": 1.06
}

SPECIALIZATIONS = {
    "Playmaker": {"boost": {"teamwork": 0.12, "accuracy": 0.06}, "favored_sports": ["Basketball", "Soccer", "Tennis"]},
    "Sniper":    {"boost": {"accuracy": 0.15, "clutch": 0.06}, "favored_sports": ["Basketball", "Tennis", "Soccer"]},
    "Defender":  {"boost": {"defense": 0.15, "stamina": 0.06}, "favored_sports": ["Wrestling", "Boxing", "Soccer"]},
    "Powerhouse":{"boost": {"power": 0.18, "stamina": 0.05}, "favored_sports": ["Boxing", "Wrestling", "Basketball"]},
    "Speedster": {"boost": {"speed": 0.18, "clutch": 0.04}, "favored_sports": ["Tennis", "Soccer", "Basketball"]},
    "Balanced":  {"boost": {}, "favored_sports": ["Basketball","Boxing","Tennis","Wrestling","Soccer"]}
}

def choose_specialization_from_tiers(tiers_map):
    rank_map = {k: tier_index_of(tiers_map.get(k, "B")) for k in STAT_KEYS}
    max_rank = max(rank_map.values())
    top_stats = [k for k,v in rank_map.items() if v == max_rank]
    if "teamwork" in top_stats: return "Playmaker"
    if "accuracy" in top_stats and "clutch" in top_stats: return "Sniper"
    if "defense" in top_stats or "stamina" in top_stats: return "Defender"
    if "power" in top_stats: return "Powerhouse"
    if "speed" in top_stats: return "Speedster"
    return "Balanced"

def apply_specialization_modifier(name, base_stats, sport_name):
    p = merged_roster.get(name, {})  # merged_roster includes official + community
    spec = p.get("specialization", "Balanced")
    cfg = SPECIALIZATIONS.get(spec, {})
    boosts = cfg.get("boost", {})
    favored = cfg.get("favored_sports", [])
    mod_stats = base_stats.copy()
    for k in STAT_KEYS:
        val = mod_stats.get(k, 0)
        boost = boosts.get(k, 0)
        if sport_name in favored:
            val = int(round(val * (1 + boost)))
        else:
            val = int(round(val * (1 + boost * 0.45)))
        mod_stats[k] = max(1, min(10, val))
    return mod_stats

# ---------------------------
# Helper: create player dict from tier profile
# Each player record structure:
# {
#   "tiers": {...}, "stats": {...}, "weight_class": str,
#   "specialization": str, "official": bool
# }
# ---------------------------
def make_player_from_profile(profile_tiers, wc="Middleweight", official=False):
    tiers_map = {k: profile_tiers.get(k, "B") for k in STAT_KEYS}
    stats = {k: stat_value_within_tier(tiers_map[k]) for k in STAT_KEYS}
    spec = choose_specialization_from_tiers(tiers_map)
    return {"tiers": tiers_map, "stats": stats, "weight_class": wc, "specialization": spec, "official": official}

# ---------------------------
# Default official players (used to seed official file if missing)
# ---------------------------
DEFAULT_PLAYERS = {
    "LeBron James": make_player_from_profile({"power":"A","speed":"A","stamina":"S","accuracy":"A","defense":"A","clutch":"S","teamwork":"S"}, "Heavyweight", official=True),
    "Michael Jordan": make_player_from_profile({"power":"S","speed":"S","stamina":"A","accuracy":"S","defense":"A","clutch":"S","teamwork":"A"}, "Lightweight", official=True),
    "Kobe Bryant": make_player_from_profile({"power":"A","speed":"A","stamina":"A","accuracy":"S","defense":"A","clutch":"S","teamwork":"B"}, "Lightweight", official=True),
    "Muhammad Ali": make_player_from_profile({"power":"A","speed":"S","stamina":"S","accuracy":"A","defense":"A","clutch":"A","teamwork":"B"}, "Middleweight", official=True),
    "Mike Tyson": make_player_from_profile({"power":"S","speed":"A","stamina":"B","accuracy":"A","defense":"B","clutch":"B","teamwork":"D"}, "Light-Heavy", official=True),
    "Roger Federer": make_player_from_profile({"power":"B","speed":"A","stamina":"S","accuracy":"S","defense":"A","clutch":"A","teamwork":"B"}, "Lightweight", official=True),
    "Rafael Nadal": make_player_from_profile({"power":"A","speed":"A","stamina":"S","accuracy":"A","defense":"A","clutch":"S","teamwork":"B"}, "Lightweight", official=True),
    "Novak Djokovic": make_player_from_profile({"power":"A","speed":"A","stamina":"S","accuracy":"S","defense":"S","clutch":"A","teamwork":"B"}, "Lightweight", official=True),
    "Shaq": make_player_from_profile({"power":"S","speed":"D","stamina":"D","accuracy":"D","defense":"A","clutch":"B","teamwork":"A"}, "Heavyweight", official=True),
    "Stephen Curry": make_player_from_profile({"power":"D","speed":"A","stamina":"A","accuracy":"S","defense":"B","clutch":"A","teamwork":"B"}, "Lightweight", official=True),
    "Generic Star": make_player_from_profile({"power":"B","speed":"B","stamina":"B","accuracy":"B","defense":"B","clutch":"B","teamwork":"B"}, "Middleweight", official=True)
}

# ---------------------------
# Sports definitions
# (same as before; Soccer included)
# ---------------------------
sports = {
    "Basketball": {
        "icon": "🏀", "type": "team", "team_size": 5,
        "weights": {"power":0.30,"defense":0.25,"accuracy":0.15,"stamina":0.15,"clutch":0.10,"teamwork":0.05},
        "narratives": [
            "{p1} isolates, sizes up the defender and knocks down a mid-range jumper — pure footwork.",
            "{p2} drives baseline and finishes with a tomahawk dunk off the glass!",
            "{p1} calls for the pick-and-roll: the roller slips to the rim for an easy layup."
        ]
    },
    "Boxing": {
        "icon": "🥊", "type": "duel",
        "rounds_default": 12, "rounds_options":[4,8,10,12],
        "weights": {"power":0.40,"defense":0.25,"stamina":0.25,"accuracy":0.10},
        "narratives":[
            "{p1} opens with a probing jab — testing range and timing.",
            "{p2} feints low then lands a sharp counter right hand."
        ]
    },
    "Tennis": {
        "icon":"🎾", "type":"duel",
        "sets_default":3, "sets_options":[3,5],
        "weights":{"speed":0.35,"accuracy":0.30,"stamina":0.25,"clutch":0.10},
        "narratives":[
            "{p1} serves an ace down the T— pinpoint placement.",
            "{p2} returns with heavy topspin that pushes {p1} wide."
        ]
    },
    "Wrestling": {
        "icon":"🤼", "type":"duel", "rounds_default":5, "rounds_options":[1,3,5],
        "weights":{"power":0.35,"speed":0.25,"stamina":0.25,"defense":0.10,"clutch":0.05},
        "narratives":[
            "{p1} shoots for a single-leg takedown and drives through for 2 points!",
            "{p2} counters with a slick reversal — control switches!"
        ]
    },
    "Soccer": {
        "icon":"⚽", "type":"team", "team_size":7, "match_minutes":90,
        "weights":{"teamwork":0.30,"stamina":0.25,"accuracy":0.20,"speed":0.15,"power":0.06,"defense":0.04},
        "narratives":[
            "{p1} threads a perfect through ball — the attack is on!",
            "{p2} makes a last-ditch sliding tackle to deny the chance."
        ]
    }
}

# ---------------------------
# Persistence: load/write official roster (protected) & community players
# ---------------------------
def load_official_players():
    if os.path.exists(OFFICIAL_PLAYERS_FILE):
        try:
            with open(OFFICIAL_PLAYERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # ensure structure
            fixed = {}
            for name, rec in data.items():
                tiers = rec.get("tiers", {k:"B" for k in STAT_KEYS})
                stats = {k:int(rec.get("stats",{}).get(k, stat_value_within_tier(tiers.get(k,"B")))) for k in STAT_KEYS}
                wc = rec.get("weight_class","Middleweight")
                spec = rec.get("specialization", choose_specialization_from_tiers(tiers))
                fixed[name] = {"tiers":tiers,"stats":stats,"weight_class":wc,"specialization":spec,"official":True}
            return fixed
        except Exception as e:
            print("Failed to load official players:", e)
    # write defaults
    save_official_players(DEFAULT_PLAYERS)
    return {k:v.copy() for k,v in DEFAULT_PLAYERS.items()}

def save_official_players(pdict):
    # Write official file if it doesn't exist; do not allow overwriting via UI
    try:
        tmp = OFFICIAL_PLAYERS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(pdict, f, indent=2)
        os.replace(tmp, OFFICIAL_PLAYERS_FILE)
    except Exception as e:
        print("Error saving official players:", e)

def load_community_players():
    if os.path.exists(PLAYERS_FILE):
        try:
            with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            fixed = {}
            for name, rec in data.items():
                # community players are expected in upgraded structure; if legacy, attempt migration (same as earlier logic)
                tiers = rec.get("tiers", {k:"B" for k in STAT_KEYS})
                stats = {k:int(rec.get("stats",{}).get(k, stat_value_within_tier(tiers.get(k,"B")))) for k in STAT_KEYS}
                wc = rec.get("weight_class","Middleweight")
                spec = rec.get("specialization", choose_specialization_from_tiers(tiers))
                fixed[name] = {"tiers":tiers,"stats":stats,"weight_class":wc,"specialization":spec,"official":False}
            return fixed
        except Exception as e:
            print("Failed loading community players:", e)
    # return empty if missing
    return {}

def save_community_players(pdict):
    try:
        tmp = PLAYERS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(pdict, f, indent=2)
        os.replace(tmp, PLAYERS_FILE)
    except Exception as e:
        print("Error saving community players:", e)

official_players = load_official_players()
community_players = load_community_players()

# merged_roster is used for read-only interactions; updates to community must go separate
def build_merged_roster():
    merged = {}
    merged.update(official_players)
    merged.update(community_players)
    return merged

merged_roster = build_merged_roster()

# ---------------------------
# Rating & narrative utilities
# ---------------------------
def weight_modifier_for_player(name):
    wc = merged_roster.get(name, {}).get("weight_class", "Middleweight")
    return WEIGHT_CLASS_MOD.get(wc, 1.0)

def team_rating_by_weights(team_players, weight_map, sport_name):
    totals = {k:0 for k in STAT_KEYS}
    for name in team_players:
        if name not in merged_roster: continue
        base = merged_roster[name]["stats"]
        mod_base = apply_specialization_modifier(name, base, sport_name)
        mod = weight_modifier_for_player(name)
        for k in STAT_KEYS:
            totals[k] += mod_base.get(k,0) * mod
    rating = sum(totals.get(k,0) * w for k,w in weight_map.items())
    return rating

def duel_rating_by_weights(name, weight_map, sport_name):
    if name not in merged_roster: return 0
    base = merged_roster[name]["stats"]
    mod_base = apply_specialization_modifier(name, base, sport_name)
    mod = weight_modifier_for_player(name)
    base_score = sum(mod_base.get(k,0) * w for k,w in weight_map.items())
    return base_score * mod

def generate_narrative(sport_name, p1, p2):
    templates = sports[sport_name]["narratives"]
    return random.choice(templates).format(p1=p1, p2=p2)

def synthesize_technique_summary(sport_name, winners, losers):
    cfg = sports[sport_name]; weights = cfg["weights"]
    def agg_stats(names):
        agg = {k:0 for k in STAT_KEYS}
        for n in names:
            if n not in merged_roster: continue
            mod = weight_modifier_for_player(n)
            mod_base = apply_specialization_modifier(n, merged_roster[n]["stats"], sport_name)
            for k in STAT_KEYS:
                agg[k] += mod_base[k] * mod
        return agg
    win_stats = agg_stats(winners); lose_stats = agg_stats(losers)
    diffs = {k: win_stats.get(k,0) - lose_stats.get(k,0) for k in STAT_KEYS}
    sorted_stats = sorted(diffs.items(), key=lambda x: x[1], reverse=True)
    top = [s for s,v in sorted_stats if v>0][:3]
    techniques = []
    for stat in top:
        if stat=="power": techniques.append("powerful finishing and heavy shots.")
        elif stat=="speed": techniques.append("speed & transitions opened space.")
        elif stat=="stamina": techniques.append("endurance paid off late.")
        elif stat=="accuracy": techniques.append("precision & placement created chances.")
        elif stat=="defense": techniques.append("tight defense and effective counters.")
        elif stat=="clutch": techniques.append("composed clutch plays at key moments.")
        elif stat=="teamwork": techniques.append("excellent team coordination & build-up.")
    if not techniques: techniques = ["Balanced skills and tactical execution."]
    summary = "Techniques & tactics that decided the contest:\n"
    for i,t in enumerate(techniques, start=1): summary += f"  {i}. {t}\n"
    return summary

# ---------------------------
# Tier drift (post-match) - same logic; updates community roster only
# ---------------------------
def post_match_tier_drift(winners, losers, sport_name, standout_players=None):
    standout_players = set(standout_players or [])
    # only update community players; official players remain unchanged
    for group, is_winner in [(winners, True), (losers, False)]:
        for name in group:
            if name not in community_players: continue  # only community players change
            pdata = community_players[name]
            for stat in STAT_KEYS:
                current_tier = pdata["tiers"].get(stat, "B")
                lo, hi = TIER_RANGES.get(current_tier, (1,10))
                new_val = random.randint(lo, hi)
                promote_chance = 0.12 if is_winner else 0.05
                demote_chance = 0.05 if is_winner else 0.18
                if name in standout_players:
                    promote_chance += 0.18; demote_chance -= 0.06
                new_val = max(1, min(10, new_val))
                pdata["stats"][stat] = new_val
                if random.random() < promote_chance:
                    new_t = tier_up(current_tier)
                    # cap community to B? No — allow community to drift tiers within logic, but your request capped new creations only.
                    pdata["tiers"][stat] = new_t
                    pdata["stats"][stat] = random.randint(*TIER_RANGES[new_t])
                elif random.random() < demote_chance:
                    new_t = tier_down(current_tier)
                    pdata["tiers"][stat] = new_t
                    pdata["stats"][stat] = random.randint(*TIER_RANGES[new_t])
            if random.random() < 0.06:
                pdata["specialization"] = choose_specialization_from_tiers(pdata["tiers"])
    save_community_players(community_players)
    # refresh merged view
    global merged_roster; merged_roster = build_merged_roster()

# ---------------------------
# GUI helpers & layout
# ---------------------------
def append_output(txt, transcript_list=None):
    output_box.insert(tk.END, txt)
    output_box.see(tk.END)
    output_box.update()
    if transcript_list is not None:
        transcript_list.append(txt)

BASE_SLEEP = 0.65
def safe_sleep(sec):
    time.sleep(sec * BASE_SLEEP)

def update_progress_ui(percent, label_text=""):
    prog_var.set(percent); progress_label_var.set(label_text); progress_bar.update()

# ---------------------------
# Avatar Canvas: draw players and update during simulation
# ---------------------------
AVATAR_W = 220; AVATAR_H = 180
def init_avatar_canvas(frame):
    c = tk.Canvas(frame, width=AVATAR_W, height=AVATAR_H, bg="#111")
    c.pack(side="left", padx=8, pady=6)
    return c

def draw_team_avatars(canvas, team_players, x0=10, y0=10, row=0):
    # draw horizontally
    canvas.delete(f"team{row}")
    for i, name in enumerate(team_players):
        cx = x0 + i*60
        cy = y0 + row*80
        r = 22
        color = "#FFD700" if merged_roster.get(name,{}).get("official") else "#66B3FF"
        canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, tags=(f"team{row}",))
        # initials
        initials = "".join([p[0] for p in name.split()][:2]).upper()
        canvas.create_text(cx, cy, text=initials, fill="black", font=("Helvetica", 10, "bold"), tags=(f"team{row}",))
        # small star for official
        if merged_roster.get(name,{}).get("official"):
            canvas.create_text(cx+16, cy-16, text="★", fill="#FFF", font=("Helvetica", 10), tags=(f"team{row}",))
        # name tooltip-like label
        canvas.create_text(cx, cy+30, text=name.split()[0], fill="#EEE", font=("Helvetica", 8), tags=(f"team{row}",))

def update_avatar_sport_icon(canvas, icon):
    canvas.delete("sport_icon")
    canvas.create_text(AVATAR_W-24, 16, text=icon, font=("Segoe UI Emoji", 18), tags=("sport_icon",))

# ---------------------------
# Simulation implementations (concise to fit multisport mode)
# ---------------------------
def simulate_single_sport_team(sport_name, team1, team2, transcript, avatar_canvas=None):
    cfg = sports[sport_name]; weight_map = cfg["weights"]
    append_output(f"\n--- {cfg['icon']} {sport_name} ---\n", transcript)
    update_progress_ui(0, f"Simulating {sport_name}...")
    safe_sleep(0.6)
    # show avatars and sport icon
    if avatar_canvas:
        draw_team_avatars(avatar_canvas, team1, row=0)
        draw_team_avatars(avatar_canvas, team2, row=1)
        update_avatar_sport_icon(avatar_canvas, cfg.get("icon","?"))
        avatar_canvas.update()
    # simulate via rating check with some narrative
    r1 = team_rating_by_weights(team1, weight_map, sport_name) + random.uniform(-10,10)
    r2 = team_rating_by_weights(team2, weight_map, sport_name) + random.uniform(-10,10)
    # short play-by-play
    events = random.randint(3,7)
    for i in range(events):
        p1 = random.choice(team1); p2 = random.choice(team2)
        append_output(generate_narrative(sport_name, p1, p2) + "\n", transcript)
        safe_sleep(0.25 + random.random()*0.5)
        update_progress_ui(int((i+1)/events*100), f"{sport_name} running...")
    # decide
    if r1 > r2:
        append_output(f"{sport_name} Winner: Team 1\n", transcript)
        return 1
    else:
        append_output(f"{sport_name} Winner: Team 2\n", transcript)
        return 2

def simulate_single_sport_duel(sport_name, p1, p2, transcript, avatar_canvas=None):
    cfg = sports[sport_name]; weight_map = cfg["weights"]
    append_output(f"\n--- {cfg['icon']} {sport_name}: {p1} vs {p2} ---\n", transcript)
    update_progress_ui(0, f"Simulating {sport_name} duel...")
    safe_sleep(0.6)
    if avatar_canvas:
        draw_team_avatars(avatar_canvas, [p1], row=0)
        draw_team_avatars(avatar_canvas, [p2], row=1)
        update_avatar_sport_icon(avatar_canvas, cfg.get("icon","?"))
        avatar_canvas.update()
    r1 = duel_rating_by_weights(p1, weight_map, sport_name) + random.uniform(-12,12)
    r2 = duel_rating_by_weights(p2, weight_map, sport_name) + random.uniform(-12,12)
    # short narrative sequence
    for _ in range(random.randint(2,5)):
        append_output(generate_narrative(sport_name, p1, p2) + "\n", transcript)
        safe_sleep(0.3 + random.random()*0.4)
    winner = p1 if r1 > r2 else p2
    append_output(f"{sport_name} Winner: {winner}\n", transcript)
    return 1 if winner==p1 else 2

# ---------------------------
# Multisport (Best-of-5) logic
# - Selects 5 sports randomly from available (ensures diverse set)
# - Enforces that a single player may play in max 2 different sports during the multisport match
# - Encourages deeper rosters and collecting
# ---------------------------
def simulate_multisport_match(team1, team2, avatar_canvas=None):
    transcript = []
    append_output("=== Multisport Match: Best of 5 sports (first to 3) ===\n", transcript)
    # pick 5 distinct sports (if less than 5 available pick all)
    all_sports = list(sports.keys())
    if len(all_sports) >= 5:
        chosen = random.sample(all_sports, 5)
    else:
        chosen = all_sports[:]
    append_output(f"Sports in this matchup: {', '.join(chosen)}\n\n", transcript)
    # enforce usage limit: players can be used in at most 2 sports
    usage_limit = 2
    usage_counts = {n:0 for n in set(team1+team2)}
    # check before starting: if any player count potential > limit (we don't know per sport selections here),
    # we'll simply enforce during resolution by skipping a player if they exceeded limit (this encourages smarter selection)
    score1 = score2 = 0
    for sport_name in chosen:
        cfg = sports[sport_name]
        # Build team rosters for this sport with strategy: try to avoid players who already hit usage limit
        def build_sport_team(team):
            # prefer players with usage < limit
            players_allowed = [p for p in team if usage_counts.get(p,0) < usage_limit]
            if not players_allowed:
                # if everybody hit limit, allow everyone (break tie)
                players_allowed = team[:]
            size = cfg.get("team_size", 1) if cfg["type"]=="team" else 1
            # choose a selection: if team has >= size players, pick top rated ones for sport
            if len(players_allowed) <= size:
                sel = players_allowed[:]
            else:
                # score each by its duel/team rating when alone
                scored = sorted(players_allowed, key=lambda n: duel_rating_by_weights(n, cfg["weights"], sport_name) if cfg["type"]=="duel" else team_rating_by_weights([n], cfg["weights"], sport_name), reverse=True)
                sel = scored[:size]
            return sel
        s1 = build_sport_team(team1); s2 = build_sport_team(team2)
        # increment usage counts for selected players
        for p in s1 + s2: usage_counts[p] = usage_counts.get(p,0) + 1
        # simulate (team or duel)
        if cfg["type"] == "team":
            winner = simulate_single_sport_team(sport_name, s1, s2, transcript, avatar_canvas)
            if winner == 1: score1 += 1
            else: score2 += 1
        else:
            # for duel, pick representative players (best ones)
            sel1 = s1[0] if s1 else random.choice(team1)
            sel2 = s2[0] if s2 else random.choice(team2)
            winner = simulate_single_sport_duel(sport_name, sel1, sel2, transcript, avatar_canvas)
            if winner == 1: score1 += 1
            else: score2 += 1
        append_output(f"Score after {sport_name}: Team1 {score1} — Team2 {score2}\n\n", transcript)
        safe_sleep(0.6)
        # early termination if someone reached 3
        if score1 >= 3 or score2 >= 3: break
    if score1 > score2:
        append_output(f"🏆 MULTISPORT WINNER: Team1 ({score1}-{score2})\n", transcript)
        # post-match drift: pick standout winners (top usage or selects)
        # determine winners/losers lists (full teams)
        post_match_tier_drift(team1, team2, "Multisport", standout_players=set([p for p,c in usage_counts.items() if p in team1 and c>0][:2]))
    elif score2 > score1:
        append_output(f"🏆 MULTISPORT WINNER: Team2 ({score2}-{score1})\n", transcript)
        post_match_tier_drift(team2, team1, "Multisport", standout_players=set([p for p,c in usage_counts.items() if p in team2 and c>0][:2]))
    else:
        append_output("Match ended tied across sports — no clear winner.\n", transcript)
    global last_transcript; last_transcript = transcript

# ---------------------------
# GUI Setup
# ---------------------------
root = tk.Tk(); root.title("Universus — Public Simulator (Official + Community)")
root.geometry("1250x880")

# scrollable frame
main_frame = tk.Frame(root); main_frame.pack(fill="both", expand=True)
canvas = tk.Canvas(main_frame)
scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)
scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0,0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Top controls
top_frame = ttk.Frame(scrollable_frame, padding=(8,8)); top_frame.grid(row=0, column=0, sticky="ew")
top_frame.columnconfigure(8, weight=1)
ttk.Label(top_frame, text="Select Sport:").grid(row=0, column=0, padx=6, sticky="w")
sport_var = tk.StringVar(value="Basketball")
sport_selector = ttk.Combobox(top_frame, textvariable=sport_var, values=list(sports.keys()), state="readonly", width=16)
sport_selector.grid(row=0, column=1, padx=4, sticky="w")
sport_icon_var = tk.StringVar(value=sports[sport_var.get()]["icon"])
sport_icon_lbl = ttk.Label(top_frame, textvariable=sport_icon_var, font=("Segoe UI Emoji", 16))
sport_icon_lbl.grid(row=0, column=2, padx=6, sticky="w")

# Multisport toggle
multisport_var = tk.BooleanVar(value=False)
ttk.Checkbutton(top_frame, text="Multisport Best-of-5", variable=multisport_var).grid(row=0, column=3, padx=12, sticky="w")

# sport settings
sport_settings = ttk.Frame(top_frame); sport_settings.grid(row=0, column=4, padx=10, sticky="w")
ttk.Label(sport_settings, text="Boxing rounds:").grid(row=0, column=0, padx=3, sticky="w")
boxing_rounds_var = tk.IntVar(value=sports["Boxing"]["rounds_default"])
boxing_rounds_cb = ttk.Combobox(sport_settings, textvariable=boxing_rounds_var, values=sports["Boxing"]["rounds_options"], state="readonly", width=6)
boxing_rounds_cb.grid(row=0, column=1, padx=3, sticky="w")
ttk.Label(sport_settings, text="Tennis sets (to win):").grid(row=0, column=2, padx=8, sticky="w")
tennis_sets_var = tk.IntVar(value=sports["Tennis"]["sets_default"])
tennis_sets_cb = ttk.Combobox(sport_settings, textvariable=tennis_sets_var, values=sports["Tennis"]["sets_options"], state="readonly", width=6)
tennis_sets_cb.grid(row=0, column=3, padx=3, sticky="w")

simulate_btn = ttk.Button(top_frame, text="Simulate"); simulate_btn.grid(row=0, column=5, padx=12)
export_btn = ttk.Button(top_frame, text="Export Transcript"); export_btn.grid(row=0, column=6, padx=6)

# Selection area + Avatar canvas
selectors_frame = ttk.LabelFrame(scrollable_frame, text="Team / Player Selection", padding=(8,8)); selectors_frame.grid(row=1, column=0, padx=8, pady=8, sticky="ew")
selectors_frame.columnconfigure(1, weight=1); selectors_frame.columnconfigure(3, weight=1)
team1_selectors = []; team2_selectors = []

# Avatar panel
avatar_panel = ttk.LabelFrame(scrollable_frame, text="Avatars & Visuals", padding=(8,8))
avatar_panel.grid(row=1, column=1, padx=8, pady=8, sticky="n")
avatar_canvas = init_avatar_canvas(avatar_panel)

def refresh_merged_roster():
    global merged_roster
    merged_roster = build_merged_roster()

def view_selected_player_stats(name):
    if not name:
        messagebox.showerror("Error", "No player selected."); return
    if name not in merged_roster:
        messagebox.showerror("Error", f"{name} not found."); return
    stats = merged_roster[name]
    popup = tk.Toplevel(root); popup.title(f"Stats — {name}"); popup.geometry("520x480")
    ttk.Label(popup, text=f"{name} {'★ Official' if stats.get('official') else '• Community'}", font=("Helvetica", 14, "bold")).pack(pady=8)
    frame = ttk.Frame(popup); frame.pack(padx=8, pady=6, fill="x")
    for i, k in enumerate(STAT_KEYS):
        val = stats["stats"].get(k,0)
        ttk.Label(frame, text=f"{k.capitalize():12}", width=12).grid(row=i, column=0, sticky="w", padx=6, pady=4)
        ttk.Label(frame, text=str(val), width=6).grid(row=i, column=1, sticky="w")
        pb = ttk.Progressbar(frame, orient="horizontal", length=280, mode="determinate", maximum=100, value=int(val*10))
        pb.grid(row=i, column=2, padx=6, sticky="w")
    ttk.Label(popup, text=f"Weight class: {stats.get('weight_class','Middleweight')}").pack(pady=6)
    ttk.Label(popup, text=f"Specialization: {stats.get('specialization','Balanced')}").pack(pady=6)
    btn_frame = ttk.Frame(popup); btn_frame.pack(pady=8)
    if not stats.get("official"):
        ttk.Button(btn_frame, text="Delete", command=lambda: delete_community_player(name, popup)).pack(side="left", padx=6)
    else:
        ttk.Label(btn_frame, text="Official players cannot be deleted.", foreground="gray").pack(side="left", padx=6)
    ttk.Button(btn_frame, text="Close", command=popup.destroy).pack(side="left", padx=6)

def delete_community_player(name, popup=None):
    if messagebox.askyesno("Confirm", f"Delete community player '{name}'?"):
        community_players.pop(name, None)
        save_community_players(community_players)
        refresh_player_lists()
        refresh_merged_roster()
        if popup: popup.destroy()

def build_selectors_for_sport(sport_name):
    # clear previous dynamic widgets
    for w in selectors_frame.winfo_children():
        w.destroy()
    team1_selectors.clear(); team2_selectors.clear()
    cfg = sports[sport_name]; typ = cfg["type"]
    ttk.Label(selectors_frame, text="Team/Player 1:").grid(row=0, column=0, sticky="w", padx=6)
    ttk.Label(selectors_frame, text="Team/Player 2:").grid(row=0, column=2, sticky="w", padx=6)
    all_names = sorted(merged_roster.keys(), key=lambda n: (not merged_roster[n].get("official"), n))  # official first
    if typ == "team":
        size = cfg.get("team_size", 5)
        ttk.Label(selectors_frame, text="Team 1 Players:").grid(row=1, column=0, sticky="w", padx=6)
        for i in range(size):
            cb = ttk.Combobox(selectors_frame, values=all_names, width=48)
            cb.grid(row=2+i, column=0, padx=6, pady=2, sticky="w")
            team1_selectors.append(cb)
            ttk.Button(selectors_frame, text="View", command=lambda c=cb: view_selected_player_stats(c.get())).grid(row=2+i, column=1, padx=4, sticky="w")
        ttk.Label(selectors_frame, text="Team 2 Players:").grid(row=1, column=2, sticky="w", padx=6)
        for i in range(size):
            cb = ttk.Combobox(selectors_frame, values=all_names, width=48)
            cb.grid(row=2+i, column=2, padx=6, pady=2, sticky="w")
            team2_selectors.append(cb)
            ttk.Button(selectors_frame, text="View", command=lambda c=cb: view_selected_player_stats(c.get())).grid(row=2+i, column=3, padx=4, sticky="w")
    else:
        cb1 = ttk.Combobox(selectors_frame, values=all_names, width=48)
        cb1.grid(row=2, column=0, padx=6, pady=6, sticky="w"); team1_selectors.append(cb1)
        ttk.Button(selectors_frame, text="View", command=lambda: view_selected_player_stats(cb1.get())).grid(row=2, column=1, padx=4)
        cb2 = ttk.Combobox(selectors_frame, values=all_names, width=48)
        cb2.grid(row=2, column=2, padx=6, pady=6, sticky="w"); team2_selectors.append(cb2)
        ttk.Button(selectors_frame, text="View", command=lambda: view_selected_player_stats(cb2.get())).grid(row=2, column=3, padx=4)

build_selectors_for_sport(sport_var.get())

def on_sport_change(event=None):
    build_selectors_for_sport(sport_var.get())
    sport_icon_var.set(sports[sport_var.get()]["icon"])
    boxing_rounds_cb.configure(state="readonly" if sport_var.get()=="Boxing" else "disabled")
    tennis_sets_cb.configure(state="readonly" if sport_var.get()=="Tennis" else "disabled")

sport_selector.bind("<<ComboboxSelected>>", on_sport_change)

# Output area
ttk.Label(scrollable_frame, text="Results / Play-by-play:").grid(row=2, column=0, sticky="w", padx=8)
output_box = scrolledtext.ScrolledText(scrollable_frame, height=18, width=110, font=("Courier", 10))
output_box.grid(row=3, column=0, padx=8, pady=6, columnspan=2)

# Progress & status row
progress_frame = ttk.Frame(scrollable_frame); progress_frame.grid(row=4, column=0, padx=8, pady=4, sticky="w")
prog_var = tk.IntVar(value=0)
progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=600, mode="determinate", variable=prog_var, maximum=100)
progress_bar.pack(side="left", padx=6)
progress_label_var = tk.StringVar(value=""); progress_label = ttk.Label(progress_frame, textvariable=progress_label_var)
progress_label.pack(side="left", padx=8)

# Add / Edit community players section (kept but capped & protected vs official)
add_frame = ttk.LabelFrame(scrollable_frame, text="➕ Add / Edit a Community Player (community players capped at B-tier)", padding=(8,8))
add_frame.grid(row=5, column=0, padx=8, pady=6, sticky="ew")
add_frame.columnconfigure(1, weight=1)
ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky="e")
entry_name = ttk.Entry(add_frame, width=36); entry_name.grid(row=0, column=1, padx=4, pady=3, sticky="w")

tier_vars = {}
stat_frame = ttk.Frame(add_frame); stat_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=6)
for idx, stat in enumerate(STAT_KEYS):
    r = idx // 2; c = (idx % 2) * 2
    ttk.Label(stat_frame, text=stat.capitalize()+":").grid(row=r, column=c, sticky="e", padx=(0,6))
    var = tk.StringVar(value="B")  # default community cap B
    cb = ttk.Combobox(stat_frame, textvariable=var, values=list(TIER_RANGES.keys()), width=6, state="readonly")
    cb.grid(row=r, column=c+1, sticky="w", padx=(0,10))
    tier_vars[stat] = var

ttk.Label(add_frame, text="Weight Class:").grid(row=3, column=0, sticky="e", pady=6)
weight_var = tk.StringVar(value="Middleweight")
weight_cb = ttk.Combobox(add_frame, textvariable=weight_var, values=WEIGHT_CLASSES, state="readonly", width=18)
weight_cb.grid(row=3, column=1, sticky="w", pady=6)

def add_or_update_player():
    name = entry_name.get().strip()
    if not name:
        messagebox.showerror("Error", "Name cannot be empty."); return
    if name in official_players:
        messagebox.showerror("Protected", f"'{name}' is an official roster player and cannot be overwritten.") ; return
    # cap tiers to B for new/updated community players
    selected_tiers = {}
    for k in STAT_KEYS:
        t = tier_vars[k].get()
        # cap to B if higher
        if tier_index_of(t) > tier_index_of("B"):
            t = "B"
        selected_tiers[k] = t
    stats_map = {k: stat_value_within_tier(selected_tiers[k]) for k in STAT_KEYS}
    wc = weight_var.get()
    spec = choose_specialization_from_tiers(selected_tiers)
    community_players[name] = {"tiers":selected_tiers, "stats":stats_map, "weight_class":wc, "specialization":spec, "official":False}
    save_community_players(community_players)
    refresh_player_lists()
    refresh_merged_roster()
    messagebox.showinfo("Saved", f"Community player '{name}' saved (specialization: {spec}). Note: community players are capped at B-tier upon creation.")
    entry_name.delete(0, tk.END)

ttk.Button(add_frame, text="Add / Update Community Player", command=add_or_update_player).grid(row=4, column=0, columnspan=2, pady=6)

def refresh_player_lists():
    all_names = sorted(merged_roster.keys(), key=lambda n: (not merged_roster[n].get("official"), n))
    for cb in team1_selectors + team2_selectors:
        current = cb.get()
        cb['values'] = all_names
        if current in all_names:
            cb.set(current)
        else:
            cb.set("")

# Simulation control
def gather_selection():
    sport_name = sport_var.get(); cfg = sports[sport_name]; typ = cfg["type"]
    if typ == "team":
        t1 = [c.get() for c in team1_selectors if c.get()]
        t2 = [c.get() for c in team2_selectors if c.get()]
        return ("team", t1, t2)
    else:
        p1 = team1_selectors[0].get() if team1_selectors else ""; p2 = team2_selectors[0].get() if team2_selectors else ""
        return ("duel", p1, p2)

last_transcript = []

def simulate_handler():
    sel = gather_selection()
    output_box.delete("1.0", tk.END)
    update_progress_ui(0,"")
    # refresh merged roster before sim
    refresh_merged_roster()
    sport_name = sport_var.get()
    if multisport_var.get():
        # Multisport mode requires team format (we'll allow team-based multisport)
        if sel[0] != "team":
            messagebox.showerror("Error", "Multisport mode requires teams (not single-duels)."); return
        team1, team2 = sel[1], sel[2]
        if not team1 or not team2:
            messagebox.showerror("Error","Both teams must have at least one player selected."); return
        invalid = [p for p in team1 + team2 if p not in merged_roster]
        if invalid:
            messagebox.showerror("Error", f"Invalid players: {invalid}"); return
        # start multisport in thread
        threading.Thread(target=simulate_multisport_match, args=(team1, team2, avatar_canvas), daemon=True).start()
        return
    # single sport path
    if sel[0] == "team":
        team1, team2 = sel[1], sel[2]
        if not team1 or not team2:
            messagebox.showerror("Error","Both teams must have at least one player selected."); return
        invalid = [p for p in team1 + team2 if p not in merged_roster]
        if invalid: messagebox.showerror("Error", f"Invalid players: {invalid}"); return
        # route by sport
        if sport_name == "Basketball":
            threading.Thread(target=lambda: (simulate_single_sport_team("Basketball", team1, team2, [], avatar_canvas), None), daemon=True).start()
        elif sport_name == "Soccer":
            threading.Thread(target=lambda: (simulate_single_sport_team("Soccer", team1, team2, [], avatar_canvas), None), daemon=True).start()
        else:
            # fallback to team sim for any team-type sport
            threading.Thread(target=lambda: (simulate_single_sport_team(sport_name, team1, team2, [], avatar_canvas), None), daemon=True).start()
    else:
        p1, p2 = sel[1], sel[2]
        if not p1 or not p2:
            messagebox.showerror("Error","Select two players for the duel."); return
        if p1 not in merged_roster or p2 not in merged_roster:
            messagebox.showerror("Error","One or both players not in DB."); return
        if sport_name == "Boxing":
            rounds = int(boxing_rounds_var.get())
            threading.Thread(target=lambda: (simulate_single_sport_duel("Boxing", p1, p2, [], avatar_canvas), None), daemon=True).start()
        elif sport_name == "Tennis":
            sets = int(tennis_sets_var.get())
            threading.Thread(target=lambda: (simulate_single_sport_duel("Tennis", p1, p2, [], avatar_canvas), None), daemon=True).start()
        elif sport_name == "Wrestling":
            rounds = int(sports["Wrestling"]["rounds_default"])
            threading.Thread(target=lambda: (simulate_single_sport_duel("Wrestling", p1, p2, [], avatar_canvas), None), daemon=True).start()
        else:
            messagebox.showerror("Error","Unknown duel sport.")

simulate_btn.configure(command=simulate_handler)

# Export transcript
def export_transcript():
    global last_transcript
    content = "".join(last_transcript) if last_transcript else output_box.get("1.0", tk.END).strip()
    if not content:
        messagebox.showerror("Error", "No transcript to export."); return
    default_name = f"transcript_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=default_name, filetypes=[("Text files","*.txt")])
    if not path: return
    with open(path, "w", encoding="utf-8") as f: f.write(content)
    messagebox.showinfo("Saved", f"Transcript exported to:\n{path}")

export_btn.configure(command=export_transcript)

# periodic refresh
def periodic_refresh():
    refresh_player_lists()
    root.after(2500, periodic_refresh)
root.after(2500, periodic_refresh)
on_sport_change()
refresh_player_lists()
root.mainloop()



