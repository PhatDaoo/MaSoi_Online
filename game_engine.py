import threading
import time
import random
import traceback
import sys

from common.const import CMD_MSG, CMD_SYSTEM, CMD_ROLE, CMD_ACTION, CMD_PHASE, CMD_OVER
from roles.mappings import *

class GameEngine:
    def __init__(self):
        self.players = [] 
        self.is_running = False
        self.day_count = 0
        self.log_callback = None
        self.discussion_event = threading.Event() 

    # --- CÁC HÀM CƠ BẢN (GIỮ NGUYÊN) ---
    def log(self, msg): 
        print(f"[GAME] {msg}", flush=True)
        if self.log_callback: self.log_callback(msg)

    def add_player(self, player):
        player.lover_id = None; player.status = {}
        # Khởi tạo kho đồ cho role đặc biệt
        player.inventory = {
            "witch_heal": True, "witch_poison": True, # Phù thủy
            "guard_last_target": None # Bảo vệ
        }
        self.players.append(player)
        self.broadcast(CMD_SYSTEM, f"👋 {player.name} tham gia! (Tổng: {len(self.players)})")

    def remove_player(self, player):
        if player in self.players:
            self.players.remove(player)
            self.broadcast(CMD_SYSTEM, f"🏃 {player.name} rời làng!")

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

    def handle_message(self, player, data):
        msg_type = data.get("type")
        payload = data.get("payload")
        if msg_type == "MSG":
            status = "" if player.is_alive else "[HỒN MA] "
            self.broadcast(CMD_MSG, f"{status}[{player.name}]: {payload}")
        elif msg_type == "INPUT":
            player.receive_input_from_web(payload)

    # --- SETUP & START (GIỮ NGUYÊN) ---
    def start_game_sequence(self, setup_roles_list):
        if len(self.players) < 1: return
        if self.is_running: return
        
        # Reset trạng thái
        for p in self.players: 
            p.lover_id = None; p.status = {}; p.is_alive = True
            p.inventory = {"witch_heal": True, "witch_poison": True, "guard_last_target": None}

        self.broadcast(CMD_SYSTEM, "⏳ Đang khởi tạo thế giới...")
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
            "Dân Làng": Villager, "Sói": Werewolf, "Tiên Tri": Seer, "Bảo vệ": Protector,
            "Thợ săn": Hunter, "Phù thủy": Witch, "Sói con": WolfCub, "Sói đầu đàn": AlphaWolf,
            "Thần tình yêu": Cupid, "Kẻ chán đời": Tanner, "Ma cà rồng": Vampire, "Con lai": Lycan,
            "Khủng bố": Terrorist, "Du côn": Hoodlum, "Chủ giáo phái": CultLeader
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
            p.send({"type": CMD_ROLE, "payload": {"role_name": p.role.name, "description": p.role.description}})
            self.log(f"[ROLE] {p.name} -> {p.role.name}")

    # --- GAME LOOP (GIỮ NGUYÊN) ---
    def game_loop(self):
        while self.is_running:
            try:
                self.day_count += 1
                
                # --- BAN ĐÊM ---
                self.broadcast(CMD_PHASE, "NIGHT")
                self.broadcast(CMD_SYSTEM, f"\n=== ĐÊM THỨ {self.day_count} ==="); time.sleep(2)
                self.play_night_logic_v2()
                
                # --- BAN NGÀY ---
                self.broadcast(CMD_PHASE, "DAY")
                self.broadcast(CMD_SYSTEM, f"\n=== TRỜI SÁNG ==="); time.sleep(2)
                
                died = self.calculate_night_deaths()
                if died:
                    names = ", ".join([p.name for p in died])
                    self.broadcast(CMD_SYSTEM, f"💀 Đêm qua: {names} đã chết!")
                    self.process_deaths(died)
                else:
                    self.broadcast(CMD_SYSTEM, "🎉 Đêm nay bình yên, không ai chết.")

                if self.check_win_condition(): break

                # ========================================================
                # --- SỬA ĐỔI: THẢO LUẬN KHÔNG GIỚI HẠN THỜI GIAN ---
                # ========================================================
                self.broadcast(CMD_SYSTEM, "🗣️ BẮT ĐẦU THẢO LUẬN...")
                self.broadcast(CMD_SYSTEM, "(Chờ Quản trò bấm 'KẾT THÚC' để bỏ phiếu)")
                
                # Bật cờ để biết đang trong giờ thảo luận
                self.is_discussion_phase = True
                self.discussion_event.clear() # Đặt lại sự kiện về trạng thái chờ
                
                # Server sẽ DỪNG Ở ĐÂY mãi mãi cho đến khi admin bấm nút
                self.discussion_event.wait()
                
                # Khi code chạy xuống đây tức là Admin đã bấm nút
                self.is_discussion_phase = False
                self.broadcast(CMD_SYSTEM, "🛑 HẾT GIỜ THẢO LUẬN!")
                time.sleep(1)
                # ========================================================

                # Vote
                self.broadcast(CMD_SYSTEM, "⚖️ BẮT ĐẦU BỎ PHIẾU TREO CỔ."); time.sleep(1) 
                self.process_voting()
                if self.check_win_condition(): break

                # Reset status cuối ngày
                for p in self.players:
                    p.status["protected"] = False
                    p.status["targeted"] = False
                    p.status["poisoned"] = False

            except Exception as e:
                self.log(f"LOOP ERROR: {e}"); traceback.print_exc(); self.is_running = False

    # =========================================================================
    # --- LOGIC ĐÊM NÂNG CAO (V2) ---
    # =========================================================================
    def play_night_logic_v2(self):
        # 1. THẦN TÌNH YÊU (Chỉ đêm 1)
        if self.day_count == 1:
            self.trigger_role_action("Thần tình yêu", self.action_cupid)

        # 2. BẢO VỆ (Thức trước để bảo vệ)
        self.trigger_role_action("Bảo vệ", self.action_bodyguard)
        
        # 3. SÓI (Cắn người) -> Trả về nạn nhân tạm thời
        wolf_victim = self.process_werewolf_phase()

        # 4. PHÙ THỦY (Biết ai bị cắn, dùng bình)
        self.trigger_role_action("Phù thủy", lambda p: self.action_witch(p, wolf_victim))

        # 5. TIÊN TRI (Soi)
        self.trigger_role_action("Tiên Tri", self.action_seer)
        
        # 6. CÁC ROLE KHÁC (Thợ săn, Ma cà rồng...) gọi chung
        # (Bạn có thể thêm hàm riêng nếu muốn logic phức tạp hơn)

    def end_discussion(self):
        """Hàm này được gọi từ app.py khi Admin bấm nút màu Cam"""
        if self.is_discussion_phase:
            self.broadcast(CMD_SYSTEM, "🔔 Quản trò đã kết thúc phiên thảo luận.")
            self.discussion_event.set() # Mở khóa cho game_loop chạy tiếp

    def trigger_role_action(self, role_name, action_func):
        """Tìm người chơi có role này và cho họ hành động"""
        actors = [p for p in self.players if p.is_alive and p.role.name == role_name]
        for p in actors:
            self.broadcast(CMD_SYSTEM, f"💤 {role_name} đang thức giấc...", exclude=None)
            action_func(p)
            time.sleep(1)

    # --- LOGIC CỤ THỂ TỪNG ROLE ---

    def action_cupid(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive]
        self.broadcast(CMD_SYSTEM, "💘 Thần tình yêu đang ghép đôi...", exclude=player)
        
        # Chọn người thứ 1
        c1 = player.wait_for_input("Chọn người yêu thứ nhất:", targets)
        if c1 == "SKIP": return
        
        # Chọn người thứ 2 (loại người 1 ra)
        targets_2 = [t for t in targets if t[0] != c1]
        c2 = player.wait_for_input("Chọn người yêu thứ hai:", targets_2)
        if c2 == "SKIP": return

        # Ghép đôi
        p1 = self.get_player_by_id(c1)
        p2 = self.get_player_by_id(c2)
        if p1 and p2:
            p1.lover_id = p2.sid
            p2.lover_id = p1.sid
            p1.send({"type": CMD_SYSTEM, "payload": f"💘 BẠN ĐANG YÊU {p2.name}!"})
            p2.send({"type": CMD_SYSTEM, "payload": f"💘 BẠN ĐANG YÊU {p1.name}!"})
            player.send({"type": CMD_SYSTEM, "payload": f"✅ Đã ghép {p1.name} ❤️ {p2.name}"})

    def action_bodyguard(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive]
        
        targets.append(("SKIP", "Không bảo vệ"))
        
        choice = player.wait_for_input("Bảo vệ ai đêm nay?", targets)
        if choice and choice != "SKIP":
            target = self.get_player_by_id(choice)
            if target:
                # Cập nhật trạng thái bảo vệ
                target.status["protected_by_bodyguard"] = True
                target.status["protected"] = True
                # Lưu lại người vừa bảo vệ (Dù luật mới cho phép lặp lại, ta cứ lưu để log hoặc mở rộng sau này)
                player.inventory["guard_last_target"] = target.sid
                
                player.send({"type": CMD_SYSTEM, "payload": f"🛡️ Đang bảo vệ {target.name}"})
        else:
            player.inventory["guard_last_target"] = None

    def process_werewolf_phase(self):
        wolves = [p for p in self.players if p.is_alive and "Sói" in p.role.name]
        if not wolves: return None
        
        self.broadcast(CMD_SYSTEM, "🐺 Sói đang tìm mồi...")
        targets = [(p.sid, p.name) for p in self.players if p.is_alive and "Sói" not in p.role.name]
        targets.append(("SKIP", "Không cắn"))
        
        # Đơn giản hóa: Chỉ cần con Sói đầu tiên chọn (để tránh xung đột luồng phức tạp trên Web)
        # Nếu muốn Vote kín giữa các sói, cần logic phức tạp hơn.
        leader_wolf = wolves[0] 
        victim_id = leader_wolf.wait_for_input("CẮN AI?", targets)
        
        # Đồng bộ kết quả cho các sói khác biết
        victim = None
        if victim_id != "SKIP":
            victim = self.get_player_by_id(victim_id)
            if victim:
                victim.status["targeted"] = True
                for w in wolves: w.send({"type": CMD_SYSTEM, "payload": f"🩸 Đã chọn cắn: {victim.name}"})
        else:
             for w in wolves: w.send({"type": CMD_SYSTEM, "payload": "🩸 Đêm nay ăn chay."})
        
        return victim

    def action_witch(self, player, wolf_victim):
        # 1. Bình Cứu
        has_heal = player.inventory.get("witch_heal", True)
        used_heal = False
        
        if has_heal and wolf_victim:
            choice = player.wait_for_input(f"🔮 {wolf_victim.name} bị cắn. CỨU KHÔNG?", [("YES", "Cứu"), ("NO", "Không")])
            if choice == "YES":
                wolf_victim.status["targeted"] = False # Hủy sát thương sói
                player.inventory["witch_heal"] = False
                player.send({"type": CMD_SYSTEM, "payload": f"✨ Đã cứu {wolf_victim.name}"})
                used_heal = True
        
        # 2. Bình Độc (Chỉ dùng nếu chưa cứu đêm nay - Luật thường gặp)
        has_poison = player.inventory.get("witch_poison", True)
        if has_poison and not used_heal:
            targets = [(p.sid, p.name) for p in self.players if p.is_alive]
            targets.append(("SKIP", "Không dùng độc"))
            
            target_id = player.wait_for_input("☠️ Dùng ĐỘC lên ai?", targets)
            if target_id != "SKIP":
                target = self.get_player_by_id(target_id)
                if target:
                    target.status["poisoned"] = True
                    player.inventory["witch_poison"] = False
                    player.send({"type": CMD_SYSTEM, "payload": f"☠️ Đã đầu độc {target.name}"})

    def action_seer(self, player):
        targets = [(p.sid, p.name) for p in self.players if p.is_alive and p != player]
        choice = player.wait_for_input("Soi ai?", targets)
        if choice != "SKIP":
            target = self.get_player_by_id(choice)
            if target:
                # Logic soi cơ bản (Sói/Người)
                result = "PHE SÓI" if "Sói" in target.role.name else "PHE NGƯỜI"
                if target.role.name == "Con lai": result = "PHE SÓI" # Con lai soi ra Sói
                player.send({"type": CMD_SYSTEM, "payload": f"👁️ {target.name} là {result}"})

    # --- XỬ LÝ CÁI CHẾT ---
    def calculate_night_deaths(self):
        dead = []
        for p in self.players:
            if not p.is_alive: continue
            
            # Chết do Sói (nếu ko được bảo vệ)
            if p.status.get("targeted") and not p.status.get("protected"):
                dead.append(p)
            
            # Chết do Phù thủy
            elif p.status.get("poisoned"):
                dead.append(p)
                
        return list(set(dead))

    def process_deaths(self, dead_list):
        # Đánh dấu chết và kiểm tra cặp đôi
        final_dead = list(dead_list)
        
        # Duyệt đệ quy để tìm người yêu chết theo
        i = 0
        while i < len(final_dead):
            victim = final_dead[i]
            victim.is_alive = False
            
            # Kiểm tra Thợ săn (Kéo theo ngay lập tức)
            if victim.role.name == "Thợ săn":
                self.trigger_hunter_revenge(victim, final_dead)

            # Kiểm tra người yêu
            if victim.lover_id:
                lover = self.get_player_by_id(victim.lover_id)
                if lover and lover.is_alive and lover not in final_dead:
                    self.broadcast(CMD_SYSTEM, f"💔 {lover.name} chết theo tình yêu với {victim.name}!")
                    lover.is_alive = False
                    final_dead.append(lover)
            i += 1

    def trigger_hunter_revenge(self, hunter, dead_list_ref):
        # Thợ săn chọn 1 người để kéo theo
        targets = [(p.sid, p.name) for p in self.players if p.is_alive and p not in dead_list_ref]
        if not targets: return
        
        # Do thợ săn đã chết, ta gửi request đặc biệt
        target_id = hunter.wait_for_input("🔫 KÉO THEO AI?", targets)
        if target_id != "SKIP":
            target = self.get_player_by_id(target_id)
            if target:
                self.broadcast(CMD_SYSTEM, f"🔫 ĐOÀNG! Thợ săn {hunter.name} đã bắn chết {target.name}!")
                target.is_alive = False
                dead_list_ref.append(target)

    # --- VOTING (RÚT GỌN CHO WEB) ---
    def process_voting(self):
        alive = [p for p in self.players if p.is_alive]
        if not alive: return
        
        candidates = [(p.sid, p.name) for p in alive] + [("SKIP", "Hủy phiếu")]
        
        # Mở luồng hỏi từng người
        results = []
        threads = []
        def ask(v):
            c = v.wait_for_input("Treo cổ ai?", candidates)
            if c != "SKIP": results.append(c)
        
        for v in alive: 
            t = threading.Thread(target=ask, args=(v,)); t.start(); threads.append(t)
        for t in threads: t.join()

        # Kiểm phiếu
        votes = {}
        for target_id in results:
            votes[target_id] = votes.get(target_id, 0) + 1
            
        if not votes: 
            self.broadcast(CMD_SYSTEM, "⚪ Không ai bị treo cổ."); return

        # Tìm người cao phiếu nhất
        max_v = max(votes.values())
        most = [pid for pid, n in votes.items() if n == max_v]
        
        if len(most) == 1:
            victim = self.get_player_by_id(most[0])
            if victim:
                self.broadcast(CMD_SYSTEM, f"⚖️ {victim.name} bị treo cổ với {max_v} phiếu!")
                self.process_deaths([victim]) # Xử lý chết (bao gồm thợ săn/người yêu)
        else:
            self.broadcast(CMD_SYSTEM, f"⚖️ Hòa phiếu ({max_v}). Không ai chết.")

    def check_win_condition(self):
        alive = [p for p in self.players if p.is_alive]
        wolves = [p for p in alive if "Sói" in p.role.name]
        
        if not wolves: 
            self.broadcast(CMD_OVER, {"winner": "PHE DÂN LÀNG", "list": []})
            self.is_running = False; return True
        
        if len(wolves) >= len(alive) - len(wolves): 
            self.broadcast(CMD_OVER, {"winner": "PHE SÓI", "list": []})
            self.is_running = False; return True
            
        # Thêm điều kiện Phe thứ 3 nếu cần
        return False