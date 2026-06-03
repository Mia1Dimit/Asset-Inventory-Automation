"""
Loads and manages all resource extractors. Discovers resources and delegates extraction to the appropriate extractor module for each resource type.
"""
import logging
from typing import Any, Dict, List
 
from importlib import import_module
from azure.mgmt.resource import ResourceManagementClient

class PluginFactory:
    def __init__(self, config: Dict[str, Any], credential):
        self.config = config
        self.credential = credential
        self.handlers = self._load_handlers()

    def _load_handlers(self):
        # Only load extractors set to true in config['families']
        families_cfg = self.config.get('families', {})
        handlers = {}
        for fam, enabled in families_cfg.items():
            if enabled:
                try:
                    mod = import_module(f"extractors.{fam}")
                    handlers[fam] = mod
                except ImportError as e:
                    logging.warning(f"Module {fam} not loaded: {e}")
        # Always load 'generic' as fallback if present
        if 'generic' not in handlers:
            try:
                mod = import_module("extractors.generic")
                handlers['generic'] = mod
            except ImportError as e:
                logging.warning(f"Module generic not loaded: {e}")
        return handlers

    def discover_resources(self, resource_group: str, subscription_id: str) -> List[Any]:
        client = ResourceManagementClient(self.credential, subscription_id)
        return list(client.resources.list_by_resource_group(resource_group))

    def extract_all(self, resources: List[Any], pe_mapping: dict = None) -> Dict[str, List[dict]]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os
        by_type = {}
        def extract_resource(res):
            fam = self._map_type_to_family(res.type)
            handler = self.handlers.get(fam)
            fam_cfg = self.config.get('families', {}).get(fam, {})
            if not fam_cfg or not fam_cfg.get('enabled', False):
                return res.type, None
            # Extract resource type key (e.g., 'databaseAccounts', 'servers', etc.)
            res_type_key = res.type.split('/')[-1]
            # Some types may have subtypes (e.g., Microsoft.Sql/servers/databases)
            if res.type.count('/') > 1:
                res_type_key = res.type.split('/')[-2] + '_' + res.type.split('/')[-1]
            resources_cfg = fam_cfg.get('resources', {})
            enabled = resources_cfg.get(res_type_key, resources_cfg.get(res_type_key.lower(), True))
            if not enabled:
                return res.type, None
            try:
                if handler and hasattr(handler, 'extract'):
                    return res.type, handler.extract(res, self.credential, pe_mapping=pe_mapping)
                else:
                    generic = self.handlers.get('generic')
                    return res.type, generic.extract(res, self.credential, pe_mapping=pe_mapping) if generic else None
            except Exception as e:
                logging.error(f"Error extracting {res.id}: {e}")
                return res.type, None
        max_workers = min(8, os.cpu_count() or 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(extract_resource, res) for res in resources]
            for future in as_completed(futures):
                res_type, extracted = future.result()
                if extracted:
                    by_type.setdefault(res_type, []).append(extracted)
        return by_type

    def _map_type_to_family(self, resource_type: str) -> str:
        mapping = {
            # Compute
            'Microsoft.Compute/virtualMachines': 'compute',
            'Microsoft.Compute/disks': 'compute',
            'Microsoft.Compute/virtualMachineScaleSets': 'compute',
            'Microsoft.Compute/sshPublicKeys': 'compute',
            'Microsoft.Batch/batchAccounts': 'compute',
            # Storage
            'Microsoft.Storage/storageAccounts': 'storage',
            'Microsoft.DataProtection/BackupVaults': 'storage',
            # Network
            'Microsoft.Network/virtualNetworks': 'network',
            'Microsoft.Network/networkInterfaces': 'network',
            'Microsoft.Network/networkSecurityGroups': 'network',
            'Microsoft.Network/loadBalancers': 'network',
            'Microsoft.Network/publicIPAddresses': 'network',
            'Microsoft.Network/privateEndpoints': 'network',
            # Database
            'Microsoft.Sql/servers': 'database',
            'Microsoft.Sql/databases': 'database',
            'Microsoft.Sql/servers/databases': 'database',
            'Microsoft.DBforMySQL/servers': 'database',
            'Microsoft.DBforPostgreSQL/servers': 'database',
            'Microsoft.DBforPostgreSQL/flexibleServers': 'database',
            'Microsoft.DocumentDB/databaseAccounts': 'database',
            'Microsoft.Cache/Redis': 'database',
            # Identity
            'Microsoft.ManagedIdentity/userAssignedIdentities': 'identity',
            'Microsoft.ManagedIdentity/systemAssignedIdentities': 'identity',
            'Microsoft.AzureActiveDirectory/b2cDirectories': 'identity',
            'Microsoft.Applications/registrations': 'identity',
            # App Services
            'Microsoft.Web/sites': 'appservices',
            'Microsoft.Web/serverFarms': 'appservices',
            'Microsoft.Web/serverfarms': 'appservices',
            'Microsoft.Web/connections': 'appservices',
            'Microsoft.Web/functionApps': 'appservices',
            'Microsoft.Web/webApps': 'appservices',

            # AI (Document Intelligence, Search, Bot)
            'Microsoft.CognitiveServices/accounts': 'ai',
            'Microsoft.Search/searchServices': 'ai',
            'Microsoft.BotService/botServices': 'ai',
            # Messaging
            'Microsoft.ServiceBus/namespaces': 'messaging',
            'Microsoft.EventHub/namespaces': 'messaging',
            'Microsoft.EventGrid/domains': 'messaging',
            'Microsoft.EventGrid/topics': 'messaging',
            'Microsoft.Storage/storageQueues': 'messaging',
            # Monitoring & Security
            'Microsoft.OperationalInsights/workspaces': 'monitoring_security',
            'Microsoft.Insights/components': 'monitoring_security',
            'Microsoft.Security/securityContacts': 'monitoring_security',
            # Key Vault
            'Microsoft.KeyVault/vaults': 'keyvault',
            # Data Factory
            'Microsoft.DataFactory/factories': 'datafactory',
            # Synapse
            'Microsoft.Synapse/workspaces': 'synapse',
            # Databricks
            'Microsoft.Databricks/workspaces': 'databricks',
            # OpenShift
            'Microsoft.RedHatOpenShift/openShiftClusters': 'openshift',
            # Container Registry
            'Microsoft.ContainerRegistry/registries': 'containerRegistry',
            # Load Testing
            'Microsoft.LoadTestService/loadTests': 'loadTesting',
        }
        return mapping.get(resource_type, 'generic')

    def get_timestamp(self):
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    # All parameters must be provided explicitly
