FOODI 배포 가이드
개요
이 문서는 FOODI 프로젝트를 다양한 환경에 배포하는 방법을 설명합니다. 
개발 환경부터 프로덕션 환경까지의 배포 프로세스를 단계별로 안내합니다.
📋 사전 요구사항
시스템 요구사항

운영체제: Linux (Ubuntu 20.04+ 권장), macOS, Windows
Python: 3.8 이상
메모리: 최소 2GB, 권장 4GB 이상
디스크: 최소 5GB 여유 공간
네트워크: HTTP/HTTPS 포트 접근 가능

필수 소프트웨어

Git
Python 3.8+
pip (Python 패키지 관리자)
SQLite 3
웹 서버 (Nginx, Apache 등)


🔧 로컬 개발 환경 설정
1. 프로젝트 클론
bashgit clone https://github.com/your-username/foodi-chatbot.git
cd foodi-chatbot
2. 가상 환경 생성 및 활성화
bash# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
3. 의존성 설치
bashpip install -r requirements.txt
4. 환경 변수 설정
bash# .env 파일 생성 (.env.example을 참고)
cp .env.example .env

# .env 파일 편집
nano .env
.env 파일 예시:
env# Flask 설정
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Google Maps API
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# 데이터베이스
DATABASE_PATH=data/database/foodi.db

# 로깅
LOG_LEVEL=INFO
LOG_DIR=logs
5. 데이터베이스 초기화
bashpython scripts/init_database.py
6. 샘플 데이터 로드
bashpython scripts/load_restaurant_data.py
7. 개발 서버 실행
bashpython run.py
서버가 성공적으로 시작되면 http://localhost:5000에서 접근 가능합니다.

🐳 Docker를 이용한 배포
1. Dockerfile 작성
프로젝트 루트에 Dockerfile 생성:
dockerfileFROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 패키지 설치
RUN apt-get update && apt-get install -y \
		gcc \
		sqlite3 \
		&& rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉토리 생성
RUN mkdir -p data/database logs

# 데이터베이스 초기화
RUN python scripts/init_database.py

# 포트 노출
EXPOSE 5000

# 애플리케이션 실행
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]
2. docker-compose.yml 작성
yamlversion: '3.8'

services:
	foodi-app:
		build: .
		ports:
			- "5000:5000"
		environment:
			- FLASK_ENV=production
			- SECRET_KEY=${SECRET_KEY}
			- OPENAI_API_KEY=${OPENAI_API_KEY}
			- GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
		volumes:
			- ./data:/app/data
			- ./logs:/app/logs
		restart: unless-stopped
		
	nginx:
		image: nginx:alpine
		ports:
			- "80:80"
			- "443:443"
		volumes:
			- ./nginx.conf:/etc/nginx/nginx.conf
			- ./ssl:/etc/nginx/ssl
		depends_on:
			- foodi-app
		restart: unless-stopped
3. Docker 빌드 및 실행
bash# 이미지 빌드
docker build -t foodi-app .

# 컨테이너 실행
docker run -d \
	--name foodi \
	-p 5000:5000 \
	-v $(pwd)/data:/app/data \
	-v $(pwd)/logs:/app/logs \
	--env-file .env \
	foodi-app

# 또는 docker-compose 사용
docker-compose up -d

🌐 클라우드 배포
AWS EC2 배포
1. EC2 인스턴스 생성

인스턴스 타입: t3.small 이상 권장
운영체제: Ubuntu 20.04 LTS
보안 그룹: HTTP (80), HTTPS (443), SSH (22) 포트 개방

2. 서버 초기 설정
bash# 서버 접속
ssh -i your-key.pem ubuntu@your-server-ip

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y python3 python3-pip python3-venv git nginx sqlite3

# Python 심볼릭 링크 생성
sudo ln -sf /usr/bin/python3 /usr/bin/python
3. 애플리케이션 배포
bash# 프로젝트 클론
git clone https://github.com/your-username/foodi-chatbot.git
cd foodi-chatbot

# 가상 환경 설정
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
pip install gunicorn

# 환경 변수 설정
cp .env.example .env
nano .env

# 데이터베이스 초기화
python scripts/init_database.py
python scripts/load_restaurant_data.py
4. Gunicorn 설정
bash# Gunicorn 서비스 파일 생성
sudo nano /etc/systemd/system/foodi.service
ini[Unit]
Description=FOODI Flask App
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/foodi-chatbot
Environment="PATH=/home/ubuntu/foodi-chatbot/venv/bin"
EnvironmentFile=/home/ubuntu/foodi-chatbot/.env
ExecStart=/home/ubuntu/foodi-chatbot/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
bash# 서비스 활성화 및 시작
sudo systemctl daemon-reload
sudo systemctl enable foodi
sudo systemctl start foodi
sudo systemctl status foodi
5. Nginx 설정
bash# Nginx 설정 파일 생성
sudo nano /etc/nginx/sites-available/foodi
nginxserver {
		listen 80;
		server_name your-domain.com www.your-domain.com;

		location / {
				proxy_pass http://127.0.0.1:5000;
				proxy_set_header Host $host;
				proxy_set_header X-Real-IP $remote_addr;
				proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
				proxy_set_header X-Forwarded-Proto $scheme;
		}

		location /static {
				alias /home/ubuntu/foodi-chatbot/static;
				expires 1y;
				add_header Cache-Control "public, immutable";
		}
}
bash# 설정 파일 활성화
sudo ln -s /etc/nginx/sites-available/foodi /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
Google Cloud Platform (GCP) 배포
1. App Engine 배포
app.yaml 파일 생성:
yamlruntime: python39

env_variables:
	SECRET_KEY: your-secret-key
	OPENAI_API_KEY: your-openai-api-key
	GOOGLE_MAPS_API_KEY: your-google-maps-api-key

automatic_scaling:
	min_instances: 1
	max_instances: 10
배포 명령:
bash# gcloud CLI 설치 및 로그인
gcloud auth login
gcloud config set project your-project-id

# 배포
gcloud app deploy
2. Compute Engine 배포
EC2와 유사한 과정으로 진행하되, 방화벽 규칙 설정:
bash# HTTP/HTTPS 트래픽 허용
gcloud compute firewall-rules create allow-http --allow tcp:80
gcloud compute firewall-rules create allow-https --allow tcp:443

🔒 SSL/HTTPS 설정
Let's Encrypt를 이용한 무료 SSL
bash# Certbot 설치
sudo apt install certbot python3-certbot-nginx

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
# 0 12 * * * /usr/bin/certbot renew --quiet
수동 SSL 인증서 설정
nginxserver {
		listen 443 ssl;
		server_name your-domain.com;

		ssl_certificate /path/to/your/certificate.crt;
		ssl_certificate_key /path/to/your/private.key;
		ssl_protocols TLSv1.2 TLSv1.3;
		ssl_ciphers HIGH:!aNULL:!MD5;

		location / {
				proxy_pass http://127.0.0.1:5000;
				proxy_set_header Host $host;
				proxy_set_header X-Real-IP $remote_addr;
				proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
				proxy_set_header X-Forwarded-Proto https;
		}
}

server {
		listen 80;
		server_name your-domain.com;
		return 301 https://$server_name$request_uri;
}

📊 모니터링 및 로깅
1. 로그 관리
bash# 로그 로테이션 설정
sudo nano /etc/logrotate.d/foodi
/home/ubuntu/foodi-chatbot/logs/*.log {
		daily
		missingok
		rotate 52
		compress
		delaycompress
		notifempty
		create 644 ubuntu ubuntu
}
2. 시스템 모니터링
bash# htop 설치 (시스템 리소스 모니터링)
sudo apt install htop

# 서비스 상태 확인
sudo systemctl status foodi
sudo systemctl status nginx

# 로그 확인
sudo journalctl -u foodi -f
tail -f logs/foodi.log
3. 애플리케이션 모니터링
python# health check 엔드포인트 추가
@app.route('/health')
def health_check():
		return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

🔄 배포 자동화
GitHub Actions를 이용한 CI/CD
.github/workflows/deploy.yml:
yamlname: Deploy to Production

on:
	push:
		branches: [ main ]

jobs:
	deploy:
		runs-on: ubuntu-latest
		
		steps:
		- uses: actions/checkout@v3
		
		- name: Setup Python
			uses: actions/setup-python@v3
			with:
				python-version: '3.9'
		
		- name: Install dependencies
			run: |
				pip install -r requirements.txt
		
		- name: Run tests
			run: |
				python -m pytest tests/
		
		- name: Deploy to server
			uses: appleboy/ssh-action@v0.1.5
			with:
				host: ${{ secrets.HOST }}
				username: ${{ secrets.USERNAME }}
				key: ${{ secrets.SSH_KEY }}
				script: |
					cd /home/ubuntu/foodi-chatbot
					git pull origin main
					source venv/bin/activate
					pip install -r requirements.txt
					python scripts/init_database.py
					sudo systemctl restart foodi

📋 체크리스트
배포 전 확인사항

	환경 변수 설정 완료
	API 키 발급 및 설정
	데이터베이스 초기화
	방화벽 설정
	SSL 인증서 설정
	도메인 연결

배포 후 확인사항

	웹사이트 정상 접근 확인
	API 엔드포인트 동작 확인
	데이터베이스 연결 확인
	로그 생성 확인
	성능 테스트
	백업 시스템 동작 확인


🚨 트러블슈팅
일반적인 문제와 해결방법
1. 서버가 시작되지 않는 경우
bash# 로그 확인
sudo journalctl -u foodi -n 50

# 포트 사용 확인
sudo netstat -tlnp | grep :5000

# 가상 환경 확인
which python
pip list
2. 데이터베이스 연결 오류
bash# 데이터베이스 파일 권한 확인
ls -la data/database/

# 디렉토리 권한 수정
sudo chown -R ubuntu:ubuntu data/
sudo chmod -R 755 data/
3. Nginx 설정 오류
bash# 설정 파일 검증
sudo nginx -t

# 오류 로그 확인
sudo tail -f /var/log/nginx/error.log
4. SSL 인증서 문제
bash# 인증서 유효성 확인
openssl x509 -in /path/to/cert.pem -text -noout

# Let's Encrypt 갱신
sudo certbot renew --dry-run

📞 지원 및 문의
배포 과정에서 문제가 발생하면:

로그 파일 확인
GitHub Issues에 문제 보고
문서의 트러블슈팅 섹션 참고
커뮤니티 포럼에서 도움 요청


배포 성공을 위한 팁:

단계별로 천천히 진행하세요
각 단계마다 테스트를 수행하세요
백업을 정기적으로 생성하세요
보안 업데이트를 정기적으로 적용하세요