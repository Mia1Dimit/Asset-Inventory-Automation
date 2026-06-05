"""
Extractor for Azure Network resources (NICs). Retrieves network interface details and private IPs.
"""
import logging
from typing import Any, Dict
from common import ResourceBase
from azure.mgmt.network import NetworkManagementClient

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    try:
        if resource.type == 'Microsoft.Network/networkInterfaces':
            # Parse resource group and NIC name from resource.id
            parts = resource.id.split('/')
            rg = parts[4]
            nic_name = parts[-1]
            subscription_id = parts[2]
            network_client = NetworkManagementClient(credential, subscription_id)
            nic = network_client.network_interfaces.get(rg, nic_name)
            private_ips = []
            subnet = None
            # nsg field removed as it is always null
            if nic.ip_configurations:
                for ipconf in nic.ip_configurations:
                    if ipconf.private_ip_address:
                        private_ips.append(ipconf.private_ip_address)
                    if ipconf.subnet:
                        subnet = ipconf.subnet.id
            return {
                'name': nic.name,
                'id': nic.id,
                'type': nic.type,
                'location': nic.location,
                'tags': nic.tags,
                'privateIpAddresses': private_ips,
                'subnet': subnet
            }
        elif resource.type == 'Microsoft.Network/virtualNetworks':
            # Extract subnets and their address prefixes
            parts = resource.id.split('/')
            rg = parts[4]
            vnet_name = parts[-1]
            subscription_id = parts[2]
            network_client = NetworkManagementClient(credential, subscription_id)
            vnet = network_client.virtual_networks.get(rg, vnet_name)
            subnets_info = []
            if hasattr(vnet, 'subnets') and vnet.subnets:
                for subnet in vnet.subnets:
                    subnet_entry = {
                        'name': subnet.name,
                        'addressPrefix': getattr(subnet, 'address_prefix', None)
                    }
                    subnets_info.append(subnet_entry)
            return {
                'name': vnet.name,
                'id': vnet.id,
                'type': vnet.type,
                'location': vnet.location,
                'tags': vnet.tags,
                'subnets': subnets_info
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
        logging.error(f"Error extracting network resource {resource.id}: {e}")
        return None
