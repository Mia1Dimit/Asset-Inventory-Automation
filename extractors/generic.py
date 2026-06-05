"""
Generic extractor for unknown or unsupported Azure resource types. Returns basic resource info.
"""

import logging
from typing import Any, Dict
from common import ResourceBase

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    try:
        # Fallback for unknown types; just return basic info, no 'properties' block
        return {
            'name': resource.name,
            'id': resource.id,
            'type': resource.type,
            'location': resource.location,
            'tags': resource.tags,
        }
    except Exception as e:
        logging.error(f"Error extracting generic resource {resource.id}: {e}")
        return None
