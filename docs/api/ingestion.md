# Generic-delimited ingestion

Reading long- and wide-format CSV/TSV via a manifest. See
[Generic delimited](../formats/generic-delimited.md) and
[Manifest version 1](../formats/manifest-v1.md).

## The manifest

::: openauc.formats.manifest.GenericManifest

::: openauc.formats.manifest.load_manifest

## Parser registry

::: openauc.formats.registry.get_parser

::: openauc.formats.registry.registered_ids

::: openauc.formats.base.FormatInfo

## Extending

A first-party parser subclasses `Parser` and registers itself. See
[Parser detection](../formats/parser-detection.md) and ADR-0004.

::: openauc.formats.base.Parser
