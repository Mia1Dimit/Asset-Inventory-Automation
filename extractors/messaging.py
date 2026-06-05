"""
Extractor for Azure Messaging resources (Service Bus, Event Hubs). Retrieves messaging details and associated private endpoints.
"""

import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.servicebus import ServiceBusManagementClient

def extract(resource: Any, credential: Any, pe_mapping: dict = None) -> Dict[str, Any]:
    try:
        if resource.type == 'Microsoft.ServiceBus/namespaces':
            parts = resource.id.split('/')
            rg = parts[4]
            ns_name = parts[-1]
            subscription_id = parts[2]
            sb_client = ServiceBusManagementClient(credential, subscription_id)
            ns = sb_client.namespaces.get(rg, ns_name)
            props = ns.as_dict()
            # Attach all private endpoints associated with this messaging resource (resource.id)
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            if pe_mapping and getattr(ns, 'id', None) in pe_mapping:
                for pe_info in pe_mapping[getattr(ns, 'id', None)]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            # Fallback: if no mapping, still show the private endpoint connection IDs
            elif props.get('private_endpoint_connections'):
                for pe in props.get('private_endpoint_connections', []):
                    pe_id = pe.get('id') if isinstance(pe, dict) else getattr(pe, 'id', None)
                    private_eps.append({'id': pe_id, 'ip_addresses': []})
            return {
                'name': getattr(ns, 'name', None),
                'id': getattr(ns, 'id', None),
                'type': getattr(ns, 'type', None),
                'location': getattr(ns, 'location', None),
                'tags': getattr(ns, 'tags', None),
                'sku': getattr(getattr(ns, 'sku', None), 'name', None) or props.get('sku', {}).get('name'),
                'messagingType': props.get('messaging_type', None),
                'privateEndpoints': private_eps,
            }
        else:
            return ResourceBase(
                name=resource.name,
                id=resource.id,
                type=resource.type,
                location=resource.location,
                tags=resource.tags
            ).to_dict()
    except Exception as e:
        logging.error(f"Error extracting messaging resource {resource.id}: {e}")
        return None
