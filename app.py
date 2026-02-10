# app.py
import eventlet
eventlet.monkey_patch() 
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading, time, random, string
from game_engine import GameEngine
from common.const import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'masoi_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60)

ROOMS = {} 
LAST_UPDATE_TIME = {} 

# === TỪ ĐIỂN CẤU HÌNH (QUAN TRỌNG NHẤT) ===
# Key: Role ID Tiếng Anh (từ const.py)
# Value: Tên Tiếng Việt, Ảnh, Mô tả, Phe (để sort Godmode)
ROLE_CONFIG = {
    # --- SÓI ---
    ROLE_WEREWOLF: {"name": "Sói", "img": "wolf.PNG", "desc": "Cắn người mỗi đêm.", "team": "wolf"},
    ROLE_LEADER_WOLF: {"name": "Sói Đầu Đàn", "img": "leader_wolf.PNG", "desc": "Còn sống -> Sói cắn 2 người.", "team": "wolf"},
    ROLE_ALPHA_WOLF: {"name": "Sói Alpha", "img": "alpha_wolf.PNG", "desc": "Biến 1 người thành Sói (1 lần).", "team": "wolf"},
    ROLE_WOLF_CUB: {"name": "Sói Con", "img": "wolf_cub.PNG", "desc": "Chết -> Đêm sau Sói cắn 2 người.", "team": "wolf"},
    ROLE_LONE_WOLF: {"name": "Sói Cô Độc", "img": "lone_wolf.PNG", "desc": "Thắng lẻ.", "team": "wolf"},
    ROLE_SORCERESS: {"name": "Bà Đồng", "img": "sorceress.PNG", "desc": "Soi Tiên Tri.", "team": "wolf"},
    ROLE_DIRE_WOLF: {"name": "Nanh Sói", "img": "dire_wolf.PNG", "desc": "Kết nghĩa, chết chùm.", "team": "wolf"},
    ROLE_VEGETARIAN_WOLF: {"name": "Sói Ăn Chay", "img": "vegetarian_wolf.PNG", "desc": "Không cắn.", "team": "wolf"},
    ROLE_WOLFMAN: {"name": "Người Sói", "img": "wolfman.PNG", "desc": "Soi ra Dân.", "team": "wolf"},

    # --- DÂN ---
    ROLE_VILLAGER: {"name": "Dân Làng", "img": "villager.PNG", "desc": "Ngủ.", "team": "villager"},
    ROLE_SEER: {"name": "Tiên Tri", "img": "seer.PNG", "desc": "Soi phe.", "team": "villager"},
    ROLE_BODYGUARD: {"name": "Bảo Vệ", "img": "bodyguard.PNG", "desc": "Bảo vệ 1 người.", "team": "villager"},
    ROLE_WITCH: {"name": "Phù Thủy", "img": "witch.PNG", "desc": "Bình Cứu/Độc.", "team": "villager"},
    ROLE_HUNTER: {"name": "Thợ Săn", "img": "hunter.PNG", "desc": "Chết kéo theo.", "team": "villager"},
    ROLE_CUPID: {"name": "Thần Tình Yêu", "img": "cupid.PNG", "desc": "Ghép đôi.", "team": "villager"},
    ROLE_LYCAN: {"name": "Con Lai", "img": "lycan.PNG", "desc": "Soi ra Sói.", "team": "villager"},
    ROLE_OLD_MAN: {"name": "Già Làng", "img": "old_man.PNG", "desc": "Chết theo ngày.", "team": "villager"},
    ROLE_APPRENTICE_SEER: {"name": "Tiên Tri Tập Sự", "img": "apprentice_seer.PNG", "desc": "Kế thừa Tiên tri.", "team": "villager"},
    ROLE_TOUGH_GUY: {"name": "Thanh Niên Cứng", "img": "tough_guy.PNG", "desc": "Chết chậm.", "team": "villager"},
    ROLE_SICK_MAN: {"name": "Người Bệnh", "img": "sick_man.PNG", "desc": "Sói cắn bị bệnh.", "team": "villager"},
    ROLE_PRINCE: {"name": "Hoàng Tử", "img": "prince.PNG", "desc": "Không bị treo cổ.", "team": "villager"},
    ROLE_INSOMNIAC: {"name": "Kẻ Mất Ngủ", "img": "insomniac.PNG", "desc": "Biết hàng xóm dậy.", "team": "villager"},
    ROLE_BEHOLDER: {"name": "Kẻ Quan Sát", "img": "beholder.PNG", "desc": "Biết Tiên tri.", "team": "villager"},
    ROLE_HUNTRESS: {"name": "Nữ Thợ Săn", "img": "huntress.PNG", "desc": "Bắn đêm.", "team": "villager"},
    ROLE_MENTALIST: {"name": "Nhà Tâm Lý", "img": "mentalist.PNG", "desc": "Soi cùng phe.", "team": "villager"},
    ROLE_REVEALER: {"name": "Nhà Thám Hiểm", "img": "revealer.PNG", "desc": "Soi chết luôn.", "team": "villager"},
    ROLE_PRIEST: {"name": "Mục Sư", "img": "priest.PNG", "desc": "Ban bất tử.", "team": "villager"},
    ROLE_DOPPELGANGER: {"name": "Nhân Bản", "img": "doppelganger.PNG", "desc": "Copy role.", "team": "villager"},
    ROLE_DRUNK: {"name": "Bợm Nhậu", "img": "drunk.PNG", "desc": "Đổi phe đêm 3.", "team": "villager"},
    ROLE_DETECTIVE: {"name": "Thám Tử", "img": "detective.PNG", "desc": "Điều tra tội phạm.", "team": "villager"},
    ROLE_AURA_SEER: {"name": "Tiên Tri Hào Quang", "img": "aura_seer.PNG", "desc": "Soi chức năng.", "team": "villager"},
    ROLE_MAYOR: {"name": "Thị Trưởng", "img": "mayor.PNG", "desc": "Vote x2.", "team": "villager"},
    ROLE_MARTYR: {"name": "Thiếu Nữ", "img": "martyr.PNG", "desc": "Chết thay.", "team": "villager"},
    ROLE_TWINS: {"name": "Song Sinh", "img": "twins.PNG", "desc": "Biết mặt nhau.", "team": "villager"},
    ROLE_MYSTIC_SEER: {"name": "Tiên Tri Huyền Bí", "img": "mystic_seer.PNG", "desc": "Soi chính xác role.", "team": "villager"},
    ROLE_CURSED: {"name": "Kẻ Bị Nguyền", "img": "cursed.PNG", "desc": "Bị cắn hóa Sói.", "team": "villager"},
    ROLE_LITTLE_GIRL: {"name": "Cô Bé Khăn Đỏ", "img": "little_girl.PNG", "desc": "Soi Sói nếu Bà chết.", "team": "villager"},
    ROLE_GRANNY: {"name": "Bà Ngoại", "img": "granny.PNG", "desc": "Chết kích hoạt Cháu.", "team": "villager"},

    # --- PHE 3 ---
    ROLE_TERRORIST: {"name": "Khủng Bố", "img": "terrorist.PNG", "desc": "Nổ chết chùm.", "team": "neutral"},
    ROLE_TANNER: {"name": "Kẻ Chán Đời", "img": "tanner.PNG", "desc": "Thích bị treo cổ.", "team": "neutral"},
    ROLE_VAMPIRE: {"name": "Ma Cà Rồng", "img": "vampire.PNG", "desc": "Cắn chết chậm.", "team": "neutral"},
    ROLE_CULT_LEADER: {"name": "Chủ Giáo Phái", "img": "cult_leader.PNG", "desc": "Truyền đạo.", "team": "neutral"},
    ROLE_HOODLUM: {"name": "Du Côn", "img": "hoodlum.PNG", "desc": "Chọn mục tiêu.", "team": "neutral"},
    ROLE_MUMMY: {"name": "Xác Ướp", "img": "mummy.PNG", "desc": "Thôi miên vote.", "team": "neutral"},
    ROLE_BLOODY_MARY: {"name": "Bloody Mary", "img": "bloody_mary.PNG", "desc": "Chết kéo theo.", "team": "neutral"},
    ROLE_CHUPACABRA: {"name": "Quỷ Hút Máu", "img": "chupacabra.PNG", "desc": "Ăn Sói.", "team": "neutral"},
}

def generate_room_id():
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if rid not in ROOMS: return rid

# Player Wrapper
class WebPlayer:
    def __init__(self, sid, name, engine, room_id):
        self.sid = sid; self.name = name; self.engine = engine; self.room_id = room_id
        self.role = None; self.is_alive = True; self.status = {}; self.lover_id = None
        self.input_event = threading.Event(); self.input_value = None
    def send(self, data):
        try: socketio.emit('server_msg', data, room=self.sid)
        except: pass
    def wait_for_input(self, prompt, options):
        self.send({"type": "INPUT", "payload": {"prompt": prompt, "options": options}})
        self.input_event.clear(); self.input_value = None
        self.input_event.wait(timeout=300)
        return self.input_value if self.input_value else "SKIP"
    def receive_input_from_web(self, value):
        self.input_value = value; self.input_event.set()

def create_logger(room_id):
    def log_func(msg):
        print(f"[{room_id}] {msg}")
        socketio.emit('server_log', {'msg': msg}, room=room_id)
    return log_func

def update_admin_dashboard(room_id):
    if room_id not in ROOMS: return
    # Throttle update
    current_time = time.time()
    if current_time - LAST_UPDATE_TIME.get(room_id, 0) < 0.2: return 
    LAST_UPDATE_TIME[room_id] = current_time

    engine = ROOMS[room_id]['engine']
    players_data = []
    for p in engine.players:
        # Lấy tên hiển thị tiếng Việt từ Config
        role_display = "..."
        if p.role:
            conf = ROLE_CONFIG.get(p.role.name)
            role_display = conf["name"] if conf else p.role.name
            
        players_data.append({"sid": p.sid, "name": p.name, "alive": p.is_alive, "role": role_display})
    
    socketio.emit('admin_update', {
        'players': players_data, 'started': ROOMS[room_id]['started'], 'room_id': room_id
    }, room=room_id)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/godmode')
def godmode(): return render_template('godmode.html')

@socketio.on('create_room')
def on_create_room(): 
    room_id = generate_room_id()
    engine = GameEngine()
    engine.log_callback = create_logger(room_id)
    # Gắn callback update
    engine.update_callback = lambda: update_admin_dashboard(room_id)
    
    ROOMS[room_id] = { "engine": engine, "started": False, "host_sid": request.sid }
    join_room(room_id)
    # Gửi ROLE_CONFIG xuống client để render
    emit('room_created', {'room_id': room_id, 'roles_config': ROLE_CONFIG}) 
    print(f"✅ Created Room: {room_id}")

@socketio.on('join_game')
def on_join(data):
    room_id = data.get('room_id', '').upper().strip()
    name = data.get('name', 'Unknown')
    if room_id not in ROOMS: emit('server_msg', {'type': 'SYS', 'payload': '❌ Phòng không tồn tại!'}); return
    if ROOMS[room_id]['started']: emit('server_msg', {'type': 'SYS', 'payload': '❌ Game đang chạy!'}); return
    
    engine = ROOMS[room_id]['engine']
    if any(p.name == name for p in engine.players):
        emit('server_msg', {'type': 'SYS', 'payload': '❌ Tên trùng!'}); return

    join_room(room_id)
    p = WebPlayer(request.sid, name, engine, room_id)
    engine.add_player(p)
    emit('join_success', {'room_id': room_id, 'roles_config': ROLE_CONFIG})
    update_admin_dashboard(room_id)

@socketio.on('disconnect')
def on_disconnect():
    for rid, rdata in ROOMS.items():
        engine = rdata['engine']
        p_rem = next((p for p in engine.players if p.sid == request.sid), None)
        if p_rem:
            engine.remove_player(p_rem)
            update_admin_dashboard(rid)
            break

@socketio.on('admin_start_game')
def on_admin_start(data):
    room_id = data.get('room_id')
    if room_id in ROOMS and not ROOMS[room_id]['started']:
        # data['roles'] bây giờ là { "Werewolf": 2, "Seer": 1 } (Key là tiếng Anh)
        threading.Thread(target=run_game_thread, args=(room_id, data.get('roles', {}))).start()

@socketio.on('admin_end_discussion')
def on_admin_end_discuss(data):
    if data.get('room_id') in ROOMS: ROOMS[data['room_id']]['engine'].end_discussion()

@socketio.on('admin_kick')
def on_admin_kick(data):
    room_id = data.get('room_id'); sid = data.get('sid')
    if room_id in ROOMS:
        p = ROOMS[room_id]['engine'].get_player_by_id(sid)
        if p:
            ROOMS[room_id]['engine'].remove_player(p)
            socketio.emit('server_msg', {'type': 'SYS', 'payload': 'KICKED!'}, room=sid)
            update_admin_dashboard(room_id)

def run_game_thread(room_id, role_config):
    ROOMS[room_id]['started'] = True
    update_admin_dashboard(room_id)
    engine = ROOMS[room_id]['engine']
    
    # Tạo list role từ config (Config key là tiếng Anh rồi)
    setup_list = []
    for r_id, count in role_config.items():
        for _ in range(int(count)): setup_list.append(r_id)
    
    # Fill dân làng nếu thiếu
    while len(setup_list) < len(engine.players): setup_list.append(ROLE_VILLAGER)
    # Cắt nếu thừa
    setup_list = setup_list[:len(engine.players)]
        
    engine.start_game_sequence(setup_list)
    ROOMS[room_id]['started'] = False
    update_admin_dashboard(room_id)

@socketio.on('chat_msg')
def on_chat(data):
    for rid, rdata in ROOMS.items():
        sender = next((p for p in rdata['engine'].players if p.sid == request.sid), None)
        if sender: rdata['engine'].handle_message(sender, {"type": "MSG", "payload": data.get('msg')}); break

@socketio.on('send_action')
def on_action(data):
    for rid, rdata in ROOMS.items():
        sender = next((p for p in rdata['engine'].players if p.sid == request.sid), None)
        if sender: sender.receive_input_from_web(data.get('value')); break

@socketio.on('admin_chat_msg')
def on_admin_chat(data):
    room_id = data.get('room_id')
    msg = data.get('msg')
    
    if room_id in ROOMS and msg:
        # 1. Gửi cho tất cả người chơi (hiện lên khung chat của họ)
        # Dùng icon Cảnh sát hoặc Loa để làm nổi bật tin Admin
        full_msg = f"👮 [QUẢN TRÒ]: {msg}"
        socketio.emit('server_msg', {'type': 'MSG', 'payload': full_msg}, room=room_id)
        
        # 2. Gửi lại vào Log hệ thống của Admin (để Admin biết tin đã đi)
        socketio.emit('server_log', {'msg': f"🗣️ [BẠN NÓI]: {msg}"}, room=room_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)