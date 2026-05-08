# 🚀 PM2.5 Thailand Monitor — ENG23 3074

> ระบบติดตามคุณภาพอากาศ PM2.5 ประเทศไทยแบบ Real-time สร้างด้วย Python FastAPI + PostgreSQL + HTML/JS containerize ด้วย Docker และ deploy บน Kubernetes ผ่าน Jenkins CI/CD pipeline อัตโนมัติ

---

## 👥 สมาชิกในกลุ่ม

| รหัสนักศึกษา | ชื่อ-นามสกุล | ความรับผิดชอบ |
|-------------|-------------|---------------|
| 6XXXXXXX | ชื่อ นามสกุล | Git, App Development |
| 6XXXXXXX | ชื่อ นามสกุล | Jenkins, Docker |
| 6XXXXXXX | ชื่อ นามสกุล | Terraform, Ansible |
| 6XXXXXXX | ชื่อ นามสกุล | Kubernetes, Monitoring |

---

## 📌 ภาพรวมโปรเจค

### แอปพลิเคชัน
- **ชื่อ:** PM2.5 Thailand Monitor
- **ประเภท:** Full-Stack Web App (REST API + Static Frontend)
- **ภาษา / Framework:** Python FastAPI (Backend) · HTML/CSS/JavaScript (Frontend) · PostgreSQL (Database)
- **คำอธิบาย:** ระบบแสดงข้อมูลคุณภาพอากาศ PM2.5 ทั่วประเทศไทยแบบ Real-time โดยดึงข้อมูลจาก Air4Thai API (กรมควบคุมมลพิษ) คำนวณค่า AQI แสดงสถานะสถานีตรวจวัดทั่วประเทศ และรองรับการบันทึกสถานีโปรดลงฐานข้อมูล PostgreSQL

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
│   └── Dockerfile              # คำสั่งสร้าง Docker image สำหรับ backend
├── frontend/
│   ├── index.html              # Single-page UI แสดงแผนที่และข้อมูลสถานี PM2.5
│   ├── nginx.conf              # Nginx config สำหรับ serve frontend + reverse proxy ไป backend
│   └── Dockerfile              # คำสั่งสร้าง Docker image สำหรับ frontend (Nginx)
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

## ⚙️ สิ่งที่ต้องติดตั้งก่อน (Prerequisites)

ตรวจสอบให้แน่ใจว่าติดตั้งทุก tool ครบก่อนรันโปรเจค

| Tool | Version | หน้าที่ |
|------|---------|---------| 
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

## 🏃 วิธีรันโปรเจค (Quick Start)

### 1. Clone Repository
```bash
git clone https://github.com/10xkz/PM2.5-Thailand.git
cd PM2.5-Thailand
```

### 2. รันแอปด้วย Docker Compose (แนะนำ)
```bash
# รัน core services (db + backend + frontend)
docker compose up -d

# รัน core services + prometheus monitoring
docker compose --profile monitoring up -d
```

| Service | URL |
|---------|-----|
| Frontend (UI) | http://localhost:8080 |
| Backend (API docs) | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |

### 3. รัน Backend โดยตรง (ไม่ผ่าน Docker)
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs ที่ http://localhost:8000/docs
```

---

## 🔄 CI/CD Pipeline (Jenkins)

### ลำดับการทำงานของ Pipeline

```
Checkout ──▶ Build ──▶ Test ──▶ Docker Build ──▶ Push to Hub ──▶ Deploy
```

| Stage | คำอธิบาย |
|-------|----------|
| **Checkout** | ดึงโค้ดล่าสุดจาก GitHub ผ่าน `checkout scm` |
| **Build** | ตรวจ syntax `backend/main.py` ด้วย `py_compile` และตรวจไฟล์จำเป็น |
| **Test** | รัน unit test (echo ผ่าน) |
| **Docker Build** | build image `rubchek/pm25-backend` และ `rubchek/pm25-frontend` พร้อม tag ด้วย BUILD_NUMBER |
| **Push to Hub** | อัปโหลด image ขึ้น Docker Hub ด้วย credentials `docker-hub-credentials` |
| **Deploy** | รัน Terraform + Ansible → apply k8s manifests ทั้งหมดใน `k8s/` → rollout restart → health check |

### วิธีตั้งค่า Jenkins
1. ติดตั้ง Jenkins และเปิดที่ `http://localhost:8080`
2. ติดตั้ง plugin: **Git**, **Pipeline**, **Docker Pipeline**
3. เพิ่ม credentials สำหรับ Docker Hub (ชื่อ `docker-hub-credentials`)
4. สร้าง Pipeline job ใหม่ และชี้ไปที่ repository นี้
5. ตั้งค่า Webhook ใน GitHub:
   - ไปที่ **Settings → Webhooks → Add webhook**
   - Payload URL: `http://[jenkins-host]:8080/github-webhook/`
   - Content type: `application/json`
   - ติ๊ก trigger: **Just the push event**

---

## 🏗️ Infrastructure as Code

### Terraform — Provision Infrastructure
```bash
cd terraform
terraform init      # ดาวน์โหลด provider plugins (kreuzwerker/docker, hashicorp/local, hashicorp/tls)
terraform plan      # ตรวจสอบว่าจะสร้างอะไรบ้าง
terraform apply     # สร้าง resource จริง
```
> **สิ่งที่ Terraform สร้าง:** RSA SSH key pair (4096-bit) บันทึกเป็นไฟล์ `ansible_id_rsa` / `ansible_id_rsa.pub`, Docker network ชื่อ `terraform-pm25-net`, และ Docker container `ansible-target-node` จำลอง VM สำหรับ Ansible

### Ansible — Configure Environment
```bash
cd ansible
ansible-playbook -i inventory.ini playbook.yml
```
> **สิ่งที่ Ansible ทำ:** อัปเดต apt cache, ติดตั้ง curl/wget/git/ca-certificates, ติดตั้ง Docker Engine (ถ้าไม่ได้รันใน container), เพิ่ม ubuntu user เข้า docker group, สร้าง directory `/opt/pm25-monitor`

> ⚠️ **หมายเหตุ:** ใน pipeline จริง Jenkins จะเรียก Terraform และ Ansible อัตโนมัติในขั้นตอน Deploy ไม่ต้องรันด้วยมือ

---

## ☸️ Kubernetes Deployment

### Apply Manifests ด้วยตัวเอง
```bash
kubectl apply -R -f k8s/
```

### ตรวจสอบสถานะ
```bash
kubectl get pods -n jenkins
kubectl get svc  -n jenkins
```

### ผลลัพธ์ที่ควรจะได้
```
NAME                            READY   STATUS    RESTARTS   AGE
pm25-backend-xxxxxxxxx-xxxxx    1/1     Running   0          2m
pm25-frontend-xxxxxxxxx-yyyyy   1/1     Running   0          2m

NAME               TYPE       CLUSTER-IP     PORT(S)          AGE
pm25-frontend-svc  NodePort   10.96.xx.xxx   80:30080/TCP     2m
pm25-backend-svc   NodePort   10.96.xx.xxx   8000:30800/TCP   2m
```

### เข้าถึงแอปพลิเคชัน
```
Frontend UI  → http://localhost:30080
Backend API  → http://localhost:30800/docs
```

---

## 📊 Monitoring

### Prometheus — เก็บ Metrics
- ไฟล์ config: `prometheus/prometheus.yml`
- Scrape ทุก **15 วินาที**
- Target endpoint: `http://backend:8000/metrics` (prometheus-fastapi-instrumentator)

รัน Prometheus (ผ่าน Docker Compose):
```bash
docker compose --profile monitoring up -d prometheus
# เปิด UI ที่ http://localhost:9090
```

### Grafana — แสดง Dashboard
- Deploy บน Kubernetes ใน `k8s/04-monitoring/grafana/`
- Data source: Prometheus (`http://localhost:9090`)

วิธี import dashboard:
1. เปิด Grafana ที่ `http://localhost:3000`
2. ไปที่ **Dashboards → Import**
3. อัปโหลดไฟล์ dashboard json

### Panels ใน Dashboard

| Panel | Metric (PromQL) | แสดงข้อมูลอะไร |
|-------|-----------------|----------------|
| Request Rate | `rate(http_requests_total[1m])` | จำนวน request ต่อวินาที |
| Error Rate | `rate(http_requests_total{status=~"5.."}[1m])` | จำนวน error 5xx ต่อวินาที |
| Latency (p95) | `histogram_quantile(0.95, ...)` | response time ที่ percentile 95 |
| Pod Health | `up{job="pm25_backend"}` | service ขึ้นหรือล่ม (1/0) |

---

## 🌿 Branching Strategy

```
main        ──── โค้ดที่พร้อม production, protected branch
dev         ──── รวมโค้ดก่อน merge ขึ้น main
feature/*   ──── พัฒนา feature แต่ละอัน (เช่น feature/add-login)
```

| Branch | Protected | คำอธิบาย |
|--------|-----------|----------|
| `main` | ✅ | trigger pipeline อัตโนมัติเมื่อ merge |
| `dev` | ✅ | ทดสอบก่อน merge ขึ้น main |
| `feature/*` | ❌ | พัฒนาแยกกันแล้วค่อย merge เข้า dev |

---

## 🧪 API Endpoints

| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| `GET` | `/health` | Liveness probe — ตรวจว่า backend ยังรันอยู่ |
| `GET` | `/metrics` | Prometheus metrics endpoint |
| `GET` | `/api/locations` | ดึงข้อมูลสถานีตรวจวัด PM2.5 ทั่วประเทศไทยจาก Air4Thai |
| `GET` | `/api/measurements/{location_id}` | ดึงข้อมูลละเอียด (PM2.5, PM10, O3, CO, NO2, SO2, AQI) ของสถานีนั้น |
| `GET` | `/api/summary` | สรุปสถิติ PM2.5 ระดับประเทศ (avg, max, min, worst station) |
| `POST` | `/api/discover` | Trigger discovery refresh (Air4Thai mode: skipped) |
| `GET` | `/api/favorites` | ดึงรายการสถานีโปรดจาก PostgreSQL |
| `POST` | `/api/favorites` | บันทึกสถานีโปรดลง PostgreSQL |

---

## Database Schema
```sql
CREATE TABLE IF NOT EXISTS favorites (
  id SERIAL PRIMARY KEY,
  station_id TEXT,
  station_name TEXT NOT NULL,
  pm25_value NUMERIC,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```
---

## Backend response

###  sample `GET /api/summary`
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

### sample `GET /api/favorites`
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

## 🐛 ปัญหาที่พบบ่อย (Troubleshooting)

**Pods ค้างอยู่ที่ `Pending` ไม่ยอม Running**
```bash
kubectl describe pod [pod-name] -n jenkins
# ดูที่ Events: อาจเกิดจาก resource ไม่พอ หรือ image pull error
```

**Jenkins pipeline ล้มเหลวตอน Docker Build**
```bash
# ตรวจว่า Docker daemon รันอยู่
sudo systemctl start docker
# เพิ่ม jenkins user เข้า docker group
sudo usermod -aG docker jenkins
```

**Prometheus แสดง target เป็น DOWN**
```bash
# ตรวจว่าแอปเปิด /metrics ได้จริง
curl http://localhost:8000/metrics
# ตรวจ prometheus.yml ว่า host:port ตรงกับแอปจริง (backend:8000)
```

**Backend ต่อ PostgreSQL ไม่ได้**
```bash
# ตรวจสอบ environment variables
echo $DB_HOST $DB_NAME $DB_USER
# ค่า default: db / mydatabase / user / password
# ตรวจสอบ health ของ db container
docker compose ps
```

**Air4Thai API ไม่ตอบสนอง (503)**
```bash
# ทดสอบเรียก Air4Thai โดยตรง
curl "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php"
# ข้อมูลจะ cache ไว้ 30 นาที (CACHE_TTL_DATA = 1800s)
```

---

## 📚 เอกสารอ้างอิง

- [Jenkinsfile Declarative Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)
- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [Ansible Documentation](https://docs.ansible.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Markdown Guide](https://www.markdownguide.org/)
- [GitHub Markdown Syntax](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax)