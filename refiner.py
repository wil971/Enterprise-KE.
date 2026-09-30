import hashlib
import json
import re
import asyncio
import requests

from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List

from config import (
    AI_API_KEY,
    AI_API_URL,
    AI_MODEL,
    NEO4J_DATABASE,
    logger,
)

from database import get_driver


# ==============================================================================
# LIMITS
# ==============================================================================

MAX_DOCUMENT_LENGTH = 200_000
MAX_TITLE_LENGTH = 500
MAX_ENTITY_LENGTH = 500
MAX_ENTITIES = 100
AI_TIMEOUT_SECONDS = 60


# ==============================================================================
# VALIDATION HELPERS
# ==============================================================================

def _clean_string(
    value: Any,
    field_name: str,
    max_length: int,
) -> str:
    """
    Normalize a string field and enforce a maximum size.
    """

    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    if len(value) > max_length:
        raise ValueError(
            f"{field_name} cannot exceed "
            f"{max_length} characters."
        )

    return value


def _normalize_entity_name(value: Any) -> str:
    """
    Normalize an extracted entity name.
    """

    value = _clean_string(
        value,
        "Entity name",
        MAX_ENTITY_LENGTH,
    )

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ==============================================================================
# DOCUMENT VALIDATION
# ==============================================================================

def validate_document_input(
    title: str,
    text: str,
) -> Tuple[str, str]:
    """
    Validate document title and content before extraction.
    """

    title = _clean_string(
        title,
        "Document title",
        MAX_TITLE_LENGTH,
    )

    text = _clean_string(
        text,
        "Document text",
        MAX_DOCUMENT_LENGTH,
    )

    if not title:
        raise ValueError(
            "Document title cannot be empty."
        )

    if not text:
        raise ValueError(
            "Document text cannot be empty."
        )

    return title, text


# ==============================================================================
# EXTRACTION VALIDATION
# ==============================================================================

def validate_extraction(
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize the AI extraction into the application's
    expected structure.

    Missing values remain empty rather than inventing information.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "AI extraction must be a JSON object."
        )

    client = _clean_string(
        data.get("client", ""),
        "Client",
        MAX_ENTITY_LENGTH,
    )

    project = _clean_string(
        data.get("project", ""),
        "Project",
        MAX_ENTITY_LENGTH,
    )

    deadline = _clean_string(
        data.get("deadline", ""),
        "Deadline",
        200,
    )

    document_type = _clean_string(
        data.get("document_type", ""),
        "Document type",
        200,
    )

    raw_entities = data.get(
        "important_entities",
        [],
    )

    if raw_entities is None:
        raw_entities = []

    if not isinstance(raw_entities, list):
        raise ValueError(
            "important_entities must be a list."
        )

    entities: List[str] = []
    seen = set()

    for raw_entity in raw_entities:

        entity = _normalize_entity_name(
            raw_entity
        )

        if not entity:
            continue

        normalized_key = entity.casefold()

        if normalized_key in seen:
            continue

        seen.add(normalized_key)
        entities.append(entity)

        if len(entities) >= MAX_ENTITIES:
            break

    return {
        "client": client,
        "project": project,
        "deadline": deadline,
        "document_type": document_type,
        "important_entities": entities,
    }


# ==============================================================================
# AI EXTRACTION
# ==============================================================================

def extract_business_entities(
    text: str,
) -> Dict[str, Any]:
    """
    Extract structured enterprise information from a document.

    The model is instructed to return JSON only.
    No information is fabricated locally if extraction fails.
    """

    if not isinstance(text, str):
        raise ValueError(
            "Document text must be a string."
        )

    text = text.strip()

    if not text:
        raise ValueError(
            "Document text cannot be empty."
        )

    if len(text) > MAX_DOCUMENT_LENGTH:
        raise ValueError(
            f"Document text cannot exceed "
            f"{MAX_DOCUMENT_LENGTH} characters."
        )

    if not AI_API_KEY:
        raise RuntimeError(
            "AI API key is not configured."
        )

    prompt = f"""
You are an enterprise information extraction engine.

Analyze the business document below.

Extract only information that is explicitly supported by
the document.

Return ONLY valid JSON using exactly this structure:

{{
    "client": "",
    "project": "",
    "deadline": "",
    "document_type": "",
    "important_entities": []
}}

Rules:

1. Do not invent information.
2. Use an empty string when a field is not supported.
3. important_entities must be an array of strings.
4. Do not include explanations outside the JSON.
5. Include meaningful business entities such as:
   companies, people, products, systems, locations,
   departments, contracts, technologies, or other
   explicitly identifiable entities.

DOCUMENT:

{text}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {AI_API_KEY}",
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise enterprise "
                    "information extraction system."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.0,
        "response_format": {
            "type": "json_object"
        },
    }

    try:
        response = requests.post(
            AI_API_URL,
            json=payload,
            headers=headers,
            timeout=AI_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        logger.exception(
            "AI extraction request failed."
        )

        raise RuntimeError(
            "Enterprise information extraction failed."
        ) from exc

    try:
        response_data = response.json()

        raw_content = (
            response_data["choices"][0]
            ["message"]["content"]
        )

        extracted = json.loads(
            raw_content
        )

    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        json.JSONDecodeError,
    ) as exc:

        logger.exception(
            "Invalid AI extraction response."
        )

        raise RuntimeError(
            "AI extraction returned an invalid response."
        ) from exc

    return validate_extraction(
        extracted
    )


# ==============================================================================
# DETERMINISTIC ENTITY ID
# ==============================================================================

def _entity_key(
    tenant_id: str,
    entity_type: str,
    name: str,
) -> str:
    """
    Generate a deterministic identifier for an entity.

    This prevents repeated ingestion from creating
    a new entity identity every time.
    """

    raw = (
        f"{tenant_id}|"
        f"{entity_type.casefold()}|"
        f"{name.casefold().strip()}"
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ==============================================================================
# STORE DOCUMENT + KNOWLEDGE GRAPH
# ==============================================================================

async def store_business_document(
    tenant_id: str,
    document_id: str,
    title: str,
    text: str,
    extracted: Dict[str, Any],
) -> None:
    """
    Store the document and extracted knowledge in Neo4j.

    Creates:

        Tenant
          └── OWNS → Document
                       ├── MENTIONS → Client
                       ├── MENTIONS → Project
                       └── MENTIONS → Entity

        Client
          └── OWNS_PROJECT → Project

    All generated entities are tenant-scoped.
    """

    if not tenant_id:
        raise ValueError(
            "Tenant ID cannot be empty."
        )

    if not document_id:
        raise ValueError(
            "Document ID cannot be empty."
        )

    title, text = validate_document_input(
        title,
        text,
    )

    extracted = validate_extraction(
        extracted
    )

    driver = get_driver()

    if driver is None:
        raise RuntimeError(
            "Neo4j driver is not configured."
        )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    client_name = extracted.get(
        "client",
        "",
    ).strip()

    project_name = extracted.get(
        "project",
        "",
    ).strip()

    deadline = extracted.get(
        "deadline",
        "",
    ).strip()

    document_type = extracted.get(
        "document_type",
        "",
    ).strip()

    important_entities = extracted.get(
        "important_entities",
        [],
    )

    # --------------------------------------------------------------------------
    # Stable identifiers
    # --------------------------------------------------------------------------

    client_id = None

    if client_name:
        client_id = _entity_key(
            tenant_id,
            "Client",
            client_name,
        )

    project_id = None

    if project_name:
        project_id = _entity_key(
            tenant_id,
            "Project",
            project_name,
        )

    entity_rows = []

    for entity_name in important_entities:

        entity_id = _entity_key(
            tenant_id,
            "Entity",
            entity_name,
        )

        entity_rows.append(
            {
                "id": entity_id,
                "name": entity_name,
            }
        )

    # --------------------------------------------------------------------------
    # Neo4j transaction
    # --------------------------------------------------------------------------

    query = """
    MERGE (t:Tenant {id: $tenant_id})

    MERGE (d:Document {id: $document_id})

    SET
        d.title = $title,
        d.content = $text,
        d.document_type = $document_type,
        d.updated_at = $timestamp

    MERGE (t)-[:OWNS]->(d)

    WITH t, d

    FOREACH (_ IN CASE
        WHEN $client_id IS NULL THEN []
        ELSE [1]
    END |
        MERGE (c:Client {
            id: $client_id,
            tenant_id: $tenant_id,
            name: $client_name
        })

        SET
            c.updated_at = $timestamp

        MERGE (d)-[:MENTIONS]->(c)
    )

    WITH t, d

    FOREACH (_ IN CASE
        WHEN $project_id IS NULL THEN []
        ELSE [1]
    END |
        MERGE (p:Project {
            id: $project_id,
            tenant_id: $tenant_id,
            name: $project_name
        })

        SET
            p.deadline = $deadline,
            p.updated_at = $timestamp

        MERGE (d)-[:MENTIONS]->(p)
    )

    WITH t, d

    FOREACH (_ IN CASE
        WHEN $client_id IS NULL OR $project_id IS NULL
        THEN []
        ELSE [1]
    END |
        MATCH (c:Client {
            id: $client_id,
            tenant_id: $tenant_id
        })

        MATCH (p:Project {
            id: $project_id,
            tenant_id: $tenant_id
        })

        MERGE (c)-[:OWNS_PROJECT]->(p)
    )

    WITH d

    UNWIND $entities AS entity_data

    MERGE (e:Entity {
        id: entity_data.id,
        tenant_id: $tenant_id,
        name: entity_data.name
    })

    SET
        e.updated_at = $timestamp

    MERGE (d)-[:MENTIONS]->(e)

    RETURN d.id AS document_id
    """

    parameters = {
        "tenant_id": tenant_id,
        "document_id": document_id,
        "title": title,
        "text": text,
        "document_type": document_type,
        "timestamp": timestamp,
        "client_id": client_id,
        "client_name": client_name,
        "project_id": project_id,
        "project_name": project_name,
        "deadline": deadline,
        "entities": entity_rows,
    }

    async with driver.session(
        database=NEO4J_DATABASE
    ) as session:

        result = await session.run(
            query,
            parameters,
        )

        await result.consume()


# ==============================================================================
# SYNCHRONOUS PIPELINE
# ==============================================================================

def process_and_store_document(
    tenant_id: str,
    document_id: str,
    title: str,
    text: str,
) -> Tuple[
    bool,
    str,
    Dict[str, Any],
]:
    """
    Synchronous document-processing entry point.

    This preserves the interface expected by app.py.
    """

    try:

        title, text = validate_document_input(
            title,
            text,
        )

        extracted = extract_business_entities(
            text
        )

        extracted = validate_extraction(
            extracted
        )

        async def _store() -> None:
            await store_business_document(
                tenant_id=tenant_id,
                document_id=document_id,
                title=title,
                text=text,
                extracted=extracted,
            )

        try:
            asyncio.get_running_loop()

        except RuntimeError:
            asyncio.run(_store())

        else:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            ) as executor:

                future = executor.submit(
                    asyncio.run,
                    _store(),
                )

                future.result()

        stats = {
            "client": extracted.get(
                "client"
            ),
            "project": extracted.get(
                "project"
            ),
            "document_type": extracted.get(
                "document_type"
            ),
            "deadline": extracted.get(
                "deadline"
            ),
            "entities_extracted": len(
                extracted.get(
                    "important_entities",
                    [],
                )
            ),
            "status": "Synced",
        }

        return (
            True,
            (
                f"Successfully processed and "
                f"stored '{title}'."
            ),
            stats,
        )

    except Exception as exc:

        logger.exception(
            "Failed to process document "
            "title=%s document_id=%s",
            title,
            document_id,
        )

        return (
            False,
            "Document processing failed.",
            {},
)
