"""
Guardrails and JSON output validator for Amazon Bedrock responses.
Ensures that any generated text from LLMs strictly conforms to BedrockInvestigationReport.
"""
import json
import logging
from typing import Tuple, Optional
from pydantic import ValidationError
from genai.schemas.investigation_report import BedrockInvestigationReport

logger = logging.getLogger(__name__)


def validate_bedrock_response(raw_text: str) -> Tuple[bool, Optional[BedrockInvestigationReport], Optional[str]]:
    """
    Validates and cleans raw string responses from Bedrock LLMs.
    
    Returns:
        (is_valid, parsed_report, error_message)
    """
    try:
        cleaned_text = raw_text.strip()
        # Handle markdown fences if LLM accidentally includes them
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        data = json.loads(cleaned_text)
        report = BedrockInvestigationReport.model_validate(data)
        return True, report, None
    except json.JSONDecodeError as err:
        error_msg = f"Failed to decode JSON from Bedrock response: {str(err)}"
        logger.error(error_msg)
        return False, None, error_msg
    except ValidationError as err:
        error_msg = f"Schema validation error on Bedrock response: {err.errors()}"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as err:
        error_msg = f"Unexpected error validating Bedrock response: {str(err)}"
        logger.error(error_msg)
        return False, None, error_msg
