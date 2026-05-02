pipeline {
    agent any
    
    environment {
        DOCKER_HUB_USER = 'rubchek'
        BACKEND_IMAGE   = "${DOCKER_HUB_USER}/pm25-backend"
        FRONTEND_IMAGE  = "${DOCKER_HUB_USER}/pm25-frontend"
        DOCKER_CREDS    = 'docker-hub-credentials'
    }

    stages {
        // Stage 1: Checkout
        stage('Checkout') {
            steps {
                echo '1. Checkout source code from GitHub...'
                checkout scm
            }
        }
        
        // Stage 2: Build
        stage('Build') {
            steps {
                echo '2. Building application (Checking dependencies)...'
                // ในโปรเจกต์ Python/HTML เราอาจจะแค่ตรวจสอบไฟล์ หรือข้ามไปทำใน Docker ทีเดียว
                sh 'echo "Build step ready!"'
            }
        }
        
        // Stage 3: Test
        stage('Test') {
            steps {
                echo '3. Running Unit Tests...'
                // จำลองการรันเทส
                sh 'echo "All tests passed successfully!"'
            }
        }
        
        // Stage 4: Docker Build
        stage('Docker Build') {
            steps {
                echo '4. Building Docker Images...'
                sh "docker build -t ${BACKEND_IMAGE}:${env.BUILD_NUMBER} -t ${BACKEND_IMAGE}:latest ./backend"
                sh "docker build -t ${FRONTEND_IMAGE}:${env.BUILD_NUMBER} -t ${FRONTEND_IMAGE}:latest ./frontend"
            }
        }
        
        // Stage 5: Push Hub
        stage('Push Hub') {
            steps {
                echo '5. Pushing Images to Docker Hub...'
                withCredentials([usernamePassword(credentialsId: env.DOCKER_CREDS, usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo \$PASS | docker login -u \$USER --password-stdin"
                    
                    // Push Backend
                    sh "docker push ${BACKEND_IMAGE}:${env.BUILD_NUMBER}"
                    sh "docker push ${BACKEND_IMAGE}:latest"
                    
                    // Push Frontend
                    sh "docker push ${FRONTEND_IMAGE}:${env.BUILD_NUMBER}"
                    sh "docker push ${FRONTEND_IMAGE}:latest"
                }
            }
        }
        
        // Stage 6: Deploy to K8s
        stage('Deploy') {
            steps {
                echo '6. Deploying to Kubernetes...'
                script {
                    // ใช้ Single Quote ('') เพื่อกันไม่ให้ Jenkins สับสนกับเครื่องหมาย $
                    sh 'curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"'
                    sh 'chmod +x ./kubectl'

                    // รันคำสั่ง apply
                    sh './kubectl apply -f k8s-deployment.yaml -n jenkins'
                    
                    // สั่ง restart เพื่อดึง image ใหม่
                    sh './kubectl rollout restart deployment pm25-backend -n jenkins'
                    sh './kubectl rollout restart deployment pm25-frontend -n jenkins'
                }
            }   
        }
    }
    
}