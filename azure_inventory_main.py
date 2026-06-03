import argparse
import logging
import time
import sys
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from common import setup_logging, load_config, write_json_output
from plugin_factory import PluginFactory


logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

def main():
    parser = argparse.ArgumentParser(description="Azure Resource Group Inventory Tool")
    parser.add_argument('--resource-group', required=True, help='Azure Resource Group name')
    parser.add_argument('--subscription', required=True, help='Azure Subscription ID')
    parser.add_argument('--output', required=True, help='Output JSON file')
    parser.add_argument('--config', required=True, default='config.yaml', help='Config YAML file')
    args = parser.parse_args()
    try:
        t_start = time.time()
        config = load_config(args.config)
        from common import setup_logging
        setup_logging(config)
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        from plugin_factory import PluginFactory
        factory = PluginFactory(config, credential)
        logger = logging.getLogger("azure_inventory")
        logger.info(f"Scanning resource group: {args.resource_group}")
        from azure.mgmt.resourcegraph import ResourceGraphClient
        t_pe_start = time.time()
        subscription_id = args.subscription
        arg_client = ResourceGraphClient(credential)
        pe_query = """
Resources
| where type =~ 'microsoft.network/privateendpoints'
| project id, name, resourceGroup, networkInterfaces = properties.networkInterfaces, privateLinkServiceConnections = properties.privateLinkServiceConnections
"""
        pe_results = arg_client.resources({
            "subscriptions": [subscription_id],
            "query": pe_query
        })
        pes = pe_results.data if hasattr(pe_results, 'data') else pe_results['data']
        # Collect all NIC IDs
        nic_ids = set()
        for pe in pes:
            for nic in pe.get('networkInterfaces') or []:
                if isinstance(nic, dict) and 'id' in nic:
                    nic_ids.add(nic['id'])
                elif isinstance(nic, str):
                    nic_ids.add(nic)
        # Batch query NICs
        if nic_ids:
            nic_id_list = list(nic_ids)
            # ARG only allows 1000 items in 'in' clause, so batch if needed
            nics = {}
            for i in range(0, len(nic_id_list), 900):
                batch = nic_id_list[i:i+900]
                nic_query = f"""
Resources
| where type =~ 'microsoft.network/networkinterfaces'
| where id in ({','.join([repr(x) for x in batch])})
| project id, ipConfigs = properties.ipConfigurations
"""
                nic_results = arg_client.resources({
                    "subscriptions": [subscription_id],
                    "query": nic_query
                })
                for nic in (nic_results.data if hasattr(nic_results, 'data') else nic_results['data']):
                    nics[nic['id']] = nic.get('ipConfigs', [])
        else:
            nics = {}
        # Build mapping: service_resource_id -> list of {pe_name, pe_id, ip_addresses, subresource, hostname}
        service_pe_mapping = {}
        for pe in pes:
            pe_id = pe['id']
            pe_name = pe['name']
            # For each PE, collect all (ip, fqdn) pairs from all its NICs
            nic_entries = []
            for nic in pe.get('networkInterfaces') or []:
                nic_id = nic['id'] if isinstance(nic, dict) and 'id' in nic else nic
                ip_configs = nics.get(nic_id, [])
                for ipconf in ip_configs:
                    ip = ipconf.get('privateIPAddress') or ipconf.get('properties', {}).get('privateIPAddress')
                    props = ipconf.get('properties', {})
                    plcp = props.get('privateLinkConnectionProperties', {})
                    fqdns = plcp.get('fqdns', [])
                    # If FQDNs present, pair each with the IP (if any), else just IP
                    if ip and fqdns:
                        for fqdn in fqdns:
                            nic_entries.append({'ip': ip, 'fqdn': fqdn})
                    elif ip:
                        nic_entries.append({'ip': ip, 'fqdn': ''})
                    elif fqdns:
                        for fqdn in fqdns:
                            nic_entries.append({'ip': '', 'fqdn': fqdn})
            for conn in pe.get('privateLinkServiceConnections', []):
                service_id = conn.get('privateLinkServiceId') or conn.get('properties', {}).get('privateLinkServiceId')
                # Extract subresource type from groupIds if present
                group_ids = conn.get('groupIds') or conn.get('properties', {}).get('groupIds')
                subresource = None
                if group_ids and isinstance(group_ids, list) and len(group_ids) > 0:
                    subresource = group_ids[0] if len(group_ids) == 1 else group_ids
                # For each (ip, fqdn) pair, create a separate entry
                if nic_entries:
                    for pair in nic_entries:
                        entry = {
                            'pe_name': pe_name,
                            'pe_id': pe_id,
                            'ip_addresses': [pair['ip']] if pair['ip'] else [],
                            'subresource': subresource,
                            'hostname': pair['fqdn']
                        }
                        if service_id:
                            if service_id not in service_pe_mapping:
                                service_pe_mapping[service_id] = []
                            service_pe_mapping[service_id].append(entry)
                else:
                    # No NIC/IP/FQDN found, still add a minimal entry
                    entry = {
                        'pe_name': pe_name,
                        'pe_id': pe_id,
                        'ip_addresses': [],
                        'subresource': subresource,
                        'hostname': ''
                    }
                    if service_id:
                        if service_id not in service_pe_mapping:
                            service_pe_mapping[service_id] = []
                        service_pe_mapping[service_id].append(entry)
        t_pe_end = time.time()
        logger.info(f"[TIMER] Fetch PEs: {t_pe_end-t_pe_start:.2f}s")

        t_res_start = time.time()
        resources = factory.discover_resources(args.resource_group, args.subscription)
        t_res_end = time.time()
        logger.info(f"[TIMER] Discover resources: {t_res_end-t_res_start:.2f}s")

        t_proc_start = time.time()
        resources_by_type = factory.extract_all(resources, pe_mapping=service_pe_mapping)
        t_proc_end = time.time()
        logger.info(f"[TIMER] Process resources: {t_proc_end-t_proc_start:.2f}s")

        output = {
            "metadata": {
                "subscription_id": args.subscription,
                "resource_group": args.resource_group,
                "scan_timestamp": factory.get_timestamp(),
                "total_resources": sum(len(v) for v in resources_by_type.values())
            },
            "resources_by_type": resources_by_type
        }
        # Only export JSON if export_json is true
        if config.get('output', {}).get('export_json', True):
            json_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Reports', 'Json')
            os.makedirs(json_dir, exist_ok=True)
            json_filename = os.path.basename(args.output)
            json_path = os.path.join(json_dir, json_filename)
            # Always apply json_pretty if JSON is exported
            json_cfg = dict(config.get('output', {}))
            json_cfg['json_pretty'] = config.get('output', {}).get('json_pretty', True)
            write_json_output(output, json_path, json_cfg)
        # Excel export if enabled
        if config.get('output', {}).get('export_excel', False):
            from excel_export import export_to_excel
            excel_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Reports', 'Excel')
            os.makedirs(excel_dir, exist_ok=True)
            excel_filename = os.path.splitext(os.path.basename(args.output))[0] + '.xlsx'
            excel_path = os.path.join(excel_dir, excel_filename)
            export_to_excel(output['resources_by_type'], args.resource_group, excel_path)
            logger.info(f"Excel workbook written to {excel_path}")
        t_end = time.time()
        logger.info(f"Inventory written to {json_path}")
        logger.info(f"[TIMER] Total running time: {t_end-t_start:.2f}s")
    except Exception as e:
        logging.getLogger("azure_inventory").exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
