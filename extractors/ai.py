"""
Extractor for Azure AI services: Document Intelligence, AI Search, and Bot Services.
"""
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.botservice import AzureBotService


def extract(resource, credential, **kwargs):
    """
    Extractor for Azure AI services: Document Intelligence, AI Search, and Bot Services.
    Follows the same logic as other extractors: receives a single resource, credential, and kwargs.
    """
    pe_mapping = kwargs.get('pe_mapping', {})
    subscription_id = resource.id.split('/')[2]
    result = {
        'name': resource.name,
        'id': resource.id,
        'type': resource.type,
        'location': resource.location,
        'resource_group': resource.id.split('/')[4],
        'tags': getattr(resource, 'tags', {}),
    }

    if resource.type.lower() == 'microsoft.cognitiveservices/accounts':
        client = CognitiveServicesManagementClient(credential, subscription_id)
        acct = client.accounts.get(resource.id.split('/')[4], resource.name)
        minimal = {
            'name': acct.name,
            'id': acct.id,
            'type': acct.type,
            'location': acct.location,
            'resource_group': acct.id.split('/')[4],
            'tags': getattr(acct, 'tags', {}),
        }
        # Pricing tier (SKU)
        pricing_tier = None
        if hasattr(acct, 'sku') and getattr(acct.sku, 'name', None):
            pricing_tier = acct.sku.name
        minimal['pricing_tier'] = pricing_tier
        # Add privateEndpoints if available (hostname now attached in mapping)
        from extractors.private_endpoint_utils import expand_private_endpoint_entries
        pe_list = pe_mapping.get(acct.id, [])
        if pe_list:
            expanded = []
            for pe_info in pe_list:
                expanded.extend(expand_private_endpoint_entries(pe_info))
            minimal['privateEndpoints'] = expanded
        return minimal

    # Azure AI Search (Microsoft.Search/searchServices)
    if resource.type.lower() == 'microsoft.search/searchservices':
        client = SearchManagementClient(credential, subscription_id)
        svc = client.services.get(resource.id.split('/')[4], resource.name)
        result['searchServiceName'] = svc.name
        result['sku'] = svc.sku.name if hasattr(svc, 'sku') and svc.sku else None
        result['location'] = svc.location
        result['tags'] = getattr(svc, 'tags', {})
        from extractors.private_endpoint_utils import expand_private_endpoint_entries
        pe_list = pe_mapping.get(resource.id, [])
        if pe_list:
            expanded = []
            for pe_info in pe_list:
                expanded.extend(expand_private_endpoint_entries(pe_info))
            result['privateEndpoints'] = expanded
        return result

    # Azure Bot Services (Microsoft.BotService/botServices)
    if resource.type.lower() == 'microsoft.botservice/botservices':
        client = AzureBotService(credential, subscription_id)
        bot = client.bots.get(resource.id.split('/')[4], resource.name)
        result['botServiceName'] = bot.name
        result['location'] = bot.location
        result['tags'] = getattr(bot, 'tags', {})
        from extractors.private_endpoint_utils import expand_private_endpoint_entries
        pe_list = pe_mapping.get(resource.id, [])
        if pe_list:
            expanded = []
            for pe_info in pe_list:
                expanded.extend(expand_private_endpoint_entries(pe_info))
            result['privateEndpoints'] = expanded
        return result

    # fallback: just return basic info
    return result
