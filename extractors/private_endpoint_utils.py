def expand_private_endpoint_entries(pe_info):
    """
    Given a PE info dict (from pe_mapping), return a list of dicts, one per IP/FQDN pair.
    If both ips and fqdns are present and same length, pair them. If only one fqdn, assign to all ips. If only ips, just split. If only fqdns, just split. If neither, return one block.
    Always include pe_name, pe_id, subresource, and hostname (empty if not present).
    """
    ips = pe_info.get('ip_addresses', [])
    fqdns = []
    if 'hostname' in pe_info and pe_info['hostname']:
        fqdns = [fqdn.strip() for fqdn in pe_info['hostname'].split(',') if fqdn.strip()]
    blocks = []
    if ips and fqdns and len(ips) == len(fqdns):
        for ip, fqdn in zip(ips, fqdns):
            blocks.append({
                'pe_name': pe_info.get('pe_name'),
                'pe_id': pe_info.get('pe_id'),
                'ip_addresses': [ip],
                'subresource': pe_info.get('subresource', None),
                'hostname': fqdn
            })
    elif ips and fqdns and len(fqdns) == 1:
        for ip in ips:
            blocks.append({
                'pe_name': pe_info.get('pe_name'),
                'pe_id': pe_info.get('pe_id'),
                'ip_addresses': [ip],
                'subresource': pe_info.get('subresource', None),
                'hostname': fqdns[0]
            })
    elif ips:
        for ip in ips:
            blocks.append({
                'pe_name': pe_info.get('pe_name'),
                'pe_id': pe_info.get('pe_id'),
                'ip_addresses': [ip],
                'subresource': pe_info.get('subresource', None),
                'hostname': fqdns[0] if len(fqdns) == 1 else ''
            })
    elif fqdns:
        for fqdn in fqdns:
            blocks.append({
                'pe_name': pe_info.get('pe_name'),
                'pe_id': pe_info.get('pe_id'),
                'ip_addresses': [],
                'subresource': pe_info.get('subresource', None),
                'hostname': fqdn
            })
    else:
        blocks.append({
            'pe_name': pe_info.get('pe_name'),
            'pe_id': pe_info.get('pe_id'),
            'ip_addresses': pe_info.get('ip_addresses', []),
            'subresource': pe_info.get('subresource', None),
            'hostname': ''
        })
    return blocks
"""
Utility functions for resolving Azure Private Endpoint resource IDs and extracting associated private IP addresses. Used by extractors for PE mapping.
"""

import logging
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient


def get_private_endpoint_id_from_connection_name(connection_name: str, credential, subscription_id):
    """
    Enumerate all private endpoints in the subscription and return (resource_group, private_endpoint_id) if found by name.
    """
    try:
        resource_client = ResourceManagementClient(credential, subscription_id)
        network_client = NetworkManagementClient(credential, subscription_id)
        connection_name_lc = connection_name.lower()
        for rg in resource_client.resource_groups.list():
            for pe in network_client.private_endpoints.list(rg.name):
                pe_name_lc = pe.name.lower()
                # Match if connection_name is contained in the PE name
                if connection_name_lc in pe_name_lc:
                    return rg.name, pe.id
                # Also match if connection_name is in any tag value
                if hasattr(pe, 'tags') and pe.tags:
                    for v in pe.tags.values():
                        if connection_name_lc in str(v).lower():
                            return rg.name, pe.id
        return None, None
    except Exception as e:
        logging.warning(f"[PE-UTILS] Could not resolve private endpoint for connection name {connection_name}: {e}")
        return None, None

def get_private_endpoint_ips(private_endpoint_id: str, credential, subscription_id):
    """
    Given a private endpoint resource ID, return all private IPs from its network interfaces.
    """
    try:
        parts = private_endpoint_id.split('/')
        rg = parts[4]
        pe_name = parts[-1]
        network_client = NetworkManagementClient(credential, subscription_id)
        pe = network_client.private_endpoints.get(rg, pe_name)
        ips = []
        for nic_ref in pe.network_interfaces:
            nic_id = nic_ref.id
            nic_name = nic_id.split('/')[-1]
            nic = network_client.network_interfaces.get(rg, nic_name)
            for ipconf in nic.ip_configurations:
                if ipconf.private_ip_address:
                    ips.append(ipconf.private_ip_address)
        return ips
    except Exception as e:
        logging.warning(f"[PE-UTILS] Could not resolve private endpoint IPs for {private_endpoint_id}: {e}")
        return []
