"""
Extractor for Azure Managed Identities and role assignments. (Stub: returns basic info.)
"""

import logging
from typing import Any, Dict
from common import ResourceBase
# from azure.mgmt.msi import ManagedServiceIdentityClient
# from azure.mgmt.authorization import AuthorizationManagementClient

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    try:
        return ResourceBase(
            name=resource.name,
            id=resource.id,
            type=resource.type,
            location=resource.location,
            tags=resource.tags
        ).to_dict()
    except Exception as e:
        logging.error(f"Error extracting identity resource {resource.id}: {e}")
        return None
