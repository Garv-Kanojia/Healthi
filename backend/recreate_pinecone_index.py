"""
One-time migration script:
  - Deletes the existing 'eds-knowledge-base' Pinecone index (384-dim)
  - Recreates it with 1024 dimensions to match Amazon Titan Text Embed V2

Run from: Healthi/backend/
    python recreate_pinecone_index.py

After running this, re-ingest your EDS documents using your ingestion pipeline.
"""

import os
import time
import dotenv
from pinecone import Pinecone, ServerlessSpec

dotenv.load_dotenv()

INDEX_NAME = "eds-knowledge-base"
NEW_DIMENSION = 1024          # Amazon Titan Text Embed V2 output size
METRIC = "cosine"             # keep the same similarity metric
CLOUD = "aws"
REGION = "us-east-1"         # must match your Pinecone project region

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# ── Step 1: Show current state ──────────────────────────────────────────────
existing = [i.name for i in pc.list_indexes()]
print(f"Existing indexes: {existing}")

if INDEX_NAME not in existing:
    print(f"Index '{INDEX_NAME}' does not exist yet — will create fresh.")
else:
    # ── Step 2: Delete old index ─────────────────────────────────────────────
    confirm = input(
        f"\n⚠️  This will DELETE '{INDEX_NAME}' (384-dim) and all its vectors.\n"
        "All stored knowledge-base and memory vectors will be lost.\n"
        "Type 'yes' to continue: "
    )
    if confirm.strip().lower() != "yes":
        print("Aborted.")
        exit(0)

    print(f"\nDeleting index '{INDEX_NAME}'...")
    pc.delete_index(INDEX_NAME)

    # Wait until it's fully removed
    while INDEX_NAME in [i.name for i in pc.list_indexes()]:
        print("  Waiting for deletion to complete...")
        time.sleep(3)
    print("  Deleted ✓")

# ── Step 3: Create new index with 1024 dims ──────────────────────────────────
print(f"\nCreating index '{INDEX_NAME}' with dimension={NEW_DIMENSION}, metric='{METRIC}'...")
pc.create_index(
    name=INDEX_NAME,
    dimension=NEW_DIMENSION,
    metric=METRIC,
    spec=ServerlessSpec(cloud=CLOUD, region=REGION),
)

# Wait until ready
while not pc.describe_index(INDEX_NAME).status["ready"]:
    print("  Waiting for index to be ready...")
    time.sleep(3)

print(f"\n✅ Index '{INDEX_NAME}' is ready!")
print(f"   Dimension : {NEW_DIMENSION}")
print(f"   Metric    : {METRIC}")
print(f"\nNext step: re-run your EDS document ingestion pipeline to re-embed and upload the knowledge base.")
