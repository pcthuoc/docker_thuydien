# TÀI LIỆU HƯỚNG DẪN TRIỂN KHAI
## HỆ THỐNG GIÁM SÁT VẬN HÀNH NHÀ MÁY THỦY ĐIỆN

---

| | |
|---|---|
| **Mã tài liệu** | HTD-DEPLOY-001 |
| **Phiên bản** | 1.0 |
| **Ngày ban hành** | 15/07/2026 |
| **Phân loại** | Tài liệu kỹ thuật — Dùng nội bộ |

---

## MỤC LỤC

1. Tổng quan hệ thống
2. Yêu cầu hạ tầng
3. Cài đặt môi trường
4. Triển khai hệ thống
5. Khởi tạo dữ liệu ban đầu
6. Cấu hình vận hành
7. Nâng cấp hệ thống
8. Xử lý sự cố

---

## 1. TỔNG QUAN HỆ THỐNG

Hệ thống giám sát vận hành nhà máy thủy điện được xây dựng theo kiến trúc containerized (Docker), cho phép triển khai nhanh và đồng nhất trên nhiều môi trường khác nhau.

### 1.1 Kiến trúc kho mã nguồn

Hệ thống được tổ chức thành **2 kho mã nguồn riêng biệt**:

| Kho mã nguồn | Địa chỉ | Vai trò |
|---|---|---|
| **docker_thuydien** | `github.com/pcthuoc/docker_thuydien` | Hạ tầng Docker — cấu hình triển khai |
| **thuydien** | `github.com/pcthuoc/thuydien` | Mã nguồn ứng dụng web (tích hợp dạng submodule) |

> Thư mục `repo/` bên trong `docker_thuydien` là **git submodule** tự động liên kết về kho `thuydien`. Khi cập nhật mã nguồn ứng dụng, chỉ cần thao tác trong kho `thuydien`; kho `docker_thuydien` sẽ ghi nhận phiên bản tương ứng.

### 1.2 Các dịch vụ Docker

| Tên dịch vụ | Container | Chức năng |
|---|---|---|
| Ứng dụng web | `vnoj_site` | Django ASGI — giao diện giám sát |
| Cơ sở dữ liệu | `vnoj_mysql` | MariaDB — lưu trữ dữ liệu |
| Cache & Queue | `vnoj_redis` | Redis — bộ nhớ đệm và hàng đợi tác vụ |
| Web server | `vnoj_nginx` | Nginx — reverse proxy |
| MQTT Broker | `mosquitto` | Eclipse Mosquitto — nhận dữ liệu từ thiết bị IoT |
| Dịch vụ MQTT | `vnoj_mqtt_service` | Xử lý và lưu dữ liệu từ broker |
| Tác vụ nền | `vnoj_celery_worker` | Celery Worker — xử lý tác vụ bất đồng bộ |
| Lập lịch | `vnoj_celery_beat` | Celery Beat — lập lịch tính toán định kỳ |
| Quản trị Docker | `vnoj_portainer` | Portainer — giao diện quản lý container |

---

## 2. YÊU CẦU HẠ TẦNG

### 2.1 Máy chủ

| Thông số | Yêu cầu tối thiểu | Khuyến nghị |
|---|---|---|
| Hệ điều hành | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Lưu trữ | 40 GB SSD | 100 GB SSD |
| Băng thông | 10 Mbps | 50 Mbps |

### 2.2 Cổng mạng cần mở trên tường lửa

| Cổng | Giao thức | Mục đích |
|---|---|---|
| 80 | TCP | HTTP — truy cập web qua Nginx |
| 443 | TCP | HTTPS — (nếu cấu hình SSL) |
| 1883 | TCP | MQTT — thiết bị IoT gửi dữ liệu lên |

### 2.3 Tên miền

Cần chuẩn bị **2 bản ghi DNS loại A** trỏ về địa chỉ IP máy chủ:

| Bản ghi DNS | Mục đích |
|---|---|
| `ten-nha-may.com` | Ứng dụng giám sát chính |
| `hub.ten-nha-may.com` | Giao diện quản trị Docker (Portainer) |

---

## 3. CÀI ĐẶT MÔI TRƯỜNG

Thực hiện trên máy chủ với quyền `root`. Chỉ cần thực hiện **một lần** khi lần đầu cài đặt.

### 3.1 Cài đặt Docker Engine

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 3.2 Cài đặt Docker Compose và Git

```bash
apt-get update && apt-get install -y docker-compose-plugin git
```

### 3.3 Kiểm tra cài đặt

```bash
docker compose version
git --version
```

---

## 4. TRIỂN KHAI HỆ THỐNG

### 4.1 Tải mã nguồn

```bash
cd /root

# Clone kho Docker kèm submodule web app
git clone --recurse-submodules git@github.com:pcthuoc/docker_thuydien.git docker

cd docker
```

> **Lưu ý:** Nếu đã clone nhưng thư mục `repo/` còn rỗng, chạy thêm:
> ```bash
> git submodule update --init --recursive
> ```

Sau khi clone, cấu trúc thư mục như sau:

```
docker/
├── docker-compose.yml
├── DEPLOYMENT.md
├── environment/
│   ├── site.env.example         ← mẫu cấu hình ứng dụng
│   ├── mysql.env.example        ← mẫu cấu hình cơ sở dữ liệu
│   └── mysql-admin.env.example  ← mẫu mật khẩu quản trị DB
├── nginx/conf.d/nginx.conf      ← cấu hình web server
├── base/Dockerfile
├── site/Dockerfile
├── mqtt_service/Dockerfile
├── mqtt/config/                 ← cấu hình MQTT broker
├── scripts/                     ← công cụ quản lý Django
└── repo/                        ← mã nguồn web (submodule)
```

### 4.2 Tạo file cấu hình từ mẫu

```bash
cd /root/docker/environment

cp site.env.example        site.env
cp mysql.env.example       mysql.env
cp mysql-admin.env.example mysql-admin.env
```

### 4.3 Điền thông tin cấu hình

#### 4.3.1 Cấu hình ứng dụng — `environment/site.env`

Mở file và thay thế các giá trị sau:

| Biến môi trường | Mô tả | Lưu ý |
|---|---|---|
| `SECRET_KEY` | Khóa bí mật Django | Sinh ngẫu nhiên, tối thiểu 50 ký tự |
| `HOST` | Tên miền chính | Ví dụ: `nhamay-abc.com` |
| `CSRF_TRUSTED_ORIGINS` | URL đầy đủ | Ví dụ: `https://nhamay-abc.com` |
| `MQTT_PASS` | Mật khẩu MQTT | Đặt mật khẩu mạnh |

Lệnh sinh `SECRET_KEY` ngẫu nhiên:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### 4.3.2 Cấu hình cơ sở dữ liệu — `environment/mysql.env` và `mysql-admin.env`

```env
# mysql.env
MYSQL_PASSWORD=MatKhauManhChoNhamay@2024

# mysql-admin.env
MARIADB_ROOT_PASSWORD=MatKhauRootManhChoNhamay@2024
MARIADB_PASSWORD=MatKhauManhChoNhamay@2024
```

#### 4.3.3 Cấu hình tên miền — `nginx/conf.d/nginx.conf`

Tìm và thay thế tên miền tại **2 vị trí** trong file:

```nginx
# Vị trí 1 — ứng dụng chính
server_name nhamay-abc.com;

# Vị trí 2 — Portainer admin
server_name hub.nhamay-abc.com;
```

### 4.4 Build và khởi động

```bash
cd /root/docker

# Bước 1: Build image cơ sở (chỉ thực hiện 1 lần hoặc khi đổi thư viện)
docker compose build --no-cache base

# Bước 2: Build các dịch vụ ứng dụng
docker compose build site mqtt_service

# Bước 3: Khởi động toàn bộ hệ thống
docker compose up -d

# Bước 4: Kiểm tra trạng thái
docker ps
```

> Chờ khoảng **30–60 giây** để cơ sở dữ liệu hoàn tất khởi tạo trước khi thực hiện mục 5.

---

## 5. KHỞI TẠO DỮ LIỆU BAN ĐẦU

Thực hiện **một lần duy nhất** sau khi triển khai hệ thống lần đầu:

```bash
# Bước 1: Tạo cấu trúc bảng cơ sở dữ liệu
docker exec -it vnoj_site python manage.py migrate

# Bước 2: Thu thập file tĩnh (CSS, JavaScript, hình ảnh)
docker exec -it vnoj_site python manage.py collectstatic --noinput

# Bước 3: Tạo tài khoản quản trị viên
docker exec -it vnoj_site python manage.py createsuperuser
# → Hệ thống sẽ yêu cầu nhập: tên đăng nhập, email, mật khẩu
```

---

## 6. CẤU HÌNH VẬN HÀNH

Đăng nhập vào trang quản trị tại địa chỉ `https://nhamay-abc.com/admin/` và thực hiện theo thứ tự:

| Thứ tự | Module | Nội dung cần cấu hình |
|---|---|---|
| 1 | **Sites** | Cập nhật tên miền của hệ thống |
| 2 | **Site Profile** | Chu kỳ tính toán, thông số đặc thù nhà máy |
| 3 | **Stations** | Thêm danh sách trạm đo (thiết bị IoT đầu cuối) |
| 4 | **Calculated Values** | Cấu hình các đại lượng tính toán (lưu lượng, mực nước...) |
| 5 | **Watershed Zone** | Thêm lưu vực địa lý (nếu có trạm đo mưa) |

---

## 7. NÂNG CẤP HỆ THỐNG

### 7.1 Cập nhật mã nguồn ứng dụng web

```bash
cd /root/docker/repo
git pull origin dev/sensor-report

# Restart dịch vụ để tải mã nguồn mới
docker restart vnoj_site vnoj_mqtt_service vnoj_celery_worker vnoj_celery_beat
```

### 7.2 Cập nhật khi có thay đổi thư viện Python

```bash
cd /root/docker

docker compose build --no-cache base
docker compose build site mqtt_service
docker compose up -d --force-recreate site mqtt_service celery_worker celery_beat
```

### 7.3 Ghi nhận phiên bản vào kho Docker

```bash
cd /root/docker
git add repo
git commit -m "chore: update submodule to version YYYY-MM-DD"
git push origin master
```

---

## 8. XỬ LÝ SỰ CỐ

### 8.1 Bảng sự cố thường gặp

| Hiện tượng | Nguyên nhân phổ biến | Biện pháp xử lý |
|---|---|---|
| Trang web trả về lỗi 502 | Dịch vụ `vnoj_site` chưa sẵn sàng | Xem nhật ký: `docker logs vnoj_site --tail=50` |
| Lỗi CSRF verification failed | Tên miền chưa khớp cấu hình | Kiểm tra `CSRF_TRUSTED_ORIGINS` trong `site.env` |
| Lỗi Error loading MySQLdb | Thiếu thư viện kết nối CSDL | Xác nhận `mysqlclient` trong `requirements.txt` không bị comment |
| Thiết bị IoT không kết nối được | Cổng 1883 bị chặn hoặc sai thông tin | Kiểm tra tường lửa và `MQTT_PASS` trong `site.env` |
| Dữ liệu không hiển thị trên web | Chưa chạy migrate | `docker exec -it vnoj_site python manage.py migrate` |
| Thư mục `repo/` rỗng sau clone | Chưa clone đệ quy | `git submodule update --init --recursive` |

### 8.2 Xem nhật ký hệ thống

```bash
docker logs vnoj_site         # Nhật ký ứng dụng Django
docker logs vnoj_nginx        # Nhật ký web server
docker logs vnoj_mqtt_service # Nhật ký dịch vụ MQTT
docker logs vnoj_mysql        # Nhật ký cơ sở dữ liệu
```

### 8.3 Khởi động lại dịch vụ

```bash
# Khởi động lại toàn bộ
docker compose restart

# Khởi động lại từng dịch vụ
docker restart vnoj_site
docker restart vnoj_nginx
docker restart vnoj_mysql
```
