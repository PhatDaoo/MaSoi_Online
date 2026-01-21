# roles/base.py

class Role:
    def __init__(self, name, team, description):
        self.name = name
        self.team = team # "Villager", "Werewolf", "Solo", "Third"
        self.description = description
        self.wake_order = 99 # Thứ tự thức dậy (số nhỏ dậy trước)

    def on_night(self, game, my_player):
        """
        Hành động ban đêm. 
        Return: Chuỗi thông báo kết quả (String) hoặc None
        """
        return None

    def on_day(self, game, my_player):
        """Hành động nội tại ban ngày (nếu có)"""
        pass
    
    def on_death(self, game, my_player):
        """
        Hàm chạy khi người chơi bị chết (bị cắn hoặc treo cổ).
        Dùng cho: Thợ săn (bắn), Khủng bố (nổ), v.v.
        """
        pass