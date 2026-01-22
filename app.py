import eventlet
eventlet.monkey_patch() 

from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import threading
import time
import random
import string

# Import Logic
from game_engine import GameEngine
from common.const import *

app = Flask(__name__)
app.config['SECRET_KEY'] = 'masoi_secret_key'
# Thêm ping_timeout để tránh disconnect oan uổng
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', ping_timeout=60)

# --- QUẢN LÝ PHÒNG ---
ROOMS = {} # room_id -> { "engine": ..., "started": ... }
LAST_UPDATE_TIME = {} 

# DANH SÁCH ROLE ĐẦY ĐỦ
ROLES_INFO = [
    {"name": "Dân Làng", "img": "villager.PNG", "desc": "Ngủ suốt đêm."},
    {"name": "Sói", "img": "wolf.PNG", "desc": "Cắn người mỗi đêm."},
    {"name": "Tiên Tri", "img": "seer.PNG", "desc": "Soi phe (Tốt/Xấu)."},
    {"name": "Bảo vệ", "img": "protector.PNG", "desc": "Bảo vệ 1 người khỏi Sói."},
    {"name": "Thợ săn", "img": "hunter.PNG", "desc": "Chết kéo theo 1 người."},
    {"name": "Phù thủy", "img": "witch.PNG", "desc": "Có bình Cứu và Độc."},
    {"name": "Sói con", "img": "wolf_cub.PNG", "desc": "Chết thì đêm sau Sói cắn 2 người."},
    {"name": "Sói đầu đàn", "img": "alpha_wolf.PNG", "desc": "Biến người thành Sói."},
    {"name": "Sói ăn chay", "img": "vegetarian_wolf.PNG", "desc": "Phe Sói nhưng không cắn."},
    {"name": "Sói đơn độc", "img": "lone_wolf.PNG", "desc": "Thắng nếu còn lại cuối cùng."},
    {"name": "Nanh sói", "img": "dire_wolf.PNG", "desc": "Kết nghĩa, chết kéo theo."},
    {"name": "Ma cà rồng", "img": "vampire.PNG", "desc": "Cắn người, chết chậm."},
    {"name": "Kẻ chán đời", "img": "tanner.PNG", "desc": "Thắng nếu bị treo cổ."},
    {"name": "Khủng bố", "img": "terrorist.PNG", "desc": "Nổ chết người giết mình."},
    {"name": "Du côn", "img": "hoodlum.PNG", "desc": "Chọn 2 mục tiêu để thắng."},
    {"name": "Chủ giáo phái", "img": "cult_leader.PNG", "desc": "Lôi kéo tín đồ."},
    {"name": "Song sinh", "img": "twins.PNG", "desc": "Sống chết cùng nhau."},
    {"name": "Thần tình yêu", "img": "cupid.PNG", "desc": "Ghép đôi 2 người."},
    {"name": "Thị trưởng", "img": "mayor.PNG", "desc": "Phiếu vote tính x2."},
    {"name": "Hoàng tử", "img": "prince.PNG", "desc": "Không bị treo cổ."},
    {"name": "Kẻ Phá Rối", "img": "troublemaker.PNG", "desc": "Tráo đổi vai trò 2 người."},
    {"name": "Bà đồng", "img": "medium.PNG", "desc": "Soi xem người chết nói gì."},
    {"name": "Mục sư", "img": "priest.PNG", "desc": "Ban phước bất tử (1 lần)."},
    {"name": "Nữ thợ săn", "img": "huntress.PNG", "desc": "Bắn chết 1 người vào ban đêm."},
    {"name": "Con bạc", "img": "gambler.PNG", "desc": "Đoán đúng Sói thì Sói chết."},
    {"name": "Tiên tri hào quang", "img": "aura_seer.PNG", "desc": "Soi xem ai có chức năng."},
    {"name": "Tiên tri bí ẩn", "img": "mystic_seer.PNG", "desc": "Soi chính xác role."},
    {"name": "Tiên tri tập sự", "img": "apprentice_seer.PNG", "desc": "Kế thừa nếu Tiên tri chết."},
    {"name": "Nhà ngoại cảm", "img": "paranormal.PNG", "desc": "Soi 2 người cùng phe hay khác."},
    {"name": "Thám tử", "img": "detective.PNG", "desc": "Soi ai là tội phạm."},
    {"name": "Pháp sư", "img": "magician.PNG", "desc": "Yểm bùa câm lặng."},
    {"name": "Mụ già", "img": "old_hag.PNG", "desc": "Ám 1 người (bị câm)."},
    {"name": "Bà ngoại", "img": "granny.PNG", "desc": "Chết thì Cháu thức tỉnh."},
    {"name": "Cô bé quàng khăn đỏ", "img": "little_girl.PNG", "desc": "Soi Sói nếu Bà chết."},
    {"name": "Nhân bản", "img": "doppelganger.PNG", "desc": "Sao chép role người chết."},
    {"name": "Người bệnh", "img": "sick_man.PNG", "desc": "Sói cắn sẽ bị bệnh."},
    {"name": "Thanh niên cứng", "img": "tough_guy.PNG", "desc": "Bị cắn chết chậm 1 ngày."},
    {"name": "Bợm nhậu", "img": "drunk.PNG", "desc": "Đêm 3 hóa role mới."},
    {"name": "Con lai", "img": "lycan.PNG", "desc": "Là Dân nhưng bị soi là Sói."},
    {"name": "Hồn ma", "img": "ghost.PNG", "desc": "Chết đêm đầu, gửi gợi ý."},
    {"name": "Kẻ bị nguyền", "img": "cursed.PNG", "desc": "Bị cắn hóa Sói."}
]

def generate_room_id():
    while True:
        rid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        if rid not in ROOMS: return rid

# --- PLAYER WRAPPER ---
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
        self.input_event.wait(timeout=60)
        return self.input_value if self.input_value else "SKIP"

    def receive_input_from_web(self, value):
        self.input_value = value; self.input_event.set()

# --- HELPER FUNCTIONS ---
def create_logger(room_id):
    def log_func(msg):
        print(f"[{room_id}] {msg}")
        socketio.emit('server_log', {'msg': msg}, room=room_id)
    return log_func

def update_admin_dashboard(room_id):
    if room_id not in ROOMS: return
    current_time = time.time()
    last_time = LAST_UPDATE_TIME.get(room_id, 0)
    if current_time - last_time < 0.5: return 
    LAST_UPDATE_TIME[room_id] = current_time

    engine = ROOMS[room_id]['engine']
    players_data = []
    for p in engine.players:
        role_name = p.role.name if p.role else "..."
        players_data.append({"sid": p.sid, "name": p.name, "alive": p.is_alive, "role": role_name})
    
    socketio.emit('admin_update', {
        'players': players_data, 'started': ROOMS[room_id]['started'], 'room_id': room_id
    }, room=room_id)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/godmode')
def godmode(): return render_template('godmode.html')

# --- SOCKET EVENTS ---

@socketio.on('create_room')
def on_create_room(): 
    room_id = generate_room_id()
    engine = GameEngine()
    engine.log_callback = create_logger(room_id)
    
    ROOMS[room_id] = { "engine": engine, "started": False, "host_sid": request.sid }
    join_room(room_id)
    emit('room_created', {'room_id': room_id, 'roles_info': ROLES_INFO})
    print(f"✅ Created Room: {room_id}")

@socketio.on('join_game')
def on_join(data):
    room_id = data.get('room_id', '').upper().strip()
    name = data.get('name', 'Unknown')
    
    if room_id not in ROOMS:
        emit('server_msg', {'type': 'SYS', 'payload': '❌ Phòng không tồn tại!'}); return
    
    room_data = ROOMS[room_id]
    if room_data['started']:
        emit('server_msg', {'type': 'SYS', 'payload': '❌ Game đang chạy!'}); return

    engine = room_data['engine']
    for p in engine.players:
        if p.name == name:
            emit('server_msg', {'type': 'SYS', 'payload': '❌ Tên đã tồn tại!'}); return

    join_room(room_id)
    p = WebPlayer(request.sid, name, engine, room_id)
    engine.add_player(p)
    emit('join_success', {'room_id': room_id})
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
        role_config = data.get('roles', {})
        threading.Thread(target=run_game_thread, args=(room_id, role_config)).start()

@socketio.on('admin_end_discussion')
def on_admin_end_discuss(data):
    room_id = data.get('room_id')
    if room_id in ROOMS: ROOMS[room_id]['engine'].end_discussion()

@socketio.on('admin_kick')
def on_admin_kick(data):
    room_id = data.get('room_id'); sid = data.get('sid')
    if room_id in ROOMS:
        p = ROOMS[room_id]['engine'].get_player_by_id(sid)
        if p:
            ROOMS[room_id]['engine'].remove_player(p)
            socketio.emit('server_msg', {'type': 'SYS', 'payload': 'Bạn đã bị kick!'}, room=sid)
            update_admin_dashboard(room_id)

def run_game_thread(room_id, role_config):
    ROOMS[room_id]['started'] = True
    update_admin_dashboard(room_id)
    engine = ROOMS[room_id]['engine']
    
    setup_list = []
    for r_name, count in role_config.items():
        for _ in range(int(count)): setup_list.append(r_name)
    
    curr = len(engine.players)
    if len(setup_list) > curr: setup_list = setup_list[:curr]
    elif len(setup_list) < curr:
        while len(setup_list) < curr: setup_list.append("Dân Làng")
        
    engine.start_game_sequence(setup_list)
    ROOMS[room_id]['started'] = False
    update_admin_dashboard(room_id)

@socketio.on('chat_msg')
def on_chat(data):
    for rid, rdata in ROOMS.items():
        engine = rdata['engine']
        sender = next((p for p in engine.players if p.sid == request.sid), None)
        if sender:
            engine.handle_message(sender, {"type": "MSG", "payload": data.get('msg')}); break

@socketio.on('send_action')
def on_action(data):
    for rid, rdata in ROOMS.items():
        engine = rdata['engine']
        sender = next((p for p in engine.players if p.sid == request.sid), None)
        if sender: sender.receive_input_from_web(data.get('value')); break

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)