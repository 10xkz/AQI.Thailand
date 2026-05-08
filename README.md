# PM2.5 Thailand Monitor — ENG23 3074

> ระบบติดตามคุณภาพอากาศ PM2.5 ประเทศไทยแบบ Real-time พัฒนาด้วย Python FastAPI และ PostgreSQL พร้อม Static Frontend (HTML/JS) ทำงานบน Docker Container และ deploy อัตโนมัติผ่าน Jenkins CI/CD Pipeline บน Kubernetes Cluster

---

## 👥 สมาชิกในกลุ่ม

| รหัสนักศึกษา | ชื่อ-นามสกุล | ความรับผิดชอบ |
|:-----------:|-------------|---------------|
| B6608798 | นายรับเช็ค อึ่งชัยภูมิ | Git, App Development |
| B6629045 | นายศิริเดช สุภาพ | Jenkins, Docker |
| B6608798 | นายจารุวัฒน์ ทองมาก | Terraform, Ansible |
| B6612979 | นางสาววราภรณ์ ท้าวพา | Kubernetes, Monitoring |

---

## 📌 ภาพรวมโปรเจค

### แอปพลิเคชัน

| รายละเอียด | คำอธิบาย |
|-----------|----------|
| **ชื่อ** | PM2.5 Thailand Monitor |
| **ประเภท** | Full-Stack Web Application (REST API + Static Frontend) |
| **Backend** | Python FastAPI |
| **Frontend** | HTML / CSS / JavaScript |
| **Database** | PostgreSQL |
| **คำอธิบาย** | ระบบแสดงข้อมูลคุณภาพอากาศ PM2.5 ทั่วประเทศไทยแบบ Real-time โดยดึงข้อมูลจาก Air4Thai API (กรมควบคุมมลพิษ) คำนวณค่า AQI แสดงสถานะสถานีตรวจวัดทั่วประเทศ และรองรับการบันทึกสถานีโปรดลงฐานข้อมูล |

### Architecture Diagram

```
Developer
    │
    ▼  git push
 GitHub ──── webhook ────▶ Jenkins CI/CD
                                 │
                     ┌───────────┼───────────┐
                     ▼           ▼           ▼
                  Build        Test      Docker Build
                (py_compile)  (echo)   (backend+frontend)
                                             │
                                             ▼
                                        Docker Hub
                                    (rubchek/pm25-*)
                                             │
                                     ┌───────┴───────┐
                                     ▼               ▼
                                 Terraform        Ansible
                              (SSH key + Docker  (ติดตั้ง Docker
                               network + node)    + สร้าง dir)
                                     │               │
                                     └───────┬───────┘
                                             ▼
                            Kubernetes Cluster (namespace: jenkins)
                            ┌─────────────────────────────────┐
                            │  PostgreSQL  Backend  Frontend  │
                            │    (Pod)      (Pod)    (Pod)    │
                            │                                 │
                            │  Service NodePort :30080 (UI)   │
                            │  Service NodePort :30800 (API)  │
                            └─────────────────────────────────┘
                                             │
                               ┌─────────────┴──────────────┐
                               ▼                             ▼
                           Prometheus  ──────────────▶  Grafana
                        (scrape :8000/metrics)        (dashboard)
```

---

## 📁 โครงสร้าง Repository

```
PM2.5-Thailand/
├── backend/
│   ├── main.py                 # FastAPI app — Air4Thai proxy, AQI calc, favorites API
│   ├── requirements.txt        # Python dependencies (fastapi, httpx, psycopg2, prometheus)
│   └── Dockerfile              # Docker image สำหรับ backend
├── frontend/
│   ├── index.html              # Single-page UI แสดงแผนที่และข้อมูลสถานี PM2.5
│   ├── nginx.conf              # Nginx config สำหรับ serve frontend + reverse proxy ไป backend
│   └── Dockerfile              # Docker image สำหรับ frontend (Nginx)
├── database/
│   └── init.sql                # SQL script สร้างตาราง favorites สำหรับ PostgreSQL
├── k8s/
│   ├── 01-database/            # Kubernetes manifests สำหรับ PostgreSQL
│   ├── 02-backend/             # Kubernetes manifests สำหรับ FastAPI backend
│   │   ├── 1-deployment.yaml
│   │   └── 2-service.yaml
│   ├── 03-frontend/            # Kubernetes manifests สำหรับ Nginx frontend
│   └── 04-monitoring/          # Kubernetes manifests สำหรับ Prometheus + Grafana
│       ├── grafana/
│       └── prometheus/
├── terraform/
│   └── main.tf                 # Provision SSH key, Docker network และ target node สำหรับ Ansible
├── ansible/
│   ├── inventory.ini           # รายชื่อ host เป้าหมาย (ansible-target-node)
│   └── playbook.yml            # ติดตั้ง Docker, สร้าง ubuntu user, สร้าง /opt/pm25-monitor
├── prometheus/
│   └── prometheus.yml          # ตั้งค่า scrape target: backend:8000 ทุก 15 วินาที
├── jenkins/                    # Jenkins configuration files
├── Jenkinsfile                 # กำหนด CI/CD pipeline 6 stages
├── docker-compose.yml          # รันทุก service พร้อมกัน (db, backend, frontend, prometheus)
└── README.md
```

---

## ⚙️ Prerequisites

ตรวจสอบให้แน่ใจว่าติดตั้ง tool ต่อไปนี้ครบถ้วนก่อนเริ่มใช้งานโปรเจค

| Tool | Version | หน้าที่ |
|------|:-------:|---------| 
| Git | ≥ 2.x | จัดการ source code |
| Docker | ≥ 24.x | สร้างและรัน container |
| Jenkins | ≥ 2.4xx | ระบบ CI/CD automation |
| Terraform | ≥ 1.x | Provision infrastructure (SSH key, Docker network) |
| Ansible | ≥ 2.15 | Configure environment บน target node |
| kubectl | ≥ 1.28 | สั่งงาน Kubernetes cluster |
| Minikube / K3s | latest | Kubernetes แบบ local |
| Prometheus | ≥ 2.53 | เก็บ metrics จาก backend |
| Grafana | ≥ 10.x | แสดง dashboard |

---

## 🏃 วิธีรันโปรเจค

### 1. Clone Repository

```bash
git clone https://github.com/10xkz/PM2.5-Thailand.git
cd PM2.5-Thailand
```

### 2. รันด้วย Docker Compose (แนะนำ)

```bash
# รัน core services (db + backend + frontend)
docker compose up -d

# รัน core services พร้อม prometheus monitoring
docker compose --profile monitoring up -d
```

| Service | URL |
|---------|-----|
| Frontend (UI) | http://localhost:8080 |
| Backend (API Docs) | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |

### 3. รัน Backend โดยตรง (ไม่ผ่าน Docker)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# เข้าถึง API docs ได้ที่ http://localhost:8000/docs
```

---

## 🔄 CI/CD Pipeline (Jenkins)

### ลำดับการทำงาน

```
Checkout ──▶ Build ──▶ Test ──▶ Docker Build ──▶ Push to Hub ──▶ Deploy
```

| Stage | คำอธิบาย |
|-------|----------|
| **Checkout** | ดึงโค้ดล่าสุดจาก GitHub ผ่าน `checkout scm` |
| **Build** | ตรวจ syntax ของ `backend/main.py` ด้วย `py_compile` และตรวจสอบไฟล์ที่จำเป็น |
| **Test** | รัน unit test |
| **Docker Build** | Build image `rubchek/pm25-backend` และ `rubchek/pm25-frontend` พร้อม tag ด้วย `BUILD_NUMBER` |
| **Push to Hub** | อัปโหลด image ขึ้น Docker Hub ด้วย credentials `docker-hub-credentials` |
| **Deploy** | รัน Terraform + Ansible → apply k8s manifests ทั้งหมดใน `k8s/` → rollout restart → health check |

### การตั้งค่า Jenkins

1. ติดตั้ง Jenkins และเปิดที่ `http://localhost:8080`
2. ติดตั้ง plugin ที่จำเป็น: **Git**, **Pipeline**, **Docker Pipeline**
3. เพิ่ม credentials สำหรับ Docker Hub (ID: `docker-hub-credentials`)
4. สร้าง Pipeline job ใหม่ และกำหนด source ไปยัง repository นี้
5. ตั้งค่า Webhook ใน GitHub:
   - ไปที่ **Settings → Webhooks → Add webhook**
   - Payload URL: `http://[jenkins-host]:8080/github-webhook/`
   - Content type: `application/json`
   - Trigger: **Just the push event**

---

## 🏗️ Infrastructure as Code

### Terraform — Provision Infrastructure

```bash
cd terraform
terraform init      # ดาวน์โหลด provider plugins
terraform plan      # ตรวจสอบ resource ที่จะถูกสร้าง
terraform apply     # สร้าง resource จริง
```

**Resource ที่ Terraform จัดการ:**
- RSA SSH key pair (4096-bit) บันทึกเป็นไฟล์ `ansible_id_rsa` และ `ansible_id_rsa.pub`
- Docker network ชื่อ `terraform-pm25-net`
- Docker container `ansible-target-node` สำหรับจำลอง VM ให้ Ansible

### Ansible — Configure Environment

```bash
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```

**Task ที่ Ansible ดำเนินการ:**
- อัปเดต apt cache และติดตั้ง dependencies (`curl`, `wget`, `git`, `ca-certificates`)
- ติดตั้ง Docker Engine (กรณีที่ยังไม่ได้รันใน container)
- เพิ่ม `ubuntu` user เข้า `docker` group
- สร้าง working directory `/opt/pm25-monitor`

> **หมายเหตุ:** ใน pipeline จริง Jenkins จะเรียก Terraform และ Ansible อัตโนมัติในขั้นตอน Deploy ไม่จำเป็นต้องรันด้วยมือ

---

## ☸️ Kubernetes Deployment

### Apply Manifests

```bash
kubectl apply -R -f k8s/
```

### ตรวจสอบสถานะ

```bash
kubectl get pods -n jenkins
kubectl get svc  -n jenkins
```

### ผลลัพธ์ที่คาดหวัง

```
NAME                            READY   STATUS    RESTARTS   AGE
pm25-backend-xxxxxxxxx-xxxxx    1/1     Running   0          2m
pm25-frontend-xxxxxxxxx-yyyyy   1/1     Running   0          2m

NAME               TYPE       CLUSTER-IP     PORT(S)          AGE
pm25-frontend-svc  NodePort   10.96.xx.xxx   80:30080/TCP     2m
pm25-backend-svc   NodePort   10.96.xx.xxx   8000:30800/TCP   2m
```

### เข้าถึงแอปพลิเคชัน

| Service | URL |
|---------|-----|
| Frontend UI | http://localhost:30080 |
| Backend API Docs | http://localhost:30800/docs |

---

## 📊 Monitoring

### Prometheus — Metrics Collection

- Config file: `prometheus/prometheus.yml`
- Scrape interval: **ทุก 15 วินาที**
- Target endpoint: `http://backend:8000/metrics` (prometheus-fastapi-instrumentator)

```bash
# รัน Prometheus ผ่าน Docker Compose
docker compose --profile monitoring up -d prometheus
# เปิด UI ที่ http://localhost:9090
```

### Grafana — Dashboard Visualization

- Deploy บน Kubernetes ใน `k8s/04-monitoring/grafana/`
- Data source: Prometheus (`http://localhost:9090`)

**วิธี Import Dashboard:**
1. เปิด Grafana ที่ `http://localhost:3000`
2. ไปที่ **Dashboards → Import**
3. อัปโหลดไฟล์ dashboard JSON

### Dashboard Panels

| Panel | PromQL | คำอธิบาย |
|-------|--------|----------|
| Request Rate | `rate(http_requests_total[1m])` | จำนวน request ต่อวินาที |
| Error Rate | `rate(http_requests_total{status=~"5.."}[1m])` | จำนวน 5xx error ต่อวินาที |
| Latency (p95) | `histogram_quantile(0.95, ...)` | Response time ที่ percentile 95 |
| Pod Health | `up{job="pm25_backend"}` | สถานะ service (1 = up / 0 = down) |

---

## 🌿 Branching Strategy

```
main        ──── โค้ดที่พร้อม production (protected branch)
dev         ──── รวมโค้ดและทดสอบก่อน merge ขึ้น main
feature/*   ──── พัฒนา feature แต่ละอัน (เช่น feature/add-login)
```

| Branch | Protected | คำอธิบาย |
|--------|:---------:|----------|
| `main` | ✅ | Trigger CI/CD pipeline อัตโนมัติเมื่อมีการ merge |
| `dev` | ✅ | Integration branch สำหรับทดสอบก่อน release |
| `feature/*` | ❌ | Feature branch แยกตาม task แล้ว merge เข้า `dev` |

---

## 🧪 API Reference

| Method | Endpoint | คำอธิบาย |
|:------:|----------|----------|
| `GET` | `/health` | Liveness probe — ตรวจสอบสถานะ backend |
| `GET` | `/metrics` | Prometheus metrics endpoint |
| `GET` | `/api/locations` | ดึงรายการสถานีตรวจวัด PM2.5 ทั่วประเทศจาก Air4Thai |
| `GET` | `/api/measurements/{location_id}` | ดึงข้อมูลละเอียด (PM2.5, PM10, O3, CO, NO2, SO2, AQI) ของสถานีที่ระบุ |
| `GET` | `/api/summary` | สรุปสถิติ PM2.5 ระดับประเทศ (avg, max, min, worst station) |
| `POST` | `/api/discover` | Trigger discovery refresh |
| `GET` | `/api/favorites` | ดึงรายการสถานีโปรดจาก PostgreSQL |
| `POST` | `/api/favorites` | บันทึกสถานีโปรดลง PostgreSQL |

---

## 🗄️ Database Schema

```sql
CREATE TABLE IF NOT EXISTS favorites (
  id          SERIAL PRIMARY KEY,
  station_id  TEXT,
  station_name TEXT NOT NULL,
  pm25_value  NUMERIC,
  created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📋 Backend Response Examples

### `GET /api/summary`

```json
{
  "total_stations": 75,
  "stations_with_data": 72,
  "pm25_avg": 26.4,
  "pm25_max": 84.1,
  "pm25_min": 3.2,
  "worst_station": {
    "name": "Bangkok Startup Station",
    "city": "Bangkok",
    "pm25": 84.1,
    "aqi": { "label": "Unhealthy", "color": "#ef4444", "level": 4 }
  },
  "aqi_distribution": { "Good": 20, "Moderate": 35, "Unhealthy": 17 },
  "fetched_at": "2026-05-08T13:49:46.663000+00:00",
  "source": "air4thai"
}
```

### `GET /api/favorites`

```json
{
  "favorites": [
    {
      "id": 1,
      "station_id": "bangkok_startup_station",
      "station_name": "Bangkok Startup Station",
      "pm25_value": 25.5,
      "created_at": "2026-05-08T14:21:02.990000+00:00"
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Pods ค้างอยู่ที่ `Pending`

```bash
kubectl describe pod <pod-name> -n jenkins
# ตรวจสอบที่ Events — อาจเกิดจาก resource ไม่เพียงพอ หรือ image pull error
```

### Jenkins Pipeline ล้มเหลวที่ Docker Build Stage

```bash
# ตรวจสอบว่า Docker daemon กำลังรันอยู่
sudo systemctl start docker

# เพิ่ม jenkins user เข้า docker group
sudo usermod -aG docker jenkins
```

### Prometheus แสดง Target เป็น DOWN

```bash
# ทดสอบ metrics endpoint โดยตรง
curl http://localhost:8000/metrics

# ตรวจสอบ prometheus.yml ว่า host:port ตรงกับ service จริง (backend:8000)
```

### Backend เชื่อมต่อ PostgreSQL ไม่ได้

```bash
# ตรวจสอบ environment variables
echo $DB_HOST $DB_NAME $DB_USER
# ค่า default: db / mydatabase / user / password

# ตรวจสอบสถานะ database container
docker compose ps
```

### Air4Thai API ไม่ตอบสนอง (503)

```bash
# ทดสอบเรียก Air4Thai API โดยตรง
curl "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php"

# หมายเหตุ: ข้อมูลถูก cache ไว้ 30 นาที (CACHE_TTL_DATA = 1800s)
```

---

## 📚 References

- [Jenkins Declarative Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Ansible Documentation](https://docs.ansible.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [GitHub Flavored Markdown](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)