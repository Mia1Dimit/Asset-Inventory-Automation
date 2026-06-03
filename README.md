# Azure Inventory Automation Tool

## Overview
This tool inventories Azure resources in a given resource group and subscription, extracting private endpoint mappings and key metadata for whitelisted services. It is modular, config-driven, and easily extensible for new Azure services.

## Pipeline and File Roles

- **azure_inventory_main.py**: Main entry point. Loads config, discovers resources, builds private endpoint mapping, delegates extraction to plugins, writes JSON and Excel outputs.
- **plugin_factory.py**: Loads extractors for each resource family, manages resource-to-extractor mapping, and parallelizes extraction.
- **extractors/**: Folder with one extractor per Azure resource family (e.g., `compute.py`, `database.py`, `storage.py`, `appservices.py`, etc.). Each extractor implements an `extract()` function. `generic.py` is the fallback for unknown types.
- **common.py**: Logging, config loading, output writing, and shared base class for resources.
- **extractors/private_endpoint_utils.py**: Utility functions for resolving private endpoint IDs and IPs.
- **excel_export.py**: Maps extracted resource data to business columns and writes Excel output.


## Features

- Extracts all whitelisted Azure services and subservices (see `config.yaml`)
- Maps private endpoints and their IPs to resources using a unified, robust mapping in all extractors
- All extractors use a robust, attribute-based Azure SDK extraction pattern for reliability and extensibility (no `.as_dict()` except for sub-objects if needed)
- Flexible Server extractors (e.g., PostgreSQL Flexible Server) now include detailed subnet and virtual network info (`virtualNetwork`, `subnet`, `subnetName`, `delegatedSubnetResourceId`) for reporting
- Excel export logic maps new fields for VMs, disks, NICs, and flexible servers, including subnet formatting as `VN/SUBNET (IP range)` and LUN reporting for disks
- Parallelized extraction for performance
- **Configurable**: enable/disable entire families or individual resource types
- **Easily extensible**: add new extractors or resource types as needed
- **Excel export:** Outputs inventory to an Excel workbook (`.xlsx`) with business-aligned columns and grouping, if `export_excel: true` in `config.yaml`
- **Multi-hostname/IP support:** For resources like storage accounts and Synapse, each (hostname, IP) pair is output as a separate row in Excel
- **Config-driven:** All operational settings (logging, retry, output, extraction) are in `config.yaml`
- **Unified output structure:** Extractors now provide consistent fields (e.g., hostnames, privateEndpoints, subnet info) for downstream processing


## How a Typical Run Works

1. **User runs** `python azure_inventory_main.py --resource-group <RG> --subscription <SUB> --output <OUT>.json --config config.yaml`.
2. The main script loads config and credentials, discovers all resources in the group.
3. It queries all private endpoints and network interfaces, building a unified mapping of service resource IDs to private endpoint info (name, id, IPs, subresource, hostname).
4. Each resource is passed to the correct extractor (plugin) based on its type. Extractors use the private endpoint mapping to attach correct IPs and hostnames, and (for flexible servers) resolve and include subnet and VN info.
5. All extracted resources are grouped by type and written to JSON, preserving all relevant fields for downstream reporting (including subnet/VN info for flexible servers).
6. If enabled, the Excel exporter writes a workbook with one row per (resource, hostname, IP) pair, using business-aligned columns and formatting subnet columns as needed.

## Configuration
- `config.yaml` controls all operational settings:
   - Which resource families and resource types are extracted
   - Logging and retry settings
   - Output options (pretty JSON, Excel export)
- To disable a whole family, set `enabled: false` under that family.
- To disable a specific resource type, set it to `false` under `resources:` for that family.
- Example:
   ```yaml
   families:
      database:
         enabled: true
         resources:
            databaseAccounts: true
            servers: false  # disables SQL servers
            databases: true
   output:
      json_pretty: true
      export_excel: true
   logging:
      level: INFO
   retry:
      max_attempts: 5
      backoff_factor: 2
   ```

## Adding Support for New Services or Features

1. **Create a new extractor:**
   - Add a file in `extractors/` (e.g., `ai.py`).
   - Implement an `extract(resource, credential, **kwargs)` function that returns a dict with all required fields (see other extractors for examples).
   - Use direct attribute access for all fields, following the robust SDK-based extraction pattern (avoid `.as_dict()` except for sub-objects if needed).
   - Use the `pe_mapping` argument to attach private endpoint info if needed (this is now unified for all extractors).
   - Add docstrings and comments explaining the logic.
2. **Register the resource type:**
   - In `plugin_factory.py`, add your Azure resource type to the `_map_type_to_family()` mapping, pointing to your new family (e.g., `'Microsoft.CognitiveServices/accounts': 'ai'`).
   - Add your family to the config.yaml under `families`.
3. **Update config.yaml:**
   - Add your new family and resource types, with `enabled: true` and resource toggles as needed.
4. **Update Excel export (if needed):**
   - If your resource has special fields or needs new columns, update `excel_export.py` to map them.
5. **Test and verify:**
   - Run the pipeline and check both JSON and Excel outputs for your new resource type.
   - Ensure private endpoint mapping works as expected.
6. **Document:**
   - Add/extend docstrings and comments in your extractor and update this README if new concepts are introduced.

## Requirements
- Python 3.8+
- Azure credentials (DefaultAzureCredential)
- Required Python packages (see requirements.txt)
- openpyxl (for Excel export)

## Running on a New Machine
1. Clone the repo
2. Install Python 3.8+ and pip
3. Run `pip install -r requirements.txt`
   - For Excel export, ensure `openpyxl` is installed (included in requirements.txt)
4. Ensure you have Azure credentials (e.g., `az login` or environment variables)
5. Edit `config.yaml` as needed
6. Run the tool as shown above

## Troubleshooting
- If you see warnings about missing extractors, either add the extractor or disable the family in `config.yaml`.
- If a resource is not extracted, check that both the family and resource type are enabled in `config.yaml` and mapped in `_map_type_to_family`.
- For Azure authentication issues, ensure you are logged in with `az login` or have set the appropriate environment variables.
- If Excel export does not work, ensure `openpyxl` is installed and `export_excel: true` is set in config.yaml.

## Extending/Modifying
- To support more Azure services, repeat the steps in **Adding Support for New Services or Features** above.
- For custom extraction logic, implement a new extractor in `extractors/` and ensure it is loaded.
- New extractors should follow the robust, attribute-based SDK extraction pattern for all fields.
- To add new Excel columns or change mapping, edit `excel_export.py`.

## Team Collaboration and Editing
- All code is modular and documented with docstrings and comments.
- Extractors are independent and easy to extend.
- The README and config.yaml should be updated with every new feature or resource type.
- If you have questions, check the docstrings in each file and the comments at the top of each extractor.
