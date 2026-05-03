terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0.1"
    }
  }
}

provider "docker" {
  # เชื่อมต่อกับ Docker Daemon บนเครื่องคุณเอง (Local)
  # สำหรับ WSL/Windows ปกติ docker จะ expose ผ่าน pipe นี้
  # หรือสามารถละไว้ถ้ารัน terraform ใน WSL เลยมันจะหา sock เจอเอง
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
  image = docker_image.ubuntu.image_id

  command = ["tail", "-f", "/dev/null"]

  networks_advanced {
    name = docker_network.pm25_net.name
  }

  ports {
    internal = 22
    external = 2222
  }
}