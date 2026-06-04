"""
Extractor for Azure SQL and Cosmos DB resources. Retrieves database details and associated private endpoints.
"""

import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.sql import SqlManagementClient

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    try:
        pe_mapping = kwargs.get('pe_mapping')
        # Unify extraction for all database resource types
        # SQL Server
        if resource.type == 'Microsoft.Sql/servers':
            from azure.mgmt.sql import SqlManagementClient
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            parts = resource.id.split('/')
            rg = parts[4]
            server_name = parts[-1]
            subscription_id = parts[2]
            sql_client = SqlManagementClient(credential, subscription_id)
            server = sql_client.servers.get(rg, server_name)
            private_eps = []
            if pe_mapping and server.id in pe_mapping:
                for pe_info in pe_mapping[server.id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(server, 'private_endpoint_connections') and server.private_endpoint_connections:
                for pe in server.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            admin_login = getattr(server, 'administrator_login', None)
            return {
                'name': server.name,
                'id': server.id,
                'type': server.type,
                'location': server.location,
                'tags': server.tags,
                'adminLogin': admin_login,
                'privateEndpoints': private_eps,
            }
        # SQL Database
        elif resource.type in ['Microsoft.Sql/databases', 'Microsoft.Sql/servers/databases']:
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            db_id = getattr(resource, 'id', None)
            if pe_mapping and db_id in pe_mapping:
                for pe_info in pe_mapping[db_id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(resource, 'private_endpoint_connections') and resource.private_endpoint_connections:
                for pe in resource.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            return {
                'name': getattr(resource, 'name', None),
                'id': getattr(resource, 'id', None),
                'type': getattr(resource, 'type', None),
                'location': getattr(resource, 'location', None),
                'tags': getattr(resource, 'tags', None),
                'privateEndpoints': private_eps,
            }
        # MySQL
        elif resource.type == 'Microsoft.DBforMySQL/servers':
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            mysql_id = getattr(resource, 'id', None)
            if pe_mapping and mysql_id in pe_mapping:
                for pe_info in pe_mapping[mysql_id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(resource, 'private_endpoint_connections') and resource.private_endpoint_connections:
                for pe in resource.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            admin_login = getattr(resource, 'administrator_login', None)
            fqdn = getattr(resource, 'fully_qualified_domain_name', None)
            return {
                'name': getattr(resource, 'name', None),
                'id': getattr(resource, 'id', None),
                'type': getattr(resource, 'type', None),
                'location': getattr(resource, 'location', None),
                'tags': getattr(resource, 'tags', None),
                'adminLogin': admin_login,
                'fullyQualifiedDomainName': fqdn,
                'privateEndpoints': private_eps,
            }
        # PostgreSQL
        elif resource.type == 'Microsoft.DBforPostgreSQL/servers':
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            pg_id = getattr(resource, 'id', None)
            if pe_mapping and pg_id in pe_mapping:
                for pe_info in pe_mapping[pg_id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(resource, 'private_endpoint_connections') and resource.private_endpoint_connections:
                for pe in resource.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            admin_login = getattr(resource, 'administrator_login', None)
            fqdn = getattr(resource, 'fully_qualified_domain_name', None)
            return {
                'name': getattr(resource, 'name', None),
                'id': getattr(resource, 'id', None),
                'type': getattr(resource, 'type', None),
                'location': getattr(resource, 'location', None),
                'tags': getattr(resource, 'tags', None),
                'adminLogin': admin_login,
                'fullyQualifiedDomainName': fqdn,
                'privateEndpoints': private_eps,
            }
        # Cosmos DB
        elif resource.type == 'Microsoft.DocumentDB/databaseAccounts':
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            cosmos_id = getattr(resource, 'id', None)
            if pe_mapping and cosmos_id in pe_mapping:
                for pe_info in pe_mapping[cosmos_id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(resource, 'private_endpoint_connections') and resource.private_endpoint_connections:
                for pe in resource.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            return {
                'name': getattr(resource, 'name', None),
                'id': getattr(resource, 'id', None),
                'type': getattr(resource, 'type', None),
                'location': getattr(resource, 'location', None),
                'tags': getattr(resource, 'tags', None),
                'privateEndpoints': private_eps,
            }
        # Redis
        elif resource.type == 'Microsoft.Cache/Redis':
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            private_eps = []
            redis_id = getattr(resource, 'id', None)
            if pe_mapping and redis_id in pe_mapping:
                for pe_info in pe_mapping[redis_id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(resource, 'private_endpoint_connections') and resource.private_endpoint_connections:
                for pe in resource.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            return {
                'name': getattr(resource, 'name', None),
                'id': getattr(resource, 'id', None),
                'type': getattr(resource, 'type', None),
                'location': getattr(resource, 'location', None),
                'tags': getattr(resource, 'tags', None),
                'privateEndpoints': private_eps,
            }
        # PostgreSQL Flexible Server
        elif resource.type == 'Microsoft.DBforPostgreSQL/flexibleServers':
            from azure.mgmt.rdbms.postgresql_flexibleservers import PostgreSQLManagementClient
            from azure.mgmt.network import NetworkManagementClient
            from extractors.private_endpoint_utils import expand_private_endpoint_entries
            parts = resource.id.split('/')
            rg = parts[4]
            server_name = parts[-1]
            subscription_id = parts[2]
            pg_client = PostgreSQLManagementClient(credential, subscription_id)
            network_client = NetworkManagementClient(credential, subscription_id)
            server = pg_client.servers.get(rg, server_name)
            server_dict = server.as_dict()
            private_eps = []
            pe_mapping = kwargs.get('pe_mapping')
            if pe_mapping and server.id in pe_mapping:
                for pe_info in pe_mapping[server.id]:
                    private_eps.extend(expand_private_endpoint_entries(pe_info))
            elif hasattr(server, 'private_endpoint_connections') and server.private_endpoint_connections:
                for pe in server.private_endpoint_connections:
                    pe_id = pe.id if hasattr(pe, 'id') else None
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            admin_login = getattr(server, 'administrator_login', None)
            fqdn = getattr(server, 'fully_qualified_domain_name', None)
            sku_name = server.sku.name if hasattr(server, 'sku') and server.sku else None
            storage_size_gb = None
            if hasattr(server, 'storage') and server.storage:
                storage_size_gb = getattr(server.storage, 'storage_size_gb', None)
            # Parse delegatedSubnetResourceId for vnet and subnet names
            subnet_id = None
            vnet_name = None
            subnet_name = None
            address_prefix = None
            try:
                if hasattr(server, 'network') and server.network and getattr(server.network, 'delegated_subnet_resource_id', None):
                    subnet_id = server.network.delegated_subnet_resource_id
                    subnet_parts = subnet_id.split('/')
                    vnet_name = subnet_parts[subnet_parts.index('virtualNetworks') + 1]
                    subnet_name = subnet_parts[subnet_parts.index('subnets') + 1]
                    # Fetch the subnet to get addressPrefix
                    vnet_rg = subnet_parts[subnet_parts.index('resourceGroups') + 1]
                    subnet_obj = network_client.subnets.get(vnet_rg, vnet_name, subnet_name)
                    address_prefix = subnet_obj.address_prefix
                else:
                    subnet_id = None
                    vnet_name = None
                    subnet_name = None
                    address_prefix = None
            except Exception as e:
                logging.warning(f"Could not extract subnet info for flexible server {server_name}: {e}")
                subnet_id = None
                vnet_name = None
                subnet_name = None
                address_prefix = None
            result = {
                'name': server.name,
                'id': server.id,
                'type': server.type,
                'location': server.location,
                'tags': server.tags,
                'adminLogin': admin_login,
                'fullyQualifiedDomainName': fqdn,
                'sku': {'name': sku_name} if sku_name else None,
                'storage': {'storageSizeGB': storage_size_gb} if storage_size_gb is not None else None,
                'privateEndpoints': private_eps,
            }
            if address_prefix:
                result['subnet'] = address_prefix
            if vnet_name:
                result['virtualNetwork'] = vnet_name
            if subnet_name:
                result['subnetName'] = subnet_name
            if subnet_id:
                result['delegatedSubnetResourceId'] = subnet_id
            return result
        else:
            return ResourceBase(
                name=resource.name,
                id=resource.id,
                type=resource.type,
                location=resource.location,
                tags=resource.tags
            ).to_dict()
    except Exception as e:
        logging.error(f"Error extracting database resource {resource.id}: {e}")
        return None
