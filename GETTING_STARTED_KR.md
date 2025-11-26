# Tech Recon 웹 애플리케이션 시작 가이드

> **🏠 로컬 환경 설치 가이드**
>
> 이 가이드는 Tech Recon 웹 애플리케이션을 **로컬 컴퓨터** (Windows, macOS, Linux)에서 처음부터 설치하고 실행하는 방법을 안내합니다.

## 사전 요구사항

로컬 시스템에 다음 항목들이 설치되어 있어야 합니다:

- **Python 3.12 이상** - [Python 다운로드](https://www.python.org/downloads/)
- **pip** (Python과 함께 설치됨) 또는 **UV 패키지 매니저** (빠른 설치를 위해 권장)
- **Git** (선택사항) - [Git 다운로드](https://git-scm.com/downloads)
- **AWS 계정** (Amazon Bedrock 접근 권한 필요)
- **AWS CLI** (자격 증명 설정 필요) - [AWS CLI 설치](https://aws.amazon.com/cli/)
- **Tavily API Key** (검색 기능용) - [API Key 받기](https://tavily.com)

## 빠른 시작 (요약)

경험 있는 사용자를 위한 빠른 설치:

```bash
# 1. 저장소 클론 및 이동
git clone https://github.com/aws-samples/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/01_tech_recon

# 2. 가상환경 설정 (UV 방식 - 권장)
```bash
cd setup
chmod +x ./create-uv-env.sh
./create-uv-env.sh tech-recon 3.12
cd ..
```

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 AWS 및 Tavily 자격 증명 입력
aws configure  # AWS 자격 증명 설정

# 4. 실행
./start_web.sh
# 또는: python web_app.py

# 5. 브라우저에서 접속
# http://localhost:5000
```

## 상세 설치 단계

### 1단계: 프로젝트 파일 받기

```bash
# GitHub에서 클론
git clone https://github.com/aws-samples/aws-ai-ml-workshop-kr.git
cd aws-ai-ml-workshop-kr/genai/aws-gen-ai-kr/20_applications/08_bedrock_manus/use_cases/01_tech_recon
```

### 2단계: 가상환경 생성

#### 옵션 A: UV 사용 (빠르고 권장됨)

```bash
# UV 설치 (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 또는 pip으로 설치
pip install uv

# 가상환경 생성
cd setup/
./create-uv-env.sh tech-recon 3.12
```

#### 옵션 B: Python venv + pip 사용

```bash
# 가상환경 생성
python3 -m venv .venv

# 가상환경 활성화
# macOS/Linux:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 의존성 설치
pip install --upgrade pip
pip install -r requirements_web.txt
```

### 3단계: 환경 변수 설정

```bash
# 예제 파일 복사
cp .env.example .env

# .env 파일 편집
nano .env  # 또는 vim, code 등
```

`.env` 파일에 다음 내용을 설정하세요:

```bash
# AWS 설정
AWS_REGION=us-west-2
AWS_DEFAULT_REGION=us-west-2
AWS_ACCOUNT_ID=your-account-id-here

# Bedrock 모델 설정
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Tavily 검색 API 설정
TAVILY_API_KEY=your-tavily-api-key-here
TAVILY_MAX_RESULTS=5
```

**중요:** 다음 항목들을 실제 값으로 변경하세요:
- `your-account-id-here` - AWS 계정 ID
- `your-tavily-api-key-here` - Tavily API 키

### 4단계: AWS 자격 증명 설정

```bash
# AWS CLI 설정
aws configure

# 입력 항목:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (예: us-west-2)
# - Default output format (예: json)

# 설정 확인
aws sts get-caller-identity
```

### 5단계: 애플리케이션 실행

```bash
# 프로젝트 루트 디렉토리로 이동
cd /path/to/01_tech_recon

# 실행 스크립트 사용
./start_web.sh

# 또는 수동 실행
source .venv/bin/activate  # 가상환경 활성화
python web_app.py
```

### 6단계: 브라우저에서 접속

브라우저를 열고 다음 주소로 접속:
```
http://localhost:5000
```

## 주요 기능

- **실시간 로그 스트리밍**: 실행 과정을 실시간으로 확인
- **Part1/Part2 실행**: 웹 UI에서 버튼 클릭으로 실행
- **파일 다운로드**: 생성된 파일을 개별 또는 ZIP으로 다운로드
- **시각적 모니터링**: 실행 상태와 통계를 한눈에 확인

## 문제 해결

### 포트 5000이 이미 사용 중

```bash
# macOS/Linux
lsof -i :5000
kill -9 <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### AWS 자격 증명 오류

```bash
# AWS CLI 재설정
aws configure

# 자격 증명 파일 확인
cat ~/.aws/credentials  # macOS/Linux
type %USERPROFILE%\.aws\credentials  # Windows
```

### 패키지 설치 오류

```bash
# pip 업그레이드 후 재설치
pip install --upgrade pip
pip install -r requirements_web.txt --force-reinstall
```

### Bedrock 접근 거부 오류

1. AWS 콘솔에서 Bedrock 모델 접근 권한 활성화:
   - AWS Console → Bedrock → Model Access
   - Claude 모델 활성화 (Haiku, Sonnet 등)

2. IAM 권한 확인:
   - `bedrock:InvokeModel` 권한 필요
   - `bedrock:InvokeModelWithResponseStream` 권한 필요

## 시스템 요구사항

### 최소 요구사항
- **OS**: macOS 10.15+, Windows 10+, Ubuntu 20.04+
- **CPU**: 2코어
- **RAM**: 4GB
- **Python**: 3.12 이상
- **네트워크**: 안정적인 인터넷 연결

### 권장 사양
- **OS**: macOS 12+, Windows 11, Ubuntu 22.04+
- **CPU**: 4코어 이상
- **RAM**: 8GB 이상
- **Python**: 3.12+
- **네트워크**: 광대역 인터넷 (10Mbps 이상)

## 자주 묻는 질문 (FAQ)

### Q: Windows에서 실행할 수 있나요?
**A:** 네! Windows 10/11에서 정상 작동합니다. PowerShell이나 Command Prompt를 사용하세요.

### Q: SageMaker가 필요한가요?
**A:** 아니요! 이 가이드는 로컬 컴퓨터에서 실행하는 방법입니다. Python, AWS 자격 증명, 인터넷 연결만 있으면 됩니다.

### Q: 어떤 AWS 서비스가 필요한가요?
**A:** Amazon Bedrock (특히 Claude 모델) 접근 권한이 필요합니다. AWS 콘솔에서 모델 접근을 활성화하세요.

### Q: 비용이 얼마나 드나요?
**A:** 사용량에 따라 다릅니다:
- **AWS Bedrock**: 토큰당 과금 (모델별로 다름)
- **Tavily API**: 무료 티어 제공, 이후 사용량 기반 과금
- **로컬 컴퓨팅**: 무료 (자신의 컴퓨터에서 실행)

### Q: 다른 AI 모델을 사용할 수 있나요?
**A:** 네! `.env` 파일에서 `BEDROCK_MODEL_ID`를 변경하면 됩니다 (예: Claude Sonnet, Haiku, Nova 등).

### Q: 서버를 어떻게 중지하나요?
**A:** 서버가 실행 중인 터미널에서 `Ctrl+C`를 누르세요.

### Q: 휴대폰/태블릿에서 접속할 수 있나요?
**A:** 네! 같은 로컬 네트워크에 있다면:
1. 컴퓨터의 로컬 IP 주소 확인
2. 모바일 브라우저에서 `http://YOUR-LOCAL-IP:5000` 접속

## 보안 주의사항

1. **`.env` 파일을 절대 커밋하지 마세요**
   ```bash
   echo ".env" >> .gitignore
   ```

2. **AWS 자격 증명 보호**
   - AWS Access Key를 공유하지 마세요
   - 가능하면 임시 자격 증명 사용
   - 정기적으로 자격 증명 교체

3. **로컬 네트워크만 접근하도록 설정** (선택사항)
   ```python
   # web_app.py에서
   socketio.run(app, host='127.0.0.1', port=5000, debug=False)
   ```

## 도움말

문제가 발생하면:

1. 위의 **문제 해결** 섹션 확인
2. [GitHub Issues](https://github.com/aws-samples/aws-ai-ml-workshop-kr/issues) 검색
3. [AWS Bedrock 문서](https://docs.aws.amazon.com/bedrock/) 참조
4. 상세한 오류 메시지와 함께 새 이슈 생성

## 추가 자료

- **상세 영문 가이드**: [GETTING_STARTED.md](GETTING_STARTED.md)
- **웹 기능 문서**: [WEB_README.md](WEB_README.md)
- **프로젝트 개요**: [README.md](README.md)
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **Tavily API**: https://tavily.com
- **Flask 문서**: https://flask.palletsprojects.com/

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
