# roles/mappings.py
import random
from roles.base import Role
from common.const import *

# ==========================================
# 1. PHE DÂN LÀNG (VILLAGER FACTION)
# ==========================================

class Villager(Role):
    def __init__(self): super().__init__(ROLE_VILLAGER, "Villager", "Ngủ.")

class Seer(Role):
    def __init__(self): super().__init__(ROLE_SEER, "Villager", "Soi phe (Sói/Người).")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            # Người sói (Wolfman) soi ra Dân
            if t.role.name == ROLE_WOLFMAN: 
                return f"👁️ {t.name} là PHE NGƯỜI."
            # Con lai (Lycan) soi ra Sói
            if t.role.name == ROLE_LYCAN: 
                return f"👁️ {t.name} là PHE SÓI."
            
            is_wolf = t.role.team == "Werewolf"
            return f"👁️ {t.name} là {'PHE SÓI' if is_wolf else 'PHE NGƯỜI'}."
        return None

class Bodyguard(Role):
    def __init__(self): super().__init__(ROLE_BODYGUARD, "Villager", "Bảo vệ 1 người.")

class Witch(Role):
    def __init__(self): super().__init__(ROLE_WITCH, "Villager", "Bình Cứu/Độc.")

class Hunter(Role):
    def __init__(self): 
        super().__init__(ROLE_HUNTER, "Villager", "Bị treo cổ -> Được bắn 1 người.")

class Cupid(Role):
    def __init__(self): super().__init__(ROLE_CUPID, "Villager", "Ghép đôi.")

class Lycan(Role):
    def __init__(self): super().__init__(ROLE_LYCAN, "Villager", "Dân bị soi ra Sói.")

class OldMan(Role): # Già làng
    def __init__(self): 
        super().__init__(ROLE_OLD_MAN, "Villager", "Chết vào đêm X (X = Số lượng Sói ban đầu).")
    
    def on_night(self, game, my_player):
        # 1. Tính số lượng Sói ban đầu (Tính cả người đã chết để lấy số lượng gốc)
        # Bao gồm tất cả các role có team là "Werewolf" (Sói, Sói con, Alpha, Bà đồng,...)
        initial_wolf_count = sum(1 for p in game.players if p.role.team == "Werewolf")
        
        # 2. Kiểm tra nếu đêm nay trùng với số lượng Sói
        if game.day_count == initial_wolf_count:
            my_player.is_alive = False
            return f"👴 Đêm thứ {game.day_count} (trùng số lượng Sói), tuổi già sức yếu nên bạn đã qua đời."
        
        return None

class ApprenticeSeer(Role):
    def __init__(self): super().__init__(ROLE_APPRENTICE_SEER, "Villager", "Kế thừa Tiên tri.")
    def on_night(self, game, my_player):
        seer_alive = any(p.is_alive and p.role.name == ROLE_SEER for p in game.players)
        if not seer_alive:
            targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
            tid = my_player.wait_for_input("👁️ [THỨC TỈNH] Soi ai?", targets)
            t = game.get_player_by_id(tid)
            if t:
                is_wolf = t.role.team == "Werewolf"
                return f"👁️ {t.name} là {'PHE SÓI' if is_wolf else 'PHE NGƯỜI'}."
        return "Tiên tri vẫn còn sống."

class ToughGuy(Role):
    def __init__(self): super().__init__(ROLE_TOUGH_GUY, "Villager", "Bị cắn chết chậm.")

class SickMan(Role):
    def __init__(self): super().__init__(ROLE_SICK_MAN, "Villager", "Sói cắn bị bệnh.")
    def on_death(self, game, my_player):
        if my_player.status.get("targeted"):
            game.status["wolves_skip_hunt"] = True
            game.broadcast(CMD_SYSTEM, "🤢 Sói cắn phải Người bệnh! Đêm mai Sói bị ốm.")

class Prince(Role):
    def __init__(self): super().__init__(ROLE_PRINCE, "Villager", "Không bị treo cổ.")

class Insomniac(Role):
    def __init__(self): super().__init__(ROLE_INSOMNIAC, "Villager", "Biết hàng xóm dậy.")
    def on_night(self, game, my_player):
        neighbors = game.get_neighbors(my_player)
        # Check xem hàng xóm có role nào dậy đêm không
        woke = [n.name for n in neighbors if hasattr(n.role, 'on_night') and n.role.on_night.__code__ != Role.on_night.__code__]
        if woke: return f"👀 Hàng xóm {', '.join(woke)} đã thức giấc!"
        return "👀 Hàng xóm ngủ ngon."

class Beholder(Role):
    def __init__(self): super().__init__(ROLE_BEHOLDER, "Villager", "Biết Tiên tri.")
    def on_night(self, game, my_player):
        seers = [p.name for p in game.players if p.role.name == ROLE_SEER]
        return f"Tiên tri là: {', '.join(seers)}" if seers else "Không có Tiên tri."

class Huntress(Role):
    def __init__(self): 
        super().__init__(ROLE_HUNTRESS, "Villager", "Bắn đêm (1 lần).")
        self.used = False
    def on_night(self, game, my_player):
        if self.used: return None
        targets = [(p.sid, p.name) for p in game.players if p.is_alive and p != my_player] + [("SKIP", "Không")]
        tid = my_player.wait_for_input("🏹 Bắn ai?", targets)
        if tid != "SKIP":
            t = game.get_player_by_id(tid)
            if t:
                t.status["killed_by_huntress"] = True
                self.used = True
                return f"Đã bắn {t.name}"
        return None

class Mentalist(Role):
    def __init__(self): super().__init__(ROLE_MENTALIST, "Villager", "Soi cùng phe.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        if len(targets) < 2: return "Thiếu người."
        id1 = my_player.wait_for_input("Người 1:", targets)
        t2 = [x for x in targets if x[0] != id1]
        id2 = my_player.wait_for_input("Người 2:", t2)
        p1 = game.get_player_by_id(id1); p2 = game.get_player_by_id(id2)
        if p1 and p2:
            same = (p1.role.team == p2.role.team)
            return f"{p1.name} và {p2.name} {'CÙNG' if same else 'KHÁC'} phe."
        return None

class Revealer(Role):
    def __init__(self): super().__init__(ROLE_REVEALER, "Villager", "Soi Sói chết, Dân mình chết.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🔦 Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            if t.role.team == "Werewolf":
                t.status["revealed_kill"] = True # Cần engine xử lý chết
                return f"Đã khám phá ra Sói {t.name}!"
            else:
                my_player.status["revealed_kill"] = True # Tự sát
                return "Đây là Dân! Bạn sẽ chết."
        return None

class Priest(Role):
    def __init__(self): 
        super().__init__(ROLE_PRIEST, "Villager", "Ban bất tử (1 lần, trừ bản thân).")
        self.used = False
        
    def on_night(self, game, my_player):
        if self.used: return None
        
        # SỬA: Loại bỏ my_player khỏi danh sách targets (Không tự ban phước)
        targets = [(p.sid, p.name) for p in game.players if p.is_alive and p != my_player]
        
        tid = my_player.wait_for_input("✝️ Ban phước ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["blessed"] = True # Gán trạng thái Bất Tử
            self.used = True
            return f"Đã ban phước cho {t.name}. Người này sẽ bất tử vào ban đêm!"
        return None

class Doppelganger(Role):
    def __init__(self): 
        super().__init__(ROLE_DOPPELGANGER, "Villager", "Sao chép role.")
        self.target_sid = None
    def on_night(self, game, my_player):
        if game.day_count == 1:
            targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
            self.target_sid = my_player.wait_for_input("👤 Sao chép ai?", targets)
            return "Đã chọn mục tiêu."
        return None

class Drunk(Role):
    def __init__(self): super().__init__(ROLE_DRUNK, "Villager", "Đêm 3 chọn phe.")
    def on_night(self, game, my_player):
        if game.day_count == 3:
            c = my_player.wait_for_input("🍺 Chọn phe:", [("WOLF", "Sói"), ("VILLAGER", "Dân")])
            if c == "WOLF": my_player.role.team = "Werewolf"
            return "Đã chọn phe."
        return None

class Detective(Role):
    def __init__(self): 
        super().__init__(ROLE_DETECTIVE, "Villager", "Soi hàng xóm của mục tiêu.")

    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🕵️ Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            # Lấy danh sách hàng xóm CỦA MỤC TIÊU (t), không phải của Thám tử
            target_neighbors = game.get_neighbors(t)
            
            # Kiểm tra xem trong số hàng xóm đó, có ai thuộc team "Werewolf" không
            has_wolf_neighbor = any(n.role.team == "Werewolf" for n in target_neighbors)
            
            if has_wolf_neighbor:
                return f"⚠️ Có mùi nguy hiểm! Một trong những người ngồi cạnh {t.name} là SÓI."
            else:
                return f"✅ An toàn. Hai người ngồi cạnh {t.name} đều KHÔNG PHẢI Sói."
        
        return None

class AuraSeer(Role):
    def __init__(self): super().__init__(ROLE_AURA_SEER, "Villager", "Soi chức năng.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("✨ Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            no_abil = [ROLE_VILLAGER, ROLE_WEREWOLF]
            return f"{t.name}: {'CÓ' if t.role.name not in no_abil else 'KHÔNG'} chức năng."
        return None

class Mayor(Role):
    def __init__(self): super().__init__(ROLE_MAYOR, "Villager", "Vote x2.")

class Martyr(Role):
    def __init__(self): super().__init__(ROLE_MARTYR, "Villager", "Chết thay.")

class Twins(Role):
    def __init__(self): super().__init__(ROLE_TWINS, "Villager", "Biết mặt nhau.")
    def on_night(self, game, my_player):
        if game.day_count == 1:
            others = [p.name for p in game.players if p.role.name == ROLE_TWINS and p != my_player]
            return f"Song sinh: {', '.join(others)}" if others else "Lẻ loi."
        return None

class MysticSeer(Role):
    def __init__(self): super().__init__(ROLE_MYSTIC_SEER, "Villager", "Soi role chính xác.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🔮 Soi role ai?", targets)
        t = game.get_player_by_id(tid)
        if t: return f"Vai trò của {t.name}: {t.role.name}"
        return None

class Cursed(Role):
    def __init__(self): super().__init__(ROLE_CURSED, "Villager", "Bị cắn hóa Sói.")

class LittleGirl(Role):
    def __init__(self): super().__init__(ROLE_LITTLE_GIRL, "Villager", "Soi Sói nếu Bà chết.")
    def on_night(self, game, my_player):
        granny_dead = any(p.role.name == ROLE_GRANNY and not p.is_alive for p in game.players)
        if not granny_dead: return "Bà vẫn khỏe."
        
        # Danh sách soi được (CONST)
        targets = [
            ROLE_WEREWOLF, ROLE_ALPHA_WOLF, ROLE_LEADER_WOLF, 
            ROLE_WOLF_CUB, ROLE_LONE_WOLF, ROLE_SORCERESS, 
            ROLE_DIRE_WOLF, ROLE_VEGETARIAN_WOLF, ROLE_WOLFMAN
        ]
        visible = [p for p in game.players if p.is_alive and p.role.name in targets and p != my_player]
        
        if visible:
            wolf = random.choice(visible)
            return f"👀 Hé lộ: {wolf.name} là {wolf.role.name}!"
        return "Không thấy bóng sói."

class Granny(Role):
    def __init__(self): super().__init__(ROLE_GRANNY, "Villager", "Chết -> Cháu thức tỉnh.")


# ==========================================
# 2. PHE SÓI (WEREWOLF FACTION)
# ==========================================

class Werewolf(Role):
    def __init__(self): super().__init__(ROLE_WEREWOLF, "Werewolf", "Cắn.")

class LeaderWolf(Role):
    def __init__(self): super().__init__(ROLE_LEADER_WOLF, "Werewolf", "Cắn 2.")

class AlphaWolf(Role):
    def __init__(self): 
        super().__init__(ROLE_ALPHA_WOLF, "Werewolf", "Biến hình.")
        self.ability_used = False

class WolfCub(Role):
    def __init__(self): super().__init__(ROLE_WOLF_CUB, "Werewolf", "Chết -> Cắn thêm.")
    def on_death(self, game, my_player):
        game.status["extra_wolf_kill"] = True
        game.broadcast(CMD_SYSTEM, "🐺 Sói Con chết! Đêm mai Sói hung hãn hơn!")

class LoneWolf(Role):
    def __init__(self): super().__init__(ROLE_LONE_WOLF, "Werewolf", "Thắng lẻ.")

class Sorceress(Role):
    def __init__(self): super().__init__(ROLE_SORCERESS, "Werewolf", "Soi Tiên tri.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🔮 Tìm Tiên tri:", targets)
        t = game.get_player_by_id(tid)
        if t:
            seers = [ROLE_SEER, ROLE_APPRENTICE_SEER, ROLE_MYSTIC_SEER, ROLE_AURA_SEER]
            return f"{t.name} {'LÀ' if t.role.name in seers else 'KHÔNG PHẢI'} Tiên Tri."
        return None

class DireWolf(Role):
    def __init__(self): 
        # Sửa mô tả cho đúng logic mới
        super().__init__(ROLE_DIRE_WOLF, "Werewolf", "Đêm 1 dậy cùng bầy. Ngủ đông đến khi là Sói cuối cùng.")

class VegetarianWolf(Role):
    def __init__(self): super().__init__(ROLE_VEGETARIAN_WOLF, "Werewolf", "Ăn chay.")
    def on_night(self, game, my_player): return "Ăn chay ngủ ngon."

class Wolfman(Role):
    def __init__(self): super().__init__(ROLE_WOLFMAN, "Werewolf", "Soi ra Dân.")

# ==========================================
# 3. PHE THỨ 3 (NEUTRAL)
# ==========================================

class Terrorist(Role):
    def __init__(self): super().__init__(ROLE_TERRORIST, "Neutral", "Nổ.")

class Tanner(Role):
    def __init__(self): super().__init__(ROLE_TANNER, "Neutral", "Thích chết.")

class Vampire(Role):
    def __init__(self): super().__init__(ROLE_VAMPIRE, "Neutral", "Hút máu.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🧛 Cắn ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["bitten_by_vampire"] = True
            return f"Đã cắn {t.name}"
        return None

class CultLeader(Role):
    def __init__(self): 
        super().__init__(ROLE_CULT_LEADER, "Neutral", "Truyền đạo.")
        self.followers = []
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive and p.sid not in self.followers]
        tid = my_player.wait_for_input("🙏 Truyền đạo:", targets)
        if tid:
            self.followers.append(tid)
            t = game.get_player_by_id(tid)
            if t: 
                t.send({"type": CMD_SYSTEM, "payload": "🙏 Bạn đã gia nhập Giáo Phái!"})
                return f"Đã dụ dỗ {t.name}"
        return None

class Hoodlum(Role):
    def __init__(self): 
        super().__init__(ROLE_HOODLUM, "Neutral", "Chọn mục tiêu.")
        self.targets = []
    def on_night(self, game, my_player):
        if game.day_count == 1:
            targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
            if len(targets) < 2: return "Thiếu người."
            id1 = my_player.wait_for_input("Mục tiêu 1:", targets)
            t2 = [x for x in targets if x[0] != id1]
            id2 = my_player.wait_for_input("Mục tiêu 2:", t2)
            self.targets = [id1, id2]
            return "Đã chọn mục tiêu."
        return None

class Mummy(Role):
    def __init__(self): super().__init__(ROLE_MUMMY, "Neutral", "Thôi miên.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🤕 Thôi miên ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            # SỬA LỖI: Lưu TÊN (Name) thay vì SID để tránh lỗi khi F5
            t.status["hypnotized_by"] = my_player.name 
            return f"Đã thôi miên {t.name}."
        return None

class BloodyMary(Role):
    def __init__(self): 
        super().__init__(ROLE_BLOODY_MARY, "Neutral", "Chết -> Hồn ma báo thù hằng đêm.")

    def on_night(self, game, my_player):
        # Nếu còn sống thì ngủ như bình thường
        if my_player.is_alive: 
            return None

        # Lấy thông tin chết vào buổi nào (được lưu trong engine)
        death_phase = my_player.status.get("death_phase")
        if not death_phase: return None

        targets = []
        msg = ""

        if death_phase == "NIGHT":
            # Chết ban đêm -> Giết Sói + Phe 3
            msg = "🩸 Báo thù (Sói/Phe 3):"
            # Lọc mục tiêu: Còn sống VÀ (là Sói HOẶC là Phe 3)
            targets = [(p.sid, p.name) for p in game.players if p.is_alive and (p.role.team == "Werewolf" or p.role.team == "Neutral")]
        else: 
            # Chết ban ngày (DAY) -> Giết Dân
            msg = "🩸 Báo thù (Dân làng):"
            # Lọc mục tiêu: Còn sống VÀ là Dân
            targets = [(p.sid, p.name) for p in game.players if p.is_alive and p.role.team == "Villager"]

        if not targets: return "👻 Không còn ai để báo thù."

        tid = my_player.wait_for_input(msg, targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["killed_by_bloody_mary"] = True
            return f"👻 Đã chọn ám sát {t.name}."
        
        return None

class Chupacabra(Role):
    def __init__(self): 
        super().__init__(ROLE_CHUPACABRA, "Neutral", "Ăn Sói (Sói hết -> Ăn Dân).")

    def on_night(self, game, my_player):
        # 1. Kiểm tra xem còn Sói nào sống không (Trừ bản thân nếu bị tính là Wolf team, nhưng Chupa là Neutral nên ko sao)
        wolves_alive = any(p.is_alive and p.role.team == "Werewolf" for p in game.players)
        
        # 2. Xác định mục tiêu và câu hỏi dựa trên tình hình
        msg_prompt = "🩸 Tìm Sói:"
        if not wolves_alive:
            msg_prompt = "🩸 Sói đã tuyệt chủng! Ăn thịt bất kỳ ai:"
        
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input(msg_prompt, targets)
        t = game.get_player_by_id(tid)
        
        if t:
            if wolves_alive:
                # --- TRƯỜNG HỢP CÒN SÓI: CHỈ ĂN ĐƯỢC SÓI ---
                if t.role.team == "Werewolf":
                    t.status["killed_by_chupacabra"] = True
                    return f"NGON! {t.name} là Sói và đã chết."
                else:
                    return f"SAI! {t.name} không phải Sói. Bạn không thể ăn."
            else:
                # --- TRƯỜNG HỢP HẾT SÓI: ĂN TẠP ---
                t.status["killed_by_chupacabra"] = True
                return f"Đã ăn thịt {t.name} (Vì Sói đã hết)."
        
        return None
    
'''class Detective(Role):
    def __init__(self): super().__init__(ROLE_DETECTIVE, "Villager", "Điều tra tội phạm.")
    def on_night(self, game, my_player):
        targets = [(p.sid, p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🕵️ Điều tra ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            # Check xem có phải role giết người không
            killers = [ROLE_WEREWOLF, ROLE_ALPHA_WOLF, ROLE_LEADER_WOLF, ROLE_VAMPIRE, ROLE_CHUPACABRA, ROLE_TERRORIST]
            is_killer = t.role.name in killers
            return f"{t.name} {'LÀ' if is_killer else 'KHÔNG PHẢI'} tội phạm."
        return None'''