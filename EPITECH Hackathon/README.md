# Relationship Extraction Tool

<img width="1600" height="852" alt="Image" src="https://github.com/user-attachments/assets/d4cbbf72-08c8-4870-93fc-c6ae76efc11f" />

로컬 Ollama를 사용하는 문서 관계 추출 MVP입니다.
This is an MVP for document relationship extraction using a local Ollama setup.

## 실행

프로젝트 루트의 `run.bat`을 더블클릭하세요.
Double-click the `run.bat` file in the project root to launch the application.

```text
C:\Users\qkdqk\OneDrive\Desktop\Hack\run.bat
```

실행하면 Ollama 서버를 시도해서 켜고, FastAPI 백엔드를 `http://127.0.0.1:8001`에서 실행한 뒤 `frontend/index.html`을 브라우저로 엽니다.
When the app starts, it will try to launch the Ollama server, run the FastAPI backend at `http://127.0.0.1:8001`, and open `frontend/index.html` in your browser.

Ollama가 없어도 간단한 fallback 추출로 그래프는 표시됩니다.
Even if Ollama is not available, the app will still display a graph using a simple fallback extraction method.

## Ollama 모델

기본 모델은 CPU에서도 비교적 빠른 `llama3.2:3b`입니다. 처음 한 번만 실행하세요.
The default model is `llama3.2:3b`, which is relatively fast even on CPU. Please run it once initially to download the model.

```powershell
ollama pull llama3.2:3b
```

다른 모델을 쓰려면 `backend/.env.example`을 참고해서 `.env`를 만들고 `OLLAMA_MODEL`을 바꾸면 됩니다.
To use a different model, refer to `backend/.env.example`, create a `.env` file, and change `OLLAMA_MODEL`.

## 분석 속도 조절

기본값은 입력을 최대 9,000자로 제한하고 최대 800토큰을 생성하며, 사용한 모델을 30분 동안 메모리에 유지합니다. 더 빠르게 하려면 `backend/.env`에서 `OLLAMA_NUM_PREDICT`와 `OLLAMA_DOCUMENT_CHAR_LIMIT`를 낮추세요. 긴 문서에서 더 자세한 결과가 필요하면 값을 높일 수 있습니다.
By default, the input is limited to 9,000 characters, up to 800 tokens are generated, and the selected model is cached in memory for 30 minutes. To make it faster, lower `OLLAMA_NUM_PREDICT` and `OLLAMA_DOCUMENT_CHAR_LIMIT` in `backend/.env`. If you need more detailed results for long documents, you can increase these values.

Intel 내장 GPU가 있는 현재 환경에서는 모델 레이어 16개를 GPU에 배치하여 CPU와 GPU를 함께 사용합니다. `OLLAMA_NUM_GPU_LAYERS=0`은 CPU 전용이며, 값이 클수록 GPU 비중이 높아집니다.
In the current environment with an Intel integrated GPU, 16 model layers are offloaded to the GPU so CPU and GPU are used together. Setting `OLLAMA_NUM_GPU_LAYERS=0` uses CPU only, while a larger value increases GPU usage.

## 구조

- `backend/`: API 서버
- `frontend/`: 순수 HTML/CSS/JS 화면
- `samples/`: 테스트 문서
- `run.bat`: 바로 실행 파일

- `backend/`: API server
- `frontend/`: Pure HTML/CSS/JS interface
- `samples/`: Sample test documents
- `run.bat`: One-click launcher
