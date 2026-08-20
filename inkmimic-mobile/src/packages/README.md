# AI Core Integration (Mobile)

### `ai-core/`
This package connects the Inkmimic mobile app to the FastAPI Handwriting AI Model Backend (`api/server.py`).

- **`generateHandwrittenArtifact({ sampleAsset, prompt, inkColor, paper, signal })`**: Sends the text and attached handwriting photo to the Python diffusion generation model backend, returning a realistic handwritten image artifact.
- **`analyzeHandwritingStyle(sampleAsset, signal)`**: Analyzes stroke thickness, slant, and confidence of a sample handwriting photo.

### Backend Setup
Run the backend server:
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

In `.env`, configure the API endpoint (use your machine's LAN IP when testing on mobile devices):
```env
EXPO_PUBLIC_API_URL=http://<YOUR_LOCAL_IP>:8000
```

