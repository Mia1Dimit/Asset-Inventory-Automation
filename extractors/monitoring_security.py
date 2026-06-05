"""
Extractor for Azure Monitoring and Security resources. (Stub: returns basic info.)
"""

import logging
from typing import Any, Dict
from common import ResourceBase
# from azure.mgmt.loganalytics import LogAnalyticsManagementClient
# from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
# from azure.mgmt.security import SecurityCenter

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
        logging.error(f"Error extracting monitoring/security resource {resource.id}: {e}")
        return None
