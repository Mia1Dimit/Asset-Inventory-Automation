"""
Extractor for Azure Synapse Analytics resources. Retrieves workspace details and associated private endpoints.
"""
from typing import Any, Dict
import logging
from extractors.private_endpoint_utils import get_private_endpoint_ips, get_private_endpoint_id_from_connection_name

def extract(resource: Any, credential: Any, pe_mapping: dict = None) -> Dict[str, Any]:
    props = resource.as_dict() if hasattr(resource, 'as_dict') else resource
    result = {
        'name': props.get('name'),
        'id': props.get('id'),
        'type': props.get('type'),
        'location': props.get('location'),
        'tags': props.get('tags'),
        'properties_summary': {},
    }
    from extractors.private_endpoint_utils import expand_private_endpoint_entries
    private_eps = []
    if pe_mapping and props.get('id') in pe_mapping:
        for pe_info in pe_mapping[props.get('id')]:
            private_eps.extend(expand_private_endpoint_entries(pe_info))
    elif 'private_endpoint_connections' in props:
        for pe in props['private_endpoint_connections']:
            pe_id = pe.get('id')
            private_eps.append({'id': pe_id, 'ip_addresses': []})
    result['privateEndpoints'] = private_eps
    return result
