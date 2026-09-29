# Seed script for Firestore artworks collection
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-01-832d146ced4c"
COLLECTION_NAME = "artworks"

SEEDED_ARTWORKS = [
    {
        "id": "art_101",
        "title": "Neon Cyberpunk Metropolis",
        "prompt": "A futuristic cyberpunk city with glowing neon signage, wet reflective streets, and flying vehicles at dusk",
        "style": "cyberpunk",
        "aspect_ratio": "16:9",
        "tags": ["neon", "cyberpunk", "futuristic", "city"],
        "created_at": "2026-09-29T08:00:00Z",
    },
    {
        "id": "art_102",
        "title": "Ethereal Misty Forest",
        "prompt": "Soft morning sunlight breaking through foggy ancient pine trees in an enchanted woodland, watercolor painting",
        "style": "watercolor",
        "aspect_ratio": "1:1",
        "tags": ["nature", "forest", "fog", "watercolor"],
        "created_at": "2026-09-29T08:30:00Z",
    },
    {
        "id": "art_103",
        "title": "Minimalist Cosmic Astronaut",
        "prompt": "A sleek astronaut floating in deep space near a pastel-colored nebula, flat vector art style",
        "style": "vector_minimalist",
        "aspect_ratio": "9:16",
        "tags": ["space", "astronaut", "minimalist", "vector"],
        "created_at": "2026-09-29T09:00:00Z",
    },
]


def seed():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(COLLECTION_NAME)

    for item in SEEDED_ARTWORKS:
        doc_id = item["id"]
        collection_ref.document(doc_id).set(item)
        print(f"Seeded document: {doc_id} -> {item['title']}")

    print(f"Successfully seeded {len(SEEDED_ARTWORKS)} items into '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed()
