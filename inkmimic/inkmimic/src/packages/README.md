# AI Core Integration

### `ai-core/`
This package connects Inkmimic to the FastAPI Handwriting AI Model Backend (`api/server.py`).

- **`generateHandwrittenArtifact({ sampleFile, prompt, inkColor, paper, signal })`**: Sends the text and optional sample handwriting image to the Python diffusion generation model backend, returning a realistic handwritten image artifact.
- **`analyzeHandwritingStyle(sampleFile, signal)`**: Analyzes stroke thickness, slant, and confidence of a sample handwriting image.

### Backend Setup
Run the backend server:
```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

In `.env`, configure the API endpoint if running remotely:
```env
VITE_API_URL=http://localhost:8000
```

