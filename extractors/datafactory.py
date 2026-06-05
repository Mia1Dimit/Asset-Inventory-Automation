"""
Extractor for Azure Data Factory resources. Retrieves factory details and associated private endpoints.
"""
from typing import Any, Dict
import logging

def extract(resource: Any, credential: Any, pe_mapping: dict = None) -> Dict[str, Any]:
    props = resource.as_dict() if hasattr(resource, 'as_dict') else resource
    result = {
        'name': props.get('name'),
        'id': props.get('id'),
        'type': props.get('type'),
        'location': props.get('location'),
        'tags': props.get('tags'),
    }
    # Attach all private endpoints associated with this Data Factory (resource.id)
    from extractors.private_endpoint_utils import expand_private_endpoint_entries
    private_eps = []
    if pe_mapping and props.get('id') in pe_mapping:
        for pe_info in pe_mapping[props.get('id')]:
            private_eps.extend(expand_private_endpoint_entries(pe_info))
    # Fallback: if no mapping, still show the private endpoint connection IDs
    elif 'privateEndpointConnections' in props:
        for pe in props['privateEndpointConnections']:
            pe_id = pe.get('id')
            private_eps.append({'id': pe_id, 'ip_addresses': []})
    result['privateEndpoints'] = private_eps
    return result
