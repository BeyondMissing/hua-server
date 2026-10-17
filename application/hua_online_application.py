import secrets
import random
import struct
import time
import asyncio
from datetime import date
from dataclasses import replace

from entity.account import Account
from entity.response import Response
from constant.command_id import *
from constant.consts import FRIEND_STATUS_FRIEND, FRIEND_STATUS_INTIMATE, FRIEND_STATUS_BLACKLIST
from exception.clothing_change_error import ClothingChangeError
from exception.social_protocol_error import SocialProtocolError
from exception.suiting_error import SuitingError
from log.log import LOG

from serialization.cloth_change_payload import parse_cloth_change_request, cloth_change_payload, ClothChangeProtocolError
from serialization.cloth_info_payload import cloth_info_payload
from serialization.home_house_payload import home_house_payload
from serialization.home_info_payload import home_info_payload
from serialization.home_tool_payload import home_tool_payload, home_depot_payload
from serialization.home_action_payload import (
    home_add_plant_payload,
    home_add_house_payload,
    home_house_back_payload,
    home_house_position_payload,
    home_pot_back_payload,
    home_pot_add_payload,
    home_tool_add_payload,
    home_plant_tool_payload,
)
from serialization.house_info_payload import (
    house_info_payload,
    pet_inhouse_info_payload,
    pet_simple_info_payload,
    house_add_goods_payload,
    house_del_goods_payload,
)
from serialization.log_in_payload import log_in_payload
from serialization.pet_base_info_payload import pet_base_info_payload
from serialization.pet_use_tool_payload import pet_use_tool_payload
from serialization.synthetic_game_payload import (
    activate_goods_payload, synthetic_start_payload, synthetic_score_payload,
)
from serialization.social_payload import item_type_info_payload, parse_item_type_request, fairy_action_payload, \
    parse_fairy_action_request, chat_info_payload, parse_chat_request, people_transform_payload, \
    parse_people_transform_request, friend_info_payload, friend_request_notice_payload
from serialization.suiting_info_payload import suiting_info_payload
from serialization.suiting_change_payload import parse_suiting_add_request, parse_suiting_delete_request, suiting_add_response, SuitingProtocolError

from storage.account_store import AccountStore
from storage.map_player_store import MapPlayerStore
from storage.session_store import SessionStore
from storage.synthetic_game_store import SyntheticGameError, ATTRIBUTE_BY_GAME

from stream import _u32, fixed_utf8
from utils import _profile_value, _enter_map_eff_payload


# The legacy map-material table stores one potential pickup per row but has
# no per-row rate.  Roll every configured location independently so maps do
# not reveal all of their materials every time they are entered.
MAP_MATERIAL_SPAWN_RATE = 0.5


class HuaOnlineApplication:

    def __init__(
        self,
        accounts: AccountStore,
        sessions: SessionStore,
        shop_half_price_day: int = 0,
    ):

        self.accounts = accounts
        self.sessions = sessions
        # The legacy game has one configurable half-price day per month. A
        # value of zero disables the promotion when no schedule is configured.
        self.shop_half_price_day = int(shop_half_price_day)
        # The application owns the active connections so friend/chat pushes
        # can always find a logged-in peer.  on_session_disconnected removes
        # each entry when its socket closes.
        self.online_sessions = set()
        self.map_player_store = MapPlayerStore()

    def install(self, server):

        server.on(CMD_LOGIN_IN, self.login_in)
        server.on(CMD_GET_REG_SIGN, self.get_reg_sign)
        server.on(CMD_NOTICE_UNLINE_INFO, self.notice_unline_info)
        server.on(CMD_LOGIN_LOCATION, self.location)
        server.on(CMD_COMMON_ONCE_FLAG, self.once_flag)
        server.on(CMD_COMMON_SET_FLAG, self.set_once_flag)
        server.on(CMD_SET_NEWUSERJOB, self.set_new_user_job)
        server.on(CMD_ENTER_MAP, self.enter_map)
        server.on(CMD_LEAVE_MAP_STATE, self.leave_map_state)
        server.on(CMD_ACTIVATE_GOODS_LIST, self.activate_goods_list)
        server.on(CMD_SYNTHETIC_GAME_REQUEST_START, self.synthetic_game_request_start)
        server.on(CMD_SYNTHETIC_GAME_RESULT, self.synthetic_game_result)
        server.on(CMD_FLOWER_GAME_REQUIRE_START, self.flower_game_require_start)
        server.on(CMD_FLOWER_GAME_REQUIRE_END, self.flower_game_require_end)
        server.on(CMD_FLOWER_GAME_AWARD_SELECTED, self.flower_game_award_selected)
        server.on(CMD_PVE_GAME_START_COMMON_COMMAND, self.pve_game_start)
        server.on(CMD_PVE_GAME_OVER_COMMON_COMMAND, self.pve_game_over)
        server.on(CMD_SELF_MOVE, self.self_move)
        server.on(CMD_NOTICE_INFO, self.ignore)
        server.on(CMD_CHANG_NICK, self.change_nick)
        server.on(CMD_FRIEND_LIST, self.friend_list)
        server.on(CMD_FRIEND_ASK, self.friend_ask)
        server.on(CMD_FRIEND_ANS, self.friend_ans)
        server.on(CMD_FRIEND_DEL, self.friend_del)
        server.on(CMD_FRIEND_SET_TEAM, self.friend_set_team)
        server.on(CMD_BLACK_FRIEND_LIST, self.black_friend_list)
        server.on(CMD_BLACK_FRIEND_ADD, self.black_friend_add)
        server.on(CMD_BLACK_FRIEND_DEL, self.black_friend_del)
        server.on(CMD_FIND_FRIEND, self.find_friend)
        server.on(CMD_FRIEND_ALLOW_SET, self.friend_allow_set)
        server.on(CMD_GAME_CLIENT_DATA_ACCOUNT, self.game_client_data_account)
        server.on(CMD_CHAT_INFO, self.chat_info)
        server.on(CMD_MEDAL_FAVOR, self.medal_favor)
        server.on(CMD_FAIRY_ACTION, self.fairy_action)
        server.on(CMD_GET_MY_MONEY, self.get_my_money)
        server.on(CMD_SELL_MY_FLOWER, self.sell_my_flower)
        server.on(CMD_SHOP_HALF_DAY, self.shop_half_day)
        server.on(CMD_GET_ITEM, self.get_item)
        server.on(CMD_PICK_UP_JOB, self.pick_up_job)
        server.on(CMD_PICK_UP_MAP, self.pick_up_map)
        server.on(CMD_USE_GOOD, self.use_good)
        server.on(CMD_START_JOB, self.start_job)
        server.on(CMD_OVER_JOB, self.over_job)
        server.on(CMD_JOB_REQ_EVENT, self.job_req_event)
        server.on(CMD_ITEM_TYPE_INFO, self.item_type_info)
        server.on(CMD_CHECK_ITEM, self.check_item)
        server.on(CMD_CHECK_USER_BG, self.check_user_bg)
        server.on(CMD_CHECK_ALL_USER_BG, self.check_all_user_bg)
        server.on(CMD_PET_BASE_INFO, self.pet_base_info)
        server.on(CMD_GET_SLEF_SIMPLE_HUABAO, self.self_simple_huabao)
        server.on(CMD_HOME_PET_INFO, self.home_pet_info)
        server.on(CMD_PET_FOLLOW, self.pet_follow)
        server.on(CMD_PET_USETOOL, self.pet_use_tool)
        server.on(CMD_PET_BACK, self.pet_back)
        server.on(CMD_PET_CHANG_NICK, self.pet_change_nick)
        server.on(CMD_PET_IN_ORPHANAGE, self.pet_in_orphanage)
        server.on(CMD_PETLETTER_LIST_TASK, self.pet_letter_list_task)
        server.on(CMD_PETLETTER_LIST_MOOD, self.pet_letter_list_mood)
        server.on(CMD_PETLETTER_READ_MOOD, self.pet_letter_read_mood)
        server.on(CMD_PETLETTER_REPLY, self.pet_letter_reply)
        server.on(CMD_PETLETTER_DELETE_MOOD, self.pet_letter_delete_mood)
        server.on(CMD_PETLETTER_REPLY_CONTENT, self.pet_letter_reply_content)
        server.on(CMD_HOME_DEPOT, self.home_depot)
        server.on(CMD_HOME_ADD_POT, self.home_add_pot)
        server.on(CMD_HOME_ADD_PLANT, self.home_add_plant)
        server.on(CMD_HOME_PLANT_TOOL, self.home_plant_tool)
        server.on(CMD_HOME_BACK_POT, self.home_back_pot)
        server.on(CMD_HOME_ADD_HOUSE, self.home_add_house)
        server.on(CMD_HOME_BACK_HOUSE, self.home_back_house)
        server.on(CMD_HOME_UPDATE_HOUSE, self.home_update_house)
        server.on(CMD_HOME_UPDATE_PLANT, self.home_update_plant)
        server.on(CMD_HOME_TOOL_ADD, self.home_tool_add)
        server.on(CMD_HOME_CHANGE_BG, self.home_change_background)
        server.on(CMD_HOME_PICK_DUST, self.home_pick_dust)
        server.on(CMD_HOME_ONEKEY_PICK_DUST, self.home_onekey_pick_dust)
        server.on(CMD_HOUSE_ADD_GOODS, self.house_add_goods)
        server.on(CMD_HOUSE_DEL_GOODS, self.house_del_goods)
        server.on(CMD_HOUSE_DEPOT, self.house_depot)
        server.on(CMD_HOUSE_UPDATE, self.house_update)
        server.on(CMD_PEOPLE_TRANSFORM, self.people_transform)
        server.on(CMD_ONE_BASE_INFO, self.one_base)
        server.on(CMD_CHAT_SAVE_WORDS, self.chat_save_words)
        server.on(CMD_CLOTH_INFO, self.cloth_info)
        server.on(CMD_SUITING_INFO, self.suiting_info)
        server.on(CMD_SUITING_ADD, self.suiting_add)
        server.on(CMD_SUITING_DELETE, self.suiting_delete)
        server.on(CMD_CLOTH_CHANGE, self.cloth_change)
        server.on(CMD_SERVER_TIMER, self.timer)
        server.on(CMD_SECRETPROTECTED_HINT, self.secret_protected_hint)
        server.on(CMD_EXT_INFO, self.ext_info)
        server.on(CMD_MINIPARTY, self.miniparty_state)
        server.on(CMD_TASK_LIST, self.tasks)
        server.on(CMD_NPC_JOBS, self.npc_jobs)
        server.on(CMD_PUPPET_MANAGER_PUPPET_INFO, self.puppet_info)
        server.on(CMD_DOLLS_MAKE_TROUBLE_INFO, self.dolls_make_trouble_info)
        server.on(CMD_MEDAL_PROGRESS, self.medal_progress)
        server.on(CMD_CHECK_MEDAL_FLAGS, self.check_medal_flags)
        server.on(CMD_MEDAL_HAVE_ONE, self.medal_have_one)
        server.on(CMD_THREE_DAY_REWARD_STATE, self.three_day_reward_state)
        server.on(CMD_SOMEONE_MEDALS, self.someone_medals)
        server.on(CMD_BEAUTY_GET_MYINFO, self.beauty_get_myinfo)
        server.on(CMD_LIST_MAP_PLAYER, self.map_players)
        server.on(CMD_MAP_GET_PICKITEM, self.map_items)
        server.on(CMD_SYNC_USERS_EXTINFO, self.sync_users_extinfo)
        server.on(CMD_USER_EXTINFO_UPDATE_NOTICE, self.ignore)

    def _account(self, s, p):
        token = p.payload[:16]
        if self.sessions.valid(token, p.user_id):
            return self.accounts.get_by_id(p.user_id)
        else:
            return None

    def _social_account(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return None
        return account

    def _online_id(self, user_id: int) -> int:
        for peer in list(self.online_sessions):
            peer_account = peer.state.get("account")
            if peer_account and int(peer_account.user_id) == int(user_id) and not peer.writer.is_closing():
                return _u32(_profile_value(peer_account, "online_id", 1)) or 1
        return 0

    def _relation_payload_rows(self, owner_id: int, statuses, limit: int):
        rows = []
        for relation in self.accounts.friend_rows(owner_id, statuses, limit):
            friend_team = int(relation.get("status", FRIEND_STATUS_FRIEND))
            row = self.accounts.friend_user_row(relation.get("friend_user_id"), friend_team)
            if row is None:
                continue
            row["online_id"] = self._online_id(row["user_id"])
            rows.append(row)
        return rows

    def _profile_row(self, account):
        row = dict(account.profile or {})
        row.setdefault("user_id", account.user_id)
        row.setdefault("nickname", account.login_name)
        return row

    async def _push_friend_request(self, target_user_id: int, sender_account):
        sender = self._profile_row(sender_account)
        try:
            if (self.accounts.is_blacklisted(target_user_id, sender_account.user_id)
                    or self.accounts.is_blacklisted(sender_account.user_id, target_user_id)):
                return False
        except Exception as exc:
            LOG.warning("friend request blacklist check failed for uid=%s target=%s: %s",
                        sender_account.user_id, target_user_id, exc)
        payload = friend_request_notice_payload(sender)
        peers = list(self.online_sessions)
        LOG.info(
            "FRIEND_ASK push target=%s sender=%s sessions=%d",
            target_user_id,
            sender_account.user_id,
            len(peers),
        )
        for peer in peers:
            peer_account = peer.state.get("account")
            if (peer_account and int(peer_account.user_id) == int(target_user_id)
                    and not peer.writer.is_closing()):
                LOG.info(
                    "FRIEND_ASK push 1005 target=%s sender=%s peer=%s",
                    target_user_id,
                    sender_account.user_id,
                    peer.peer,
                )
                await peer.send_response(CMD_NOTICE_INFO, user_id=sender_account.user_id, payload=payload)
                return True
        LOG.info("FRIEND_ASK target=%s is not an active online session", target_user_id)
        return False

    def friend_list(self, session, packet):
        """Return intimate friends (11) and friends (10) in one relation list.

        The AS3 client reads one count followed by fixed UserInfo records and
        separates them by FriendTeam.  Current-scene users are command 1004;
        recent contacts are maintained locally by SaveUserInfo.
        """
        account = self._social_account(session, packet)
        if account is None or packet.payload:
            return Response(user_id=packet.user_id, status=401 if account is None else 400)
        intimate = self._relation_payload_rows(account.user_id, (FRIEND_STATUS_INTIMATE,), 30)
        friends = self._relation_payload_rows(account.user_id, (FRIEND_STATUS_FRIEND,), 70)
        return Response(friend_info_payload(intimate + friends), user_id=account.user_id)

    def black_friend_list(self, session, packet):
        account = self._social_account(session, packet)
        if account is None or packet.payload:
            return Response(user_id=packet.user_id, status=401 if account is None else 400)
        rows = self._relation_payload_rows(account.user_id, (FRIEND_STATUS_BLACKLIST,), 30)
        return Response(friend_info_payload(rows), user_id=account.user_id)

    def black_friend_add(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        friend_user_id = struct.unpack(">I", packet.payload)[0]
        try:
            changed = self.accounts.add_black_friend(account.user_id, friend_user_id)
        except Exception as exc:
            LOG.warning("BLACK_FRIEND_ADD failed for uid=%s target=%s: %s",
                        account.user_id, friend_user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def black_friend_del(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        friend_user_id = struct.unpack(">I", packet.payload)[0]
        try:
            changed = self.accounts.delete_black_friend(account.user_id, friend_user_id)
        except Exception as exc:
            LOG.warning("BLACK_FRIEND_DEL failed for uid=%s target=%s: %s",
                        account.user_id, friend_user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def find_friend(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        target_user_id = struct.unpack(">I", packet.payload)[0]
        target = next(
            (peer for peer in list(self.online_sessions)
             if not peer.writer.is_closing()
             and peer.state.get("account") is not None
             and int(peer.state["account"].user_id) == int(target_user_id)),
            None,
        )
        if target is None:
            payload = struct.pack(">5I", 0, 0, 0, 0, 0)
        else:
            scene_kind = target.state.get("scene_kind", "outdoor")
            if scene_kind == "home":
                map_type = 1
            elif scene_kind == "house":
                map_type = int(target.state.get("house_id", 0))
            else:
                map_type = 0
            payload = struct.pack(
                ">5I", 1, map_type,
                int(target.state.get("map_id", 0)) & 0xFFFFFFFF,
                int(target.state.get("map_x", 0)) & 0xFFFFFFFF,
                int(target.state.get("map_y", 0)) & 0xFFFFFFFF,
            )
        return Response(payload, user_id=account.user_id)

    async def friend_ask(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        target_user_id = struct.unpack(">I", packet.payload)[0]
        try:
            status = self.accounts.add_friend_request(account.user_id, target_user_id)
        except Exception as exc:
            LOG.warning("FRIEND_ASK failed for uid=%s target=%s: %s", account.user_id, target_user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        if status == 0:
            try:
                await self._push_friend_request(target_user_id, account)
            except Exception as exc:
                LOG.warning("FRIEND_ASK notice push failed for uid=%s target=%s: %s",
                            account.user_id, target_user_id, exc)
        return Response(user_id=account.user_id, status=status)

    def friend_ans(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        # FRIEND_ANS is sent with uint32 id, 16-byte nickname, six appearance
        # uint32 values, and type (0 accept, 1 reject).
        if len(packet.payload) != 4 + 16 + 6 * 4 + 4:
            return Response(user_id=account.user_id, status=400)
        requester_id = struct.unpack_from(">I", packet.payload, 0)[0]
        answer = struct.unpack_from(">I", packet.payload, 44)[0]
        try:
            status = self.accounts.answer_friend_request(account.user_id, requester_id, 0 if answer else 1)
        except Exception as exc:
            LOG.warning("FRIEND_ANS failed for uid=%s requester=%s: %s", account.user_id, requester_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=status)

    def friend_set_team(self, session, packet):
        """Move a friend between the regular (10) and intimate (11) lists."""
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        friend_user_id, friend_status = struct.unpack(">2I", packet.payload)
        if friend_status not in (FRIEND_STATUS_FRIEND, FRIEND_STATUS_INTIMATE):
            return Response(user_id=account.user_id, status=400)
        try:
            changed = self.accounts.set_friend_status(account.user_id, friend_user_id, friend_status)
        except Exception as exc:
            LOG.warning("FRIEND_SET_TEAM failed for uid=%s friend=%s: %s",
                        account.user_id, friend_user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def friend_del(self, session, packet):
        """Remove both directional rows for the requested friend (1009)."""
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        friend_user_id = struct.unpack(">I", packet.payload)[0]
        try:
            deleted = self.accounts.delete_friend(account.user_id, friend_user_id)
        except Exception as exc:
            LOG.warning("FRIEND_DEL failed for uid=%s friend=%s: %s",
                        account.user_id, friend_user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if deleted else 404)

    def game_client_data_account(self, session, packet):
        """1229 is a client analytics event; its response is not consumed."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        return Response(user_id=account.user_id)

    def get_my_money(self, session, packet):
        """Return the authenticated player's current shop balance (1105)."""
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        try:
            money = self.accounts.money(account.user_id)
        except Exception:
            LOG.exception("GET_MY_MONEY query failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(struct.pack(">I", money), user_id=account.user_id)

    def get_item(self, session, packet):
        """Buy a shop item and return the item id and quantity (1017)."""
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        item_id, quantity = struct.unpack(">2I", packet.payload)
        try:
            status, purchased_id, purchased_quantity = self.accounts.buy_shop_item(
                account.user_id, item_id, quantity
            )
        except Exception:
            LOG.exception("GET_ITEM purchase failed for uid=%s item=%s quantity=%s",
                          account.user_id, item_id, quantity)
            return Response(user_id=account.user_id, status=5001)
        if status:
            return Response(user_id=account.user_id, status=status)
        return Response(
            struct.pack(">2I", purchased_id, purchased_quantity),
            user_id=account.user_id,
        )

    def sell_my_flower(self, session, packet):
        """Sell flowers through SELL_MY_FLOWER (1106)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)

        _unknown, flower_id, amount = struct.unpack(">3I", packet.payload)
        try:
            status, income = self.accounts.sell_flower(account.user_id, flower_id, amount)
        except Exception as exc:
            LOG.exception(
                "SELL_MY_FLOWER failed for uid=%s flower=%s amount=%s: %s",
                account.user_id, flower_id, amount, exc,
            )
            return Response(user_id=account.user_id, status=5001)
        if status:
            return Response(user_id=account.user_id, status=status)
        # SellModule.gotmoney reads exactly one uint32: this sale's income.
        return Response(struct.pack(">I", income), user_id=account.user_id)

    def shop_half_day(self, session, packet):
        """Return whether the requested shop is half-price today (1045)."""
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        shop_id = struct.unpack(">I", packet.payload)[0]
        # ShopXML defines shop IDs 1 through 16. The response is a single
        # uint32 flag; the per-category eligibility remains client-side.
        if not 1 <= shop_id <= 16:
            return Response(user_id=account.user_id, status=400)
        active = self.shop_half_price_day > 0 and date.today().day == self.shop_half_price_day
        return Response(struct.pack(">I", int(active)), user_id=account.user_id)

    def friend_allow_set(self, session, packet):
        account = self._social_account(session, packet)
        if account is None:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        # 1002/LOGIN_IN expose the historical inverted Friend_flag wire value:
        # zero means the player accepts friend applications.
        wire_flag = struct.unpack(">I", packet.payload)[0]
        enabled = 1 if wire_flag == 0 else 0
        try:
            self.accounts.set_friends_application(account.user_id, enabled)
        except Exception as exc:
            LOG.warning("FRIEND_ALLOW_SET failed for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        session.state["account"] = replace(
            account, profile={**(account.profile or {}), "enable_friends_application": enabled,
                              "friend_flag": wire_flag}
        )
        return Response(user_id=account.user_id)

    def login_in(self, session, packet):
        account = self._account(session, packet)
        if not account:
            return Response(user_id=packet.user_id,status=401)
        try:
            account = Account(account.user_id, account.login_name, account.password_hash, account.role_created, account.banned, {**(account.profile or {}), **self.accounts.profile(account.user_id)})
        except Exception:
            pass
        # Keep the profile location in session state so subsequent map-cache
        # requests can select ``map:<id>:players`` before ENTER_MAP arrives.
        session.state.update(
            user_id=account.user_id,
            account=account,
            map_id=_u32(_profile_value(account, "map_id", 1)),
            house_id=0,
            map_x=_u32(_profile_value(account, "map_x", 480)),
            map_y=_u32(_profile_value(account, "map_y", 280))
        )
        session.state["on_disconnect"] = self.on_session_disconnected
        session.state["map_registered"] = True
        session.state["map_announced"] = False
        self.online_sessions.add(session)
        self._store_map_player(session)
        return Response(log_in_payload(account), user_id=account.user_id)

    def get_reg_sign(self, session, packet):
        """Issue the 16-byte token consumed by NoticeLogic's bus redirect.

        GET_REG_SIGN has no request payload.  The original service returns an
        opaque value (not a player-profile field); keeping it on the TCP
        session also prevents one player's token from being reused by another
        connection.  A new token is intentionally issued for every request,
        matching SessionManager's periodic refresh behavior.
        """
        account = session.state.get("account")
        if account is None or int(getattr(account, "user_id", -1)) != int(packet.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            # The AS3 call is SocketConnection.send(GET_REG_SIGN) with no
            # arguments.  Ignore malformed trailing bytes rather than making
            # the response shape ambiguous.
            LOG.debug("GET_REG_SIGN received unexpected payload length=%d", len(packet.payload))
        sign = secrets.token_bytes(16)
        session.state["reg_sign"] = sign
        session.state["reg_sign_time"] = int(time.time())
        return Response(sign, user_id=packet.user_id)

    def notice_unline_info(self, session, packet):
        """Return pending friend requests as embedded NOTICE_INFO frames.

        Res_NOTICE_UNLINE_INFO starts with ``Cnt:uint32`` and then embeds
        command headers plus payloads.  Each embedded ``Len`` is the complete
        TMF frame length, while the embedded bytes omit that frame's first
        four-byte length prefix.  Pending player_friends rows are represented
        by nested command 1005 records so NoticeLogic handles them identically
        to online notifications.
        """
        account = session.state.get("account")
        # SocketConnection.send(NOTICE_UNLINE_INFO) has no arguments. Some
        # client builds leave the request header user id as zero, so the
        # authenticated session is authoritative in that case.
        if account is None or packet.user_id not in (0, int(getattr(account, "user_id", -1))):
            return Response(user_id=packet.user_id, status=401)
        notices = []
        try:
            for relation in self.accounts.incoming_friend_requests(account.user_id):
                requester = self.accounts.get_by_id(int(relation["owner_user_id"]))
                if requester:
                    notices.append(friend_request_notice_payload(self._profile_row(requester)))
        except Exception as exc:
            LOG.warning("offline friend notice query failed for uid=%s: %s", account.user_id, exc)
        payload = bytearray(struct.pack(">I", len(notices)))
        for notice in notices:
            nested = session.codec.encode_response(CMD_NOTICE_INFO, user_id=account.user_id, payload=notice)
            # Res_NOTICE_UNLINE_INFO reads Len as the complete TMF frame
            # length (including its four-byte prefix), but it starts parsing
            # the embedded bytes at the version byte.  Therefore keep Len as
            # len(nested) while omitting nested[0:4] from the embedded body.
            nested_body = nested[4:]
            payload += struct.pack(">I", len(nested))
            payload += nested_body
        LOG.info(
            "NOTICE_UNLINE_INFO uid=%s pending=%d payload_len=%d",
            account.user_id,
            len(notices),
            len(payload),
        )
        return Response(bytes(payload), user_id=account.user_id)

    def location(self, s, p):
        """Accept the post-login ClientConfig.REG_location report (2163).

        MainEntry sends one uint32 roughly five seconds after connecting and
        does not install a callback.  The original server still acknowledges
        it with a normal empty success packet, as shown in the capture.
        """
        a = s.state.get('account')
        location = struct.unpack_from('>I', p.payload, 0)[0] if len(p.payload) >= 4 else 0
        uid = int(getattr(a, 'user_id', p.user_id)) if a else p.user_id
        s.state['login_location'] = location
        if a:
            try:
                self.accounts.set_login_location(uid, location)
            except Exception as exc:
                # The optional table may not have been migrated yet; the
                # in-session value still preserves the report for this login.
                LOG.warning("LOGIN_LOCATION persistence failed for uid=%s: %s", uid, exc)
        return Response(b'', user_id=uid)

    def once_flag(self, s, p):
        """Read one per-player one-time flag (1880).

        The client reads exactly one byte from the response and treats any
        non-zero value as already seen.
        """
        a = s.state.get('account')
        uid = int(getattr(a, 'user_id', p.user_id)) if a else p.user_id
        flag_id = struct.unpack_from('>I', p.payload, 0)[0] if len(p.payload) >= 4 else 0
        value = 0
        if a and flag_id:
            try:
                value = self.accounts.get_once_flag(uid, flag_id)
            except Exception as exc:
                value = int(s.state.get('once_flags', {}).get(flag_id, 0))
                LOG.warning("COMMON_ONCE_FLAG query failed for uid=%s flag=%s: %s", uid, flag_id, exc)
        return Response(bytes((1 if value else 0,)), user_id=uid)

    def set_once_flag(self, s, p):
        """Set a one-time flag; this command is normally fire-and-forget."""
        a = s.state.get('account')
        uid = int(getattr(a, 'user_id', p.user_id)) if a else p.user_id
        flag_id = struct.unpack_from('>I', p.payload, 0)[0] if len(p.payload) >= 4 else 0
        if flag_id:
            s.state.setdefault('once_flags', {})[flag_id] = 1
            if a:
                try:
                    self.accounts.set_once_flag(uid, flag_id, 1)
                except Exception as exc:
                    LOG.warning("COMMON_SET_FLAG persistence failed for uid=%s flag=%s: %s", uid, flag_id, exc)
        # SocketConnection.send has no callback, but an empty success response
        # is harmless and keeps the wire behavior conventional.
        return Response(b'', user_id=uid)

    def set_new_user_job(self, session, packet):
        """Persist the new-user tutorial step sent by NewUserJob.swf (1040)."""
        account = session.state.get('account')
        if account is None or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        new_user_job = struct.unpack('>I', packet.payload)[0]
        try:
            self.accounts.set_new_user_job(account.user_id, new_user_job)
        except Exception as exc:
            LOG.warning("SET_NEWUSERJOB persistence failed for uid=%s value=%s: %s",
                        account.user_id, new_user_job, exc)
            return Response(user_id=account.user_id, status=5001)
        session.state['account'] = replace(
            account,
            profile={**(account.profile or {}), 'new_user_job': new_user_job},
        )
        return Response(user_id=account.user_id)

    async def enter_map(self,s,p):
        a = s.state.get('account')
        # Some captures show user_id=0 in the request header.  The logged-in
        # session remains authoritative while a non-zero mismatching ID is
        # still rejected.
        if not a or (p.user_id not in (0, a.user_id)) or len(p.payload) < 16:
            return Response(user_id=p.user_id, status=401)
        vals = struct.unpack('>4I', p.payload[:16])
        scene_type, destination_id, map_x, map_y = vals
        was_registered = bool(s.state.get("map_registered"))
        was_announced = bool(s.state.get("map_announced"))
        is_home = scene_type == 1
        is_house = scene_type > 400000
        old_scope = self._map_scope(s)
        new_scope = (int(destination_id), int(scene_type) if is_house else 0)
        if was_registered and ((is_home or is_house) or old_scope != new_scope):
            self._remove_map_player(s, old_scope)
            s.state["map_registered"] = False
            s.state["map_announced"] = False
            await self._broadcast_map(
                old_scope,
                CMD_LEAVE_MAP,
                struct.pack(">I", a.user_id),
                s,
                a.user_id,
            )
        s.state['map_id'], s.state['house_id'] = destination_id, scene_type if is_house else 0
        s.state['scene_kind'] = "house" if is_house else "home" if is_home else "outdoor"
        s.state['map_scope'] = new_scope
        s.state['map_x'], s.state['map_y'] = map_x, map_y

        # Home.requestHomeInfo sends ENTER_MAP(1, owner_uid, 480, 280).  The
        # live service acknowledges 1002 with an empty payload, then pushes
        # home, house and tool state as three separate command frames.
        if is_home:

            s.state['home_owner_id'] = destination_id
            try:
                home, plants, houses, tools = self.accounts.home_state(destination_id)
            except Exception as exc:
                LOG.warning("home-state query failed for owner=%s: %s", destination_id, exc)
                home, plants, houses, tools = {}, [], [], []

            home.setdefault('user_id', destination_id)
            if not home.get('home_name'):
                try:
                    owner = self.accounts.get_by_id(destination_id)
                except Exception:
                    owner = None
                if owner:
                    home['home_name'] = str(_profile_value(owner, 'nickname', owner.login_name))
                else:
                    home['home_name'] = str(destination_id)

            # A home is still a shared player-map scope.  Register the
            # visitor before returning the home data so LIST_MAP_PLAYER can
            # include them and existing visitors receive ENTER_MAP.  The
            # previous early return skipped both operations, which made
            # players in homes invisible while outdoor maps and houses worked.
            profile = dict(a.profile or {})
            profile.update(
                user_id=a.user_id,
                map_id=destination_id,
                map_x=map_x,
                map_y=map_y,
            )
            s.state["map_registered"] = True
            s.state["map_announced"] = True
            self._store_map_player(s)
            if not was_announced or old_scope != new_scope:
                await self._broadcast_map(
                    new_scope,
                    CMD_ENTER_MAP,
                    _enter_map_eff_payload(profile),
                    s,
                    a.user_id,
                )

            return [
                Response(b'', command_id=CMD_ENTER_MAP, user_id=a.user_id),
                Response(home_info_payload(home, plants), command_id=CMD_HOME_INFO, user_id=0),
                Response(home_house_payload(houses), command_id=CMD_HOME_HOUSE_INFO, user_id=0),
                Response(home_tool_payload(tools), command_id=CMD_HOME_TOOL_INFO, user_id=0),
            ]

        if is_house:
            owner_id = int(destination_id)
            house_id = int(scene_type)
            try:
                goods = self.accounts.house_goods(owner_id)
                resting_pets = self.accounts.pet_rows(owner_id, 2)
            except Exception as exc:
                LOG.warning("house-state query failed for owner=%s: %s", owner_id, exc)
                goods = []
                resting_pets = []

            profile = dict(a.profile or {})
            profile.update(
                user_id=a.user_id,
                map_id=owner_id,
                map_x=map_x,
                map_y=map_y,
            )
            s.state["map_registered"] = True
            s.state["map_announced"] = True
            self._store_map_player(s)
            if not was_announced or old_scope != new_scope:
                await self._broadcast_map(
                    new_scope,
                    CMD_ENTER_MAP,
                    _enter_map_eff_payload(profile),
                    s,
                    a.user_id,
                )

            return [
                Response(b"", command_id=CMD_ENTER_MAP, user_id=a.user_id),
                Response(
                    house_info_payload(owner_id, house_id, goods),
                    command_id=CMD_HOUSE_INFO,
                    user_id=0,
                ),
                Response(
                    pet_inhouse_info_payload(resting_pets),
                    command_id=CMD_PET_INHOUSE_INFO,
                    user_id=0,
                ),
            ]

        profile = dict(a.profile or {})
        profile.update(user_id=a.user_id, map_id=destination_id, map_x=map_x, map_y=map_y)
        s.state["map_registered"] = True
        s.state["map_announced"] = True
        self._store_map_player(s)
        if not was_announced or old_scope != new_scope:
            await self._broadcast_map(
                destination_id,
                CMD_ENTER_MAP,
                _enter_map_eff_payload(profile),
                s,
                a.user_id,
            )
        # ENTER_MAP carries a Res_ENTER_MAP_EFF record.  It is consumed by
        # PeopleLogic.oneInMap, including the self player's multi-effect list.
        return Response(_enter_map_eff_payload(profile), user_id=a.user_id)

    async def leave_map_state(self, session, packet):
        """Acknowledge the transition from a map into a mini-game.

        The AS3 client waits for the successful 1037 response before it
        starts loading the game's SWF.  The request contains one uint (the
        game/state id); the response itself has no body.
        """
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)

        map_scope = self._map_scope(session)
        if session.state.get("map_registered"):
            self._remove_map_player(session, map_scope)
            session.state["map_registered"] = False
            session.state["map_announced"] = False
            await self._broadcast_map(
                map_scope,
                CMD_LEAVE_MAP,
                struct.pack(">I", account.user_id),
                session,
                account.user_id,
            )
        return Response(user_id=account.user_id)

    def activate_goods_list(self, session, packet):
        account = self._social_account(session, packet)
        if not account:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        game_id = struct.unpack(">I", packet.payload)[0]
        try:
            rows = self.accounts.synthetic_games.activated_goods(account.user_id, game_id)
            return Response(activate_goods_payload(rows), user_id=account.user_id)
        except SyntheticGameError:
            return Response(user_id=account.user_id, status=400)
        except Exception:
            LOG.exception("ACTIVATE_GOODS_LIST failed for uid=%s game=%s", account.user_id, game_id)
            return Response(user_id=account.user_id, status=RESULT_SYSTEM_ERROR)

    def synthetic_game_request_start(self, session, packet):
        account = self._social_account(session, packet)
        if not account:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        item_id, mode = struct.unpack(">2I", packet.payload)
        token = session.state.setdefault("synthetic_game_token", secrets.token_hex(32))
        try:
            result = self.accounts.synthetic_games.start(account.user_id, item_id, mode, token)
            return Response(synthetic_start_payload(result), user_id=account.user_id)
        except SyntheticGameError:
            return Response(user_id=account.user_id, status=400)
        except Exception:
            LOG.exception("SYNTHETIC_GAME_REQUEST_START failed for uid=%s item=%s", account.user_id, item_id)
            return Response(user_id=account.user_id, status=RESULT_SYSTEM_ERROR)

    def synthetic_game_result(self, session, packet):
        account = self._social_account(session, packet)
        if not account:
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4 or "synthetic_game_token" not in session.state:
            return Response(user_id=account.user_id, status=400)
        score = struct.unpack(">I", packet.payload)[0]
        try:
            result = self.accounts.synthetic_games.finish(account.user_id, score, session.state["synthetic_game_token"])
            # Keep the online profile in sync with the attribute already committed
            # to MySQL. The client also applies this increment from ScoreDecoder.
            for exp_type, column in ATTRIBUTE_BY_GAME.values():
                if result[1] == exp_type:
                    account.profile[column] = int(account.profile.get(column) or 0) + result[2]
                    break
            return Response(synthetic_score_payload(result), user_id=account.user_id)
        except SyntheticGameError:
            return Response(user_id=account.user_id, status=400)
        except Exception:
            LOG.exception("SYNTHETIC_GAME_RESULT failed for uid=%s score=%s", account.user_id, score)
            return Response(user_id=account.user_id, status=RESULT_SYSTEM_ERROR)

    # MusicWavePanel sends game id 13, caps scores at 9999, and promises a
    # reward at 1000 points. The original reward contents are server-side
    # and cannot be recovered from AS3; this is an adjustable local policy.
    MUSIC_WAVE_GAME_ID = 13
    MUSIC_WAVE_MIN_SCORE = 1000
    MUSIC_WAVE_MAX_SCORE = 9999
    MUSIC_WAVE_REWARDS = ((1600001, 1),)

    def pve_game_start(self, session, packet):
        """1633: remember MusicWave's game id and acknowledge with no body."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        game_id = struct.unpack(">I", packet.payload)[0]
        if game_id != self.MUSIC_WAVE_GAME_ID or "pve_game_id" in session.state:
            return Response(user_id=account.user_id, status=400)
        session.state["pve_game_id"] = game_id
        return Response(user_id=account.user_id)

    def pve_game_over(self, session, packet):
        """1634: game id, reward count, then (item id, amount) uint32 pairs."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        game_id = session.state.get("pve_game_id")
        score = struct.unpack(">I", packet.payload)[0]
        if game_id != self.MUSIC_WAVE_GAME_ID or score > self.MUSIC_WAVE_MAX_SCORE:
            return Response(user_id=account.user_id, status=400)
        rewards = self.MUSIC_WAVE_REWARDS if score >= self.MUSIC_WAVE_MIN_SCORE else ()
        payload = struct.pack(">2I", game_id, len(rewards))
        payload += b"".join(struct.pack(">2I", item_id, amount) for item_id, amount in rewards)
        if rewards:
            try:
                self.accounts.add_pve_game_rewards(account.user_id, rewards)
            except Exception:
                LOG.exception("PVE_GAME_OVER failed for uid=%s game=%s score=%s",
                              account.user_id, game_id, score)
                return Response(user_id=account.user_id, status=RESULT_SYSTEM_ERROR)
        # Keep the run on DB failure so the client can retry. Successful
        # settlement, including quitting with score 0, consumes it once.
        session.state.pop("pve_game_id")
        return Response(payload, user_id=account.user_id)

    def flower_game_require_start(self, session, packet):
        """Acknowledge the client's request to start the loaded mini-game.

        The AS3 ``FlowerGameStartDecoder`` has no fields, so a successful
        response is a 1063 frame with result 0 and an empty payload.  The
        request carries the game id as one uint32; it is retained in session
        state for logging/game handlers but is otherwise client-selected.
        """
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)

        session.state["flower_game_id"] = struct.unpack(">I", packet.payload)[0]
        return Response(user_id=account.user_id)

    # The original client has no local score-to-reward table.  It always reads
    # three uint32 pairs from 1064, so keep exactly three slots in every tier;
    # zero pairs are the protocol's representation of "no reward".
    FLOWER_GAME_REWARD_TIERS = (
        (0, ()),
        (1000, ((1600001, 1), (1600002, 1), (1600003, 1))),
        (5000, ((1600001, 5), (1600002, 5), (1600003, 5))),
        (10000, ((1600001, 10), (1600002, 5), (1600003, 10))),
    )

    @classmethod
    def _flower_game_rewards(cls, score: int):
        """Return three reward slots for a score, padding empty slots."""
        selected = ()
        for lower_bound, rewards in cls.FLOWER_GAME_REWARD_TIERS:
            if score >= lower_bound:
                selected = rewards
        return tuple(selected)[:3] + ((0, 0),) * (3 - len(selected))

    @staticmethod
    def _flower_game_payload(rewards) -> bytes:
        return b"".join(struct.pack(">2I", int(item_id), int(amount)) for item_id, amount in rewards)

    def flower_game_require_end(self, session, packet):
        """Return the three reward choices for the score sent by the client."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        score = struct.unpack(">I", packet.payload)[0]
        rewards = self._flower_game_rewards(score)
        # Save the complete candidate list, including zero slots, so 1065 can
        # only grant an item returned by this particular 1064 response.
        session.state["flower_game_score"] = score
        session.state["flower_game_awards"] = rewards
        return Response(self._flower_game_payload(rewards), user_id=account.user_id)

    def flower_game_award_selected(self, session, packet):
        """Grant one selected 1064 item and consume the pending choice."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        item_id = struct.unpack(">I", packet.payload)[0]
        pending = session.state.get("flower_game_awards")
        if not pending:
            return Response(user_id=account.user_id, status=400)
        reward = next(((rid, amount) for rid, amount in pending
                       if rid == item_id and amount > 0), None)
        if reward is None:
            return Response(user_id=account.user_id, status=400)
        try:
            self.accounts.add_flower_game_reward(account.user_id, *reward)
        except Exception:
            LOG.exception("FLOWER_GAME_AWARD_SELECTED failed for uid=%s item=%s",
                          account.user_id, item_id)
            return Response(user_id=account.user_id, status=5001)
        session.state.pop("flower_game_awards", None)
        session.state.pop("flower_game_score", None)
        return Response(user_id=account.user_id)

    def _map_player_row(self, session):
        account = session.state.get("account")
        profile = account.profile or {}
        fields = (
            "vip_level", "action", "action_other", "nationality", "nickname",
            "face_color", "face", "eye", "eyebrow", "lip", "title_id",
            "tool", "headdress", "mask", "hair", "earring", "necklace",
            "belt", "cloth", "bangle", "shoes", "anklet", "skirt", "wing",
            "faerie_follow_id", "pet_action", "pet_adoption",
        )
        row = {key: profile[key] for key in fields if key in profile}
        row["pet"] = profile.get("pet")
        row.update(
            user_id=account.user_id,
            map_id=_u32(session.state.get("map_id", 0)),
            map_x=_u32(session.state.get("map_x", 480)),
            map_y=_u32(session.state.get("map_y", 280)),
        )
        return row

    async def change_nick(self, session, packet):
        response = self._change_nick(session, packet)
        if hasattr(response, "__await__"):
            await response
            account = session.state.get("account")
            return Response(struct.pack(">I", account.user_id) + fixed_utf8(account.profile.get("nickname", ""), 16), user_id=account.user_id)
        return response

    def _change_nick(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) > 16 or not packet.payload:
            return Response(user_id=account.user_id, status=400)
        try:
            nickname = packet.payload.split(b"\x00", 1)[0].decode("utf-8")
        except UnicodeDecodeError:
            return Response(user_id=account.user_id, status=400)
        if not nickname:
            return Response(user_id=account.user_id, status=400)
        try:
            changed = self.accounts.rename_player(account.user_id, nickname)
        except Exception:
            LOG.exception("CHANG_NICK failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        if not changed:
            return Response(user_id=account.user_id, status=404)
        fresh = self.accounts.profile(account.user_id)
        session.state["account"] = replace(account, profile={**(account.profile or {}), **fresh, "nickname": nickname})
        self._store_map_player(session)
        return self._broadcast_map(self._map_scope(session), CMD_CHANG_NICK,
                                   struct.pack(">I", account.user_id) + fixed_utf8(nickname, 16),
                                   None, account.user_id)

    def medal_favor(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        medal_id, show_flag = struct.unpack(">2I", packet.payload)
        show_flag = 1 if show_flag else 0
        try:
            changed = self.accounts.set_medal_show_flag(account.user_id, medal_id, show_flag)
        except Exception:
            LOG.exception("MEDAL_FAVOR failed for uid=%s medal=%s", account.user_id, medal_id)
            return Response(user_id=account.user_id, status=5001)
        if not changed:
            return Response(user_id=account.user_id, status=404)
        return Response(struct.pack(">2I", medal_id, show_flag), user_id=account.user_id)

    @staticmethod
    def _map_scope(session):
        """Return the online-player scope as (owner/map id, house id)."""
        return (
            int(session.state.get("map_id", 0)),
            int(session.state.get("house_id", 0)),
        )

    def _store_map_player(self, session):
        if not self.map_player_store or not session.state.get("map_registered", True):
            return
        try:
            self.map_player_store.upsert(self._map_scope(session), self._map_player_row(session))
        except Exception as exc:
            LOG.warning("map player upsert failed: %s", exc)

    def _remove_map_player(self, session, map_id=None):
        if not self.map_player_store:
            return
        account = session.state.get("account")
        if not account:
            return
        try:
            self.map_player_store.remove(
                self._map_scope(session) if map_id is None else map_id,
                account.user_id,
            )
        except Exception as exc:
            LOG.warning("map player removal failed: %s", exc)

    async def _broadcast_map(self, map_scope, command_id, payload, exclude=None, user_id=0,
                             respect_blacklist=False):
        if not isinstance(map_scope, (tuple, list)):
            map_scope = (int(map_scope), 0)
        map_scope = (int(map_scope[0]), int(map_scope[1]))
        peers = [
            peer for peer in list(getattr(self, "online_sessions", ()))
            if peer is not exclude
               and not peer.writer.is_closing()
               and peer.state.get("map_registered")
               and self._map_scope(peer) == map_scope
               and peer.state.get("account") is not None
        ]
        if respect_blacklist:
            sender_id = int(user_id)
            allowed = []
            for peer in peers:
                peer_id = int(peer.state["account"].user_id)
                try:
                    blocked = (self.accounts.is_blacklisted(sender_id, peer_id)
                               or self.accounts.is_blacklisted(peer_id, sender_id))
                except Exception as exc:
                    LOG.warning("blacklist check failed for uid=%s peer=%s: %s",
                                sender_id, peer_id, exc)
                    blocked = False
                if not blocked:
                    allowed.append(peer)
            peers = allowed
        results = await asyncio.gather(
            *(peer.send_response(command_id, user_id=user_id, payload=payload) for peer in peers),
            return_exceptions=True,
        )
        for peer, result in zip(peers, results):
            if isinstance(result, Exception):
                LOG.warning("map broadcast to %s failed: %s", peer.peer, result)

    async def on_session_disconnected(self, session):
        if session.state.get("map_registered"):
            map_scope = self._map_scope(session)
            user_id = int(session.state.get("account").user_id)
            self._remove_map_player(session, map_scope)
            await self._broadcast_map(
                map_scope, CMD_LEAVE_MAP, struct.pack(">I", user_id), session, user_id
            )
        session.state["map_registered"] = False
        self.online_sessions.discard(session)

    async def self_move(self, s, p):
        account = s.state.get("account")
        if not account or p.user_id not in (0, account.user_id):
            return Response(user_id=p.user_id, status=401)
        if len(p.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        map_x, map_y = struct.unpack(">2I", p.payload)
        s.state["map_x"], s.state["map_y"] = map_x, map_y
        s.state["map_registered"] = True
        self._store_map_player(s)
        payload = struct.pack(">4I", 1, account.user_id, map_x, map_y)
        await self._broadcast_map(
            self._map_scope(s), CMD_SELF_MOVE, payload, s, account.user_id
        )
        return None

    async def chat_info(self, session, packet):
        """Broadcast public chat to map peers or deliver a private message."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        try:
            target_user_id, message = parse_chat_request(packet.payload)
        except (SocialProtocolError, UnicodeError) as exc:
            LOG.warning("CHAT_INFO rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)

        nickname = _profile_value(account, "nickname", account.login_name)
        payload = chat_info_payload(
            account.user_id, nickname, target_user_id if target_user_id else 0, message
        )
        if target_user_id:
            try:
                if (self.accounts.is_blacklisted(account.user_id, target_user_id)
                        or self.accounts.is_blacklisted(target_user_id, account.user_id)):
                    return None
            except Exception as exc:
                LOG.warning("private chat blacklist check failed for uid=%s target=%s: %s",
                            account.user_id, target_user_id, exc)
            try:
                self.accounts.touch_last_contact(account.user_id, target_user_id)
            except Exception as exc:
                LOG.debug("last contact update failed for uid=%s target=%s: %s",
                          account.user_id, target_user_id, exc)
            target = next(
                (
                    peer for peer in list(self.online_sessions)
                    if peer is not session
                       and not peer.writer.is_closing()
                       and peer.state.get("account") is not None
                       and int(peer.state["account"].user_id) == int(target_user_id)
                ),
                None,
            )
            if target is not None:
                await target.send_response(
                    CMD_CHAT_INFO, user_id=account.user_id, payload=payload
                )
            return None

        await self._broadcast_map(
            self._map_scope(session),
            CMD_CHAT_INFO,
            payload,
            session,
            account.user_id,
            respect_blacklist=True,
        )
        return None

    async def fairy_action(self, session, packet):
        """Relay one validated character action to the other map players."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        try:
            action_values = parse_fairy_action_request(packet.payload)
        except SocialProtocolError as exc:
            LOG.warning("FAIRY_ACTION rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)

        action, action_other, _, _ = action_values
        session.state["account"] = replace(
            account,
            profile={
                **(account.profile or {}),
                "action": action,
                "action_other": action_other,
            },
        )
        self._store_map_player(session)
        await self._broadcast_map(
            self._map_scope(session),
            CMD_FAIRY_ACTION,
            fairy_action_payload(account.user_id, action_values),
            session,
            account.user_id,
        )
        return None

    def item_type_info(self, session, packet):
        """Return the player's inventory records for ITEM_TYPE_INFO."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        try:
            item_type = parse_item_type_request(packet.payload)
        except SocialProtocolError as exc:
            LOG.warning("ITEM_TYPE_INFO rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)

        try:
            if item_type == 19:
                rows = self.accounts.actions(account.user_id)
            else:
                rows = self.accounts.inventory_items(account.user_id, item_type)
        except Exception as exc:
            LOG.exception("ITEM_TYPE_INFO query failed for uid=%s type=%s: %s",
                          account.user_id, item_type, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(
            item_type_info_payload(item_type, rows), user_id=account.user_id
        )

    def pick_up_job(self, session, packet):
        """Record one picked-up task item (PICK_UP_JOB, 1028)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        item_id = struct.unpack(">I", packet.payload)[0]
        try:
            completed = self.accounts.add_task_item_and_progress(account.user_id, item_id)
        except Exception as exc:
            LOG.exception("PICK_UP_JOB query failed for uid=%s item=%s: %s",
                          account.user_id, item_id, exc)
            return Response(user_id=account.user_id, status=5001)
        # The normal acknowledgement has no body.  A completed process is a
        # separate unsolicited command consumed by JobModel's 1059 listener.
        responses = [Response(user_id=account.user_id)]
        responses.extend(
            Response(
                command_id=CMD_JOB_PROCESS_OVER,
                user_id=account.user_id,
                payload=struct.pack(">2I", job_id, step),
            )
            for job_id, step in completed
        )
        return responses

    def pick_up_map(self, session, packet):
        """Grant one map material picked through PICK_UP_MAP (1029)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)

        item_id, item_x, item_y = struct.unpack(">3I", packet.payload)
        try:
            self.accounts.add_map_material(account.user_id, item_id)
        except Exception as exc:
            LOG.exception(
                "PICK_UP_MAP grant failed for uid=%s item=%s x=%s y=%s: %s",
                account.user_id, item_id, item_x, item_y, exc,
            )
            return Response(user_id=account.user_id, status=5001)

        # PickUpModule decodes this acknowledgement as user/item/x/y/qid.
        # qid=0 denotes an ordinary material with no questionnaire follow-up.
        return Response(
            struct.pack(">5I", account.user_id, item_id, item_x, item_y, 0),
            user_id=account.user_id,
        )

    def start_job(self, session, packet):
        """Accept one task step (START_JOB, 1051)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        job_id, step = struct.unpack(">2I", packet.payload)
        try:
            self.accounts.start_task(account.user_id, job_id, step)
        except Exception as exc:
            LOG.exception("START_JOB query failed for uid=%s job=%s step=%s",
                          account.user_id, job_id, step)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    def use_good(self, session, packet):
        """Consume one task item (USE_GOOD, 1039)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        item_id = struct.unpack(">I", packet.payload)[0]
        try:
            self.accounts.use_task_item(account.user_id, item_id)
        except Exception as exc:
            LOG.exception("USE_GOOD query failed for uid=%s item=%s", account.user_id, item_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    def over_job(self, session, packet):
        """Complete one task step and move progress to the next step (1052)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        job_id, step, reward_id = struct.unpack(">3I", packet.payload)
        try:
            response_id = self.accounts.finish_task_step(
                account.user_id,
                job_id,
                step,
                reward_id,
                int(_profile_value(account, "nationality", 1)),
            )
        except Exception as exc:
            LOG.exception("OVER_JOB query failed for uid=%s job=%s step=%s",
                          account.user_id, job_id, step)
            return Response(user_id=account.user_id, status=5001)
        # JobModel.backOverOneJob reads this one uint32 from every success.
        return Response(struct.pack(">I", response_id), user_id=account.user_id)

    def job_req_event(self, session, packet):
        """Handle JOB_REQ_EVENT (1073) and acknowledge the client request.

        Event 4 means that the requested task step has reached its target, so
        its persisted process is set to total_process.
        """
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        event_id, job_id, step = struct.unpack(">3I", packet.payload)
        if event_id in (4, 6):
            try:
                self.accounts.complete_task_event(account.user_id, job_id, step)
            except Exception:
                LOG.exception("JOB_REQ_EVENT query failed for uid=%s job=%s step=%s",
                              account.user_id, job_id, step)
                return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    def check_user_bg(self, session, packet):
        """1852: return the selected personal background for the requested user."""
        account = session.state.get("account")
        if account is None or len(packet.payload) != 4:
            return Response(user_id=packet.user_id, status=401 if account is None else 400)
        target_id = struct.unpack(">I", packet.payload)[0]
        try:
            background_id = self.accounts.user_background(target_id)
        except Exception:
            LOG.exception("CHECK_USER_BG query failed for uid=%s", target_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(struct.pack(">I", background_id), user_id=account.user_id)

    def check_all_user_bg(self, session, packet):
        """1850: return the authenticated player's owned background IDs."""
        account = session.state.get("account")
        if account is None or packet.payload:
            return Response(user_id=packet.user_id, status=401 if account is None else 400)
        try:
            ids = self.accounts.user_backgrounds(account.user_id)
        except Exception:
            LOG.exception("CHECK_ALL_USER_BG query failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(struct.pack(">I", len(ids)) + b"".join(struct.pack(">I", item) for item in ids), user_id=account.user_id)

    def check_item(self, session, packet):
        """1023: legacy CHECK_ITEM(count, item_id[, ...]) inventory lookup.

        Unlike ITEM_TYPE_INFO (1034), this command uses the first uint32 as
        the number of item IDs that follow and returns that many ID/count
        pairs.  The sick-pet flow reads all three uint32 values even when it
        asks for one item (800018).
        """
        account = session.state.get("account")
        if account is None or len(packet.payload) < 4:
            return Response(user_id=packet.user_id, status=401 if account is None else 400)
        item_count = struct.unpack_from(">I", packet.payload)[0]
        if len(packet.payload) != 4 * (item_count + 1):
            return Response(user_id=account.user_id, status=400)
        item_ids = list(struct.unpack_from(">" + ("I" * item_count), packet.payload, 4)) if item_count else []
        try:
            counts = self.accounts.inventory_item_counts(account.user_id, item_ids)
        except Exception:
            LOG.exception("CHECK_ITEM query failed for uid=%s items=%s", account.user_id, item_ids)
            return Response(user_id=account.user_id, status=5001)
        payload = bytearray(struct.pack(">I", item_count))
        for item_id in item_ids:
            payload += struct.pack(">2I", item_id, int(counts.get(item_id, 0)) & 0xFFFFFFFF)
        return Response(bytes(payload), user_id=account.user_id)

    def home_depot(self, session, packet):
        """Return the authenticated player's HOME_DEPOT inventory."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id) or packet.payload:
            return Response(user_id=packet.user_id, status=401 if not account else 400)
        # HOME_DEPOT is the authenticated player's personal home inventory.
        # ENTER_MAP(1, owner_id, ...) only selects which home's decorations
        # are being viewed; it must not change the identity used for this
        # player's depot query when visiting somebody else.
        owner_id = int(account.user_id)
        try:
            rows = self.accounts.home_depot_items(owner_id)
        except Exception as exc:
            LOG.exception("HOME_DEPOT query failed for owner=%s: %s", owner_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(home_depot_payload(rows), user_id=account.user_id)

    def _pollen_home_owner(self, session, account):
        """Return the visited home owner when this is somebody else's home."""
        owner_id = int(session.state.get("home_owner_id", 0) or 0)
        if (
            session.state.get("scene_kind") != "home"
            or owner_id <= 0
            or owner_id == int(account.user_id)
            or int(session.state.get("map_id", 0)) != owner_id
        ):
            return None
        return owner_id

    def home_pick_dust(self, session, packet):
        """10021: collect one pollen from the visited player's home."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        owner_id, plot_no = struct.unpack(">2I", packet.payload)
        if self._pollen_home_owner(session, account) != owner_id:
            return Response(struct.pack(">BBI", 0, 2, 0), user_id=account.user_id)
        try:
            result = self.accounts.collect_home_pollen(account.user_id, owner_id, plot_no)
        except Exception:
            LOG.exception("HOME_PICK_DUST failed for visitor=%s owner=%s plot=%s",
                          account.user_id, owner_id, plot_no)
            return Response(user_id=account.user_id, status=5001)
        if result.get("ok"):
            return Response(
                struct.pack(">B2I", 1, int(result["plot_no"]), int(result["pollen_id"])),
                user_id=account.user_id,
            )
        return Response(
            struct.pack(">BBI", 0, int(result.get("reason", 1)), int(result.get("pollen_id", 0))),
            user_id=account.user_id,
        )

    def home_onekey_pick_dust(self, session, packet):
        """1324: collect every available pollen from the visited home."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        owner_id = self._pollen_home_owner(session, account)
        if owner_id is None:
            return Response(struct.pack(">I", 0), user_id=account.user_id)
        try:
            amounts = self.accounts.collect_all_home_pollen(account.user_id, owner_id)
        except Exception:
            LOG.exception("HOME_ONEKEY_PICK_DUST failed for visitor=%s owner=%s",
                          account.user_id, owner_id)
            return Response(user_id=account.user_id, status=5001)
        payload = bytearray(struct.pack(">I", len(amounts)))
        for pollen_id, amount in sorted(amounts.items()):
            payload += struct.pack(">2I", int(pollen_id), int(amount))
        return Response(bytes(payload), user_id=account.user_id)

    def _owns_editable_home(self, session, account) -> bool:
        """Ensure a home mutation applies only to the logged-in player's home."""
        return (
            int(session.state.get("map_id", 0)) == int(account.user_id)
            and session.state.get("scene_kind") == "home"
            and int(session.state.get("home_owner_id", 0)) == int(account.user_id)
        )

    def home_add_house(self, session, packet):
        """10011: replace the player's home house and return its placement."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 20:
            return Response(user_id=account.user_id, status=400)
        owner_id, house_id, x, y, _reserved = struct.unpack(">5I", packet.payload)
        if owner_id != int(account.user_id) or not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.change_home_house(account.user_id, house_id, x, y)
        except Exception:
            LOG.exception("HOME_ADD_HOUSE failed for uid=%s house=%s", account.user_id, house_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=404)
        return Response(
            home_add_house_payload(result["item_id"], result["x"], result["y"]),
            user_id=account.user_id,
        )

    def home_change_background(self, session, packet):
        """10450: change the logged-in player's garden background."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        background_id = struct.unpack(">I", packet.payload)[0]
        try:
            changed = self.accounts.change_home_background(account.user_id, background_id)
        except Exception:
            LOG.exception("HOME_CHANGE_BG failed for uid=%s bg=%s", account.user_id, background_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def home_tool_add(self, session, packet):
        """10023: place one unplaced garden decoration from the depot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        item_id, x, y = struct.unpack(">3I", packet.payload)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.add_home_good(account.user_id, item_id, x, y)
        except Exception:
            LOG.exception("HOME_TOOL_ADD failed for uid=%s item=%s", account.user_id, item_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=404)
        return Response(home_tool_add_payload(**result), user_id=account.user_id)

    def home_add_pot(self, session, packet):
        """10005: consume one pot and add an empty plant slot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        x, y, pot_id = struct.unpack(">3I", packet.payload)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.add_home_pot(account.user_id, pot_id, x, y)
        except Exception:
            LOG.exception("HOME_ADD_POT failed for uid=%s pot=%s", account.user_id, pot_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=403)
        return Response(home_pot_add_payload(**result), user_id=account.user_id)

    def home_add_plant(self, session, packet):
        """10007: consume one seed and plant it in the ground or an empty pot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 24:
            return Response(user_id=account.user_id, status=400)
        pot_id, plant_id, x, y, plot_no, _mode = struct.unpack(">6I", packet.payload)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.add_home_plant(
                account.user_id, pot_id, plant_id, x, y, plot_no
            )
        except Exception:
            LOG.exception("HOME_ADD_PLANT failed for uid=%s seed=%s", account.user_id, plant_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=70)
        return Response(home_add_plant_payload(result), user_id=account.user_id)

    def home_plant_tool(self, session, packet):
        """10022: consume a watering/fertilizer/shovel tool for one plant."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        plot_no, tool_id, _reserved = struct.unpack(">3I", packet.payload)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.use_home_plant_tool(account.user_id, plot_no, tool_id)
        except Exception:
            LOG.exception("HOME_PLANT_TOOL failed for uid=%s plot=%s tool=%s",
                          account.user_id, plot_no, tool_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=404)
        return Response(
            home_plant_tool_payload(result["tool_type"], result["plot_no"], result["tool_id"], result["plant"]),
            user_id=account.user_id,
        )

    def home_back_pot(self, session, packet):
        """10006: remove one pot row and return the pot to the depot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        if not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        plot_no = struct.unpack(">I", packet.payload)[0]
        try:
            result = self.accounts.back_home_pot(account.user_id, plot_no)
        except Exception:
            LOG.exception("HOME_BACK_POT failed for uid=%s plot=%s", account.user_id, plot_no)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=404)
        return Response(home_pot_back_payload(**result), user_id=account.user_id)

    def home_update_plant(self, session, packet):
        """10015: update one or more plant/pot positions."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) < 8:
            return Response(user_id=account.user_id, status=400)
        owner_id, count = struct.unpack_from(">2I", packet.payload)
        if owner_id != int(account.user_id) or not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        if count == 0 or len(packet.payload) != 8 + count * 12:
            return Response(user_id=account.user_id, status=400)
        positions = []
        offset = 8
        for _ in range(count):
            plot_no, x, y = struct.unpack_from(">3I", packet.payload, offset)
            positions.append({"plot_no": plot_no, "x": x, "y": y})
            offset += 12
        try:
            saved = self.accounts.update_home_plant_positions(account.user_id, positions)
        except Exception:
            LOG.exception("HOME_UPDATE_PLANT failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if saved else 404)

    def home_update_house(self, session, packet):
        """10014: update a displayed house position."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 20:
            return Response(user_id=account.user_id, status=400)
        owner_id, house_id, x, y, _reserved = struct.unpack(">5I", packet.payload)
        if owner_id != int(account.user_id) or not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            result = self.accounts.update_home_house_position(account.user_id, house_id, x, y)
        except Exception:
            LOG.exception("HOME_UPDATE_HOUSE failed for uid=%s house=%s", account.user_id, house_id)
            return Response(user_id=account.user_id, status=5001)
        if result is None:
            return Response(user_id=account.user_id, status=404)
        return Response(
            home_house_position_payload(
                result["owner_id"], result["item_id"], result["x"], result["y"]
            ),
            user_id=account.user_id,
        )

    def home_back_house(self, session, packet):
        """10012: remove the displayed house and return it to the depot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        owner_id, house_id = struct.unpack(">2I", packet.payload)
        if owner_id != int(account.user_id) or not self._owns_editable_home(session, account):
            return Response(user_id=account.user_id, status=403)
        try:
            removed = self.accounts.back_home_house(account.user_id, house_id)
        except Exception:
            LOG.exception("HOME_BACK_HOUSE failed for uid=%s house=%s", account.user_id, house_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(
            home_house_back_payload(house_id, success=removed, reason=0 if removed else 1),
            user_id=account.user_id,
            status=0 if removed else 404,
        )

    def house_depot(self, session, packet):
        """Return grouped, unplaced furniture for HOUSE_DEPOT (10104)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)

        owner_id = struct.unpack(">I", packet.payload)[0]
        if owner_id != int(account.user_id):
            return Response(user_id=account.user_id, status=403)
        try:
            rows = self.accounts.house_depot_items(owner_id)
        except Exception as exc:
            LOG.exception("HOUSE_DEPOT query failed for owner=%s", owner_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(home_depot_payload(rows), user_id=account.user_id)

    def house_add_goods(self, session, packet):
        """Place one depot item and return its assigned HOUSE_INFO number."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 20:
            return Response(user_id=account.user_id, status=400)
        if (
            int(session.state.get("map_id", 0)) != int(account.user_id)
            or int(session.state.get("house_id", 0)) <= 400000
        ):
            return Response(user_id=account.user_id, status=403)

        item_id, x, y, m, z = struct.unpack(">5I", packet.payload)
        try:
            no = self.accounts.add_house_good(account.user_id, item_id, x, y, m, z)
        except Exception as exc:
            LOG.exception("HOUSE_ADD_GOODS failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        if no is None:
            return Response(user_id=account.user_id, status=404)
        return Response(
            house_add_goods_payload(item_id, no, x, y),
            user_id=account.user_id,
        )

    def house_del_goods(self, session, packet):
        """Move one placed furniture row back to the house depot."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 4:
            return Response(user_id=account.user_id, status=400)
        if (
            int(session.state.get("map_id", 0)) != int(account.user_id)
            or int(session.state.get("house_id", 0)) <= 400000
        ):
            return Response(user_id=account.user_id, status=403)

        no = struct.unpack(">I", packet.payload)[0]
        try:
            item_id = self.accounts.remove_house_good(account.user_id, no)
        except Exception as exc:
            LOG.exception("HOUSE_DEL_GOODS failed for uid=%s no=%s", account.user_id, no)
            return Response(user_id=account.user_id, status=5001)
        if item_id is None:
            return Response(user_id=account.user_id, status=404)
        return Response(
            house_del_goods_payload(no, item_id),
            user_id=account.user_id,
        )

    def house_update(self, session, packet):
        """Persist changed furniture rows from HOUSE_UPDATE (10105)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) < 12:
            return Response(user_id=account.user_id, status=400)

        owner_id, house_id, count = struct.unpack_from(">3I", packet.payload)
        expected_length = 12 + count * 24
        if len(packet.payload) != expected_length:
            return Response(user_id=account.user_id, status=400)
        if owner_id != int(account.user_id):
            return Response(user_id=account.user_id, status=403)
        if (
            int(session.state.get("map_id", 0)) != owner_id
            or int(session.state.get("house_id", 0)) != house_id
        ):
            return Response(user_id=account.user_id, status=403)

        goods = []
        offset = 12
        for _ in range(count):
            no, item_id, x, y, m, z = struct.unpack_from(">6I", packet.payload, offset)
            goods.append({"no": no, "item_id": item_id, "x": x, "y": y, "m": m, "z": z})
            offset += 24
        try:
            self.accounts.update_house_goods(account.user_id, house_id, goods)
        except Exception as exc:
            LOG.exception("HOUSE_UPDATE failed for uid=%s house=%s", account.user_id, house_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    async def people_transform(self, session, packet):
        """Consume a magic action and notify every player on the map."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        try:
            target_user_id, transform_type, action_id = parse_people_transform_request(packet.payload)
        except SocialProtocolError as exc:
            LOG.warning("PEOPLE_TRANSFORM rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)

        # 1091 is the type-19 magic path.  The player using the item, rather
        # than the selected target, owns and pays for the action.
        if transform_type != 1 or not (1900001 <= action_id <= 1909999):
            return Response(user_id=account.user_id, status=400)
        target = next(
            (
                peer for peer in list(self.online_sessions)
                if not peer.writer.is_closing()
                and peer.state.get("map_registered")
                and self._map_scope(peer) == self._map_scope(session)
                and peer.state.get("account") is not None
                and int(peer.state["account"].user_id) == int(target_user_id)
            ),
            None,
        )
        if target is None:
            return Response(user_id=account.user_id, status=404)
        try:
            consumed = self.accounts.consume_action(account.user_id, action_id)
        except Exception as exc:
            LOG.exception("PEOPLE_TRANSFORM consume failed for uid=%s action=%s", account.user_id, action_id)
            return Response(user_id=account.user_id, status=5001)
        if not consumed:
            return Response(user_id=account.user_id, status=403)

        target_account = target.state.get("account")
        target.state["account"] = replace(
            target_account,
            profile={
                **(target_account.profile or {}),
                "action": action_id,
                "action_other": transform_type,
            },
        )
        self._store_map_player(target)
        payload = people_transform_payload(target_user_id, transform_type, action_id)
        await self._broadcast_map(
            self._map_scope(session),
            CMD_PEOPLE_TRANSFORM,
            payload,
            None,
            target_user_id,
        )
        return None


    def one_base(self,s,p):
        a = s.state.get('account')
        if not a or len(p.payload) != 4:
            return Response(user_id=p.user_id, status=401 if not a else 400)
        target_id = struct.unpack('>I', p.payload)[0]
        target = self.accounts.get_by_id(target_id)
        if not target:
            return Response(user_id=a.user_id, status=404)
        profile = dict(target.profile or {})
        try:
            profile.update(self.accounts.profile(target.user_id))
        except Exception:
            pass
        g = lambda k, d=0: _u32(profile.get(k, d))
        out = bytearray(struct.pack('>2I', target.user_id, g('vip_level')))
        out += fixed_utf8(str(profile.get('nickname', target.login_name)), 16)
        out += struct.pack(
            '>16I', g('face_color'), g('face'), g('eye'), g('eyebrow'), g('lip'), g('title_id'),
            g('reg_time', g('login_time', int(time.time()))), g('birthday', 1), g('nationality', 1),
            g('love'), g('beautiful'), g('wisdom'), g('plant_grade'), g('faerie_grade'),
            g('money'), g('faerie_follow_id'),
        )
        clothing = [
            g("tool"), g("headdress"),g("mask"),g("hair"),g("earring"),g("necklace"),g("belt"),
            g("cloth"),g("bangle"),g("shoes"),g("anklet"),g("skirt"),g("wing"),
        ]
        clothing = [cloth_id for cloth_id in clothing if cloth_id != 0]
        out += struct.pack('>I', len(clothing))
        if clothing:
            out += struct.pack(">" + "I" * len(clothing), *clothing)
        return Response(bytes(out), user_id=a.user_id)

    def pet_base_info(self, session, packet):
        """Return one stored pet in the HuabaoData wire layout."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        user_id, pet_id = struct.unpack(">2I", packet.payload)
        try:
            pet = self.accounts.pet_info(user_id, pet_id)
        except Exception as exc:
            LOG.exception("PET_BASE_INFO query failed for uid=%s pet=%s", user_id, pet_id)
            return Response(user_id=account.user_id, status=5001)
        if not pet:
            return Response(user_id=account.user_id, status=404)
        return Response(pet_base_info_payload(pet), user_id=account.user_id)

    def self_simple_huabao(self, session, packet):
        """10221: all of the logged-in player's pets, including resting pets."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        try:
            pets = self.accounts.pet_rows(account.user_id)
        except Exception:
            LOG.exception("GET_SLEF_SIMPLE_HUABAO query failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=RESULT_SYSTEM_ERROR)
        return Response(pet_simple_info_payload(pets), user_id=account.user_id)

    def home_pet_info(self, session, packet):
        """Return pets resting in the current Home (10200)."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        owner_id = int(session.state.get("home_owner_id", session.state.get("map_id", 0)) or 0)
        if not owner_id:
            return Response(user_id=account.user_id, status=400)
        try:
            pets = self.accounts.pet_rows(owner_id, 1)
        except Exception:
            LOG.exception("HOME_PET_INFO query failed for owner=%s", owner_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(pet_simple_info_payload(pets), user_id=0)

    def pet_in_orphanage(self, session, packet):
        """Return the orphanage pet list (10213), which is always empty.

        The orphanage feature is disabled, but the client still queries this
        command while opening the related NPC/login flow.  Its response is a
        uint32 count followed by zero pet records.
        """
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        return Response(struct.pack(">I", 0), user_id=account.user_id)

    def pet_follow(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) not in (0, 4):
            return Response(user_id=account.user_id, status=400)
        pet_id = struct.unpack(">I", packet.payload)[0] if packet.payload else int(
            session.state.get("pet_id", 0) or (account.profile.get("pet") or {}).get("pet_id", 0) or 0
        )
        if not pet_id:
            return Response(user_id=account.user_id, status=400)
        try:
            changed = self.accounts.set_pet_follow(account.user_id, pet_id)
        except Exception:
            LOG.exception("PET_FOLLOW failed for uid=%s pet=%s", account.user_id, pet_id)
            return Response(user_id=account.user_id, status=5001)
        if changed:
            try:
                fresh = self.accounts.profile(account.user_id)
                session.state["account"] = replace(account, profile={**(account.profile or {}), **fresh})
                self._store_map_player(session)
            except Exception:
                LOG.exception("PET_FOLLOW profile refresh failed for uid=%s", account.user_id)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def pet_use_tool(self, session, packet):
        """Use an owned pet supply and return the updated pet values."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 12:
            return Response(user_id=account.user_id, status=400)
        user_id, pet_id, item_id = struct.unpack(">3I", packet.payload)
        if user_id != account.user_id:
            return Response(user_id=account.user_id, status=403)
        try:
            status, pet = self.accounts.use_pet_supply(user_id, pet_id, item_id)
        except Exception:
            LOG.exception("PET_USETOOL failed for uid=%s pet=%s item=%s", user_id, pet_id, item_id)
            return Response(user_id=account.user_id, status=5001)
        if status:
            return Response(user_id=account.user_id, status=status)
        return Response(pet_use_tool_payload(pet), user_id=account.user_id)

    def pet_back(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) not in (0, 4):
            return Response(user_id=account.user_id, status=400)
        pet_id = struct.unpack(">I", packet.payload)[0] if packet.payload else int(
            session.state.get("pet_id", 0) or (account.profile.get("pet") or {}).get("pet_id", 0) or 0
        )
        if not pet_id:
            return Response(user_id=account.user_id, status=400)
        try:
            scene_kind = session.state.get("scene_kind")
            rest_at = {"home": 1, "house": 2}.get(scene_kind)
            if rest_at is None:
                return Response(user_id=account.user_id, status=400)
            changed = self.accounts.put_pet_back(account.user_id, pet_id, rest_at)
        except Exception:
            LOG.exception("PET_BACK failed for uid=%s pet=%s", account.user_id, pet_id)
            return Response(user_id=account.user_id, status=5001)
        if changed:
            try:
                fresh = self.accounts.profile(account.user_id)
                session.state["account"] = replace(account, profile={**(account.profile or {}), **fresh})
                self._store_map_player(session)
            except Exception:
                LOG.exception("PET_BACK profile refresh failed for uid=%s", account.user_id)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def pet_change_nick(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) < 4:
            return Response(user_id=account.user_id, status=400)
        pet_id = struct.unpack_from(">I", packet.payload)[0]
        raw_name = packet.payload[4:]
        if len(raw_name) > 16:
            return Response(user_id=account.user_id, status=400)
        try:
            nickname = raw_name.split(b"\x00", 1)[0].decode("utf-8")
        except UnicodeDecodeError:
            return Response(user_id=account.user_id, status=400)
        if not nickname:
            return Response(user_id=account.user_id, status=400)
        try:
            changed = self.accounts.rename_pet(account.user_id, pet_id, nickname)
        except Exception:
            LOG.exception("PET_CHANG_NICK failed for uid=%s pet=%s", account.user_id, pet_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id, status=0 if changed else 404)

    def pet_letter_list_task(self, session, packet):
        """Return task letters (1049): count + six uint32 fields per row."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if packet.payload:
            return Response(user_id=account.user_id, status=400)
        try:
            rows = self.accounts.pet_letter_tasks(account.user_id)
        except Exception:
            LOG.exception("PETLETTER_LIST_TASK query failed for uid=%s", account.user_id)
            return Response(user_id=account.user_id, status=5001)
        out = bytearray(struct.pack(">I", len(rows)))
        for row in rows:
            out += struct.pack(
                ">6I",
                _u32(row.get("task_id")), _u32(row.get("step")),
                _u32(row.get("status")), _u32(row.get("process")),
                _u32(row.get("letter_time")), _u32(row.get("total_process")),
            )
        return Response(bytes(out), user_id=account.user_id)

    def pet_letter_list_mood(self, session, packet):
        """Return mood/reply letter summaries (10300).

        The request is pet_id:uint32 followed by mail_type:uint32.  For
        mail_type 1/2 the client reads mail state; type 3 is the reply list
        and reads reply_time while treating state as 1.
        """
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        pet_id, mail_type = struct.unpack(">2I", packet.payload)
        if mail_type not in (1, 2, 3):
            return Response(user_id=account.user_id, status=400)
        try:
            rows = self.accounts.pet_letter_replies(account.user_id, pet_id, mail_type)
        except Exception:
            LOG.exception("PETLETTER_LIST_MOOD query failed for uid=%s pet=%s type=%s",
                          account.user_id, pet_id, mail_type)
            return Response(user_id=account.user_id, status=5001)
        out = bytearray(struct.pack(">2I", mail_type, len(rows)))
        for row in rows:
            send_time = _u32(row.get("send_time"))
            out += struct.pack(">2I", _u32(row.get("mail_id")), send_time)
            if mail_type == 3:
                out += struct.pack(">I", _u32(row.get("reply_time")) or send_time)
            else:
                out += struct.pack(">I", _u32(row.get("state")))
        return Response(bytes(out), user_id=account.user_id)

    def pet_letter_read_mood(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        pet_id, send_time = struct.unpack(">2I", packet.payload)
        try:
            self.accounts.mark_pet_letter_read(account.user_id, pet_id, send_time)
        except Exception:
            LOG.exception("PETLETTER_READ_MOOD failed for uid=%s pet=%s time=%s",
                          account.user_id, pet_id, send_time)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    def pet_letter_reply(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) < 12:
            return Response(user_id=account.user_id, status=400)
        pet_id, send_time, content_len = struct.unpack_from(">3I", packet.payload)
        content_bytes = packet.payload[12:]
        if content_len != len(content_bytes):
            return Response(user_id=account.user_id, status=400)
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return Response(user_id=account.user_id, status=400)
        try:
            created = self.accounts.reply_pet_letter(
                account.user_id, pet_id, send_time, content, int(time.time())
            )
        except Exception:
            LOG.exception("PETLETTER_REPLY failed for uid=%s pet=%s time=%s",
                          account.user_id, pet_id, send_time)
            return Response(user_id=account.user_id, status=5001)
        if not created:
            return Response(user_id=account.user_id, status=30001)
        return Response(struct.pack(">I", 10), user_id=account.user_id)

    def pet_letter_delete_mood(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) < 8:
            return Response(user_id=account.user_id, status=400)
        pet_id, count = struct.unpack_from(">2I", packet.payload)
        expected = 8 + count * 4
        if expected != len(packet.payload):
            return Response(user_id=account.user_id, status=400)
        send_times = struct.unpack_from(">" + ("I" * count), packet.payload, 8) if count else ()
        try:
            self.accounts.delete_pet_letters(account.user_id, pet_id, send_times)
        except Exception:
            LOG.exception("PETLETTER_DELETE_MOOD failed for uid=%s pet=%s", account.user_id, pet_id)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    def pet_letter_reply_content(self, session, packet):
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)
        if len(packet.payload) != 8:
            return Response(user_id=account.user_id, status=400)
        pet_id, send_time = struct.unpack(">2I", packet.payload)
        try:
            row = self.accounts.pet_reply_content(account.user_id, pet_id, send_time)
        except Exception:
            LOG.exception("PETLETTER_REPLY_CONTENT failed for uid=%s pet=%s time=%s",
                          account.user_id, pet_id, send_time)
            return Response(user_id=account.user_id, status=5001)
        if not row:
            return Response(user_id=account.user_id, status=30001)
        content = str(row.get("content") or "").encode("utf-8")
        payload = struct.pack(">2I", _u32(row.get("reply_time")), len(content)) + content
        return Response(payload, user_id=account.user_id)

    def chat_save_words(self, s, p):
        a = s.state.get('account')
        LOG.info(
            "CHAT_SAVE_WORDS uid=%s account=%s payload_len=%d payload=%s",
            p.user_id,
            getattr(a, "user_id", None),
            len(p.payload),
            p.payload.hex(" "),
        )
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        if len(p.payload) != 4:
            return Response(user_id=a.user_id, status=400)
        return Response(struct.pack('>I', 0), user_id=a.user_id)

    def cloth_info(self, s, p):
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        if p.payload:
            return Response(user_id=a.user_id, status=400)
        try:
            cloth_ids = self.accounts.clothes(a.user_id)
        except Exception as exc:
            LOG.warning("CLOTH_INFO query failed for uid=%s: %s", a.user_id, exc)
            cloth_ids = []
        return Response(cloth_info_payload(cloth_ids), user_id=a.user_id)

    def suiting_info(self, s, p):
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        if p.payload:
            return Response(user_id=a.user_id, status=400)
        try:
            suits = self.accounts.suitings(a.user_id)
        except Exception as exc:
            LOG.warning("SUITING_INFO query failed for uid=%s: %s", a.user_id, exc)
            suits = []
        return Response(suiting_info_payload(suits), user_id=a.user_id)


    def suiting_add(self, s, p):
        account = s.state.get("account")
        if not account or p.user_id not in (0, account.user_id):
            return Response(user_id=p.user_id, status=401)
        try:
            cloth_ids = parse_suiting_add_request(p.payload)
            vip_level = int(_profile_value(account, "vip_level", 0) or 0)
            max_slots = 10 if vip_level else 5
            slot_index = self.accounts.add_suiting(account.user_id, cloth_ids, max_slots)
        except SuitingProtocolError as exc:
            LOG.warning("SUITING_ADD rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)
        except SuitingError as exc:
            LOG.warning("SUITING_ADD rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=exc.status)
        except Exception as exc:
            LOG.exception("SUITING_ADD failed for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(suiting_add_response(slot_index), user_id=account.user_id)


    def suiting_delete(self, s, p):
        account = s.state.get("account")
        if not account or p.user_id not in (0, account.user_id):
            return Response(user_id=p.user_id, status=401)
        try:
            slot_index = parse_suiting_delete_request(p.payload)
            self.accounts.delete_suiting(account.user_id, slot_index)
        except SuitingProtocolError as exc:
            LOG.warning("SUITING_DELETE rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=400)
        except SuitingError as exc:
            LOG.warning("SUITING_DELETE rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=exc.status)
        except Exception as exc:
            LOG.exception("SUITING_DELETE failed for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=5001)
        return Response(user_id=account.user_id)

    async def cloth_change(self, session, packet):
        """Persist 1018 and push the protocol-correct 1018 map notice."""
        account = session.state.get("account")
        if not account or packet.user_id not in (0, account.user_id):
            return Response(user_id=packet.user_id, status=401)

        try:
            changes = parse_cloth_change_request(packet.payload)
            clothing, records = self.accounts.change_clothing(account.user_id, changes)
        except (ClothChangeProtocolError, ClothingChangeError) as exc:
            LOG.warning("CLOTH_CHANGE rejected for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=14)
        except Exception as exc:
            LOG.exception("CLOTH_CHANGE failed for uid=%s: %s", account.user_id, exc)
            return Response(user_id=account.user_id, status=14)

        session.state["account"] = replace(
            account, profile={**(account.profile or {}), **clothing}
        )
        payload = cloth_change_payload(account.user_id, records)
        map_scope = self._map_scope(session)
        peers = [
            peer for peer in list(self.online_sessions)
            if peer is not session
               and not peer.writer.is_closing()
               and self._map_scope(peer) == map_scope
               and peer.state.get("account") is not None
        ]
        results = await asyncio.gather(
            *(peer.send_response(
                CMD_CLOTH_CHANGE, user_id=account.user_id, payload=payload
            ) for peer in peers),
            return_exceptions=True,
        )
        for peer, result in zip(peers, results):
            if isinstance(result, Exception):
                LOG.warning("CLOTH_CHANGE push to %s failed: %s", peer.peer, result)

        return Response(payload, user_id=account.user_id)

    def timer(self,s,p):
        now = int(time.time())
        s.state['server_time'] = now
        s.state['server_time_at'] = time.monotonic()
        account = s.state.get('account')
        uid = int(getattr(account, 'user_id', p.user_id)) if account else p.user_id
        return Response(struct.pack('>I', now), user_id=uid)

    def empty(self,s,p):
        return Response(b'',user_id=p.user_id)

    def ignore(self, s, p):
        # 1279 is a client notification trigger, not a request/response
        # command.  Sending an empty frame would make PeopleLogic read a
        # missing uid and fail while initializing map players.
        return None

    def secret_protected_hint(self, s, p):
        """Return whether the account should show the secret-protection hint.

        SecretProctedBean reads one unsigned 32-bit value.  The normal account
        state is zero (skip the hint); a non-zero database value is normalized
        to one because the AS3 client only distinguishes zero from non-zero.
        """
        account = s.state.get('account')
        if not account or p.user_id not in (0, account.user_id):
            return Response(user_id=p.user_id, status=401)

        flag = 0
        try:
            rows = self.accounts.rows('player_secret_protection', account.user_id)
            if rows:
                row = rows[0]
                flag = row.get('hint_flag', row.get('flag', 0))
        except Exception as exc:
            # The table is optional for existing installations.  Returning the
            # protocol-correct default still lets login initialization proceed.
            LOG.warning("SECRET_PROTECTED_HINT query failed for uid=%s: %s", account.user_id, exc)
        return Response(struct.pack('>I', 1 if flag else 0), user_id=account.user_id)

    def ext_info(self, s, p):
        # UserExtInfo currently contains clothPKRankIdx:uint32; patrolTitle
        # is client-side defaulted to zero.  Keep the rank in its own optional
        # table so it is available even when accounts/player_profiles is owned
        # by another service.
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        value = _profile_value(a, 'cloth_pk_rank_idx', 0)
        try:
            rows = self.accounts.rows('player_ext_info', a.user_id)
            if rows:
                row = rows[0]
                value = row.get('cloth_pk_rank_idx', row.get('rank_idx', value))
        except Exception as exc:
            LOG.warning("GET_ROLER_EXT_USERINFO query failed for uid=%s: %s", a.user_id, exc)
        return Response(struct.pack('>I', _u32(value)), user_id=a.user_id)

    def miniparty_state(self, s, p):
        # MainManager reads one uint32 and then continues independently.
        a = s.state.get('account')
        if not a:
            return Response(user_id=p.user_id, status=401)
        return Response(struct.pack('>I', _u32(_profile_value(a, 'miniparty_guide_state', 0))), user_id=a.user_id)

    def tasks(self,s,p):
        a=s.state.get('account')
        if not a:
            return Response(user_id=p.user_id,status=401)
        now = int(time.time())
        try:
            rows = self.accounts.task_progress_rows(a.user_id)
        except Exception as exc:
            LOG.warning("TASK_LIST query failed for uid=%s: %s", a.user_id, exc)
            rows = []
        # Res_Task_list has a legacy completed-job section, but command 1103
        # is used by this client to refresh unfinished and unaccepted jobs.
        # Do not expose player_completed_tasks here; completed jobs are kept
        # server-side and must not be sent back in this response.
        completed = []
        out=bytearray(struct.pack('>2I', now, len(rows)))
        for r in rows:
            flag=_u32(r.get('flag',0)); out += struct.pack('>3I',_u32(r.get('job_id')), _u32(r.get('step',1)), flag)
            if flag:
                out += struct.pack('>3I',_u32(r.get('process')), _u32(r.get('total_process')), _u32(r.get('get_time')))
        out += struct.pack('>I',len(completed))
        for r in completed:
            out += struct.pack('>I', _u32(r.get('job_id')))
        return Response(bytes(out),user_id=a.user_id)

    def npc_jobs(self, s, p):
        """Return the task steps offered by an NPC (command 1057)."""
        account = s.state.get('account')
        if not account:
            return Response(user_id=p.user_id, status=401)
        if len(p.payload) != 4:
            return Response(user_id=account.user_id, status=400)

        npc_id = struct.unpack_from('>I', p.payload, 0)[0]
        try:
            rows = self.accounts.npc_job_rows(npc_id, account.user_id)
        except Exception as exc:
            LOG.warning("NPC_JOBS query failed for npc=%s uid=%s: %s", npc_id, account.user_id, exc)
            rows = []

        now = int(time.time())
        # Res_NPCJOB_INFO reads server time, the requested NPC id, then count.
        payload = bytearray(struct.pack('>3I', now, npc_id, len(rows)))
        for row in rows:
            payload += struct.pack(
                '>7I',
                _u32(row.get('job_id')),
                _u32(row.get('step', 1)),
                _u32(row.get('type')),
                _u32(row.get('status')),
                _u32(row.get('process')),
                _u32(row.get('get_time')),
                _u32(row.get('total_process')),
            )
        return Response(bytes(payload), user_id=account.user_id)

    def puppet_info(self, s, p):
        """Return PuppetInfo's eight uint32 fields (command 2053)."""
        if len(p.payload) != 4:
            return Response(user_id=p.user_id, status=400)

        target_id = struct.unpack_from('>I', p.payload, 0)[0]
        try:
            row = self.accounts.puppet_info(target_id)
        except Exception as exc:
            LOG.warning("PUPPET_INFO query failed for uid=%s: %s", target_id, exc)
            row = {'user_id': target_id}

        payload = struct.pack(
            '>8I',
            _u32(row.get('user_id', target_id)),
            _u32(row.get('puppet_id')),
            _u32(row.get('follow_flag')),
            _u32(row.get('rest_tech_point')),
            _u32(row.get('flower_num')),
            _u32(row.get('love_value')),
            _u32(row.get('kind_value')),
            _u32(row.get('evil_value')),
        )
        return Response(payload, user_id=p.user_id)

    def dolls_make_trouble_info(self, s, p):
        """Return the state header used by the NPC doll-talk filters (2050).

        The client sends a one-based index into its fixed doll NPC list, not
        the NPC id itself.  The response is always at least four words:
        ``index, completed, started, type``.  The latter two words are read
        conditionally by the AS3 client, so returning the complete idle
        record lets both ``CheckDollTroubleBean`` and
        ``CheckReceivedDollBean`` finish their callbacks when no activity
        state has been persisted yet.
        """
        account = s.state.get('account')
        if not account:
            return Response(user_id=p.user_id, status=401)
        if len(p.payload) != 4:
            return Response(user_id=account.user_id, status=400)

        npc_index = struct.unpack_from('>I', p.payload, 0)[0]
        # This is the same order as the client's _npcArr in the 2050 callers.
        if not 1 <= npc_index <= 13:
            return Response(user_id=account.user_id, status=400)

        # Activity persistence is not part of the current schema.  An idle
        # record is still a valid protocol response and, unlike no response,
        # allows the client's option filtering continuation to run.
        payload = struct.pack('>4I', npc_index, 0, 0, 0)
        return Response(payload, user_id=account.user_id)

    def sync_users_extinfo(self, s, p):
        """Return cloth-rank metadata for the users currently in the map."""
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        # The map-player list is sourced from the in-memory store in
        # map_players.  Returning
        # an empty count is valid and lets PeopleLogic finish initialization.
        return Response(struct.pack('>I', 0), user_id=a.user_id)

    def medal_progress(self,s,p):
        a=s.state.get('account')
        if not a: return Response(user_id=p.user_id,status=401)
        ids=[]
        if len(p.payload)>=4:
            n=struct.unpack_from('>I',p.payload)[0]; ids=list(struct.unpack_from('>'+('I'*min(n,(len(p.payload)-4)//4)),p.payload,4))
        try:
            progress_rows = self.accounts.rows('medal_event_progress', a.user_id)
        except Exception as exc:
            LOG.warning("MEDAL_PROGRESS query failed for uid=%s: %s", a.user_id, exc)
            progress_rows = []
        rows={int(r.get('event_id',0)):_u32(r.get('progress')) for r in progress_rows}
        out=bytearray(struct.pack('>I',len(ids)))
        for i in ids: out += struct.pack('>2I',i,rows.get(i,0))
        return Response(bytes(out),user_id=a.user_id)

    def check_medal_flags(self, s, p):
        """Return the value/time/flag tuple for each requested medal.

        CHECK_MEDAL_FLAGS (2916) uses the same wire record as
        ``PtCommonMedalInfo``: ``count`` followed by
        ``medal_id:uint32, value:uint32, time:uint32, flag:uint32`` for
        every requested ID.  A missing medal is a valid zero-valued record;
        preserving the requested IDs and count is important because the AS3
        decoder reads exactly that many records.
        """
        account = s.state.get('account')
        if not account:
            return Response(user_id=p.user_id, status=401)

        count = 0
        ids = []
        if len(p.payload) >= 4:
            requested = struct.unpack_from('>I', p.payload, 0)[0]
            available = (len(p.payload) - 4) // 4
            count = min(requested, available)
            if count:
                ids = list(struct.unpack_from('>' + ('I' * count), p.payload, 4))

        try:
            rows = self.accounts.rows('player_medals', account.user_id)
        except Exception as exc:
            LOG.warning("CHECK_MEDAL_FLAGS query failed for uid=%s: %s", account.user_id, exc)
            rows = []
        by_id = {int(row.get('medal_id', 0)): row for row in rows}

        out = bytearray(struct.pack('>I', len(ids)))
        for medal_id in ids:
            row = by_id.get(medal_id, {})
            # value_bits is the four-byte bitset exposed as MedalSingleInfo.value.
            # Accept legacy/imported column names as well while deployments
            # migrate the schema.
            value = row.get('value_bits', row.get('medal_value', row.get('value', 0)))
            get_time = row.get('get_time', row.get('time', 0))
            flag = row.get('show_flag', row.get('flag', 0))
            out += struct.pack('>4I', medal_id, _u32(value), _u32(get_time), _u32(flag))
        return Response(bytes(out), user_id=account.user_id)

    def three_day_reward_state(self, s, p):
        """Return the seven rookie-login reward states (2372).

        RookiePlayerRewardBean reads exactly seven uint32 values and treats
        state 1 as a reward that can be shown.  The table is intentionally
        sparse: an absent day is the normal, already-unavailable state 2,
        while deployments can insert/update individual days as the player
        earns or claims them.
        """
        account = s.state.get('account')
        if not account or p.user_id not in (0, account.user_id):
            return Response(user_id=p.user_id, status=401)

        states = [2] * 7
        try:
            rows = self.accounts.rows('player_three_day_rewards', account.user_id)
            for row in rows:
                day = int(row.get('day_index', 0))
                if 1 <= day <= 7:
                    states[day - 1] = _u32(row.get('reward_state', row.get('state', 2)))
        except Exception as exc:
            # Keep the protocol usable when the optional migration has not
            # been applied yet; the all-2 response is still well-formed.
            LOG.warning("THREE_DAY_REWARD_STATE query failed for uid=%s: %s", account.user_id, exc)

        return Response(struct.pack('>7I', *states), user_id=account.user_id)

    def someone_medals(self,s,p):
        uid=struct.unpack('>I',p.payload[:4])[0] if len(p.payload)>=4 else p.user_id
        try:
            rows = self.accounts.rows('player_medals', uid)
        except Exception as exc:
            LOG.warning("MEDAL_SOMEONE query failed for uid=%s: %s", uid, exc)
            rows = []
        rows = sorted(rows, key=lambda row: (int(row.get('medal_id', 0)), int(row.get('get_time', 0))))
        out=bytearray(struct.pack('>2I',int(time.time()),len(rows)))
        for r in rows: out += struct.pack('>3I',_u32(r.get('medal_id')), _u32(r.get('get_time')), _u32(r.get('show_flag')))
        return Response(bytes(out),user_id=p.user_id)

    def medal_have_one(self, s, p):
        """Return whether the logged-in player owns one requested medal (1207).

        The AS3 decoder reads a one-byte result first.  When non-zero it reads
        medal ID, acquisition time and the exchange flag (the stored medal
        value bitset), so an absent record must return exactly one zero byte.
        """
        account = s.state.get('account')
        if not account:
            return Response(user_id=p.user_id, status=401)
        if len(p.payload) < 4:
            return Response(b'\x00', user_id=account.user_id)

        medal_id = struct.unpack_from('>I', p.payload, 0)[0]
        try:
            rows = self.accounts.rows('player_medals', account.user_id)
        except Exception as exc:
            LOG.warning("MEDAL_HAVE_ONE query failed for uid=%s: %s", account.user_id, exc)
            rows = []
        row = next((item for item in rows if int(item.get('medal_id', 0)) == medal_id), None)
        if not row:
            return Response(b'\x00', user_id=account.user_id)

        get_time = row.get('get_time', row.get('time', 0))
        exchange_flag = row.get('value_bits', row.get('medal_value', row.get('value', 0)))
        payload = b'\x01' + struct.pack('>3I', medal_id, _u32(get_time), _u32(exchange_flag))
        return Response(payload, user_id=account.user_id)

    def beauty_get_myinfo(self, s, p):
        """Return the optional pageant profile in the AS3 BeautyUserInfo layout."""
        account = s.state.get('account')
        if not account or len(p.payload) != 4:
            return Response(user_id=p.user_id, status=401 if not account else 400)
        target_id = struct.unpack('>I', p.payload)[0]
        target = self.accounts.get_by_id(target_id)
        if not target:
            return Response(user_id=account.user_id, status=404)

        try:
            beauty = self.accounts.beauty_profile(target_id)
        except Exception as exc:
            LOG.warning("BEAUTY_GET_MYINFO query failed for uid=%s: %s", target_id, exc)
            beauty = None
        if not beauty:
            # BeautyUserInfoManager treats a zero count as "not entered".
            return Response(struct.pack('>I', 0), user_id=account.user_id)

        profile = dict(target.profile or {})
        try:
            profile.update(self.accounts.profile(target_id))
        except Exception:
            pass
        value = lambda key, default=0: _u32(beauty.get(key, default))
        nickname = beauty.get('user_nick') or profile.get('nickname') or target.login_name
        out = bytearray(struct.pack('>3I', 1, target_id,
                                    value('user_nation', profile.get('nationality', 1))))
        out += fixed_utf8(str(nickname), 16)
        out += fixed_utf8(str(beauty.get('user_words', '')), 30)
        out += struct.pack('>3I', value('user_rank_num', 9999), value('user_vote'), value('user_fan'))

        presents = beauty.get('recent_presents') or []
        for index in range(3):
            gift = presents[index] if index < len(presents) and isinstance(presents[index], dict) else {}
            giver_id = gift.get('presentGiverID', gift.get('present_giver_id', gift.get('giver_id', 0)))
            giver_nick = gift.get('presentGiverNick', gift.get('present_giver_nick', gift.get('giver_nick', '')))
            item_id = gift.get('presentID', gift.get('present_id', gift.get('item_id', 0)))
            out += struct.pack('>I', _u32(giver_id))
            out += fixed_utf8(str(giver_nick), 16)
            out += struct.pack('>I', _u32(item_id))

        out += struct.pack('>6I', value('user_color'), value('skin'), value('user_face'),
                           value('user_eye'), value('user_eyebrow'), value('user_lip'))
        clothes = beauty.get('clothes') or []
        clothes = [row for row in clothes if isinstance(row, (list, tuple))][:100]
        out += struct.pack('>I', len(clothes))
        for row in clothes:
            values = [_u32(item) for item in row[:18]]
            values.extend([0] * (18 - len(values)))
            out += struct.pack('>18I', *values)
        return Response(bytes(out), user_id=account.user_id)

    def map_players(self,s,p):
        # Other-player state is kept in the in-memory store; empty list is valid.
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        players = []
        # NPCs are static map occupants, not dynamic online players.
        # Homes/house interiors have their own NPC setup on the client and
        # must not receive the public-map NPC list.
        if not int(s.state.get("house_id", 0)):
            try:
                players.extend(self.accounts.npc_rows(_u32(s.state.get("map_id", 0))))
            except Exception as exc:
                LOG.warning("NPC query failed for map=%s: %s", s.state.get("map_id", 0), exc)
        if self.map_player_store:
            map_scope = self._map_scope(s)
            try:
                players.extend(
                    row
                    for row in self.map_player_store.list_players(map_scope)
                    if int(row.get("user_id", 0)) != int(a.user_id)
                )
            except Exception as exc:
                LOG.warning("map player read failed for scope=%s: %s", map_scope, exc)
        payload=bytearray(struct.pack('>I',len(players)))
        for row in players:
            payload += _enter_map_eff_payload(row)
        return Response(bytes(payload),user_id=p.user_id)

    def map_items(self,s,p):
        a = s.state.get('account')
        if not a or p.user_id not in (0, a.user_id):
            return Response(user_id=p.user_id, status=401)
        if p.payload:
            return Response(user_id=a.user_id, status=400)

        map_id = _u32(s.state.get('map_id', _profile_value(a, 'map_id', 1)))
        try:
            rows = self.accounts.map_materials(map_id)
        except Exception as exc:
            LOG.warning("MAP_GET_PICKITEM query failed for map=%s: %s", map_id, exc)
            return Response(user_id=a.user_id, status=5001)

        rows = [row for row in rows if random.random() < MAP_MATERIAL_SPAWN_RATE]
        out = bytearray(struct.pack('>I', len(rows)))
        for row in rows:
            out += struct.pack(
                '>3I',
                _u32(row.get('item_id')),
                _u32(row.get('x')),
                _u32(row.get('y')),
            )
        return Response(bytes(out), user_id=a.user_id)
