# Hướng dẫn chạy Teleoperation G1 (Inspire FTP)

Nhánh code đang dùng: `main-inspire-deps` (đang checkout đúng nhánh này).

Máy Host hiện tại:

| Mục | Giá trị |
|---|---|
| Repo | `/home/jkl/Projects/Humanoid/xr_teleoperate` |
| Conda | `/home/jkl/miniconda3`, env `tv` (Python 3.10) |
| Card mạng robot | `eno1` (**hiện đang DOWN**, chưa cắm dây) |
| Card wifi | `wlp0s20f3` — `192.168.0.113` |
| Cert TLS | `~/.config/xr_teleoperate/{cert.pem,key.pem}` |

Thiết bị:

| Thiết bị | IP |
|---|---|
| Host (mạng robot, qua `eno1`) | 192.168.123.2 — chưa cấu hình, xem Bước 0 |
| Host (wifi, để Quest vào Vuer) | 192.168.0.113 |
| PC2 (camera server) | 192.168.123.164 |
| Inspire hand phải | 192.168.123.211 |
| Inspire hand trái | 192.168.123.210 |
| Quest 3 | DHCP trên mạng `192.168.0.x` |

An toàn bắt buộc trước khi chạy robot thật:

- Robot đứng vững, không ai đứng trong tầm với hai tay.
- Sẵn sàng nút E-stop.
- Không nhấn `r` cho tới khi Quest đã kết nối và tay bạn ở gần tư thế hiện tại của robot.
- Dừng bằng `q`, không dùng `Ctrl+C` khi đang tracking.

---

## Bước 0 — Những thứ máy này còn thiếu

Kiểm tra ngày 10/08/2026 trên máy `jkl`. Env `tv` đã cài đủ phần teleop lõi và **đã chạy thử với `PYTHONNOUSERSITE=1`**: import toàn bộ chuỗi module của `teleop_hand_and_arm.py`, `G1_29_ArmIK.solve_ik()` trả về vector 14 khớp, `HandRetargeting` nạp được cả `INSPIRE_HAND` (12 khớp) lẫn `UNITREE_DEX3` (7 khớp). Phiên bản: numpy 1.26.4, scipy 1.13.1, pinocchio 3.1.0, torch 2.3.0+cu121, matplotlib 3.7.5.

Phần phần mềm đã xong hết. Chuỗi tay Inspire cũng đã thông: repo `unitree_lerobot` ở `/home/jkl/Projects/Humanoid/unitree_lerobot` (nhánh `son-makedata-headcam-fake-flat26`), `inspire_hand_ws` đã clone đúng commit `fc75490`, `inspire_sdkpy` cài editable, `pymodbus 3.6.9`. Đã chạy thử `load_dds()` của driver — trả về đủ 6 symbol DDS/IDL.

Còn hai việc thuộc về phần cứng/hệ thống:

**1. Mạng robot chưa nối.** `eno1` đang DOWN, máy chỉ có wifi `192.168.0.113`. Khi cắm dây vào robot:

```bash
sudo ip addr add 192.168.123.2/24 dev eno1
sudo ip link set eno1 up
ping -c3 192.168.123.164        # PC2 phải trả lời
```

Nếu bạn dùng IP khác `192.168.123.2` thì **phải sinh lại cert** (xem Bước 2), vì cert hiện tại chỉ ký cho các IP: `127.0.0.1`, `192.168.0.113`, `192.168.123.2`, `192.168.123.164`, và DNS `localhost`.

**2. Mở firewall** (chưa làm, cần sudo):

```bash
sudo ufw allow 8012
```

### Kiểm tra nhanh link XR mà không cần robot

Chạy được ngay bây giờ, không cần PC2/robot/camera — dựng televuer, phát ảnh gradient tổng hợp lên kính và in pose nhận về:

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
python /home/jkl/Projects/Humanoid/xr_teleoperate/tools/test_xr_link.py --hand
```

Trên Quest mở `https://192.168.0.113:8012/?ws=wss://192.168.0.113:8012` → Advanced → Proceed → **Virtual Reality**. Nếu log in ra `head_pose` khác 0 là cert + websocket + hand tracking đều thông.

---

## Bước 1 — PC2: khởi động camera server

SSH vào PC2, sau đó:

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate teleimager
cd ~/teleimager

# (tuỳ chọn) chỉ chạy khi cần dò lại camera/serial number
python -u -m teleimager.image_server --cf --rs

# chạy chính thức
python -u -m teleimager.image_server --rs
```

Chờ log:

```text
[RealSenseCamera: head_camera] initialized with 480x640 @ 30 FPS.
ZMQ: enabled, zmq_port=55555; WebRTC: enabled, webrtc_port=60001
[Image Server] head_camera is ready.
[Image Server] Running... Press Ctrl+C to exit.
```

Giữ nguyên terminal này chạy trong suốt phiên teleop. Không nhấn `Ctrl+C`.

### Nếu camera không lên / báo "Frame didn't arrive"

Đây từng là lỗi phần cứng D435i mất kết nối USB vật lý (không phải lỗi code). Cách xử lý:

1. Rút cáp USB của D435i khỏi hub/PC2.
2. Chờ 10–15 giây.
3. Cắm lại chắc chắn — ưu tiên cắm trực tiếp vào cổng USB3 của PC2, tránh qua hub nếu có thể.
4. Kiểm tra lại:

```bash
lsusb -d 8086:0b3a
```

Phải thấy tốc độ `5000M`. Sau đó chạy lại `image_server.py --rs`.

### Nếu wrist camera bị lỗi USB

Hai wrist RealSense (serial `260322270586`, `260322271454`) dễ rớt USB khi qua hub USB2. Nếu server crash do wrist timeout, tạm tắt wrist trong `cam_config_server.yaml`:

```yaml
left_wrist_camera:
  enable_zmq: false
  enable_webrtc: false

right_wrist_camera:
  enable_zmq: false
  enable_webrtc: false
```

Chỉ headcam là đủ cho teleop không record. Khi wrist ổn định lại, bật `enable_zmq: true` để dùng `--record`.

---

## Bước 2 — Host: kích hoạt môi trường

Mỗi terminal mới trên Host đều cần chạy khối này trước:

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv

export PYTHONNOUSERSITE=1
export PIP_USER=0
```

`PYTHONNOUSERSITE=1` **không phải tuỳ chọn** trên máy này: `~/.local/lib/python3.10/site-packages` có sẵn `aiohttp`, `aioice`, `absl`… và sẽ đè lên bản trong env `tv` nếu không tắt.

Env `tv` đã được vá để chạy đúng khi bật cờ này. Trước đó nó **âm thầm mượn** `multidict`, `websockets`, `msgpack`, `pyzmq`, `matplotlib`, `meshcat`, `tqdm` từ `~/.local` — chạy được nhưng chỉ vì user site che lấp chỗ thiếu. Nếu sau này thấy `ModuleNotFoundError` cho một gói mà `pip list` vẫn báo có, gần như chắc chắn là bệnh này: kiểm tra bằng

```bash
PYTHONNOUSERSITE=1 python -c "import <tên_gói>"
```

Không cần `XR_TELEOP_CERT`/`XR_TELEOP_KEY`: televuer tự tìm `~/.config/xr_teleoperate/cert.pem` và `key.pem` ([televuer.py:77-83](teleop/televuer/src/televuer/televuer.py#L77-L83)), và hai file đó đã có sẵn.

### Sinh lại cert khi đổi IP

Cert hiện tại ký cho `localhost, 127.0.0.1, 192.168.0.113, 192.168.123.2, 192.168.123.164`. Nếu IP Host đổi:

```bash
cd /home/jkl/Projects/Humanoid/xr_teleoperate/teleop/televuer
# sửa IP trong server_ext.cnf trước, rồi:
openssl x509 -req -in server.csr -CA rootCA.pem -CAkey rootCA.key -CAcreateserial \
  -out cert.pem -days 3650 -sha256 -extfile server_ext.cnf
cp cert.pem key.pem ~/.config/xr_teleoperate/
```

Quest chỉ cần bấm Advanced → Proceed nên không phải cài `rootCA.pem`; chỉ Apple Vision Pro mới cần AirDrop file đó sang và cài.

### Nếu phải dựng lại env `tv` từ đầu

Hai chỗ bắt buộc lệch khỏi README gốc, nếu làm đúng theo README sẽ hỏng:

```bash
# 1. dex-retargeting: KHÔNG để pip kéo gói "pin" về, nó đè lên pinocchio 3.1.0 của conda
cd /home/jkl/Projects/Humanoid/xr_teleoperate/teleop/robot_control/dex-retargeting
pip install -e . --no-deps
pip install "torch==2.3.0" "pytransform3d>=3.5.0" "nlopt>=2.6.1,<2.8.0" \
            "trimesh>=4.4.0" "anytree>=2.12.0" "lxml>=5.2.2"

# 2. vuer 0.0.60 khai "params-proto>=2.13.0" nhưng bản 3.x đã bỏ export Flag/PrefixProto/Proto
pip install "params-proto==2.13.2"

# 3. scipy phải là bản còn hỗ trợ numpy 1.x
pip install "scipy==1.13.1"
```

Triệu chứng nếu quên bước 2: `from vuer import Vuer` báo `cannot import name 'Vuer'` kèm gợi ý lạc hướng "install vuer[all]" — nguyên nhân thật là `ImportError: cannot import name 'Flag' from 'params_proto'`.

Triệu chứng nếu quên bước 3: `scipy.special` chết với `ValueError: All ufuncs must have type numpy.ufunc` — scipy 1.15 build cho numpy 2.x, không chạy với numpy 1.26.4.

> ⚠️ **Không dùng `pip install --ignore-installed`.** Cờ này cài đè mà không gỡ bản cũ, để lại file lẫn lộn giữa hai version. Đã dính đúng lỗi này với `params_proto` (thư mục `hyper/` của 3.3.0 còn lại, che mất `hyper.py` của 2.13.2 → `ImportError: cannot import name 'ProtoWrapper'`), `numpy` và `scipy` (dist-info của cả hai version cùng tồn tại). Dùng `--force-reinstall`, hoặc gỡ sạch thư mục gói trong `site-packages` trước khi cài lại.

---

## Bước 3 (tuỳ chọn) — Host: xem thử camera qua OpenCV

Dùng để kiểm tra nhanh ZMQ/camera, không bắt buộc trong luồng chính:

```bash
python -m teleimager.image_client --host 192.168.123.164
```

Cửa sổ OpenCV hiện ảnh camera realtime từ PC2. Nhấn `q` tại cửa sổ ảnh để đóng.

---

## Bước 4 — Host: cầu nối tay Inspire (2 terminal riêng biệt)

Driver chỉ hỗ trợ 1 tay mỗi lần chạy. Cần mở **2 terminal**.

Repo: `/home/jkl/Projects/Humanoid/unitree_lerobot`, nhánh `son-makedata-headcam-fake-flat26`.

**Không cần `export PYTHONPATH`.** Driver tự thêm đường dẫn IDL: [`add_inspire_idl_path()`](../unitree_lerobot/unitree_lerobot/eval_robot/inspire_hand_ftp_driver.py) tính `repo_root/inspire_hand_ws/inspire_hand_sdk/inspire_sdkpy` từ vị trí file rồi `sys.path.insert(0, ...)`. Đặt `PYTHONPATH` thêm là thừa, và nếu đặt sai còn dễ gây nhầm.

### Terminal 1a — tay PHẢI

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

cd /home/jkl/Projects/Humanoid/unitree_lerobot

python -u unitree_lerobot/eval_robot/inspire_hand_ftp_driver.py \
  --network-interface=eno1 \
  --hand=right \
  --ip=192.168.123.211 \
  --no-touch
```

### Terminal 1b — tay TRÁI

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

cd /home/jkl/Projects/Humanoid/unitree_lerobot

python -u unitree_lerobot/eval_robot/inspire_hand_ftp_driver.py \
  --network-interface=eno1 \
  --hand=left \
  --ip=192.168.123.210 \
  --no-touch
```

Tham số khác của driver (mặc định thường không cần đổi): `--port` (6000), `--device-id` (1), `--frequency` (20.0).

### `inspire_hand_ws` — nguồn gốc và cách cài lại

Thư mục này nằm trong repo dưới dạng **gitlink mồ côi**: có entry trong cây git nhưng `.gitmodules` chỉ khai báo mỗi `unitree_lerobot/lerobot`, không có dòng nào cho nó. Nên `git submodule update --init` không kéo được — git không biết URL.

```bash
$ git ls-tree HEAD inspire_hand_ws
160000 commit fc754900caaaa82c9b59fb12c1b79ebfd1c1a0e7    inspire_hand_ws
```

Upstream đã truy ra được: **[NaCl-1374/inspire_hand_ws](https://github.com/NaCl-1374/inspire_hand_ws)** — commit `fc75490` tồn tại đúng trong repo đó (đã xác minh bằng `git cat-file -e` trên bare clone).

Nếu phải cài lại từ đầu:

```bash
cd /home/jkl/Projects/Humanoid/unitree_lerobot
git clone https://github.com/NaCl-1374/inspire_hand_ws.git inspire_hand_ws
cd inspire_hand_ws && git checkout fc754900caaaa82c9b59fb12c1b79ebfd1c1a0e7

# cài SDK dạng editable -> inspire_sdkpy dùng được ở mọi nơi, KHÔNG cần PYTHONPATH
conda activate tv && export PYTHONNOUSERSITE=1
pip install -e /home/jkl/Projects/Humanoid/unitree_lerobot/inspire_hand_ws/inspire_hand_sdk
```

Kéo theo: PyQt5, pyqtgraph, colorcet, pyserial, và **hạ `pymodbus` xuống 3.6.9** (pin của SDK).

Muốn khỏi lặp lại chuyện này thì đăng ký submodule cho tử tế rồi commit:

```bash
git config -f .gitmodules submodule.inspire_hand_ws.path inspire_hand_ws
git config -f .gitmodules submodule.inspire_hand_ws.url https://github.com/NaCl-1374/inspire_hand_ws.git
git submodule sync
```

### `pymodbus` phải là bản < 3.8

Hiện là **3.6.9** — đúng pin trong `inspire_hand_sdk/setup.py`. **Không nâng lên 3.8+**: driver gọi kiểu positional 3 tham số — `read_holding_registers(address, count, device_id)`, `write_register(1004, 1, device_id)`, `write_registers(addr, values, device_id)` — mà từ 3.8 các tham số sau `address` thành keyword-only, sẽ lỗi `TypeError` ngay lần đọc thanh ghi đầu tiên.

Chữ ký đã kiểm chứng trên bản đang cài:

```text
read_holding_registers(self, address, count=1, slave=0, **kwargs)
```

tức tham số vị trí thứ 3 chính là `slave` — đúng ý nghĩa `--device-id`.

### Kiểm tra nhanh trước khi chạy thật

```bash
conda activate tv && export PYTHONNOUSERSITE=1
cd /home/jkl/Projects/Humanoid/unitree_lerobot

# 1. IDL cho driver (driver tự thêm thư mục inspire_sdkpy vào sys.path)
PYTHONPATH=inspire_hand_ws/inspire_hand_sdk/inspire_sdkpy \
  python -c "from inspire_dds import inspire_hand_ctrl, inspire_hand_state, inspire_hand_touch; print('inspire_dds OK')"

# 2. package cho xr_teleoperate (đã pip install -e nên không cần PYTHONPATH)
python -c "from inspire_sdkpy import inspire_dds; import inspire_sdkpy.inspire_hand_defaut; print('inspire_sdkpy OK')"
```

⚠️ `inspire_sdkpy/__init__.py` kéo cả `qt_tabs` (pyqtgraph + PyQt5 + colorcet) chỉ để export mấy class GUI. Nên `from inspire_sdkpy import inspire_dds` **bắt buộc phải có sẵn Qt stack**, dù teleop không dùng GUI. Thiếu sẽ báo `ModuleNotFoundError: No module named 'pyqtgraph'` — nghe như lỗi vô can nhưng thực chất chặn luôn tay Inspire.

Chạy `--help` được **không** có nghĩa là đã sẵn sàng: `--help` không gọi `load_dds()`. Dùng hai lệnh trên để kiểm tra thật.

Cả hai chờ log báo tần số ổn định (khoảng `~20 Hz`). Giữ cả hai terminal chạy xuyên suốt.

---

## Bước 5 — Host Terminal 2: chương trình teleop chính

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

export PYTHONPATH="/home/jkl/Projects/Humanoid/xr_teleoperate"

cd /home/jkl/Projects/Humanoid/xr_teleoperate/teleop

python teleop_hand_and_arm.py \
  --arm=G1_29 \
  --ee=inspire_ftp \
  --input-mode=hand \
  --display-mode=immersive \
  --motion \
  --img-server-ip=192.168.123.164 \
  --network-interface=eno1 \
  --record \
  --task-dir=./utils/data/ \
  --task-name="pick_bottle" \
  --task-goal="pick up the cube" \
  --task-desc="bimanual manipulation" \
  --task-steps="step1: reach; step2: grasp; step3: place"
```

Chỉ teleop, không ghi dataset — bỏ `--record` và toàn bộ `--task-*`:

```bash
python teleop_hand_and_arm.py \
  --arm=G1_29 \
  --ee=inspire_ftp \
  --input-mode=hand \
  --display-mode=immersive \
  --motion \
  --img-server-ip=192.168.123.164 \
  --network-interface=eno1
```

`PYTHONPATH` **không còn cần trỏ tới inspire SDK**: `inspire_sdkpy` đã được `pip install -e` vào env `tv` (xem Bước 4), nên [robot_hand_inspire.py:170-171](teleop/robot_control/robot_hand_inspire.py#L170-L171) import thẳng được. Chỉ giữ lại đường dẫn repo `xr_teleoperate` cho `import teleop.*`.

`--motion` bỏ qua tự chuyển robot vào development/debug mode. Robot phải đã ở Regular/Control mode (R1+X trên tay cầm Unitree) trước khi chạy.

**Quan trọng — `--img-server-ip` phải là IP thật của PC2 (`192.168.123.164`, cổng ethernet), không phải IP của Host.** Nhầm sang IP Host (`192.168.0.113`) khiến `ImageClient` không request được config, tự fallback đọc cache `cam_config_client.yaml` cũ và không subscribe được ZMQ thật — hệ quả: Quest vẫn hiện video (do WebRTC dùng port cố định khác), nhưng khi `--record` thì mọi item ghi ra sẽ có `colors: {}` trống hoàn toàn, không có ảnh nào lưu được dù `states`/`actions` (khớp tay/cánh tay) vẫn ghi đúng.

`--record` bật ghi dataset. Nhấn `s` để bắt đầu/lưu episode. Wrist camera cần `enable_zmq: true` trên PC2.

### Xem cả 3 camera trên Quest (lưới 2x2)

Thêm `--camera-layout=quad`:

```bash
python teleop_hand_and_arm.py \
  --arm=G1_29 \
  --ee=inspire_ftp \
  --input-mode=hand \
  --display-mode=immersive \
  --camera-layout=quad \
  --motion \
  --img-server-ip=192.168.123.164 \
  --network-interface=eno1
```

Bố cục hiển thị trên Quest:

```text
┌──────────────┬──────────────────────┐
│     HEAD     │  HEAD 2 (NO CAMERA)  │  ← ô đen, chỉ có 1 head cam
├──────────────┼──────────────────────┤
│  LEFT WRIST  │     RIGHT WRIST      │
└──────────────┴──────────────────────┘
```

Yêu cầu: cả 3 camera phải `enable_zmq: true` trên PC2, và `--display-mode` phải là `immersive` hoặc `ego`. Chế độ này ghép ảnh trên Host qua ZMQ thay vì dùng WebRTC head đơn.

Chờ dòng:

```text
🟢  Press [r] to start syncing the robot with your movements.
```

**Chưa nhấn `r`.**

Ngay sau khi khởi tạo `Inspire_Controller_FTP`, log sẽ in liên tục `Publish cmd L=[1000,...] R=[1000,...]` ở 100 Hz — đây là lệnh mặc định (tay mở hết), bình thường trước khi có dữ liệu tay thật từ Quest.

---

## Bước 6 — Quest 3: kết nối Vuer

Trên trình duyệt Quest, mở:

```text
https://192.168.0.113:8012/?ws=wss://192.168.0.113:8012
```

IP này là IP wifi của Host (`wlp0s20f3`), không phải IP mạng robot — Quest phải cùng mạng `192.168.0.x`. Kiểm tra lại bằng `ip -4 addr show wlp0s20f3` nếu DHCP cấp IP khác.

1. Nếu có cảnh báo: **Advanced → Proceed**.
2. Bấm **Virtual Reality**.
3. Cho phép các quyền WebXR/hand tracking.
4. Xác nhận thấy camera chuyển động (không đen, không đứng hình).
5. Xác nhận Terminal 2 (Host) hiện dòng:

```text
websocket is connected
```

### Nếu Quest thấy đen

- Kiểm tra PC2 image server vẫn chạy và `head_camera is ready`.
- Trên Quest, truy cập riêng `https://192.168.123.164:60001`, accept certificate, nhấn Start — nếu thấy headcam là PC2 OK; nếu đen là lỗi camera/server.
- `--display-mode=pass-through` hiện không hoạt động trên Quest 3 (nền đen, không có passthrough thật).

---

## Bước 7 — Căn tư thế và bắt đầu điều khiển

1. Đưa hai tay về gần tư thế hiện tại của tay robot (mặc định robot đang ở trạng thái mở tay hoàn toàn).
2. Trên Terminal 2, nhấn phím:

```text
r
```

(không cần Enter). Kỳ vọng:

```text
---------------------🚀start Tracking🚀-------------------------
```

3. Di chuyển tay chậm để kiểm tra phản hồi trước, xác nhận:
   - Video không đen/đứng hình.
   - Websocket không disconnect.
   - Log `Publish cmd` đổi giá trị theo cử động tay thật, không còn cố định `1000`.
   - Tay robot đi đúng hướng, không giật/nhảy pose.
   - Inspire hand đóng/mở đúng theo tay bạn (cả hai tay).

---

## Dừng hệ thống (theo đúng thứ tự)

1. Trên Terminal 2, nhấn:

```text
q
```

Chờ:

```text
both arms have reached the home position
Finally, exiting program
```

2. Dừng Terminal 1a và 1b (Inspire bridge phải + trái) bằng `Ctrl+C`.
3. Dừng PC2 image server bằng `Ctrl+C`.

Không dùng `Ctrl+C` cho Terminal 2 trong lúc đang tracking, trừ trường hợp khẩn cấp — nếu chuyển động nguy hiểm hoặc `q` không phản hồi, dùng nút E-stop ngay.

---

## Tham số teleop đầy đủ

| Param | Giá trị | Default | Tác dụng |
|---|---|---|---|
| `--frequency` | float | `30.0` | Tần số vòng lặp chính (Hz) |
| `--input-mode` | `hand` / `controller` | `hand` | Nguồn tracking Quest. `hand` bắt buộc cho inspire_ftp |
| `--display-mode` | `immersive` / `ego` / `pass-through` | `immersive` | Hiển thị trên Quest |
| `--camera-layout` | `head` / `quad` | `head` | `head` = chỉ headcam. `quad` = lưới 2x2: headcam / ô đen / wrist trái / wrist phải |
| `--arm` | `G1_29` / `G1_23` / `H1_2` / `H1` / `H2` | `G1_29` | Loại robot + DOF |
| `--ee` | `dex1` / `dex3` / `inspire_ftp` / `inspire_dfx` / `brainco` | None | Bộ tay/gripper |
| `--img-server-ip` | IP | `192.168.123.164` | IP PC2 image server (cổng ethernet, **không phải IP Host**) |
| `--network-interface` | string | None | Interface DDS — trên máy này là `eno1` |
| `--motion` | flag | tắt | Bỏ qua tự chuyển debug mode; arm qua `rt/arm_sdk` |
| `--headless` | flag | tắt | Tắt rerun visualizer khi record |
| `--sim` | flag | tắt | Isaac Sim (DDS domain 1) |
| `--ipc` | flag | tắt | IPC server thay sshkeyboard |
| `--affinity` | flag | tắt | Ghim CPU core + priority cao |
| `--record` | flag | tắt | Bật ghi dataset |
| `--task-dir` | path | `./utils/data/` | Thư mục gốc dataset |
| `--task-name` | string | `pick cube` | Tên task |
| `--task-goal` | string | `pick up cube.` | Mục tiêu task (ghi vào JSON) |
| `--task-desc` | string | `task description` | Mô tả task (ghi vào JSON) |
| `--task-steps` | string | `step1: do this; step2: do that;` | Các bước task (ghi vào JSON) |

Phím tắt khi chạy: `r` = bắt đầu tracking, `s` = toggle ghi/lưu episode (cần `--record` và trạng thái READY), `q` = dừng + thoát.

---

## Ghi chú sự cố đã gặp và cách đã xử lý

- **Camera D435i tự rớt khỏi USB / "Frame didn't arrive within 5000"**: xác nhận là lỗi phần cứng (cáp/hub/cổng USB), không phải lỗi code hay cấu hình. Đã kiểm chứng bằng test trực tiếp `pyrealsense2` và V4L2, đều mất thiết bị `errno=19 (No such device)` độc lập với FPS/độ phân giải/JPEG. Khắc phục bằng rút/cắm lại cáp, đổi cổng/hub, sau đó reboot PC2.
- **Wrist RealSense rớt USB (error -71, "device not accepting address")**: hai wrist cam đi qua hub USB2 (480M) dễ mất. Ưu tiên cắm trực tiếp USB3. Xác nhận bằng `lsusb -t` phải thấy `5000M`. Nếu không ổn, tắt wrist trong config và chỉ dùng headcam.
- **`NameError: name 'inspire_hand_default' is not defined`** trong `teleop/robot_control/robot_hand_inspire.py`: biến import cục bộ trong `__init__` bị dùng lại ở tiến trình con `control_process`/`_send_hand_command`. Đã sửa bằng cách lưu vào `self._inspire_hand_default`. Nếu thấy lại lỗi này, tiến trình gửi lệnh tay đã chết ngay từ đầu — dừng lại, không nhấn `r`, kiểm tra lại file này đã có bản vá chưa.
- **Wi-Fi Quest yếu / ping cao (>100ms)**: gây tải trang chậm hoặc "This site can't be reached", không phải lỗi server. Nên dùng băng 5GHz, đứng gần AP, tránh guest network/client isolation.
- **Quest đen khi dùng `--display-mode=pass-through`**: mode này chỉ tạo phiên VR rỗng, không kích hoạt passthrough camera Quest. Dùng `--display-mode=immersive` để xem headcam robot.
- **Vuer websocket disconnect / "Websocket session is missing"**: thường do Quest mất kết nối WiFi hoặc thoát VR. Không phải lỗi code. Dừng teleop (`q`), mở lại URL trên Quest, vào Virtual Reality lại.
- **Web Vuer không load ở lần chạy thứ 2, 3 trở đi**: đã xử lý tự động. Trước đây `Ctrl+C` không dọn hết, tiến trình Vuer cũ vẫn giữ port `8012` nên phiên mới không bind được. Nay:
  - `Ctrl+C` được chuyển thành lệnh dừng bình thường, cleanup luôn chạy hết (kể cả khi nhấn `Ctrl+C` nhiều lần).
  - Lúc khởi động, chương trình tự kiểm tra port `8012`. Nếu bị teleop cũ giữ → tự dọn và chạy tiếp. Nếu bị tiến trình lạ giữ → dừng lại và báo rõ PID, **không** kill bừa.
  - Các tiến trình con teleop mồ côi từ phiên trước cũng được dọn tự động.

  Xem log khi khởi động:

  ```text
  [ProcessGuard] Port 8012 still held by stale teleop process 12345; cleaning up.
  [ProcessGuard] Port 8012 is free.
  ```

  Nếu thấy `Port 8012 is held by a non-teleop process`, đó là tiến trình khác của bạn, cần tự kiểm tra:

  ```bash
  ss -tlnp | grep :8012
  ```

  Dọn tay (chỉ dùng khi cần):

  ```bash
  kill -CONT <pid> && kill -TERM <pid>
  kill -KILL <pid>   # nếu TERM không ăn
  ```

- **Sửa code trong `teleop/televuer/` mà không thấy tác dụng**: package `televuer` từng được cài dạng wheel copy, nên bản chạy thực tế nằm trong `site-packages`, không phải repo. Đã cài lại dạng editable:

  ```bash
  /home/jkl/miniconda3/envs/tv/bin/python -m pip install -e \
    /home/jkl/Projects/Humanoid/xr_teleoperate/teleop/televuer --no-deps
  ```

  Trên máy này đã cài đúng dạng editable rồi (`televuer 4.0.0`, `teleimager 1.5.0`, `dex_retargeting 0.4.7` đều trỏ vào repo).

  Kiểm tra:

  ```bash
  python -c "import televuer, inspect; print(inspect.getfile(televuer))"
  # phải trỏ vào .../xr_teleoperate/teleop/televuer/src/televuer/__init__.py
  ```

- **Lỗi chế độ `--record`** — đã sửa nhiều bug trong `episode_writer.py` và `teleop_hand_and_arm.py`:
  - **Nhấn `s` khi episode trước đang save**: trước đây toggle bị nuốt mất, phải nhấn lại. Nay toggle được giữ lại và tự retry mỗi vòng lặp cho đến khi save xong.
  - **Nhấn `s` khi không bật `--record`**: trước đây vẫn set flag RECORD_TOGGLE (vô hại nhưng lộn xộn). Nay `on_press` kiểm tra `--record` trước.
  - **Rerun logger leak**: mỗi episode tạo 1 RerunLogger mới nhưng dùng instance cũ để log → viewer Rerun mọc liên tục, dữ liệu dồn chung. Đã sửa: dùng 1 logger duy nhất xuyên suốt, không tạo thêm.
  - **Image bị mutate trước Rerun**: Rerun nhận file path thay vì numpy array. Đã đổi thứ tự: log Rerun trước, rồi mới ghi file và đổi giá trị.
  - **Frame None làm hỏng JSON**: khi camera chưa có ảnh, `cv2.imwrite(None)` crash, `json.dumps(numpy.array)` crash → mất toàn bộ item. Đã thêm guard `.bgr is not None` ở cả nơi enqueue và nơi ghi file.
  - **`image_size` metadata sai**: luôn ghi 640×480 trong `data.json` bất kể camera thật bao nhiêu. Đã truyền `image_shape` từ camera config.
  - **`close()` treo vô hạn**: `item_data_queue.join()` và `worker_thread.join()` không timeout. Đã thêm timeout 10s, log cảnh báo nếu quá hạn.
  - **Save chậm 1s**: worker thread `get(timeout=1)` khiến `need_save` bị trễ. Đã giảm timeout xuống 0.1s.

- **Hình ảnh trong dataset lệch so với thực tế / GUI Rerun hiển thị trễ dần** — đã đo trên phần cứng thật và sửa. Hai nguyên nhân độc lập:

  **1. Rerun làm hàng đợi ghi phình vô hạn.** `rerun_visualizer.py` chuyển màu bằng `color_val[:, :, ::-1]`, tạo mảng non-contiguous nên Rerun phải copy lại toàn bộ: **25.5 ms/item**, chỉ tải nổi 39 Hz trong khi vòng lặp nạp 30 Hz với 3 camera. Hàng đợi tăng tuyến tính, không bao giờ hồi phục:

  ```text
  elapsed  backlog  độ trễ GUI   RAM
    5.0s      26      0.9 s      72 MB
   10.0s      37      1.2 s     102 MB
   20.0s      80      2.7 s     221 MB
  ```

  Đã đổi sang `rr.Image(color_val, color_model="BGR")` — đưa thẳng buffer BGR cho Rerun, để viewer tự đảo kênh. Còn **2.7 ms/item, nhanh hơn 9.4×**. Đo lại sau khi sửa: backlog phẳng ở **0** suốt 20 s. Màu hiển thị không đổi (đã kiểm chứng bằng so sánh pixel).

  **2. `.bgr` trả frame cũ vĩnh viễn khi camera mất kết nối.** Trong `image_client.py`, khi poller timeout thì `None` được ghi vào ring buffer **jpg**, nhưng `_decoder_loop` lại `continue` bỏ qua, không ghi gì vào ring buffer **bgr**. Hậu quả: `.bgr` giữ nguyên ảnh cuối cùng mãi mãi, `bgr is not None` vẫn đúng nên **không có cảnh báo nào**, và cùng một tấm ảnh bị ghi lặp lại kèm các giá trị khớp khác nhau.

  Đã kiểm chứng bằng thực nghiệm: dừng publisher, `.jpg` chuyển `None` 12/12 lần nhưng `.bgr` vẫn trả frame cũ 12/12 lần.

  Ngoài ra `recv()` đọc `.jpg` và `.bgr` từ **hai ring buffer độc lập** nên hai trường trong cùng một `TeleImage` có thể là hai frame khác nhau — đo được **7.5%** lệch trên camera thật.

  Đã sửa: decoder lưu kèm jpg gốc cạnh ảnh đã giải mã, `recv()` trả về cặp jpg/bgr cùng một frame, và trả `None` khi thật sự mất frame. Kết quả đo trên 3 camera thật ở 30 Hz:

  | Chỉ số | Trước | Sau |
  |---|---|---|
  | jpg/bgr lệch frame | 7.5% | **0%** |
  | `.bgr` khả dụng | — | **100%** |
  | Frame trùng liên tiếp | ~6% | **0.9%** |
  | Phát hiện mất kết nối | không | **có** |

  Dấu vết của lỗi này còn trong 4 episode đã ghi (`consec_dup` 3.4–12.5%, có chuỗi trùng dài tới 3 frame). Dữ liệu cũ vẫn dùng được nhưng một số ảnh bị lặp không đúng với giá trị khớp đi kèm.

---

## Bước 8 — Replay dữ liệu đã ghi lên robot thật (repo `unitree_lerobot`)

Sau khi đã convert dataset raw (`data.json`) sang `LeRobotDataset` (`unitree_lerobot/utils/convert_unitree_json_to_lerobot.py`, `robot_type=Unitree_G1_Inspire_3Cam`), replay cả cánh tay và bàn tay theo đúng một episode bằng script gộp — **một tiến trình, một vòng lặp**, nên tay và bàn tay luôn khớp đúng frame, không lệch pha như chạy hai script riêng:

```bash
source /home/jkl/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1

cd /home/jkl/Projects/Humanoid/unitree_lerobot
python unitree_lerobot/eval_robot/replay_arm_and_hand_eno1.py \
  --repo-id local/place_bottle_test1 \
  --episode 10 \
  --frequency 30
```

`--episode` là **index 0-based**, không phải số thứ tự thư mục `episode_XXXX` — ví dụ `episode_0011` (thư mục thứ 11, không có `episode_0000`) ứng với `--episode 10`. Kiểm tra lại bằng `dataset.meta.episodes` nếu đổi dataset khác.

### Điều kiện trước khi chạy

- **Terminal 1a/1b** (Bước 4, `inspire_hand_ftp_driver.py` cho cả hai tay) phải đang chạy — nếu không, lệnh gửi tới bàn tay vẫn "chạy được" mà tay không nhích, không báo lỗi gì.
- Robot đứng vững, sẵn E-stop, ở Regular/Control mode (script tự gọi `ReleaseMode()` để nhả mode `ai`/Sport trước khi gửi lệnh khớp thô, trừ khi truyền `--motion`).

### Phím điều khiển

| Bước | Hành động |
|---|---|
| `Please enter the start signal... (s)` | Nhấn `s` — robot di chuyển tới tư thế đầu episode, có kiểm tra hội tụ (không phải `sleep` mù) |
| `Enter 's' to start playback` | Nhấn `s` — bắt đầu phát quỹ đạo thật |
| Trong lúc phát hoặc sau khi hết episode | Nhấn **`q`** hoặc **Ctrl+C** — dừng chương trình |

Chạy hết episode tự nhiên: robot **giữ nguyên tư thế cuối**, chương trình **không tự thoát** — chỉ dừng thật khi bạn nhấn `q`/Ctrl+C. Dù dừng theo cách nào (hết tự nhiên, `q`, hay Ctrl+C), robot đều di chuyển có kiểm soát về đúng tư thế cuối episode trước khi tiến trình thoát — không đứng lại giữa đường.

> ⚠️ Ngay khi tiến trình thoát, lực giữ chủ động mất hoàn toàn (mode `ai` chưa được khôi phục) — cánh tay có thể hơi giật/rơi nhẹ từ tư thế cuối episode. Đây là hạn chế đã biết, chưa có cách khắc phục triệt để (xem lịch sử trong session note).

### Script khác (nếu chỉ cần riêng cánh tay hoặc riêng bàn tay)

- `replay_robot_eno1.py --repo_id ... --episodes N --arm G1_29 --ee "" --frequency 30` — chỉ cánh tay (chú ý: dùng `_` không phải `-`, và `--episodes` không phải `--episode`, vì đây là wrapper quanh `replay_robot.py` gốc dùng `draccus`)
- `replay_hand_only.py --repo-id ... --episode N --frequency 30` — chỉ bàn tay, cần chạy song song ở terminal riêng nếu muốn cả hai (không đồng bộ tuyệt đối, khác với script gộp ở trên)

- **Những thứ đã loại trừ (đo thật, KHÔNG phải nguyên nhân)**: camera PC2 chạy đúng 30.1 Hz cả 3 luồng, 0 frame mất; IK `solve_ik` chỉ 4.5 ms (thừa sức 30 Hz); ghi 3 ảnh JPEG 5.6 ms; `json.dumps` 0.06 ms; gọi 3 getter camera 0.007 ms.
