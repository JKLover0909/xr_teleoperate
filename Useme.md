# Hướng dẫn chạy Teleoperation G1 (Inspire FTP)

Nhánh code đang dùng: `main-inspire-deps`.

Thiết bị:

| Thiết bị | IP |
|---|---|
| Host | 192.168.0.160 |
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
source /home/jkl0909/.holosoma_deps/miniconda3/etc/profile.d/conda.sh
conda activate tv

export PYTHONNOUSERSITE=1
export PIP_USER=0

export XR_TELEOP_CERT="$HOME/.config/xr_teleoperate/cert.pem"
export XR_TELEOP_KEY="$HOME/.config/xr_teleoperate/key.pem"
```

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

### Terminal 1a — tay PHẢI

```bash
source /home/jkl0909/.holosoma_deps/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

export PYTHONPATH="/home/jkl0909/code/Son/unitree_lerobot/inspire_hand_ws/inspire_hand_sdk/inspire_sdkpy"

cd /home/jkl0909/code/Son/unitree_lerobot

python -u unitree_lerobot/eval_robot/inspire_hand_ftp_driver.py \
  --network-interface=enp1s0 \
  --hand=right \
  --ip=192.168.123.211 \
  --no-touch
```

### Terminal 1b — tay TRÁI

```bash
source /home/jkl0909/.holosoma_deps/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

export PYTHONPATH="/home/jkl0909/code/Son/unitree_lerobot/inspire_hand_ws/inspire_hand_sdk/inspire_sdkpy"

cd /home/jkl0909/code/Son/unitree_lerobot

python -u unitree_lerobot/eval_robot/inspire_hand_ftp_driver.py \
  --network-interface=enp1s0 \
  --hand=left \
  --ip=192.168.123.210 \
  --no-touch
```

Cả hai chờ log báo tần số ổn định (khoảng `~20 Hz`). Giữ cả hai terminal chạy xuyên suốt.

---

## Bước 5 — Host Terminal 2: chương trình teleop chính

```bash
source /home/jkl0909/.holosoma_deps/miniconda3/etc/profile.d/conda.sh
conda activate tv
export PYTHONNOUSERSITE=1
export PIP_USER=0

export XR_TELEOP_CERT="$HOME/.config/xr_teleoperate/cert.pem"
export XR_TELEOP_KEY="$HOME/.config/xr_teleoperate/key.pem"

export PYTHONPATH="/home/jkl0909/code/Son/xr_teleoperate:/home/jkl0909/code/Son/unitree_lerobot/inspire_hand_ws/inspire_hand_sdk/inspire_sdkpy"

cd /home/jkl0909/code/Son/xr_teleoperate/teleop

python teleop_hand_and_arm.py \
  --arm=G1_29 \
  --ee=inspire_ftp \
  --input-mode=hand \
  --display-mode=immersive \
  --motion \
  --img-server-ip=192.168.123.164 \
  --network-interface=enp1s0 \
  --record \
  --task-dir=./utils/data/ \
  --task-name="pick_bottle" \
  --task-goal="pick up the cube" \
  --task-desc="bimanual manipulation" \
  --task-steps="step1: reach; step2: grasp; step3: place"
```
python teleop_hand_and_arm.py \
  --arm=G1_29 \
  --ee=inspire_ftp \
  --input-mode=hand \
  --display-mode=immersive \
  --motion \
  --img-server-ip=192.168.123.164 \
  --network-interface=enp1s0

`--motion` bỏ qua tự chuyển robot vào development/debug mode. Robot phải đã ở Regular/Control mode (R1+X trên tay cầm Unitree) trước khi chạy.

**Quan trọng — `--img-server-ip` phải là IP thật của PC2 (`192.168.123.164`, cổng ethernet), không phải IP của Host.** Nhầm sang IP Host (`192.168.0.161`) khiến `ImageClient` không request được config, tự fallback đọc cache `cam_config_client.yaml` cũ và không subscribe được ZMQ thật — hệ quả: Quest vẫn hiện video (do WebRTC dùng port cố định khác), nhưng khi `--record` thì mọi item ghi ra sẽ có `colors: {}` trống hoàn toàn, không có ảnh nào lưu được dù `states`/`actions` (khớp tay/cánh tay) vẫn ghi đúng.

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
  --network-interface=enp1s0
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

Nếu chỉ teleop không ghi dataset, bỏ các dòng `--record` và `--task-*`.

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
https://192.168.0.160:8012/?ws=wss://192.168.0.160:8012
```

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
| `--network-interface` | string | None | Interface DDS (ví dụ `enp1s0`) |
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
  /home/jkl0909/.holosoma_deps/miniconda3/envs/tv/bin/python -m pip install -e \
    /home/jkl0909/code/Son/xr_teleoperate/teleop/televuer --no-deps
  ```

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

- **Những thứ đã loại trừ (đo thật, KHÔNG phải nguyên nhân)**: camera PC2 chạy đúng 30.1 Hz cả 3 luồng, 0 frame mất; IK `solve_ik` chỉ 4.5 ms (thừa sức 30 Hz); ghi 3 ảnh JPEG 5.6 ms; `json.dumps` 0.06 ms; gọi 3 getter camera 0.007 ms.
