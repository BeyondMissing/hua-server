"""Persistent training/crafting for SyntheticGamePlatform (1060-1062).

All mutations lock the player's profile before progress, run and inventory
rows. No network/async work happens inside these synchronous transactions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SHANGHAI = timezone(timedelta(hours=8))
ATTRIBUTE_BY_GAME = {1: (2, "beautiful"), 2: (3, "love"), 3: (1, "wisdom")}


class SyntheticGameError(ValueError):
    """Invalid recipe, mode, locked recipe, or missing/foreign pending run."""


@dataclass(frozen=True)
class SyntheticGamePolicy:
    # These original server-side rules are NOT recoverable from the AS3.
    make_success_score: int = 60
    daily_attribute_plays: int = 10
    run_timeout_seconds: int = 3600

    def attribute_gain(self, score):
        # The GameEndPanel has display frames for gains 1..5 (6 means none).
        return (score + 19) // 20 if score else 0


@dataclass(frozen=True)
class Recipe:
    game_id: int
    item_id: int
    index: int
    variant: int
    exp_required: int
    need_vip: bool
    sex: int
    materials: tuple


def load_recipes(path=ROOT / "data" / "synthetic_game_items.xml"):
    recipes = {}
    for node in ET.parse(path).getroot():
        index, variant = map(int, node.attrib["index"].split("/"))
        materials = tuple(tuple(map(int, pair.split("/")))
                          for pair in node.attrib["req_item"].split(";") if pair)
        recipe = Recipe(int(node.attrib["game_id"]), int(node.attrib["item_id"]),
                        index, variant, int(node.attrib["total_skill_point"]),
                        bool(int(node.attrib["need_vip"])), int(node.attrib["sex"]), materials)
        if recipe.item_id in recipes or recipe.game_id not in ATTRIBUTE_BY_GAME:
            raise ValueError("Invalid synthetic game recipe catalog")
        recipes[recipe.item_id] = recipe
    return recipes


def skill_gain(score):
    """Exact scoreTimes bands in SyntheticGameManager.requestEndGame."""
    return score * (3 if score > 95 else 2 if score > 70 else 1)


class SyntheticGameStore:

    def __init__(self, accounts, policy=None):
        self.accounts = accounts
        self.policy = policy or SyntheticGamePolicy()
        self.recipes = load_recipes()


    @staticmethod
    def _sex(profile):
        # UserInfo.as: nationality 5 -> male; all other nationalities -> female.
        return 2 if int(profile.get("nationality") or 1) == 5 else 1

    def _player_recipes(self, game_id, profile):
        return sorted((r for r in self.recipes.values()
                       if r.game_id == game_id and r.sex in (0, self._sex(profile))),
                      key=lambda r: (r.index, r.variant, r.item_id))

    @staticmethod
    def _material_source(item_id):
        sources = {7: ("player_flowers", "item_id"),
                   13: ("player_pollens", "pollen_id"),
                   16: ("player_materials", "item_id")}
        try:
            return sources[item_id // 100000]
        except KeyError:
            raise SyntheticGameError("Unsupported recipe material") from None

    def _materials(self, cursor, user_id, item_ids, lock=False):
        quantities = {}
        for item_id in sorted(set(item_ids)):
            table, key = self._material_source(item_id)
            cursor.execute(f"SELECT amount FROM {table} WHERE user_id=%s AND {key}=%s"
                           + (" FOR UPDATE" if lock else ""), (user_id, item_id))
            row = cursor.fetchone() or {}
            quantities[item_id] = int(row.get("amount") or 0)
        return quantities

    @staticmethod
    def _profile(cursor, user_id):
        cursor.execute("SELECT * FROM player_profiles WHERE user_id=%s FOR UPDATE", (user_id,))
        profile = cursor.fetchone()
        if not profile:
            raise SyntheticGameError("Missing player profile")
        return profile

    @staticmethod
    def _activate(cursor, user_id, game_id, index):
        cursor.execute("INSERT IGNORE INTO player_synthetic_progress "
                       "(user_id, game_id, goods_index) VALUES (%s,%s,%s)", (user_id, game_id, index))

    @staticmethod
    def _owns_unique(cursor, user_id, recipe):
        if recipe.game_id != 1:
            return False  # Pet food and furniture can be made repeatedly.
        cursor.execute("SELECT 1 FROM player_clothes WHERE user_id=%s AND cloth_id=%s FOR UPDATE",
                       (user_id, recipe.item_id))
        return cursor.fetchone() is not None

    @staticmethod
    def _catalog(cursor, recipe):
        table = {1: "type_clothes", 2: "type_pet_supplies", 3: "type_house_goods"}[recipe.game_id]
        cursor.execute(f"SELECT 1 FROM {table} WHERE id=%s", (recipe.item_id,))
        if cursor.fetchone() is None:
            raise SyntheticGameError("Missing output item catalog entry")

    def activated_goods(self, user_id, game_id):
        if game_id not in ATTRIBUTE_BY_GAME:
            raise SyntheticGameError("Invalid gameID")
        self.accounts._ensure_connection()
        connection = self.accounts.connection
        try:
            connection.begin()
            with connection.cursor() as cursor:
                profile = self._profile(cursor, user_id)
                recipes = self._player_recipes(game_id, profile)
                self._activate(cursor, user_id, game_id, 1)
                cursor.execute("SELECT goods_index, exp_done FROM player_synthetic_progress "
                               "WHERE user_id=%s AND game_id=%s ORDER BY goods_index", (user_id, game_id))
                progress = list(cursor.fetchall())
                counts = self._materials(cursor, user_id, (m for r in recipes for m, _ in r.materials))
                rows = []
                for row in progress:
                    variants = [r for r in recipes if r.index == row["goods_index"]]
                    if not variants:
                        continue
                    materials = sorted({m for r in variants for m, _ in r.materials})
                    rows.append({"goods_index": int(row["goods_index"]),
                                 "exp_done": min(int(row["exp_done"]), variants[0].exp_required),
                                 "materials": [(m, counts[m]) for m in materials]})
            connection.commit()
            return rows
        except Exception:
            connection.rollback()
            raise

    def start(self, user_id, item_id, mode, session_token, now=None):
        recipe = self.recipes.get(item_id)
        if recipe is None or mode not in (1, 2):
            raise SyntheticGameError("Invalid itemID or gameMode")
        now = int(time.time()) if now is None else int(now)
        self.accounts._ensure_connection()
        connection = self.accounts.connection
        try:
            connection.begin()
            with connection.cursor() as cursor:
                profile = self._profile(cursor, user_id)
                if recipe.sex not in (0, self._sex(profile)):
                    raise SyntheticGameError("Wrong recipe sex")
                self._activate(cursor, user_id, recipe.game_id, 1)
                cursor.execute("SELECT exp_done FROM player_synthetic_progress "
                               "WHERE user_id=%s AND game_id=%s AND goods_index=%s FOR UPDATE",
                               (user_id, recipe.game_id, recipe.index))
                progress = cursor.fetchone()
                if progress is None:
                    raise SyntheticGameError("Recipe is not activated")
                cursor.execute("SELECT * FROM player_synthetic_runs WHERE user_id=%s FOR UPDATE", (user_id,))
                run = cursor.fetchone()
                if (run and run["active"] and run["session_token"] == session_token
                        and now - int(run["started_at"]) <= self.policy.run_timeout_seconds):
                    raise SyntheticGameError("Game already started")
                result = 0
                if mode == 2:
                    vip = int(profile.get("vip_level") or 0) > 0
                    if recipe.need_vip and not vip:
                        result = 1
                    elif self._owns_unique(cursor, user_id, recipe):
                        result = 3
                    elif int(progress["exp_done"]) < recipe.exp_required:
                        result = 4
                    else:
                        self._catalog(cursor, recipe)
                        counts = self._materials(cursor, user_id, (m for m, _ in recipe.materials), lock=True)
                        if any(counts[m] < amount for m, amount in recipe.materials):
                            result = 2
                if result == 0:
                    cursor.execute("INSERT IGNORE INTO player_synthetic_items (user_id,item_id) VALUES (%s,%s)",
                                   (user_id, item_id))
                    # A new socket may replace an abandoned run; the old socket
                    # cannot settle it because the session token no longer matches.
                    cursor.execute("INSERT INTO player_synthetic_runs "
                                   "(user_id,item_id,game_mode,session_token,started_at,active) VALUES (%s,%s,%s,%s,%s,1) "
                                   "ON DUPLICATE KEY UPDATE item_id=VALUES(item_id),game_mode=VALUES(game_mode),"
                                   "session_token=VALUES(session_token),started_at=VALUES(started_at),active=1",
                                   (user_id, item_id, mode, session_token, now))
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise

    def _grant(self, cursor, user_id, recipe):
        self._catalog(cursor, recipe)
        if recipe.game_id == 1:
            cursor.execute("INSERT INTO player_clothes (user_id,cloth_id) VALUES (%s,%s)",
                           (user_id, recipe.item_id))
        elif recipe.game_id == 2:
            cursor.execute("INSERT INTO player_pet_supplies (user_id,item_id,amount) VALUES (%s,%s,1) "
                           "ON DUPLICATE KEY UPDATE amount=amount+1", (user_id, recipe.item_id))
        else:
            cursor.execute("SELECT COALESCE(MAX(no),0) AS max_no FROM player_house_goods "
                           "WHERE user_id=%s FOR UPDATE", (user_id,))
            no = int(cursor.fetchone()["max_no"]) + 1
            cursor.execute("INSERT INTO player_house_goods (user_id,item_id,no,x,y,m,z,is_set) "
                           "VALUES (%s,%s,%s,0,0,0,0,0)", (user_id, recipe.item_id, no))

    def finish(self, user_id, score, session_token, now=None):
        if not 0 <= score <= 100:
            raise SyntheticGameError("Score must be 0..100")
        now = int(time.time()) if now is None else int(now)
        award_date = datetime.fromtimestamp(now, SHANGHAI).date()
        self.accounts._ensure_connection()
        connection = self.accounts.connection
        try:
            connection.begin()
            with connection.cursor() as cursor:
                profile = self._profile(cursor, user_id)
                cursor.execute("SELECT * FROM player_synthetic_runs WHERE user_id=%s FOR UPDATE", (user_id,))
                run = cursor.fetchone()
                if (not run or not run["active"] or run["session_token"] != session_token
                        or now - int(run["started_at"]) > self.policy.run_timeout_seconds):
                    raise SyntheticGameError("No valid pending game")
                recipe = self.recipes[int(run["item_id"])]
                mode = int(run["game_mode"])
                cursor.execute("SELECT * FROM player_synthetic_items WHERE user_id=%s AND item_id=%s FOR UPDATE",
                               (user_id, recipe.item_id))
                stats = cursor.fetchone()
                made, exp_type, attribute_gain = 0, 4, 0
                # Zero is also the client's quit message: end the run without
                # changing statistics, progress, inventory or daily allowance.
                if score:
                    cursor.execute("SELECT exp_done FROM player_synthetic_progress "
                                   "WHERE user_id=%s AND game_id=%s AND goods_index=%s FOR UPDATE",
                                   (user_id, recipe.game_id, recipe.index))
                    exp_done = int(cursor.fetchone()["exp_done"])
                    if mode == 1:
                        exp_done = min(recipe.exp_required, exp_done + skill_gain(score))
                        cursor.execute("UPDATE player_synthetic_progress SET exp_done=%s "
                                       "WHERE user_id=%s AND game_id=%s AND goods_index=%s",
                                       (exp_done, user_id, recipe.game_id, recipe.index))
                        if exp_done == recipe.exp_required and any(
                                r.index == recipe.index + 1 for r in self._player_recipes(recipe.game_id, profile)):
                            self._activate(cursor, user_id, recipe.game_id, recipe.index + 1)
                    elif score >= self.policy.make_success_score:
                        counts = self._materials(cursor, user_id, (m for m, _ in recipe.materials), lock=True)
                        vip_ok = not recipe.need_vip or int(profile.get("vip_level") or 0) > 0
                        if (vip_ok and recipe.sex in (0, self._sex(profile))
                                and exp_done >= recipe.exp_required
                                and not self._owns_unique(cursor, user_id, recipe)
                                and all(counts[m] >= amount for m, amount in recipe.materials)):
                            for item_id, amount in recipe.materials:
                                table, key = self._material_source(item_id)
                                cursor.execute(f"UPDATE {table} SET amount=amount-%s "
                                               f"WHERE user_id=%s AND {key}=%s AND amount>=%s",
                                               (amount, user_id, item_id, amount))
                                if cursor.rowcount != 1:
                                    raise SyntheticGameError("Material changed during settlement")
                            self._grant(cursor, user_id, recipe)
                            made = 1
                    if mode == 1:
                        cursor.execute("INSERT IGNORE INTO player_synthetic_daily "
                                       "(user_id,game_id,award_date) VALUES (%s,%s,%s)",
                                       (user_id, recipe.game_id, award_date))
                        cursor.execute("SELECT award_count FROM player_synthetic_daily "
                                       "WHERE user_id=%s AND game_id=%s AND award_date=%s FOR UPDATE",
                                       (user_id, recipe.game_id, award_date))
                        count = int(cursor.fetchone()["award_count"])
                        exp_type = 0
                        if count < self.policy.daily_attribute_plays:
                            exp_type, column = ATTRIBUTE_BY_GAME[recipe.game_id]
                            attribute_gain = min(self.policy.attribute_gain(score),
                                                 0xFFFFFFFF - int(profile.get(column) or 0))
                            cursor.execute(f"UPDATE player_profiles SET {column}={column}+%s WHERE user_id=%s",
                                           (attribute_gain, user_id))
                            cursor.execute("UPDATE player_synthetic_daily SET award_count=award_count+1 "
                                           "WHERE user_id=%s AND game_id=%s AND award_date=%s",
                                           (user_id, recipe.game_id, award_date))
                    cursor.execute("UPDATE player_synthetic_items SET play_count=play_count+1,"
                                   "score_total=score_total+%s,score_highest=GREATEST(score_highest,%s),"
                                   "made_count=made_count+%s,last_score=%s,last_mode=%s WHERE user_id=%s AND item_id=%s",
                                   (score, score, made, score, mode, user_id, recipe.item_id))
                    stats = dict(stats)
                    stats["play_count"] += 1
                    stats["score_total"] += score
                    stats["score_highest"] = max(stats["score_highest"], score)
                cursor.execute("UPDATE player_synthetic_runs SET active=0 WHERE user_id=%s", (user_id,))
            connection.commit()
            play_count = int(stats["play_count"])
            return (made, exp_type, attribute_gain, play_count,
                    int(stats["score_total"]) // play_count if play_count else 0,
                    int(stats["score_highest"]))
        except Exception:
            connection.rollback()
            raise
