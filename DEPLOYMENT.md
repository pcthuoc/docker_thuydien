# TÀI LIỆU TRIỂN KHAI HỆ THỐNG GIÁM SÁT IoT

**Phiên bản:** 1.0  
**Ngày ban hành:** 15/07/2026  
**Phân loại:** Tài liệu kỹ thuật — Nội bộ

---

## Kiến trúc kho mã nguồn

Hệ thống được tổ chức thành **2 kho mã nguồn riêng biệt**:

| Kho | URL | Nội dung |
|---|---|---|
| **docker_thuydien** | `github.com/pcthuoc/docker_thuydien` | Hạ tầng Docker (repo này) |
| **thuydien** | `github.com/pcthuoc/thuydien` | Mã nguồn ứng dụng web (submodule) |

Thư mục `repo/` bên trong `docker_thuydien` là **git submodule** trỏ về `thuydien`.

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

| Bản ghi | Mục đích |
|---|---|
| `domain.com` | Ứng dụng chính |
| `hub.domain.com` | Giao diện quản trị Docker (Portainer) |

---

## II. CÀI ĐẶT MÔI TRƯỜNG

Thực hiện trên máy chủ với quyền `root`:

```bash
# 1. Cài Docker Engine
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 2. Cài Docker Compose, Git và các công cụ hỗ trợ
apt-get update && apt-get install -y docker-compose-plugin git

# 3. Kiểm tra
docker compose version && git --version
```

---

## III. TRIỂN KHAI HỆ THỐNG

### 3.1 Tải mã nguồn (bao gồm submodule)

```bash
cd /root

# Clone kho Docker kèm theo submodule web app
git clone --recurse-submodules git@github.com:pcthuoc/docker_thuydien.git docker

cd docker
```

> Nếu đã clone mà chưa có submodule:
> ```bash
> git submodule update --init --recursive
> ```

Cấu trúc thư mục sau khi clone:

```
docker/
├── docker-compose.yml
├── DEPLOYMENT.md
├── .gitmodules                ← khai báo submodule
├── environment/
│   ├── site.env.example       ← mẫu cấu hình (sao chép và điền thông tin)
│   ├── mysql.env.example
│   └── mysql-admin.env.example
├── nginx/conf.d/nginx.conf
├── base/Dockerfile
├── site/Dockerfile
├── mqtt_service/Dockerfile
├── mqtt/config/
├── scripts/
└── repo/                      ← submodule: mã nguồn web app
```

### 3.2 Tạo file cấu hình từ template

```bash
cd /root/docker/environment

cp site.env.example        site.env
cp mysql.env.example       mysql.env
cp mysql-admin.env.example mysql-admin.env
```

### 3.3 Điền thông tin cấu hình

**`environment/site.env`** — các giá trị bắt buộc thay thế:

| Biến | Mô tả | Ví dụ |
|---|---|---|
| `SECRET_KEY` | Khóa bí mật Django (50+ ký tự) | Sinh bằng lệnh bên dưới |
| `HOST` | Tên miền chính | `nhamay-abc.com` |
| `CSRF_TRUSTED_ORIGINS` | URL đầy đủ với scheme | `https://nhamay-abc.com` |
| `MQTT_PASS` | Mật khẩu MQTT broker | Tự đặt |

Sinh `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

**`environment/mysql.env`** và **`mysql-admin.env`** — đặt mật khẩu database:

```env
MYSQL_PASSWORD=MatKhauDB@NhamayABC
MARIADB_ROOT_PASSWORD=MatKhauRoot@NhamayABC
MARIADB_PASSWORD=MatKhauDB@NhamayABC
```

**`nginx/conf.d/nginx.conf`** — thay tên miền tại 2 vị trí:

```nginx
server_name nhamay-abc.com;        # ứng dụng chính
server_name hub.nhamay-abc.com;    # Portainer admin
```

### 3.4 Build và khởi động

```bash
cd /root/docker

# Build image cơ sở (thực hiện một lần duy nhất)
docker compose build --no-cache base

# Build các dịch vụ ứng dụng
docker compose build site mqtt_service

# Khởi động toàn bộ hệ thống
docker compose up -d

# Xác nhận các dịch vụ đang hoạt động
docker ps
```

> Chờ khoảng 30–60 giây để cơ sở dữ liệu hoàn tất khởi tạo.

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

Đăng nhập tại `https://nhamay-abc.com/admin/` và thực hiện theo thứ tự:

| Thứ tự | Mục | Nội dung cần cấu hình |
|---|---|---|
| 1 | **Sites** | Cập nhật tên miền hiện tại |
| 2 | **Site Profile** | Chu kỳ tính toán, thông số vận hành nhà máy |
| 3 | **Stations** | Thêm danh sách trạm đo (thiết bị IoT) |
| 4 | **Calculated Values** | Cấu hình các đại lượng tính toán |
| 5 | **Watershed Zone** | Thêm lưu vực địa lý (nếu áp dụng) |

---

## VI. NÂNG CẤP HỆ THỐNG

### Cập nhật mã nguồn web app (submodule)

```bash
cd /root/docker/repo
git pull origin dev/sensor-report
cd ..

# Ghi nhận phiên bản submodule mới vào docker repo
git add repo && git commit -m "chore: update submodule to latest"
git push origin master

# Áp dụng trên server
docker restart vnoj_site
```

### Trường hợp có thay đổi thư viện Python

```bash
docker compose build --no-cache base
docker compose build site mqtt_service
docker compose up -d --force-recreate site mqtt_service celery_worker celery_beat
```

---

## VII. XỬ LÝ SỰ CỐ

| Hiện tượng | Nguyên nhân | Biện pháp xử lý |
|---|---|---|
| Trang web trả về lỗi 502 | Dịch vụ `vnoj_site` chưa sẵn sàng | `docker logs vnoj_site --tail=50` |
| Lỗi CSRF verification failed | Tên miền chưa khớp cấu hình | Kiểm tra `CSRF_TRUSTED_ORIGINS` trong `site.env` |
| Lỗi Error loading MySQLdb | Thiếu thư viện kết nối CSDL | Xác nhận `mysqlclient` trong `requirements.txt` không bị comment |
| Thiết bị IoT không kết nối | Cổng 1883 bị chặn hoặc sai thông tin xác thực | Kiểm tra tường lửa và thông số MQTT trong `site.env` |
| Dữ liệu không hiển thị | Chưa thực hiện migrate | `docker exec -it vnoj_site python manage.py migrate` |
| Submodule `repo/` rỗng | Chưa clone đệ quy | `git submodule update --init --recursive` |

**Xem nhật ký hệ thống:**
```bash
docker logs vnoj_site         # Ứng dụng Django
docker logs vnoj_nginx        # Web server
docker logs vnoj_mqtt_service # Dịch vụ MQTT
docker logs vnoj_mysql        # Cơ sở dữ liệu
```
