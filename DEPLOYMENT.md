# TÀI LIỆU TRIỂN KHAI HỆ THỐNG GIÁM SÁT IoT

**Phiên bản:** 1.0  
**Ngày ban hành:** 14/07/2026  
**Phân loại:** Tài liệu kỹ thuật — Nội bộ

---

## I. YÊU CẦU HẠ TẦNG

### Máy chủ (VPS / Dedicated Server)

| Thông số | Yêu cầu tối thiểu | Khuyến nghị |
|---|---|---|
| Hệ điều hành | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Lưu trữ | 40 GB SSD | 100 GB SSD |
| Băng thông | 10 Mbps | 50 Mbps |

### Cổng cần mở trên tường lửa

| Cổng | Giao thức | Mục đích |
|---|---|---|
| 80 | TCP | HTTP (Nginx) |
| 443 | TCP | HTTPS (nếu có SSL) |
| 1883 | TCP | MQTT Broker — thiết bị IoT kết nối |

### Tên miền

Cần chuẩn bị **2 bản ghi DNS** trỏ về IP máy chủ:

| Bản ghi | Giá trị | Mục đích |
|---|---|---|
| `domain.com` | `<IP máy chủ>` | Ứng dụng chính |
| `hub.domain.com` | `<IP máy chủ>` | Giao diện quản trị Docker |

---

## II. CÀI ĐẶT MÔI TRƯỜNG

Thực hiện trên máy chủ với quyền `root`:

```bash
# 1. Cài Docker Engine
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 2. Cài Docker Compose và các công cụ hỗ trợ
apt-get update && apt-get install -y docker-compose-plugin git unzip

# 3. Kiểm tra
docker compose version
```

---

## III. TRIỂN KHAI HỆ THỐNG

### 3.1 Tải mã nguồn

**Từ file ZIP (bàn giao):**
```bash
cd /root
unzip iot-monitor.zip -d docker
cd docker
```

**Từ kho mã nguồn Git:**
```bash
git clone git@github.com:pcthuoc/thuydien.git docker
cd docker
git checkout dev/sensor-report
```

Cấu trúc thư mục sau khi giải nén:
```
docker/
├── docker-compose.yml
├── DEPLOYMENT.md
├── environment/
│   ├── site.env          ← cấu hình ứng dụng & domain
│   ├── mysql.env         ← thông tin kết nối CSDL
│   └── mysql-admin.env   ← mật khẩu CSDL
├── nginx/conf.d/
│   └── nginx.conf        ← cấu hình Nginx & domain
├── base/Dockerfile
├── site/Dockerfile
├── mqtt_service/Dockerfile
├── mqtt/config/          ← cấu hình MQTT broker
├── repo/                 ← mã nguồn ứng dụng
└── media/                ← file media (firmware, ảnh...)
```

### 3.2 Cấu hình tên miền và bảo mật

**Bước 1 — Cập nhật `nginx/conf.d/nginx.conf`:**

Tìm và thay thế tên miền mẫu bằng tên miền thực tế tại 2 vị trí:
```nginx
server {
    server_name ten-domain-moi.com;        # ← ứng dụng chính
}

server {
    server_name hub.ten-domain-moi.com;    # ← quản trị Docker
}
```

**Bước 2 — Cập nhật `environment/site.env`:**
```env
HOST=ten-domain-moi.com
CSRF_TRUSTED_ORIGINS=https://ten-domain-moi.com

# Bắt buộc thay thế trước khi vận hành thực tế:
SECRET_KEY=<khoa_bi_mat_ngau_nhien_50_ky_tu>
```

Lệnh sinh `SECRET_KEY` ngẫu nhiên:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**Bước 3 — Cập nhật mật khẩu cơ sở dữ liệu:**

File `environment/mysql.env`:
```env
MYSQL_PASSWORD=<mat_khau_moi>
```

File `environment/mysql-admin.env`:
```env
MARIADB_ROOT_PASSWORD=<mat_khau_root_moi>
MARIADB_PASSWORD=<mat_khau_moi>
```

### 3.3 Build và khởi động

```bash
cd /root/docker

# Build image cơ sở (thực hiện một lần)
docker compose build --no-cache base

# Build các dịch vụ ứng dụng
docker compose build site mqtt_service

# Khởi động toàn bộ hệ thống
docker compose up -d

# Xác nhận các dịch vụ đang hoạt động
docker ps
```

> Chờ khoảng 30–60 giây để cơ sở dữ liệu hoàn tất khởi tạo trước khi thực hiện bước tiếp theo.

---

## IV. KHỞI TẠO DỮ LIỆU BAN ĐẦU

```bash
# Tạo cấu trúc bảng cơ sở dữ liệu
docker exec -it vnoj_site python manage.py migrate

# Thu thập file tĩnh (CSS, JavaScript)
docker exec -it vnoj_site python manage.py collectstatic --noinput

# Tạo tài khoản quản trị viên
docker exec -it vnoj_site python manage.py createsuperuser
```

---

## V. CẤU HÌNH VẬN HÀNH

Đăng nhập tại `https://ten-domain-moi.com/admin/` và thực hiện theo thứ tự:

| Thứ tự | Mục | Nội dung cần cấu hình |
|---|---|---|
| 1 | **Sites** | Cập nhật tên miền hiện tại |
| 2 | **Site Profile** | Chu kỳ tính toán, thông số vận hành nhà máy |
| 3 | **Stations** | Thêm danh sách trạm đo (thiết bị IoT) |
| 4 | **Calculated Values** | Cấu hình các đại lượng tính toán |
| 5 | **Watershed Zone** | Thêm lưu vực địa lý (nếu áp dụng) |

---

## VI. NÂNG CẤP HỆ THỐNG

Khi có phiên bản mã nguồn mới:

```bash
cd /root/docker/repo
git pull origin dev/sensor-report

# Trường hợp thông thường (thay đổi logic, giao diện)
docker restart vnoj_site

# Trường hợp có thay đổi thư viện (requirements.txt)
docker compose build --no-cache base
docker compose build site mqtt_service
docker compose up -d --force-recreate site mqtt_service celery_worker celery_beat
```

---

## VII. XỬ LÝ SỰ CỐ

| Hiện tượng | Nguyên nhân | Biện pháp xử lý |
|---|---|---|
| Trang web trả về lỗi 502 | Dịch vụ `vnoj_site` chưa sẵn sàng | Kiểm tra nhật ký: `docker logs vnoj_site --tail=50` |
| Lỗi CSRF verification failed | Tên miền chưa khớp cấu hình | Kiểm tra `CSRF_TRUSTED_ORIGINS` trong `site.env` |
| Lỗi Error loading MySQLdb | Thiếu thư viện kết nối CSDL | Xác nhận `mysqlclient` trong `requirements.txt` không bị comment |
| Thiết bị IoT không kết nối | Cổng 1883 bị chặn hoặc sai thông tin xác thực | Kiểm tra tường lửa và thông số MQTT trong `site.env` |
| Dữ liệu không hiển thị | Chưa thực hiện migrate | Chạy: `docker exec -it vnoj_site python manage.py migrate` |

**Xem nhật ký hệ thống:**
```bash
docker logs vnoj_site         # Ứng dụng Django
docker logs vnoj_nginx        # Web server
docker logs vnoj_mqtt_service # Dịch vụ MQTT
docker logs vnoj_mysql        # Cơ sở dữ liệu
```
