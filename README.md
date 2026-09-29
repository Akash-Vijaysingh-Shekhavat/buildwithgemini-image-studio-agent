# Creative Visionary — AI Image Studio Agent

![Creative Visionary Demo](https://storage.googleapis.com/image-studio-gallery-qwiklabs-gcp-01-832d146ced4c/demo.gif)

An intelligent conversational AI agent that assists digital artists, designers, and creators in brainstorming, generating, cataloging, and refining custom visual artwork, video teasers, and art concepts.

Built with Google's **Agent Development Kit (ADK)** and deployed on **Vertex AI Agent Engine**, Creative Visionary combines long-term user memory, database-backed art cataloging, Google Cloud Storage asset hosting, multi-modal image & video generation, and rich **A2UI** visual card rendering.

---

## 🚀 Wired Features & Google Cloud Integrations

The capabilities below are directly implemented and wired into the codebase (`app/agent.py` and `app/tools.py`):

### 🧠 Cross-Session Memory (Vertex AI Memory Bank)
* **Vertex AI Memory Bank Service**: Persists user facts, visual art preferences (e.g., favorite color palettes, preferred aspect ratios, cyberpunk or watercolor art styles), and brand constraints across separate chat sessions using `VertexAiMemoryBankService`.
* **PreloadMemoryTool & Callbacks**: Uses `PreloadMemoryTool` to inject past user memories into the conversation context at turn start and `generate_memories_callback` to store new facts after each turn.

### 🖼️ Multimodal AI Image & Video Generation
* **Gemini Imagen 3 (`imagen-3.0-generate-002`)**: Generates high-resolution digital artwork assets based on user prompt descriptions, custom styles, and aspect ratio parameters.
* **Google Omni Video Model (`gemini-omni-flash-preview` / `veo-3.1-generate-001`)**: Generates short animated video concepts and teasers using Vertex AI `generate_videos`. Saves MP4 bytes to ADK artifacts via `tool_context.save_artifact` for display in the ADK Web Playground.

### 🗄️ Database & Public Cloud Storage
* **Google Cloud Firestore**: Persists artwork gallery metadata documents (title, prompt, style tags, aspect ratio, public URL, creation timestamp) in GCP Firestore (`list_artworks`, `get_artwork_details`, `save_artwork`).
* **Google Cloud Storage (GCS)**: Uploads generated image and video byte streams directly to a public Cloud Storage bucket without local disk caching, returning permanent `https://storage.googleapis.com/...` asset URLs.

### 🏛️ External API Integration (The Met Museum)
* **The Metropolitan Museum of Art API**: Integrates public search (`search_museum_artworks`) over 470,000+ historical masterworks to allow artists to pull inspiration from real-world art history.

### 🎨 A2UI (Agent-to-UI Protocol v0.8)
* **Native Visual Cards**: Converts agent responses into A2UI basic catalog cards (Card, Column, Row, Text, Image) via `after_model_callback` (`a2ui_callback`), rendering live preview images and gallery cards directly inside the UI.

### 💻 Code Execution Sandbox
* **Agent Engine Sandbox**: Executes Python calculations safely in the `AgentEngineSandboxCodeExecutor` for aspect ratio math, metadata processing, and prompt matrix variations.

---

## 🛠️ Project Structure

```
.
├── demo.gif                   # Inline looping demo recording
├── agents-cli-manifest.yaml   # Manifest for agents-cli deployment (acli 1.1.0)
├── pyproject.toml             # Python package dependencies & ADK setup
├── app/
│   ├── __init__.py
│   ├── agent.py               # Main ADK root agent configuration & callbacks
│   ├── tools.py               # Firestore, GCS, Imagen, Omni Video, & Met Museum tools
│   └── a2ui_utils.py          # A2UI system prompt & model response interceptor
└── frontend/
    ├── app.py                 # FastAPI proxy forwarding A2A requests to Agent Engine
    ├── Dockerfile             # Container definition for Cloud Run deployment
    └── static/
        └── index.html         # Plain-text + A2UI mini-renderer chat interface
```

---

## 💻 Local Setup & Execution Instructions

### Prerequisites
* Python 3.10+
* `uv` or `pip` package manager
* Google Cloud SDK (`gcloud`) with application default credentials configured (`gcloud auth application-default login`)

### 1. Install Dependencies
Initialize virtual environment and install the required dependencies:
```bash
uv sync
```

### 2. Run the Agent Development UI (ADK Web)
To test the agent locally using the ADK Web Playground with full memory and A2UI card rendering:
```bash
adk web app:app
```
Then open your browser to the local URL displayed by the CLI output.

### 3. Run the Custom FastAPI Proxy & Chat Frontend
To run the standalone FastAPI proxy and custom chat UI locally:
```bash
python -m uvicorn frontend.app:app --host 0.0.0.0 --port 8080
```

---

## ☁️ Deployment Commands

### Deploy Agent Runtime to Vertex AI Agent Engine
```bash
agents-cli deploy agent-runtime
```

### Deploy Custom Frontend to Cloud Run
```bash
gcloud run deploy image-studio-frontend \
  --source ./frontend \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_DIRECTORY=app,AGENT_ENGINE_RESOURCE_NAME=projects/YOUR_PROJECT_NUMBER/locations/us-east1/reasoningEngines/YOUR_ENGINE_ID
```
