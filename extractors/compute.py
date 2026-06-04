"""
Extractor for Azure Compute resources (VMs, Disks, VMSS). Retrieves compute, network, and OS details.
"""
import logging
from typing import Any, Dict

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from common import ResourceBase

def extract(resource: Any, credential: Any, **kwargs) -> Dict[str, Any]:
    try:
        if resource.type == 'Microsoft.Compute/virtualMachines':
            # No filtering by power state; all VMs are processed
            parts = resource.id.split('/')
            rg = parts[4]
            vm_name = parts[-1]
            subscription_id = parts[2]
            compute_client = ComputeManagementClient(credential, subscription_id)
            network_client = NetworkManagementClient(credential, subscription_id)
            vm = compute_client.virtual_machines.get(rg, vm_name, expand='instanceView')
            vm_size = vm.hardware_profile.vm_size if vm.hardware_profile else None
            os_profile = vm.os_profile.as_dict() if vm.os_profile else {}
            storage_profile = vm.storage_profile.as_dict() if vm.storage_profile else {}
            network_profile = vm.network_profile.as_dict() if vm.network_profile else {}
            vcpus = None
            ram_gb = None
            try:
                sizes = compute_client.virtual_machine_sizes.list(vm.location)
                for size in sizes:
                    if size.name == vm_size:
                        vcpus = size.number_of_cores
                        ram_gb = size.memory_in_mb / 1024.0
                        break
            except Exception as e:
                logging.warning(f"Could not resolve VM size for {vm_name}: {e}")
            nic_id = None
            private_ip = None
            subnet = None
            dns_servers = None
            vnet = None
            if network_profile.get('network_interfaces'):
                nic_id = network_profile['network_interfaces'][0]['id']
                nic_name = nic_id.split('/')[-1]
                nic_rg = rg
                try:
                    nic = network_client.network_interfaces.get(nic_rg, nic_name)
                    if nic.ip_configurations:
                        private_ip = nic.ip_configurations[0].private_ip_address
                        subnet = nic.ip_configurations[0].subnet.id if nic.ip_configurations[0].subnet else None
                        vnet = subnet.split('/subnets/')[0] if subnet else None
                        dns_servers = nic.dns_settings.dns_servers if nic.dns_settings else None
                except Exception as e:
                    logging.warning(f"Could not resolve NIC for VM {vm_name}: {e}")
            return {
                'name': vm.name,
                'id': vm.id,
                'type': vm.type,
                'location': vm.location,
                'tags': vm.tags,
                'vmSize': vm_size,
                'vCPUs': vcpus,
                'ramGB': ram_gb,
                'availabilityZone': vm.zones[0] if hasattr(vm, 'zones') and vm.zones else None,
                'osType': storage_profile.get('os_disk', {}).get('os_type'),
                'osName': os_profile.get('computer_name'),
                'osVersion': os_profile.get('windows_configuration', {}).get('provision_vm_agent') if os_profile.get('windows_configuration') else None,
                'adminUsername': os_profile.get('admin_username'),
                'osDiskType': storage_profile.get('os_disk', {}).get('managed_disk', {}).get('storage_account_type'),
                'osDiskSizeGB': storage_profile.get('os_disk', {}).get('disk_size_gb'),
                'virtualNetwork': vnet,
                'subnet': subnet,
                'dnsServers': dns_servers,
                'privateIpAddress': private_ip,
            }
        elif resource.type == 'Microsoft.Compute/disks':
            # Use SDK client to fetch disk, then as_dict on the SDK object
            parts = resource.id.split('/')
            rg = parts[4]
            disk_name = parts[-1]
            subscription_id = parts[2]
            compute_client = ComputeManagementClient(credential, subscription_id)
            disk = compute_client.disks.get(rg, disk_name)
            disk_dict = disk.as_dict()
            sku = disk.sku.name if hasattr(disk, 'sku') and disk.sku else None
            performance_tier = getattr(disk, 'tier', None) or (disk.sku.tier if hasattr(disk.sku, 'tier') else None)
            # Try to find LUN if disk is attached to a VM
            lun = None
            # Optionally, get all VMs in the resource group and check their dataDisks
            try:
                vms = list(compute_client.virtual_machines.list(rg))
                for vm in vms:
                    if not hasattr(vm, 'storage_profile') or not vm.storage_profile or not vm.storage_profile.data_disks:
                        continue
                    for d in vm.storage_profile.data_disks:
                        # Compare by managed disk id
                        if hasattr(d, 'managed_disk') and d.managed_disk and getattr(d.managed_disk, 'id', None) == disk.id:
                            lun = getattr(d, 'lun', None)
                            break
                    if lun is not None:
                        break
            except Exception as e:
                logging.warning(f"Could not resolve LUN for disk {disk_name}: {e}")
            disk_result = {
                'name': disk.name,
                'id': disk.id,
                'type': disk.type,
                'location': disk.location,
                'tags': disk.tags,
                'sku': sku,
                'diskSizeGB': getattr(disk, 'disk_size_gb', None),
                'performanceTier': performance_tier,
            }
            if lun is not None:
                disk_result['lun'] = lun
            return disk_result
        elif resource.type == 'Microsoft.Batch/batchAccounts':
            props = resource.as_dict() if hasattr(resource, 'as_dict') else resource
            pe_mapping = kwargs.get('pe_mapping')
            private_eps = []
            if pe_mapping and props.get('id') in pe_mapping:
                for pe_info in pe_mapping[props.get('id')]:
                    entry = {
                        'pe_name': pe_info.get('pe_name'),
                        'pe_id': pe_info.get('pe_id'),
                        'ip_addresses': pe_info.get('ip_addresses', []),
                        'subresource': pe_info.get('subresource', None)
                    }
                    if 'hostname' in pe_info:
                        entry['hostname'] = pe_info['hostname']
                    private_eps.append(entry)
            elif 'privateEndpointConnections' in props:
                for pe in props['privateEndpointConnections']:
                    pe_id = pe.get('id')
                    private_eps.append({'pe_name': None, 'pe_id': pe_id, 'ip_addresses': [], 'subresource': None})
            return {
                'name': props.get('name'),
                'id': props.get('id'),
                'type': props.get('type'),
                'location': props.get('location'),
                'tags': props.get('tags'),
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
        logging.error(f"Error extracting compute resource {resource.id}: {e}")
        return None
