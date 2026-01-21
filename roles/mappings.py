# roles/mappings.py
import random
from roles.base import Role
from common.const import *

# ==========================================
# NHÓM DÂN LÀNG (PASSIVE / BASIC)
# ==========================================

class Villager(Role):
    def __init__(self):
        super().__init__(ROLE_VILLAGER, "Villager", "Ngủ.")

class Lycan(Role): # Con lai
    def __init__(self):
        super().__init__(ROLE_LYCAN, "Villager", "Là Dân nhưng Tiên tri soi ra Sói.")

class Mayor(Role): # Thị trưởng
    def __init__(self):
        super().__init__(ROLE_MAYOR, "Villager", "Phiếu vote tính bằng 2.")

class Cursed(Role): # Kẻ bị nguyền
    def __init__(self):
        super().__init__(ROLE_CURSED, "Villager", "Bị Sói cắn sẽ hóa Sói.")

class Prince(Role): # Hoàng tử
    def __init__(self):
        super().__init__(ROLE_PRINCE, "Villager", "Bị treo cổ sẽ lật bài và không chết.")

class SickMan(Role): # Người bệnh
    def __init__(self):
        super().__init__(ROLE_SICK_MAN, "Villager", "Sói cắn sẽ bị ngộ độc đêm sau.")

class ToughGuy(Role): # Thanh niên cứng
    def __init__(self):
        super().__init__(ROLE_TOUGH_GUY, "Villager", "Bị cắn chết chậm 1 ngày.")

class Ghost(Role): # Hồn ma
    def __init__(self):
        super().__init__(ROLE_GHOST, "Villager", "Chết đêm đầu. Mỗi đêm gửi 1 từ gợi ý.")
        self.wake_order = 0.2
    def on_night(self, game, my_player):
        return "Hãy nhập 1 từ gợi ý vào khung chat!"

# ==========================================
# NHÓM SÓI (WEREWOLF TEAM)
# ==========================================

class Werewolf(Role):
    def __init__(self):
        super().__init__(ROLE_WEREWOLF, "Werewolf", "Thống nhất cắn 1 người.")

class VegetarianWolf(Role): # Sói ăn chay
    def __init__(self):
        super().__init__(ROLE_VEGETARIAN_WOLF, "Werewolf", "Phe Sói nhưng không tham gia cắn.")
    def on_night(self, game, my_player):
        return "Bạn ăn chay, ngủ ngon."

class AlphaWolf(Role): # Sói đầu đàn
    def __init__(self):
        super().__init__(ROLE_ALPHA_WOLF, "Werewolf", "Vote x2. Có thể chọn biến nạn nhân thành Sói.")

class WolfCub(Role): # Sói con
    def __init__(self):
        super().__init__(ROLE_WOLF_CUB, "Werewolf", "Nếu chết, Sói cắn 2 người đêm sau.")

class LoneWolf(Role): # Sói đơn độc
    def __init__(self):
        super().__init__(ROLE_LONE_WOLF, "LoneWolf", "Thắng nếu là người cuối cùng.")

class DireWolf(Role): # Nanh sói
    def __init__(self):
        super().__init__(ROLE_DIRE_WOLF, "Werewolf", "Kết đôi 1 người. Chết kéo theo.")
        self.bond_target = None

    def on_night(self, game, my_player):
        if game.day_count == 1:
            targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
            tid = my_player.wait_for_input("🔗 Chọn người kết nghĩa:", targets)
            target = game.get_player_by_id(tid)
            if target:
                self.bond_target = target
                return f"Đã kết nghĩa với {target.name}"
        return None
    
    def on_death(self, game, my_player):
        if self.bond_target and self.bond_target.is_alive:
            game.broadcast("SYS", f"🔗 Nanh Sói chết, kéo theo {self.bond_target.name}!")
            self.bond_target.is_alive = False
            self.bond_target.role.on_death(game, self.bond_target)

class Medium(Role): # Bà đồng (Phe Sói)
    def __init__(self):
        super().__init__(ROLE_MEDIUM, "Werewolf", "Tìm Tiên tri.")
        self.wake_order = 1.8

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🔮 Tìm Tiên tri:", targets)
        t = game.get_player_by_id(tid)
        if t and t.role.name == ROLE_SEER:
            return f"BINGO! {t.name} là Tiên Tri!"
        return "Không phải Tiên Tri."

# ==========================================
# NHÓM BẢO VỆ & GIẾT
# ==========================================

class Protector(Role): # Bảo vệ
    def __init__(self):
        super().__init__(ROLE_PROTECTOR, "Villager", "Bảo vệ 1 người (chỉ chặn Sói).")

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive]
        tid = my_player.wait_for_input("🛡️ Bảo vệ ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["protected_by_bodyguard"] = True
            return f"Đã bảo vệ {t.name}"
        return None

class Priest(Role): # Mục sư
    def __init__(self):
        super().__init__(ROLE_PRIEST, "Villager", "Bất tử tuyệt đối (1 lần).")
        self.used = False
        self.wake_order = 0.5

    def on_night(self, game, my_player):
        if self.used: return "Đã dùng hết phép."
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive]
        targets.append(("SKIP", "Để dành"))
        c = my_player.wait_for_input("✝️ Ban phước ai?", targets)
        if c != "SKIP":
            t = game.get_player_by_id(c)
            if t:
                t.status["blessed"] = True
                self.used = True
                return f"Đã ban phước {t.name}"
        return None

class Hunter(Role): # Thợ săn
    def __init__(self):
        super().__init__(ROLE_HUNTER, "Villager", "Chết kéo theo 1 người.")
    
    def on_death(self, game, my_player):
        game.broadcast("SYS", f"🔫 {my_player.name} (THỢ SĂN) đang rút súng...")
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive and p != my_player]
        if targets:
            tid = my_player.wait_for_input("🔫 Bắn ai?", targets)
            t = game.get_player_by_id(tid)
            if t:
                game.broadcast("SYS", f"💥 ĐOÀNG! {t.name} bị bắn chết!")
                t.is_alive = False
                t.role.on_death(game, t)

class Huntress(Role): # Nữ thợ săn
    def __init__(self):
        super().__init__(ROLE_HUNTRESS, "Villager", "Bắn 1 người ban đêm (1 lần).")
        self.used = False

    def on_night(self, game, my_player):
        if self.used: return None
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        targets.append(("SKIP", "Không bắn"))
        c = my_player.wait_for_input("🏹 Bắn ai?", targets)
        if c != "SKIP":
            t = game.get_player_by_id(c)
            if t:
                t.status["killed_by_huntress"] = True
                self.used = True
                return f"Đã bắn {t.name}"
        return None

class Gambler(Role): # Con bạc
    def __init__(self):
        super().__init__(ROLE_GAMBLER, "Villager", "Đoán Sói. Đúng Sói chết, sai mình chết.")
        self.can_act = False

    def on_night(self, game, my_player):
        if game.day_count == 1: return "Đêm 1 nghỉ ngơi."
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🎲 Chọn ai là Sói?", targets)
        t = game.get_player_by_id(tid)
        if t:
            if t.role.team == "Werewolf":
                t.status["killed_by_gambler"] = True
                return f"🎲 CHÍNH XÁC! {t.name} sẽ chết."
            else:
                my_player.status["killed_by_gambler"] = True # Tự sát
                return "🎲 SAI RỒI! Bạn sẽ chết."
        return None

class Terrorist(Role): # Khủng bố
    def __init__(self):
        super().__init__(ROLE_TERRORIST, "Solo", "Nổ chết người vote hoặc Sói cắn.")
    # Logic nổ xử lý trong on_death ở Engine

# ==========================================
# NHÓM TIÊN TRI & SOI
# ==========================================

class Seer(Role): # Tiên tri
    def __init__(self):
        super().__init__(ROLE_SEER, "Villager", "Soi phe.")
        self.wake_order = 2

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        if not targets: return None
        tid = my_player.wait_for_input("👁️ Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            is_bad = (t.role.team == "Werewolf") or (t.role.name == ROLE_LYCAN)
            return f"{t.name} là {'PHE XẤU' if is_bad else 'PHE TỐT'}"
        return None

class AuraSeer(Role): # Tiên tri hào quang
    def __init__(self):
        super().__init__(ROLE_AURA_SEER, "Villager", "Soi chức năng.")

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("✨ Soi hào quang ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            no_abil = [ROLE_VILLAGER, ROLE_WEREWOLF, ROLE_VEGETARIAN_WOLF, ROLE_LYCAN]
            if t.role.name in no_abil: return f"{t.name}: Không chức năng."
            return f"{t.name}: CÓ CHỨC NĂNG."
        return None

class MysticSeer(Role): # Tiên tri bí ẩn
    def __init__(self):
        super().__init__(ROLE_MYSTIC_SEER, "Villager", "Soi role chính xác.")

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🔮 Soi role ai?", targets)
        t = game.get_player_by_id(tid)
        if t: return f"Vai trò của {t.name}: {t.role.name}"
        return None

class ApprenticeSeer(Role): # Tiên tri tập sự
    def __init__(self):
        super().__init__(ROLE_APPRENTICE_SEER, "Villager", "Kế thừa Tiên tri.")
        self.wake_order = 2.3

    def on_night(self, game, my_player):
        seer_alive = any(p.is_alive and p.role.name == ROLE_SEER for p in game.players)
        if seer_alive: return "Tiên tri còn sống."
        
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("👁️ [THỨC TỈNH] Soi ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            is_bad = (t.role.team == "Werewolf") or (t.role.name == ROLE_LYCAN)
            return f"{t.name} là {'PHE XẤU' if is_bad else 'PHE TỐT'}"
        return None

class ParanormalInvestigator(Role): # Nhà ngoại cảm
    def __init__(self):
        super().__init__(ROLE_PARANORMAL, "Villager", "Soi 2 người cùng phe không.")

    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        if len(targets) < 2: return "Không đủ người."
        
        id1 = my_player.wait_for_input("🔍 Người 1:", targets)
        t2 = [x for x in targets if x[0] != id1]
        id2 = my_player.wait_for_input("🔍 Người 2:", t2)
        
        p1 = game.get_player_by_id(id1)
        p2 = game.get_player_by_id(id2)
        if p1 and p2:
            return f"{p1.name} và {p2.name} {'CÙNG' if p1.role.team == p2.role.team else 'KHÁC'} phe."
        return None

class Detective(Role): # Thám tử
    def __init__(self):
        super().__init__(ROLE_DETECTIVE, "Villager", "Soi xem ai đã giết người.")
    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🕵️ Điều tra ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            criminal = t.role.name in [ROLE_WEREWOLF, ROLE_ALPHA_WOLF, ROLE_TERRORIST, ROLE_VAMPIRE, ROLE_LONE_WOLF]
            return f"{t.name} {'LÀ' if criminal else 'KHÔNG PHẢI'} tội phạm."
        return None

# ==========================================
# NHÓM CHỨC NĂNG ĐẶC BIỆT
# ==========================================

class Witch(Role): # Phù thủy
    def __init__(self):
        super().__init__(ROLE_WITCH, "Villager", "Cứu/Giết.")
        self.wake_order = 5
        self.has_heal = True; self.has_poison = True

    def on_night(self, game, my_player):
        res = []
        victim = next((p for p in game.players if p.status.get("targeted") and p.is_alive), None)
        
        if self.has_heal and victim:
            c = my_player.wait_for_input(f"⚗️ Cứu {victim.name}?", [("YES","Có"),("NO","Không")])
            if c == "YES":
                victim.status["targeted"] = False; victim.status["protected_by_bodyguard"] = True
                self.has_heal = False; res.append(f"Đã cứu {victim.name}")
        
        if self.has_poison:
            targets = [(str(id(p)), p.name) for p in game.players if p.is_alive and p != my_player] + [("SKIP","Không")]
            c = my_player.wait_for_input("☠️ Độc ai?", targets)
            if c != "SKIP":
                t = game.get_player_by_id(c)
                if t:
                    t.status["targeted"] = True
                    self.has_poison = False; res.append(f"Đã độc {t.name}")
        return ", ".join(res) if res else "Ngủ."

class Troublemaker(Role): # Kẻ phá rối
    def __init__(self):
        super().__init__(ROLE_TROUBLEMAKER, "Villager", "Tráo bài 2 người (1 lần).")
        self.used = False; self.wake_order = 3

    def on_night(self, game, my_player):
        if self.used: return None
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        if len(targets) < 2: return "Thiếu người."
        
        id1 = my_player.wait_for_input("🔄 Người 1:", targets)
        t2 = [x for x in targets if x[0] != id1]
        id2 = my_player.wait_for_input("🔄 Người 2:", t2)
        
        p1 = game.get_player_by_id(id1)
        p2 = game.get_player_by_id(id2)
        if p1 and p2:
            p1.role, p2.role = p2.role, p1.role
            self.used = True
            return f"Đã tráo {p1.name} <-> {p2.name}"
        return None

class Cupid(Role): # Thần tình yêu
    def __init__(self):
        super().__init__(ROLE_CUPID, "Villager", "Ghép đôi (Đêm 1).")
        self.wake_order = 0.1

    def on_night(self, game, my_player):
        if game.day_count > 1: return None
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive]
        if len(targets) < 2: return None
        
        id1 = my_player.wait_for_input("💘 Người 1:", targets)
        t2 = [x for x in targets if x[0] != id1]
        id2 = my_player.wait_for_input("💘 Người 2:", t2)
        
        p1 = game.get_player_by_id(id1)
        p2 = game.get_player_by_id(id2)
        if p1 and p2:
            p1.lover_id = id2; p2.lover_id = id1
            p1.send({"type":"SYS", "payload":f"💘 BẠN YÊU {p2.name}!"})
            p2.send({"type":"SYS", "payload":f"💘 BẠN YÊU {p1.name}!"})
            return f"Đã ghép {p1.name} ❤️ {p2.name}"
        return None

class Hoodlum(Role): # Du côn
    def __init__(self):
        super().__init__(ROLE_HOODLUM, "Solo", "Thắng nếu 2 mục tiêu chết & mình sống.")
    def on_night(self, game, my_player):
        if game.day_count == 1:
            targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
            if len(targets) < 2: return "Thiếu người."
            id1 = my_player.wait_for_input("🎯 Mục tiêu 1:", targets)
            t2 = [x for x in targets if x[0] != id1]
            id2 = my_player.wait_for_input("🎯 Mục tiêu 2:", t2)
            return f"MỤC TIÊU: {id1}, {id2}" 
        return None

class Drunk(Role): # Bợm nhậu
    def __init__(self):
        super().__init__(ROLE_DRUNK, "Villager", "Đêm 3 hóa role mới.")

class Magician(Role): # Pháp sư
    def __init__(self):
        super().__init__(ROLE_MAGICIAN, "Villager", "Yểm bùa câm.")
    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive]
        tid = my_player.wait_for_input("😶 Yểm bùa ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["silenced"] = True
            return f"Đã yểm bùa {t.name}"
        return None

class OldHag(Role): # Mụ già
    def __init__(self):
        super().__init__(ROLE_OLD_HAG, "Villager", "Ám 1 người (bị câm).")
    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p.is_alive]
        tid = my_player.wait_for_input("🧙‍♀️ Ám ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["silenced"] = True
            return f"Đã ám {t.name}"
        return None

class Vampire(Role): # Ma cà rồng
    def __init__(self):
        super().__init__(ROLE_VAMPIRE, "Solo", "Cắn người. Chết chậm.")
    def on_night(self, game, my_player):
        targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
        tid = my_player.wait_for_input("🧛 Cắn ai?", targets)
        t = game.get_player_by_id(tid)
        if t:
            t.status["bitten_by_vampire"] = True
            return f"Đã cắn {t.name}"
        return None

class Twins(Role): # Song sinh
    def __init__(self):
        super().__init__(ROLE_TWINS, "Solo", "Thắng nếu cả 2 còn sống và hết Sói.")
        self.wake_order = 0.3
    def on_night(self, game, my_player):
        if game.day_count == 1:
            for p in game.players:
                if p != my_player and p.role.name == ROLE_TWINS:
                    return f"Người anh em: {p.name}"
            return "Bạn lẻ loi."
        return None

class Granny(Role): # Bà ngoại
    def __init__(self):
        super().__init__(ROLE_GRANNY, "Villager", "Chết -> Cô bé thức tỉnh.")
    def on_death(self, game, my_player):
        game.broadcast("SYS", "👵 Bà ngoại mất! Cô bé quàng khăn đỏ thức tỉnh!")

class LittleGirl(Role): # Cô bé quàng khăn đỏ
    def __init__(self):
        super().__init__(ROLE_LITTLE_GIRL, "Villager", "Soi Sói nếu Bà chết.")
    def on_night(self, game, my_player):
        granny_dead = any(p.role.name == ROLE_GRANNY and not p.is_alive for p in game.players)
        if not granny_dead: return "Bà vẫn khỏe."
        wolves = [p for p in game.players if p.role.team == "Werewolf" and p.is_alive]
        if wolves:
            rev = random.choice(wolves)
            return f"👀 {rev.name} là SÓI!"
        return "Không thấy Sói."

class CultLeader(Role): # Chủ giáo phái
    def __init__(self):
        super().__init__(ROLE_CULT_LEADER, "Solo", "Lôi kéo người vào đạo.")
    def on_night(self, game, my_player):
        return "Đang truyền đạo..." # Logic phức tạp cần Engine hỗ trợ

class Doppelganger(Role): # Nhân bản
    def __init__(self):
        super().__init__(ROLE_DOPPELGANGER, "Villager", "Sao chép role người chết.")
        self.target_id = None
    def on_night(self, game, my_player):
        if game.day_count == 1:
            targets = [(str(id(p)), p.name) for p in game.players if p != my_player and p.is_alive]
            self.target_id = my_player.wait_for_input("👤 Sao chép ai?", targets)
            return "Đã chọn mục tiêu."
        return None

class Tanner(Role): # Kẻ chán đời
    def __init__(self):
        super().__init__(ROLE_TANNER, "Solo", "Thắng nếu bị treo cổ.")
