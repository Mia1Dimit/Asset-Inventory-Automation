"""
Extractor for Azure Storage Accounts. Retrieves storage details and associated private endpoints.
"""

import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.storage import StorageManagementClient

def extract(resource: Any, credential: Any, pe_mapping: dict = None) -> Dict[str, Any]:
    try:
        if resource.type == 'Microsoft.Storage/storageAccounts':
            parts = getattr(resource, 'id', '').split('/')
            rg = parts[4] if len(parts) > 4 else None
            account_name = parts[-1] if len(parts) > 0 else None
            storage_client = StorageManagementClient(credential, parts[2])
            acct = storage_client.storage_accounts.get_properties(rg, account_name)
            props = acct.as_dict()
                # Removed network rules extraction as not needed
            # Attach all private endpoints associated with this storage account (resource.id)
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            if pe_mapping and getattr(acct, 'id', None) in pe_mapping:
                for pe_info in pe_mapping[getattr(acct, 'id', None)]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            # Fallback: if no mapping, still show the private endpoint connection IDs
            elif props.get('private_endpoint_connections'):
                for pe in props.get('private_endpoint_connections', []):
                    pe_id = pe.get('id') if isinstance(pe, dict) else getattr(pe, 'id', None)
                    entry = {'id': pe_id, 'ip_addresses': []}
                    private_eps.append(entry)
            return {
                'name': getattr(acct, 'name', None),
                'id': getattr(acct, 'id', None),
                'type': getattr(acct, 'type', None),
                'location': getattr(acct, 'location', None),
                'tags': getattr(acct, 'tags', None),
                'sku': getattr(getattr(acct, 'sku', None), 'name', None) or props.get('sku', {}).get('name'),
                'tier': props.get('access_tier'),
                'kind': getattr(acct, 'kind', None),
                'privateEndpoints': private_eps,
            }
        else:
            return ResourceBase(
                name=getattr(resource, 'name', None),
                id=getattr(resource, 'id', None),
                type=getattr(resource, 'type', None),
                location=getattr(resource, 'location', None),
                tags=getattr(resource, 'tags', None)
            ).to_dict()
    except Exception as e:
        logging.error(f"Error extracting storage resource {getattr(resource, 'id', None)}: {e}")
        return None
