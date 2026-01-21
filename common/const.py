# common/const.py

# ==========================
# CẤU HÌNH MẠNG
# ==========================
HOST = '0.0.0.0'
PORT = 5555
BUFFER_SIZE = 4096
FORMAT = 'utf-8'

# ==========================
# GIAO THỨC (PROTOCOL)
# ==========================
CMD_NAME = "NAME"           # Gửi tên
CMD_MSG = "MSG"             # Chat thường
CMD_SYSTEM = "SYS"          # Thông báo hệ thống
CMD_ROLE = "ROLE"           # Server báo role cho client
CMD_ACTION = "ACT"          # Client gửi hành động
CMD_INPUT_REQ = "INPUT"     # Server yêu cầu nhập liệu
CMD_PHASE = "PHASE"         # Báo hiệu Ngày/Đêm
CMD_OVER = "OVER"           # <--- THÊM DÒNG NÀY (Kết thúc game)

# ==========================
# DANH SÁCH ROLES (GIỮ NGUYÊN NHƯ CŨ)
# ==========================
# (Bạn giữ nguyên phần danh sách role bên dưới của file cũ nhé)
ROLE_QUAN_TRO = "Quản trò"
ROLE_VILLAGER = "Dân Làng"
ROLE_SEER = "Tiên Tri"
ROLE_PROTECTOR = "Bảo vệ"
ROLE_HUNTER = "Thợ săn"
ROLE_WITCH = "Phù thủy"
ROLE_HUNTRESS = "Nữ thợ săn"
ROLE_APPRENTICE_SEER = "Tiên tri tập sự"
ROLE_MYSTIC_SEER = "Tiên tri bí ẩn"
ROLE_AURA_SEER = "Tiên tri hào quang"
ROLE_SICK_MAN = "Người bệnh"
ROLE_MAYOR = "Thị trưởng"
ROLE_PRIEST = "Mục sư"
ROLE_DETECTIVE = "Thám tử"
ROLE_LYCAN = "Con lai"
ROLE_GRANNY = "Bà ngoại"
ROLE_LITTLE_GIRL = "Cô bé quàng khăn đỏ"
ROLE_TROUBLEMAKER = "Kẻ Phá Rối"
ROLE_PARANORMAL = "Nhà ngoại cảm"
ROLE_TOUGH_GUY = "Thanh niên cứng"
ROLE_GHOST = "Hồn ma"
ROLE_DRUNK = "Bợm nhậu"
ROLE_PRINCE = "Hoàng tử"
ROLE_GAMBLER = "Con bạc"
ROLE_MAGICIAN = "Pháp sư"
ROLE_OLD_HAG = "Mụ già"
ROLE_CUPID = "Thần tình yêu"
ROLE_CURSED = "Kẻ bị nguyền"

ROLE_WEREWOLF = "Sói"
ROLE_VEGETARIAN_WOLF = "Sói ăn chay"
ROLE_ALPHA_WOLF = "Sói đầu đàn"
ROLE_WOLF_CUB = "Sói con"
ROLE_DIRE_WOLF = "Nanh sói"
ROLE_MEDIUM = "Bà đồng"

ROLE_LONE_WOLF = "Sói đơn độc"
ROLE_VAMPIRE = "Ma cà rồng"
ROLE_TERRORIST = "Khủng bố"
ROLE_CULT_LEADER = "Chủ giáo phái"
ROLE_DOPPELGANGER = "Nhân bản"
ROLE_HOODLUM = "Du côn"
ROLE_TANNER = "Kẻ chán đời"
ROLE_TWINS = "Song sinh"