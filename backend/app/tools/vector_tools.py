from langchain_core.tools import tool
from app.db.chroma_client import get_collection


@tool
def get_similar_past_incidents(alert_description: str) -> dict:
    """
    Search the incident knowledge base for past incidents similar to this one.
    Uses semantic (vector) search to find matches even when wording differs.
    Returns past incidents with their root cause and resolution steps.
    """
    collection = get_collection()

    try:
        results = collection.query(
            query_texts=[alert_description],
            n_results=3,
        )

        incidents = []
        for i, doc in enumerate(results["documents"][0]):
            similarity = round(1 - results["distances"][0][i], 3)
            incidents.append({
                "content": doc,
                "similarity_score": similarity,
                "metadata": results["metadatas"][0][i],
            })

        return {"similar_incidents": incidents, "total_found": len(incidents)}

    except Exception as e:
        return {"error": str(e), "similar_incidents": []}
