import json
import logging
import re
from pathlib import Path

import litellm

from backend.app.core.config import get_settings
from backend.app.schema_discovery.models import SchemaSnapshot
from backend.app.services.workspace_language import get_workspace_language, language_directive

logger = logging.getLogger(__name__)

async def generate_vault_suggestions(snapshot: SchemaSnapshot, vault_base_path: str | Path) -> None:
    settings = get_settings()
    workspace_id = snapshot.workspace_id
    language = await get_workspace_language(workspace_id)

    tables_info = "\n".join(
        [f"- {t.name}: {getattr(t, 'description', None) or 'No description'}" for t in snapshot.tables]
    )

    prompt = f"""
{language_directive(language)}

Given the following database tables for workspace '{workspace_id}', generate exactly 3 distinct, practical, and business-focused analytical questions that a user might ask in a natural language interface.
Do not ask for SQL. Just provide the natural language questions.
Return ONLY a JSON array of strings, like ["question 1", "question 2", "question 3"].

Tables:
{tables_info}
"""

    try:
        response = await litellm.acompletion(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            api_base=settings.litellm_api_base,
            api_key=settings.litellm_api_key or "sk-dummy",
            custom_llm_provider="openai",  # route through the OpenAI-compatible LiteLLM proxy
        )
        
        content = response.choices[0].message.content
        
        # Try to parse JSON array
        # Clean markdown code blocks if any
        content = re.sub(r'```json\n|\n```', '', content).strip()
        suggestions = json.loads(content)
        
        if isinstance(suggestions, dict):
            # If model returns {"questions": [...]}
            for val in suggestions.values():
                if isinstance(val, list):
                    suggestions = val
                    break
        
        if not isinstance(suggestions, list):
            suggestions = [
                "Show monthly revenue by category",
                "Top 10 customers by volume",
                "Daily active users trend"
            ]
            
        suggestions = [str(s) for s in suggestions][:3]
        
        vault_path = Path(vault_base_path) / workspace_id
        vault_path.mkdir(parents=True, exist_ok=True)
        suggestions_file = vault_path / "suggestions.json"
        
        with open(suggestions_file, "w") as f:
            json.dump(suggestions, f, indent=2)
            
        logger.info(f"Generated {len(suggestions)} suggestions for workspace {workspace_id}")
    except Exception as e:
        logger.error(f"Failed to generate suggestions for workspace {workspace_id}: {e}")
