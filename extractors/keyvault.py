"""
Extractor for Azure Key Vault resources. Retrieves vault details and associated private endpoints.
"""

import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.keyvault import KeyVaultManagementClient

def extract(resource: Any, credential: Any, pe_mapping: dict = None) -> Dict[str, Any]:
    try:
        if resource.type == 'Microsoft.KeyVault/vaults':
            parts = resource.id.split('/')
            rg = parts[4]
            vault_name = parts[-1]
            subscription_id = parts[2]
            kv_client = KeyVaultManagementClient(credential, subscription_id)
            vault = kv_client.vaults.get(rg, vault_name)
            # Use SDK object model directly, no 'properties' dict
            sku = vault.sku.name if hasattr(vault, 'sku') and vault.sku else None
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            if pe_mapping and getattr(vault, 'id', None) in pe_mapping:
                for pe_info in pe_mapping[getattr(vault, 'id', None)]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(vault, 'private_endpoint_connections') and vault.private_endpoint_connections:
                for pe in vault.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'id': pe_id, 'ip_addresses': []})
            # networkAcls: use vault.network_acls if present, else None
            network_acls = vault.network_acls.as_dict() if hasattr(vault, 'network_acls') and vault.network_acls else None
            return {
                'name': vault.name,
                'id': vault.id,
                'type': vault.type,
                'location': vault.location,
                'tags': vault.tags,
                'sku': sku,
                'privateEndpoints': private_eps,
                'networkAcls': network_acls,
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
        logging.error(f"Error extracting keyvault resource {resource.id}: {e}")
        return None
