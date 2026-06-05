"""
Extractor for Azure App Services (Web Apps, App Service Plans). Retrieves resource details and associated private endpoints.
"""

import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.web import WebSiteManagementClient

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    import logging
    try:
        if resource.type == 'Microsoft.Web/sites':
            parts = resource.id.split('/')
            rg = parts[4]
            site_name = parts[-1]
            subscription_id = parts[2]
            web_client = WebSiteManagementClient(credential, subscription_id)
            site = web_client.web_apps.get(rg, site_name)
            config = web_client.web_apps.get_configuration(rg, site_name)
            props = site.as_dict()
            # Use pe_mapping to attach all private endpoints and their IPs for this app service
            pe_mapping = kwargs.get('pe_mapping')
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            if pe_mapping and site.id in pe_mapping:
                for pe_info in pe_mapping[site.id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            # Fallback: if no mapping, still show the private endpoint connection IDs
            elif props.get('private_endpoint_connections'):
                for pe in props.get('private_endpoint_connections', []):
                    pe_id = pe.get('id') if isinstance(pe, dict) else getattr(pe, 'id', None)
                    private_eps.append({'id': pe_id, 'ip_addresses': []})
            return {
                'name': site.name,
                'id': site.id,
                'type': site.type,
                'location': site.location,
                'tags': site.tags,
                'hostNames': props.get('host_names', []),
                'subnet': props.get('virtual_network_subnet_id'),
                'appPlan': props.get('server_farm_id'),
                'privateEndpoints': private_eps,
            }
        # Add App Service Plan, etc.
        else:
            return ResourceBase(
                name=resource.name,
                id=resource.id,
                type=resource.type,
                location=resource.location,
                tags=resource.tags
            ).to_dict()
    except Exception as e:
        logging.error(f"Error extracting appservices resource {resource.id}: {e}")
        return None
