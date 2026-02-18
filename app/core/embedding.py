import voyageai
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Voyage Client
# Note: voyageai.Client will automatically look for VOYAGE_API_KEY in env or we can pass it explicitly
try:
    vo_client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Voyage AI client: {e}")
    vo_client = None

MODEL_NAME = "voyage-4"

def get_embedding(text: str) -> list[float]:
    """
    Generate embedding for a single text using Voyage AI.
    Returns a list of floats (1024 dimensions for voyage-4).
    """
    if not vo_client:
        logger.error("Voyage AI client is not initialized")
        return []

    if not text or not text.strip():
        return []

    try:
        # embed() returns a list of embeddings, we take the first one
        result = vo_client.embed([text], model=MODEL_NAME, input_type="document")
        return result.embeddings[0]
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []
