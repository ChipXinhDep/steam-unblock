# Steam Unblock

> [!TIP]
> 🇬🇧 **English version: [README.en.md](README.en.md)**

Ứng dụng nhỏ chạy dưới khay hệ thống (cạnh đồng hồ) giúp mở lại **Steam Store** và
**Steam Community** khi nhà mạng chặn, **không cần VPN** và **chỉ áp dụng cho các trang của
Steam**: game, tải game và mọi trang web khác vẫn kết nối bình thường như cũ.

> **Không liên kết hay được bảo trợ bởi Valve Corporation.** "Steam" là thương hiệu của Valve Corporation.

## Bạn có cần app này không?

Dấu hiệu thường gặp:

- Trong Steam, tab Store / Community báo **Error Code: -101**
  ("Unable to connect to server...").
- Mở `https://store.steampowered.com` bằng Chrome/Edge báo **ERR_CONNECTION_RESET**.
- Nhưng **chơi game trên Steam vẫn bình thường**, các trang web khác vẫn vào được.

Nếu đúng như vậy, nhiều khả năng nhà mạng đang chặn Steam theo tên miền, và app này sẽ giúp được.
Đổi DNS (8.8.8.8, 1.1.1.1...) sẽ **không** có tác dụng với kiểu chặn này.

## Cách sử dụng

1. Vào mục [Releases](../../releases), tải file **`SteamUnblock.exe`**.
2. Chạy file vừa tải. Cửa sổ nhỏ hiện dòng chữ xanh **"Running: Steam Store unblocked"**.
   - Nếu Windows SmartScreen cảnh báo: bấm **More info → Run anyway**
     (app chưa được ký số nên Windows cảnh báo; toàn bộ mã nguồn có trong repo này).
3. **Thoát Steam hoàn toàn rồi mở lại một lần** (Steam → Exit, không chỉ đóng cửa sổ).
4. Vào Store / Community, các trang sẽ hiện bình thường.

### Khay hệ thống

- Bấm nút thu nhỏ (–): cửa sổ ẩn xuống khay hệ thống, app vẫn chạy.
- Biểu tượng **ổ khóa mở trên nền xanh** = đang chạy, **ổ khóa đóng trên nền xám** = đã dừng.
- **Bấm** vào biểu tượng để mở lại cửa sổ. **Chuột phải** để chọn **Show / Stop (Start) / Run at Windows startup / Quit**.
- Trên Windows 11, biểu tượng có thể nằm trong mục **^** (ẩn). Kéo nó ra thanh taskbar nếu muốn luôn thấy.

### Tắt app

Bấm **Stop**, **Quit** hoặc đóng cửa sổ (X). App sẽ **trả lại cài đặt proxy của Windows như cũ**.
Khi app tắt, Steam Store lại bị chặn như trước. Muốn dùng Store thì chạy app lại.

### Tự chạy cùng Windows (tùy chọn)

Tích ô **Run at Windows startup** trong cửa sổ app (hoặc chọn mục này trong menu chuột phải ở khay hệ thống).
Từ lần đăng nhập Windows sau, app tự chạy và **ẩn luôn dưới khay hệ thống**, không hiện cửa sổ.

- Bỏ tích để tắt.
- Nếu di chuyển file `SteamUnblock.exe` sang chỗ khác, chỉ cần chạy app một lần ở chỗ mới, đường dẫn sẽ tự cập nhật.
- **Trước khi xóa** `SteamUnblock.exe`, hãy bỏ tích ô này để Windows không còn tìm chạy file đã xóa.
- App lưu tùy chọn này ở mục `SteamUnblock` trong `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
  (chỉ cho tài khoản của bạn, không cần quyền Admin).

## Cách hoạt động

Khi bạn mở một trang HTTPS, gói tin đầu tiên (TLS ClientHello) chứa **tên trang web**
(gọi là SNI) ở dạng chưa mã hóa. Nhà mạng đọc tên này, thấy là Steam thì **cắt kết nối**,
nên Steam báo lỗi -101.

App chạy một proxy nhỏ ngay trên máy bạn (`127.0.0.1:8899`). Với các trang Steam, app
**chia gói tin đầu tiên thành nhiều mảnh nhỏ**, nên bộ lọc của nhà mạng không đọc được tên
trang và cho đi qua. Sau đó dữ liệu được chuyển nguyên vẹn, đi **thẳng tới máy chủ của Steam**.

- **Không** giải mã dữ liệu, **không** cài chứng chỉ, **không** đi qua máy chủ trung gian nào.
- **Không** thu thập hay gửi dữ liệu của bạn đi đâu.
- **Chỉ các tên miền sau đi qua app** (thông qua file cấu hình proxy tự động PAC của Windows):
  `steampowered.com`, `steamcommunity.com`, `steamstatic.com`, `steamusercontent.com`, `steam-chat.com`.
  Mọi kết nối khác (game, tải game, YouTube, Google...) **đi thẳng**, không bị ảnh hưởng, không tăng ping.
- Proxy từ chối mọi yêu cầu không phải tới các tên miền trên.

### App thay đổi gì trên máy?

Khi chạy, app đặt mục **"Use setup script"** (`AutoConfigURL` trong
`HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`) trỏ tới app.
Khi tắt, app trả lại giá trị cũ.

Nếu app bị tắt đột ngột (treo máy, kill process...), cài đặt này có thể còn lại nhưng **vô hại**:
các trang Steam chỉ quay về kết nối thẳng (bị chặn như trước), các trang khác không bị ảnh hưởng.
Chạy app lại rồi tắt là sạch.

## Giới hạn

- Chỉ có tác dụng khi nhà mạng chặn theo tên miền (SNI). Nếu nhà mạng đổi cách chặn,
  app có thể ngừng hoạt động.
- Chỉ chạy trên Windows.

## Chạy từ mã nguồn / tự build

Cần Python 3.13 trở lên.

```
pip install -r requirements.txt
python steam_unblock.py          # chạy app
python steam_unblock.py --test   # tự kiểm tra
pip install pyinstaller
python -m PyInstaller --onefile --windowed --hidden-import pystray._win32 --add-data "assets;assets" --name SteamUnblock steam_unblock.py
```

File `.exe` trong Releases được GitHub Actions build tự động từ mã nguồn này
(xem `.github/workflows/release.yml`).

## Miễn trừ trách nhiệm

Phần mềm được cung cấp "nguyên trạng", không có bảo đảm (xem [LICENSE](LICENSE)).
Bạn tự chịu trách nhiệm đảm bảo việc sử dụng phù hợp với quy định nơi bạn sinh sống.

## Giấy phép

MIT, xem [LICENSE](LICENSE). Thành phần bên thứ ba: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
