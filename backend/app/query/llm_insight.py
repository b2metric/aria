import json
import logging
from typing import Any
import litellm
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

from backend.app.services.llm_resolver import ResolvedLLM

async def generate_insight_and_suggestions(
    question: str,
    sql: str,
    data_rows: list[dict[str, Any]],
    llm: ResolvedLLM | None = None,
) -> dict:
    """Generate executive summary and follow-up suggestions from query results.
    
    Args:
        question: Original user question
        sql: The SQL that was executed
        data_rows: Up to 10 rows of data from the result
        
    Returns:
        dict: {"summary": "str", "suggestions": ["Q1", "Q2", "Q3"]}
    """
    settings = get_settings()
    
    prompt = f"""You are an executive data analyst. You are provided with a user's question, the SQL query used to fetch data, and a sample of the results (up to 10 rows).
Your task is to provide:
1. A brief executive summary (max 2 sentences) interpreting the results.
2. 3 insightful follow-up questions the user might want to ask next to drill down or pivot.

Return ONLY a valid JSON object matching this schema:
{{
  "summary": "Your executive summary here...",
  "suggestions": ["Follow-up question 1", "Follow-up question 2", "Follow-up question 3"]
}}

Question: {question}
SQL: {sql}
Result Sample:
{json.dumps(data_rows, default=str)}
"""

    try:
        
        model_name = llm.model if llm else settings.llm_model
        api_base = llm.api_base if llm else settings.litellm_api_base
        api_key = llm.api_key if llm else (settings.litellm_api_key or "sk-dummy")
        
        response = await litellm.acompletion(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=30.0,
            api_base=api_base,
            api_key=api_key,
            custom_llm_provider="openai",
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Ensure correct structure
        summary = result.get("summary", "Query executed successfully.")
        suggestions = result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []
            
        return {
            "summary": summary,
            "suggestions": suggestions[:3]
        }
    except Exception as e:
        logger.warning(f"Failed to generate insights: {e}")
        return {
            "summary": "Data retrieved successfully.",
            "suggestions": []
        }
