terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5.1"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0.5"
    }
  }
}

provider "docker" {
  # เชื่อมต่อกับ Docker Daemon บนเครื่องคุณเอง (Local)
  # สำหรับ WSL/Windows ปกติ docker จะ expose ผ่าน pipe นี้
  # หรือสามารถละไว้ถ้ารัน terraform ใน WSL เลยมันจะหา sock เจอเอง
}

# สร้าง SSH key สำหรับให้ Ansible เข้าเครื่องแบบ SSH (จำลองเหมือน VM จริง)
resource "tls_private_key" "ansible" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "ansible_private_key" {
  filename        = "${path.module}/ansible_id_rsa"
  content         = tls_private_key.ansible.private_key_pem
  file_permission = "0600"
}

resource "local_file" "ansible_public_key" {
  filename        = "${path.module}/ansible_id_rsa.pub"
  content         = tls_private_key.ansible.public_key_openssh
  file_permission = "0644"
}

resource "docker_image" "ubuntu" {
  name         = "ubuntu:20.04"
  keep_locally = true
}

resource "docker_network" "pm25_net" {
  name = "terraform-pm25-net"
}

resource "docker_container" "pm25_dummy_server" {
  name  = "ansible-target-node"
  image = "my-pm25-target:latest"

  env = [
    "SSH_PUB_KEY=${tls_private_key.ansible.public_key_openssh}",
    "DEBIAN_FRONTEND=noninteractive",
  ]

  # ติดตั้ง SSH และสร้างผู้ใช้ ubuntu เพื่อจำลอง VM จริง
  command = [
    "/bin/bash", "-c",
    "useradd -m -s /bin/bash ubuntu || true; mkdir -p /home/ubuntu/.ssh; echo \"$SSH_PUB_KEY\" > /home/ubuntu/.ssh/authorized_keys; chown -R ubuntu:ubuntu /home/ubuntu/.ssh; chmod 700 /home/ubuntu/.ssh; chmod 600 /home/ubuntu/.ssh/authorized_keys; echo \"ubuntu ALL=(ALL) NOPASSWD:ALL\" >/etc/sudoers.d/ubuntu; /usr/sbin/sshd -D"
  ]

  networks_advanced {
    name = docker_network.pm25_net.name
  }

  ports {
    internal = 22
    external = 2222
  }
}