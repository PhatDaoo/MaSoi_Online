import threading
import time
import random
import traceback
import sys

from common.const import *
from roles.mappings import *

class GameEngine:
    def __init__(self):
        self.players = [] 
        self.is_running = False
        self.day_count = 0
        self.log_callback = None
        self.update_callback = None
        self.discussion_event = threading.Event() 
        self.is_last_words_phase = False
        self.last_words_player = None
        self.current_phase = "DAY"
        self.status = {} # Lưu trạng thái game

    # --- CÁC HÀM CƠ BẢN ---
    def log(self, msg): 
        print(f"[GAME] {msg}", flush=True)
        if self.log_callback: self.log_callback(msg)

    def trigger_admin_update(self):
        if self.update_callback: self.update_callback()

    def add_player(self, player):
        # 1. Kiểm tra xem người chơi này có phải đang Reconnect không?
        # (Tìm xem trong list players cũ có ai tên trùng không)
        existing_p = next((p for p in self.players if p.name == player.name), None)
        
        if existing_p:
            # Nếu là Reconnect: Cập nhật lại SID mới cho object cũ
            existing_p.sid = player.sid
            player = existing_p # Dùng lại object cũ (giữ nguyên Role, Status)
            self.log(f"♻️ {player.name} đã kết nối lại (Reconnect).")
            
            # Gửi lại thông tin Role cho người chơi vừa vào lại
            if self.is_running and player.role:
                player.send({"type": CMD_ROLE, "payload": {"role_id": player.role.name}})
                player.send({"type": CMD_SYSTEM, "payload": "🔄 Bạn đã kết nối lại vào game!"})
        else:
            # Nếu là người chơi mới hoàn toàn
            player.lover_id = None; player.status = {}
            player.inventory = {"witch_heal": True, "witch_poison": True, "guard_last_target": None}
            self.players.append(player)
            self.broadcast(CMD_SYSTEM, f"👋 {player.name} tham gia! (Tổng: {len(self.players)})")

        self.broadcast_seat_map()
        self.trigger_admin_update()

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
            self.broadcast(CMD_SYSTEM, f"🏃 {player.name} rời làng!")
            self.broadcast_seat_map()
            self.trigger_admin_update()

    def get_player_by_id(self, p_id):
        for p in self.players:
            if hasattr(p, 'sid') and p.sid == p_id: return p
            if str(id(p)) == p_id: return p
        return None

    def broadcast(self, msg_type, content, exclude=None):
        data = {"type": msg_type, "payload": content}
        for p in self.players:
            if p != exclude:
                try: p.send(data)
                except: pass
    
    def broadcast_seat_map(self):
        seats = [{"name": p.name, "alive": p.is_alive} for p in self.players]
        self.broadcast("SEAT_UPDATE", seats)

    def handle_message(self, player, data):
        msg_type = data.get("type")
        payload = data.get("payload")

        if msg_type == "MSG":
            if self.is_last_words_phase:
                if player == self.last_words_player:
                    self.broadcast(CMD_MSG, f"📢 [LỜI CUỐI] {player.name}: {payload}")
                else:
                    player.send({"type": CMD_SYSTEM, "payload": "🤫 TRẬT TỰ! Để người chết trăn trối."})
                return

            if not player.is_alive:
                dead_players = [p for p in self.players if not p.is_alive]
                for dp in dead_players:
                    dp.send({"type": CMD_MSG, "payload": f"👻 [CÕI ÂM] {player.name}: {payload}"})
                return

            is_night = (self.current_phase == 'NIGHT')
            is_werewolf = (player.role and player.role.team == "Werewolf")
            is_lone_wolf = (player.role and player.role.name in ["Sói đơn độc", "Lone Wolf"])

            if is_night and is_werewolf and not is_lone_wolf:
                wolves = [p for p in self.players if p.role.team == "Werewolf" and p.role.name not in ["Sói đơn độc", "Lone Wolf"]]
                for w in wolves:
                    w.send({"type": CMD_MSG, "payload": f"🐺 [SÓI] {player.name}: {payload}"})
            else:
                if is_night:
                    player.send({"type": CMD_SYSTEM, "payload": "🌙 Ban đêm im lặng! (Chỉ Sói chat)"})
                else:
                    self.broadcast(CMD_MSG, f"[{player.name}]: {payload}")

        elif msg_type == "INPUT":
            player.receive_input_from_web(payload)

    def get_neighbors(self, player):
        alive_players = [p for p in self.players if p.is_alive]
        if len(alive_players) < 2: return []
        try: idx = alive_players.index(player)
        except ValueError: return []
        left_idx = (idx - 1) % len(alive_players)
        right_idx = (idx + 1) % len(alive_players)
        neighbors = {alive_players[left_idx], alive_players[right_idx]}
        return list(neighbors)

    def start_game_sequence(self, setup_roles_list):
        if len(self.players) < 1: return
        if self.is_running: return
        
        self.status = {} 
        for p in self.players: 
            p.lover_id = None; p.status = {}; p.is_alive = True
            p.inventory = {"witch_heal": True, "witch_poison": True, "guard_last_target": None}

        self.broadcast(CMD_SYSTEM, "⏳ Đang khởi tạo thế giới...")
        self.broadcast_seat_map()
        
        role_deck = self.setup_deck_from_list(setup_roles_list)
        while len(role_deck) < len(self.players): role_deck.append(Villager())

        self.is_running = True
        self.assign_roles(role_deck)
        
        try: self.game_loop()
        except Exception as e:
            self.log(f"CRASH: {e}"); traceback.print_exc(); self.is_running = False

    def setup_deck_from_list(self, role_names_list):
        deck = []
        NAME_TO_CLASS = {
            ROLE_WEREWOLF: Werewolf, ROLE_LEADER_WOLF: LeaderWolf, ROLE_ALPHA_WOLF: AlphaWolf,
            ROLE_WOLF_CUB: WolfCub, ROLE_LONE_WOLF: LoneWolf, ROLE_SORCERESS: Sorceress,
            ROLE_DIRE_WOLF: DireWolf, ROLE_VEGETARIAN_WOLF: VegetarianWolf, ROLE_WOLFMAN: Wolfman,
            ROLE_VILLAGER: Villager, ROLE_SEER: Seer, ROLE_BODYGUARD: Bodyguard, ROLE_HUNTER: Hunter,
            ROLE_WITCH: Witch, ROLE_CUPID: Cupid, ROLE_LYCAN: Lycan, ROLE_OLD_MAN: OldMan,
            ROLE_APPRENTICE_SEER: ApprenticeSeer, ROLE_TOUGH_GUY: ToughGuy, ROLE_SICK_MAN: SickMan,
            ROLE_PRINCE: Prince, ROLE_INSOMNIAC: Insomniac, ROLE_BEHOLDER: Beholder, ROLE_HUNTRESS: Huntress,
            ROLE_MENTALIST: Mentalist, ROLE_REVEALER: Revealer, ROLE_PRIEST: Priest, ROLE_DOPPELGANGER: Doppelganger,
            ROLE_DRUNK: Drunk, ROLE_DETECTIVE: Detective, ROLE_AURA_SEER: AuraSeer, ROLE_MAYOR: Mayor,
            ROLE_MARTYR: Martyr, ROLE_TWINS: Twins, ROLE_MYSTIC_SEER: MysticSeer, ROLE_CURSED: Cursed,
            ROLE_LITTLE_GIRL: LittleGirl, ROLE_GRANNY: Granny,
            ROLE_TERRORIST: Terrorist, ROLE_TANNER: Tanner, ROLE_VAMPIRE: Vampire, ROLE_CULT_LEADER: CultLeader,
            ROLE_HOODLUM: Hoodlum, ROLE_MUMMY: Mummy, ROLE_BLOODY_MARY: BloodyMary, ROLE_CHUPACABRA: Chupacabra
        }
        for name in role_names_list:
            role_class = NAME_TO_CLASS.get(name, Villager) 
            deck.append(role_class())
        return deck

    def assign_roles(self, role_deck):
        random.shuffle(role_deck)
        self.broadcast(CMD_SYSTEM, "========== TRÒ CHƠI BẮT ĐẦU ==========")
        time.sleep(1)
        for i, p in enumerate(self.players):
            p.role = role_deck[i]
            p.send({"type": CMD_ROLE, "payload": {"role_id": p.role.name}})
            self.log(f"[ROLE] {p.name} -> {p.role.name}")
        self.trigger_admin_update()

    def game_loop(self):
        while self.is_running:
            try:
                self.day_count += 1
                self.current_phase = "NIGHT"
                self.broadcast(CMD_PHASE, "NIGHT")
                self.broadcast(CMD_SYSTEM, f"\n=== ĐÊM THỨ {self.day_count} ==="); time.sleep(2)
                self.log(f"--- ĐÊM {self.day_count} ---")
                
                self.play_night_logic_v2() 
                self.trigger_admin_update()
                
                self.current_phase = "DAY"
                self.broadcast(CMD_PHASE, "DAY")
                self.broadcast(CMD_SYSTEM, f"\n=== TRỜI SÁNG ==="); time.sleep(2)
                self.log(f"--- NGÀY {self.day_count} ---")
                
                died = self.calculate_night_deaths()
                if died:
                    names = ", ".join([p.name for p in died])
                    self.broadcast(CMD_SYSTEM, f"💀 Đêm qua: {names} đã chết!")
                    self.log(f"💀 CHẾT ĐÊM: {names}")
                    self.process_deaths(died)
                else:
                    self.broadcast(CMD_SYSTEM, "🎉 Đêm nay bình yên.")
                    self.log("🎉 Không ai chết.")

                self.broadcast_seat_map() 
                self.trigger_admin_update()
                if self.check_win_condition(): break

                self.broadcast(CMD_SYSTEM, "🗣️ THẢO LUẬN..."); self.is_discussion_phase = True
                self.discussion_event.clear(); self.discussion_event.wait()
                self.is_discussion_phase = False; self.broadcast(CMD_SYSTEM, "🛑 HẾT GIỜ!")
                time.sleep(1)

                self.broadcast(CMD_SYSTEM, "⚖️ BỎ PHIẾU."); time.sleep(1) 
                self.process_voting()
                self.broadcast_seat_map()
                self.trigger_admin_update()
                if self.check_win_condition(): break

                for p in self.players:
                    p.status["protected"] = False
                    p.status["targeted"] = False
                    p.status["poisoned"] = False
                    p.status["protected_by_bodyguard"] = False
                    p.status["killed_by_huntress"] = False
                    p.status["killed_by_chupacabra"] = False
                    p.status["revealed_kill"] = False
                    if "hypnotized_by" in p.status: del p.status["hypnotized_by"]

            except Exception as e:
                self.log(f"LOOP ERROR: {e}"); traceback.print_exc(); self.is_running = False

    def play_night_logic_v2(self):
        if self.day_count == 1:
            self.trigger_role_action(ROLE_CUPID, self.action_cupid)
            self.trigger_role_action(ROLE_TWINS, self.action_generic)
            self.trigger_role_action(ROLE_DOPPELGANGER, self.action_generic)

        self.trigger_role_action(ROLE_BODYGUARD, self.action_bodyguard)
        wolf_victim = self.process_werewolf_phase()
        self.trigger_role_action(ROLE_WITCH, lambda p: self.action_witch(p, wolf_victim))
        
        self.trigger_role_action(ROLE_SEER, self.action_seer) 
        self.trigger_role_action(ROLE_AURA_SEER, self.action_generic)   
        self.trigger_role_action(ROLE_MYSTIC_SEER, self.action_generic) 
        self.trigger_role_action(ROLE_APPRENTICE_SEER, self.action_generic) 
        self.trigger_role_action(ROLE_LITTLE_GIRL, self.action_generic) 
        
        self.trigger_role_action(ROLE_INSOMNIAC, self.action_generic)
        self.trigger_role_action(ROLE_DETECTIVE, self.action_generic)
        self.trigger_role_action(ROLE_MENTALIST, self.action_generic)
        self.trigger_role_action(ROLE_REVEALER, self.action_generic)
        self.trigger_role_action(ROLE_VAMPIRE, self.action_generic)
        self.trigger_role_action(ROLE_PRIEST, self.action_generic)
        self.trigger_role_action(ROLE_HUNTRESS, self.action_generic)
        self.trigger_role_action(ROLE_MUMMY, self.action_generic)
        self.trigger_role_action(ROLE_CHUPACABRA, self.action_generic)
        self.trigger_role_action(ROLE_HOODLUM, self.action_generic)
        self.trigger_role_action(ROLE_CULT_LEADER, self.action_generic)
        self.trigger_role_action(ROLE_DIRE_WOLF, self.action_generic)
        self.trigger_dead_role_action(ROLE_BLOODY_MARY, self.action_generic)

    def trigger_role_action(self, role_name, action_func):
        actors = [p for p in self.players if p.is_alive and p.role.name == role_name]
        for p in actors:
            self.broadcast(CMD_SYSTEM, f"💤 {role_name} đang thức...", exclude=None)
            action_func(p) 
            time.sleep(1)

    def trigger_dead_role_action(self, role_name, action_func):
        # Lọc những người chơi ĐÃ CHẾT và có role này
        actors = [p for p in self.players if not p.is_alive and p.role.name == role_name]
        for p in actors:
            # Chỉ gọi dậy nếu đã xác định được thời điểm chết (tránh lỗi)
            if p.status.get("death_phase"):
                p.send({"type": CMD_SYSTEM, "payload": f"👻 Oán hồn {role_name} trỗi dậy..."})
                action_func(p) 
                time.sleep(1)

    def action_generic(self, player):
        if hasattr(player.role, 'on_night'):
            res = player.role.on_night(self, player)
            if res: player.send({"type": CMD_SYSTEM, "payload": res})

    def action_cupid(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive]
        c1 = player.wait_for_input("Người yêu 1:", targets)
        if c1 == "SKIP": return
        targets_2 = [t for t in targets if t[0] != c1]
        c2 = player.wait_for_input("Người yêu 2:", targets_2)
        if c2 == "SKIP": return
        p1 = self.get_player_by_id(c1); p2 = self.get_player_by_id(c2)
        if p1 and p2:
            p1.lover_id = p2.sid; p2.lover_id = p1.sid
            p1.send({"type": CMD_SYSTEM, "payload": f"💘 BẠN YÊU {p2.name}!"})
            p2.send({"type": CMD_SYSTEM, "payload": f"💘 BẠN YÊU {p1.name}!"})
            player.send({"type": CMD_SYSTEM, "payload": f"✅ Đã ghép {p1.name} ❤️ {p2.name}"})

    def action_bodyguard(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive] + [("SKIP", "Bỏ qua")]
        choice = player.wait_for_input("Bảo vệ ai?", targets)
        if choice != "SKIP":
            t = self.get_player_by_id(choice)
            if t:
                t.status["protected_by_bodyguard"] = True; t.status["protected"] = True
                player.send({"type": CMD_SYSTEM, "payload": f"🛡️ Đã bảo vệ {t.name}"})

    def process_werewolf_phase(self):
        hunting_wolves = []
        leader_alive = False
        alpha_wolf_player = None

        for p in self.players:
            if not p.is_alive: continue
            if p.role.team == "Werewolf":
                if p.role.name == ROLE_LEADER_WOLF: leader_alive = True
                if p.role.name == ROLE_ALPHA_WOLF: alpha_wolf_player = p
                
                # --- CẬP NHẬT LOGIC NANH SÓI (DIRE WOLF) ---
                if p.role.name == ROLE_DIRE_WOLF:
                    # Kiểm tra xem còn đồng đội Sói nào khác sống không
                    # (Trừ bản thân và các role phụ như Bà Đồng, Sói Cô Độc nếu muốn)
                    teammates_alive = any(
                        w.is_alive and w.role.team == "Werewolf" and w != p 
                        and w.role.name not in [ROLE_SORCERESS, ROLE_LONE_WOLF]
                        for w in self.players
                    )
                    
                    # Logic: Dậy Đêm 1 HOẶC khi không còn đồng đội
                    if self.day_count == 1 or not teammates_alive:
                        hunting_wolves.append(p)
                        if not teammates_alive:
                            p.send({"type": CMD_SYSTEM, "payload": "🐺 Đàn sói đã chết hết! Bạn phải thức giấc để đi săn!"})
                    else:
                        # Nếu đang ngủ đông -> Gửi tin nhắn giả vờ ngủ
                        p.send({"type": CMD_SYSTEM, "payload": "💤 Bạn đang ngủ đông để ẩn mình..."})
                
                # --- CÁC SÓI KHÁC ---
                else:
                    # Giữ nguyên logic loại trừ cũ
                    excluded = [ROLE_LONE_WOLF, ROLE_SORCERESS] # Đã bỏ ROLE_DIRE_WOLF khỏi đây
                    if p.role.name not in excluded:
                        hunting_wolves.append(p)

        if not hunting_wolves: return None
        self.broadcast(CMD_SYSTEM, "🐺 Đàn Sói đang tìm mồi...")

        kills_allowed = 1
        if leader_alive: kills_allowed += 1       
        if self.status.get("extra_wolf_kill"):    
            kills_allowed += 1
            self.status["extra_wolf_kill"] = False 
            for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": "🩸 TRẢ THÙ CHO SÓI CON: Được cắn thêm người!"})

        if leader_alive:
            for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": "🩸 SÓI ĐẦU ĐÀN DẪN DẮT: Được cắn 2 người!"})

        targets = [(p.sid, p.name) for p in self.players if p.is_alive and p.role.team != "Werewolf"] + [("SKIP", "Bỏ qua")]
        last_victim = None 

        for i in range(kills_allowed):
            leader = hunting_wolves[0] 
            prompt = f"CẮN AI? (Lượt {i+1}/{kills_allowed})"
            victim_id = leader.wait_for_input(prompt, targets)
            
            if victim_id == "SKIP":
                for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": f"Lượt {i+1}: Không cắn ai."})
                continue

            victim = self.get_player_by_id(victim_id)
            if not victim: continue
            for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": f"🩸 Đã chọn: {victim.name}"})
            
            is_cursed = (victim.role.name == ROLE_CURSED)
            victim_infected = False

            if alpha_wolf_player and not getattr(alpha_wolf_player.role, 'ability_used', False) and not is_cursed:
                choice = alpha_wolf_player.wait_for_input(f"🩸 Biến {victim.name} thành Sói?", [("YES", "Biến hình"), ("NO", "Giết")])
                if choice == "YES":
                    alpha_wolf_player.role.ability_used = True
                    victim_infected = True
                    victim.role = Werewolf(); victim.role.team = "Werewolf"
                    victim.send({"type": CMD_SYSTEM, "payload": "🩸 BẠN BỊ SÓI ALPHA CẮN VÀ ĐÃ TRỞ THÀNH SÓI!"})
                    victim.send({"type": CMD_ROLE, "payload": {"role_id": ROLE_WEREWOLF}}) 
                    for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": f"🐺 Alpha đã biến {victim.name} thành đồng loại!"})

            if victim_infected: pass 
            elif is_cursed:
                self.log(f"⚠️ {victim.name} là Kẻ bị nguyền -> Hóa Sói!")
                victim.role = Werewolf(); victim.role.team = "Werewolf"
                victim.send({"type": CMD_SYSTEM, "payload": "🩸 BẠN BỊ CẮN VÀ ĐÃ HÓA SÓI!"})
                victim.send({"type": CMD_ROLE, "payload": {"role_id": ROLE_WEREWOLF}})
                for w in hunting_wolves: w.send({"type": CMD_SYSTEM, "payload": f"🐺 {victim.name} đã hóa thành SÓI!"})
            else:
                victim.status["targeted"] = True
                last_victim = victim 
                targets = [t for t in targets if t[0] != victim.sid]

        return last_victim

    def action_witch(self, player, wolf_victim):
        has_heal = player.inventory["witch_heal"]
        used_heal = False
        if has_heal and wolf_victim:
            c = player.wait_for_input(f"🔮 Cứu {wolf_victim.name}?", [("YES","Có"),("NO","Ko")])
            if c == "YES":
                wolf_victim.status["targeted"] = False
                player.inventory["witch_heal"] = False
                player.send({"type": CMD_SYSTEM, "payload": f"✨ Đã cứu {wolf_victim.name}"})
                used_heal = True
        
        has_poison = player.inventory["witch_poison"]
        if has_poison and not used_heal:
            targets = [(p.sid, p.name) for p in self.players if p.is_alive] + [("SKIP","Ko độc")]
            c = player.wait_for_input("☠️ Độc ai?", targets)
            if c != "SKIP":
                t = self.get_player_by_id(c)
                if t:
                    t.status["poisoned"] = True
                    player.inventory["witch_poison"] = False
                    player.send({"type": CMD_SYSTEM, "payload": f"☠️ Đã độc {t.name}"})

    def action_seer(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive and p != player]
        c = player.wait_for_input("Soi ai?", targets)
        if c != "SKIP":
            t = self.get_player_by_id(c)
            if t:
                res = player.role.on_night(self, player)
                if res: player.send({"type": CMD_SYSTEM, "payload": res})

    def calculate_night_deaths(self):
        dead = []
        for p in self.players:
            if not p.is_alive: continue
            
            # --- LOGIC MỤC SƯ (PRIEST) ---
            # Nếu có trạng thái "blessed" -> Bất tử mọi sát thương ĐÊM
            if p.status.get("blessed"):
                continue 

            # Các điều kiện chết thông thường
            if (p.status.get("targeted") and not p.status.get("protected")) or \
               p.status.get("poisoned") or \
               p.status.get("killed_by_chupacabra") or \
               p.status.get("killed_by_huntress") or \
               p.status.get("revealed_kill") or \
               p.status.get("killed_by_bloody_mary"): # <--- THÊM DÒNG NÀY
                dead.append(p)
                
        return list(set(dead))

    def process_deaths(self, dead_list):
        final_dead = list(dead_list)
        i = 0
        while i < len(final_dead):
            victim = final_dead[i]
            victim.is_alive = False
            
            if victim.role.name == ROLE_TERRORIST:
                self.broadcast(CMD_SYSTEM, f"💣 {victim.name} là KHỦNG BỐ! KÍCH NỔ!")
                neighbors = self.get_neighbors(victim)
                for n in neighbors:
                    if n not in final_dead:
                        self.broadcast(CMD_SYSTEM, f"🔥 Hàng xóm {n.name} chết lây!")
                        n.is_alive = False; final_dead.append(n)

            if victim.role.name == ROLE_HUNTER:
                self.trigger_hunter_revenge(victim, final_dead)
            
            if victim.role.name == ROLE_DIRE_WOLF:
                 if hasattr(victim.role, 'on_death'): victim.role.on_death(self, victim)

            if victim.role.name == ROLE_BLOODY_MARY:
                # Lưu thời điểm chết (DAY hoặc NIGHT) vào status
                victim.status["death_phase"] = self.current_phase
                self.broadcast(CMD_SYSTEM, f"🩸 Bloody Mary đã chết vào {self.current_phase}! Ả sẽ hiện về báo thù hằng đêm...")

            if victim.lover_id:
                lover = self.get_player_by_id(victim.lover_id)
                if lover and lover.is_alive and lover not in final_dead:
                    self.broadcast(CMD_SYSTEM, f"💔 {lover.name} tự sát theo tình yêu!")
                    lover.is_alive = False; final_dead.append(lover)
            
            if hasattr(victim.role, 'on_death') and victim.role.name not in [ROLE_DIRE_WOLF, ROLE_BLOODY_MARY]:
                 victim.role.on_death(self, victim)

            i += 1

    def trigger_hunter_revenge(self, hunter, dead_list_ref):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive and p not in dead_list_ref]
        if not targets: return
        tid = hunter.wait_for_input("🔫 KÉO THEO AI?", targets)
        if tid != "SKIP":
            t = self.get_player_by_id(tid)
            if t:
                self.broadcast(CMD_SYSTEM, f"💥 {t.name} bị Thợ săn bắn!")
                t.is_alive = False; dead_list_ref.append(t)

    # ============================================================
    # FIX LỖI MUMMY LOGIC (ĐÃ SỬA CHẶT CHẼ)
    # ============================================================
    def process_voting(self):
        alive = [p for p in self.players if p.is_alive]
        if not alive: return
        
        candidates = [(p.sid, p.name) for p in alive] + [("SKIP", "Hủy phiếu")]
        raw_votes = {}; threads = []
        
        def ask(v):
            c = v.wait_for_input("Treo cổ ai?", candidates)
            raw_votes[v.sid] = c

        for v in alive: 
            t = threading.Thread(target=ask, args=(v,)); t.start(); threads.append(t)
        for t in threads: t.join()

        # --- LOGIC MUMMY (ĐÃ FIX LỖI F5) ---
        # Tạo map: Tên Người Chơi -> Phiếu Bầu
        name_to_vote = {}
        for p in alive:
            vote_val = raw_votes.get(p.sid)
            if vote_val: name_to_vote[p.name] = vote_val

        for p in alive:
            # Lấy TÊN Mummy đã ám người này
            mummy_name = p.status.get("hypnotized_by") 
            if mummy_name:
                # Tìm phiếu bầu của Mummy dựa trên Tên
                mummy_vote = name_to_vote.get(mummy_name)
                
                if mummy_vote:
                    raw_votes[p.sid] = mummy_vote # Ghi đè phiếu
                    
                    # Tìm object Mummy để lấy tên hiển thị thông báo
                    # (Không quan trọng lắm nếu ko tìm thấy, chỉ để log)
                    p.send({"type": CMD_SYSTEM, "payload": f"😵 Bạn bị {mummy_name} (Xác ướp) thôi miên! Phiếu của bạn buộc phải theo hắn."})
                    self.log(f"[MUMMY] {p.name} vote theo {mummy_name} -> {mummy_vote}")
                else:
                    self.log(f"[MUMMY ERROR] Không tìm thấy phiếu của Mummy {mummy_name} (Có thể đã chết hoặc không vote)")

        # --- TỔNG HỢP KẾT QUẢ ---
        vote_details = {}; results = []
        for voter in alive:
            target_id = raw_votes.get(voter.sid)
            if not target_id: continue 
            results.append(target_id)
            if target_id == "SKIP": vote_details[voter.name] = "Trắng án"
            else:
                target = self.get_player_by_id(target_id)
                vote_details[voter.name] = target.name if target else "?"

        summary = "📊 KẾT QUẢ VOTE:\n" + "\n".join([f"- {v} ➔ {t}" for v,t in vote_details.items()])
        self.broadcast(CMD_SYSTEM, summary); time.sleep(3)

        votes = {}
        for r in results: votes[r] = votes.get(r, 0) + 1
        if not votes: return self.broadcast(CMD_SYSTEM, "⚪ Không ai bị treo.")

        max_v = max(votes.values())
        most = [pid for pid, n in votes.items() if n == max_v]
        
        # Nếu SKIP (Hủy phiếu) cao nhất thì không ai chết
        if "SKIP" in most:
             self.broadcast(CMD_SYSTEM, f"⚖️ Đa số phiếu trắng. Không ai chết.")
             return

        if len(most) == 1:
            victim = self.get_player_by_id(most[0])
            if victim:
                self.broadcast(CMD_SYSTEM, f"⚖️ {victim.name} bị treo cổ!")
                if victim.role.name == ROLE_TANNER:
                     self.broadcast(CMD_MSG, f"🤡 {victim.name} là KẺ CHÁN ĐỜI! Hắn muốn chết và hắn ĐÃ THẮNG!")
                     self.end_game("KẺ CHÁN ĐỜI (Tanner)")
                     return
                self.is_last_words_phase = True
                self.last_words_player = victim
                self.broadcast(CMD_SYSTEM, f"🎙️ {victim.name} có 15s trăn trối...")
                for k in range(15, 0, -5): self.broadcast(CMD_SYSTEM, f"⏳ {k}s..."); time.sleep(5)
                self.broadcast(CMD_SYSTEM, "🛑 HẾT GIỜ!")
                self.is_last_words_phase = False; self.last_words_player = None
                self.process_deaths([victim])
        else:
            self.broadcast(CMD_SYSTEM, f"⚖️ Hòa phiếu. Không ai chết.")

    def end_discussion(self):
        if self.is_discussion_phase:
            self.broadcast(CMD_SYSTEM, "🔔 Admin kết thúc thảo luận.")
            self.discussion_event.set()

    def check_win_condition(self):
        alive = [p for p in self.players if p.is_alive]
        wolves = [p for p in alive if p.role.team == "Werewolf"]
        chupa_list = [p for p in alive if p.role.name == ROLE_CHUPACABRA]

        # 1. Phe Sói thắng
        if wolves and len(wolves) >= len(alive) - len(wolves): 
            self.end_game("PHE SÓI") 
            return True

        # 2. Phe Dân thắng
        if not wolves: 
            if chupa_list:
                if len(chupa_list) >= len(alive) - len(chupa_list):
                    self.end_game("QUỶ HÚT MÁU (Chupacabra)")
                    return True
                return False
            else:
                self.end_game("PHE DÂN LÀNG") 
                return True

        return False
    
    def end_game(self, winner_msg):
        """Hàm xử lý kết thúc game và gửi bảng kết quả chi tiết"""
        results = []
        for p in self.players:
            results.append({
                "name": p.name,
                "role_id": p.role.name,  # ID Role (tiếng Anh) để client hiển thị ảnh
                "team": p.role.team,
                "alive": p.is_alive
            })
        
        self.broadcast(CMD_OVER, {
            "winner": winner_msg,
            "results": results
        })
        self.is_running = False