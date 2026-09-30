"""Decode a whole website JSON reply, optionally enclosed in one code fence."""
import json
import re

JSON_PRESENTATION = (
    'When the requested output is JSON, display it in one ```json code block with no surrounding prose, '
    'so website Markdown cannot consume backslash escapes. The coordinator removes that presentation fence. '
)


def unwrap_json_code_block(text):
    """Remove only a complete valid JSON presentation block, never prose/code."""
    match = re.fullmatch(r'\s*```json\s*\n([\s\S]*?)\n```\s*', text, re.IGNORECASE)
    if match:
        try:
            json.loads(match.group(1))
        except ValueError:
            return text
        return match.group(1).strip()
    return text


def decode_json_response(text):
    text = text.strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n([\s\S]*?)\n```', text, re.IGNORECASE)
        if not match:
            raise ValueError('Expected exactly one JSON code block without surrounding prose')
        text = match.group(1).strip()
    return json.loads(text)
