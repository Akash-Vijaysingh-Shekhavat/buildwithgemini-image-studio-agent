# Firestore, Image Generation, Museum, Maps & Studio Artifact API tools for Image Studio Agent
import uuid
import datetime
import json
import os
import time
import urllib.request
import urllib.parse
from google.cloud import firestore, storage
from google import genai
from google.genai import types
from google.adk.tools import ToolContext

# CRITICAL: Hardcoded project ID & GCS bucket string required for Agent Platform deployment
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-832d146ced4c"
COLLECTION_NAME = "artworks"
GCS_BUCKET_NAME = "image-studio-gallery-qwiklabs-gcp-01-832d146ced4c"


def _load_env_if_needed():
    """Helper to ensure local .env file variables are loaded into os.environ."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded GCP project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)


def list_artworks(style: str | None = None) -> list[dict]:
    """Lists artworks from the gallery collection in Firestore.

    Args:
        style: Optional filter by art style (e.g. 'cyberpunk', 'watercolor', 'vector_minimalist').

    Returns:
        A list of artwork dictionaries containing title, prompt, style, aspect_ratio, and tags.
    """
    db = get_firestore_client()
    collection_ref = db.collection(COLLECTION_NAME)

    if style:
        query = collection_ref.where("style", "==", style.lower().strip())
        docs = query.stream()
    else:
        docs = collection_ref.stream()

    artworks = []
    for doc in docs:
        artworks.append(doc.to_dict())

    return artworks


def get_artwork_details(artwork_id: str) -> dict:
    """Retrieves full details for a specific artwork from Firestore.

    Args:
        artwork_id: The document ID of the artwork (e.g., 'art_101').

    Returns:
        A dictionary containing the artwork fields, or an error message dict if not found.
    """
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_NAME).document(artwork_id)
    doc = doc_ref.get()

    if doc.exists:
        return doc.to_dict()
    return {"error": f"Artwork with ID '{artwork_id}' not found."}


def save_artwork(
    title: str,
    prompt: str,
    style: str,
    aspect_ratio: str = "1:1",
    tags: list[str] | None = None,
) -> dict:
    """Saves a new artwork metadata document into the Firestore gallery collection.

    Args:
        title: Title of the artwork.
        prompt: Detailed generation prompt used for the artwork.
        style: Visual art style (e.g. 'cyberpunk', 'watercolor', 'synthwave', 'vector_minimalist').
        aspect_ratio: Target aspect ratio (e.g. '1:1', '16:9', '9:16').
        tags: Optional list of descriptive keywords or tags.

    Returns:
        A dictionary confirming the newly created artwork record.
    """
    db = get_firestore_client()
    doc_id = f"art_{uuid.uuid4().hex[:6]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    artwork_data = {
        "id": doc_id,
        "title": title,
        "prompt": prompt,
        "style": style.lower().strip(),
        "aspect_ratio": aspect_ratio,
        "tags": tags or [style.lower().strip()],
        "created_at": now_iso,
    }

    db.collection(COLLECTION_NAME).document(doc_id).set(artwork_data)
    return {"status": "success", "message": f"Artwork '{title}' saved with ID {doc_id}", "artwork": artwork_data}


def generate_image_asset(prompt: str, style: str = "digital art", aspect_ratio: str = "1:1") -> dict:
    """Generates a real AI image asset, uploads it to Cloud Storage, and saves it into the gallery.

    Args:
        prompt: Detailed prompt description of the image to generate.
        style: Visual art style (e.g., 'cyberpunk', 'watercolor', 'synthwave', 'minimalist').
        aspect_ratio: Target aspect ratio (e.g., '1:1', '16:9', '9:16').

    Returns:
        A dictionary containing the generated image public URL, artwork ID, and saved metadata.
    """
    genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="us-central1")
    full_prompt = f"Generate a high quality {style} image: {prompt}"

    response = genai_client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=full_prompt,
    )

    image_bytes = None
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break

    if not image_bytes:
        return {"status": "error", "message": "Failed to generate image content from model."}

    # Upload PNG to Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    file_id = f"art_{uuid.uuid4().hex[:6]}"
    filename = f"{file_id}.png"
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type="image/png")

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    # Save metadata & URL to Firestore
    title = f"{style.title()} Concept: {prompt[:30]}"
    db = get_firestore_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    artwork_data = {
        "id": file_id,
        "title": title,
        "prompt": prompt,
        "style": style.lower().strip(),
        "aspect_ratio": aspect_ratio,
        "image_url": public_url,
        "tags": [style.lower().strip(), "ai_generated"],
        "created_at": now_iso,
    }

    db.collection(COLLECTION_NAME).document(file_id).set(artwork_data)

    return {
        "status": "success",
        "message": f"Successfully generated image and saved to gallery as {file_id}",
        "image_url": public_url,
        "artwork": artwork_data,
    }


async def generate_studio_image(
    prompt: str, style: str = "digital art", tool_context: ToolContext | None = None
) -> dict:
    """Generates an image using gemini-3.1-flash-lite-image in the global region, saves it as an ADK artifact, and uploads to GCS.

    Args:
        prompt: Detailed description of the image to generate.
        style: Art style for the generated image.
        tool_context: ADK ToolContext injected by the agent runtime.

    Returns:
        A dictionary containing the image public HTTPS URL, filename, and status.
    """
    genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    full_prompt = f"Generate a high quality {style} image: {prompt}"

    response = genai_client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=full_prompt,
    )

    image_bytes = None
    mime_type = "image/jpeg"
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        return {"status": "error", "message": "Failed to generate image bytes from model."}

    ext = "png" if "png" in mime_type else "jpg"
    file_id = f"studio_{uuid.uuid4().hex[:6]}"
    filename = f"{file_id}.{ext}"

    # (1) Save artifact with tool_context for Playground Artifacts panel
    if tool_context is not None:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as e:
            print(f"Warning: Failed to save artifact via tool_context: {e}")

    # (2) Upload same image bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    # Record in Firestore gallery
    db = get_firestore_client()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    artwork_data = {
        "id": file_id,
        "title": f"{style.title()} Studio: {prompt[:30]}",
        "prompt": prompt,
        "style": style.lower().strip(),
        "image_url": public_url,
        "created_at": now_iso,
    }
    db.collection(COLLECTION_NAME).document(file_id).set(artwork_data)

    return {
        "status": "success",
        "message": f"Successfully generated studio image asset {filename}",
        "image_url": public_url,
        "filename": filename,
    }


def search_museum_artworks(query: str) -> dict:
    """Searches The Metropolitan Museum of Art collection API for historic artwork reference and inspiration.

    Args:
        query: Search topic, artist, or movement (e.g., 'monet', 'van gogh', 'japanese print', 'impressionism').

    Returns:
        A dictionary containing real museum masterwork titles, artist names, dates, mediums, and image links.
    """
    _load_env_if_needed()
    api_key = os.getenv("MET_API_KEY", "")
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://collectionapi.metmuseum.org/public/collection/v1/search?q={encoded_query}&hasImages=true"

    try:
        headers = {"User-Agent": "AntigravityAgent/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        req = urllib.request.Request(search_url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            search_data = json.loads(response.read().decode())

        object_ids = search_data.get("objectIDs") or []
        artworks = []

        for obj_id in object_ids[:3]:  # Top 3 matching items
            obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"
            try:
                obj_req = urllib.request.Request(obj_url, headers=headers)
                with urllib.request.urlopen(obj_req, timeout=5) as obj_res:
                    obj = json.loads(obj_res.read().decode())
                    artworks.append({
                        "object_id": obj_id,
                        "title": obj.get("title"),
                        "artist": obj.get("artistDisplayName") or "Unknown Artist",
                        "culture": obj.get("culture") or "Various",
                        "medium": obj.get("medium") or "Mixed",
                        "object_date": obj.get("objectDate") or "",
                        "primary_image": obj.get("primaryImageSmall") or obj.get("primaryImage") or "",
                    })
            except Exception:
                continue

        return {
            "query": query,
            "total_found": search_data.get("total", 0),
            "museum_artworks": artworks,
        }
    except Exception as e:
        return {"error": f"Failed to fetch museum artworks: {str(e)}"}


async def generate_studio_video(
    prompt: str, tool_context: ToolContext | None = None
) -> dict:
    """Generates a short animated video concept or teaser for a studio item using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Do two things with the generated video:
    (1) Saves it as an ADK artifact with tool_context.save_artifact so it appears in Playground Artifacts panel.
    (2) Uploads the video bytes to the public Cloud Storage bucket and returns its public HTTPS URL.

    Args:
        prompt: Detailed description of the short video animation concept to generate.
        tool_context: ADK ToolContext injected by the agent runtime.

    Returns:
        A dictionary containing the video public HTTPS URL, filename, and generation status.
    """
    try:
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
        operation = genai_client.models.generate_videos(
            model="gemini-omni-flash-preview",
            prompt=prompt,
        )
    except Exception as e:
        print(f"Warning: Omni video generation on global endpoint failed ({e}), trying fallback in us-central1...")
        genai_client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="us-central1")
        try:
            operation = genai_client.models.generate_videos(
                model="gemini-omni-flash-preview",
                prompt=prompt,
            )
        except Exception as e2:
            print(f"Warning: Omni video model in us-central1 failed ({e2}), falling back to veo-3.1-generate-001...")
            operation = genai_client.models.generate_videos(
                model="veo-3.1-generate-001",
                prompt=prompt,
            )

    while not operation.done:
        time.sleep(3)
        operation = genai_client.operations.get(operation)

    video_bytes = None
    mime_type = "video/mp4"

    if hasattr(operation.response, "generated_videos") and operation.response.generated_videos:
        generated_vid = operation.response.generated_videos[0]
        if hasattr(generated_vid, "video"):
            vid = generated_vid.video
            if hasattr(vid, "video_bytes") and vid.video_bytes:
                video_bytes = vid.video_bytes
            else:
                try:
                    video_bytes = genai_client.files.download(file=vid)
                except Exception as dl_err:
                    print(f"File download error: {dl_err}")
                    if hasattr(vid, "uri") and vid.uri and vid.uri.startswith("gs://"):
                        parts = vid.uri[5:].split("/", 1)
                        if len(parts) == 2:
                            s_client = storage.Client(project=FIRESTORE_PROJECT_ID)
                            video_bytes = s_client.bucket(parts[0]).blob(parts[1]).download_as_bytes()

    if not video_bytes:
        return {"status": "error", "message": "Failed to extract video bytes from gemini-omni-flash-preview response."}

    file_id = f"video_{uuid.uuid4().hex[:6]}"
    filename = f"{file_id}.mp4"

    # (1) Save artifact with tool_context for Playground Artifacts panel
    if tool_context is not None:
        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as err:
            print(f"Warning: Failed to save video artifact via tool_context: {err}")

    # (2) Upload video bytes to public Cloud Storage bucket
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "message": f"Successfully generated video and uploaded to {filename}",
        "video_url": public_url,
        "filename": filename,
    }



