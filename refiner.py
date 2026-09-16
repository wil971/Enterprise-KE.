import json
import requests
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Tuple
from config import AI_API_KEY, AI_API_URL, AI_MODEL, NEO4J_DATABASE, logger
from database import get_driver


def extract_business_entities(text: str) -> Dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Document text cannot be empty.")

    prompt = f"""
You are an enterprise information extraction engine.
Read the business document and extract these fields: client, project, deadline, document_type, important_entities.
Return ONLY valid JSON matching this exact structure:
{{
    "client": "",
    "project": "",
    "deadline": "",
    "document_type": "",
    "important_entities": []
}}
DOCUMENT:
{text}
"""

    headers = {"Content-Type": "application/json"}
    if AI_API_KEY:
        headers["Authorization"] = f"Bearer {AI_API_KEY}"

    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(AI_API_URL, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    res_data = response.json()
    raw_content = res_data["choices"][0]["message"]["content"]
    extracted = json.loads(raw_content)

    if not isinstance(extracted, dict):
        raise ValueError("AI extraction did not return a dictionary object.")

    return extracted


def validate_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = ["client", "project", "deadline", "document_type", "important_entities"]
    for field in required_fields:
        if field not in data:
            data[field] = ""
    if not isinstance(data["important_entities"], list):
        data["important_entities"] = []
    return data


async def store_business_document(
    tenant_id: str,
    document_id: str,
    title: str,
    text: str,
    extracted: Dict[str, Any],
):
    driver = get_driver()
    if driver is None:
        raise RuntimeError("Neo4j driver is not configured.")

    query = """
    MERGE (t:Tenant {id: $tenant_id})
    MERGE (d:Document {id: $document_id})
    SET d.title = $title, d.content = $text, d.updated_at = $timestamp
    MERGE (t)-[:OWNS]->(d)

    MERGE (c:Client {tenant_id: $tenant_id, name: $client})
    MERGE (p:Project {tenant_id: $tenant_id, name: $project})
    SET p.deadline = $deadline, p.updated_at = $timestamp

    MERGE (d)-[:MENTIONS]->(c)
    MERGE (d)-[:MENTIONS]->(p)
    MERGE (c)-[:OWNS_PROJECT]->(p)
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    async with driver.session(database=NEO4J_DATABASE) as session:
        result = await session.run(
            query,
            tenant_id=tenant_id,
            document_id=document_id,
            title=title,
            text=text,
            client=extracted.get("client", "Unassigned"),
            project=extracted.get("project", "General"),
            deadline=extracted.get("deadline", "N/A"),
            timestamp=timestamp,
        )
        await result.consume()


def process_and_store_document(
    tenant_id: str,
    document_id: str,
    title: str,
    text: str
) -> Tuple[bool, str, Dict[str, Any]]:
    """Synchronous pipeline entry point called by app.py UI."""
    try:
        raw_extraction = extract_business_entities(text)
        validated = validate_extraction(raw_extraction)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()

        loop.run_until_complete(
            store_business_document(
                tenant_id=tenant_id,
                document_id=document_id,
                title=title,
                text=text,
                extracted=validated
            )
        )

        stats = {
            "client": validated.get("client"),
            "project": validated.get("project"),
            "entities_extracted": len(validated.get("important_entities", [])),
            "status": "Synced 🟢"
        }
        return True, f"Successfully processed and stored '{title}'.", stats

    except Exception as e:
        logger.error(f"Failed to process document {title}: {e}")
        return False, f"Processing error: {str(e)}", {}
        
