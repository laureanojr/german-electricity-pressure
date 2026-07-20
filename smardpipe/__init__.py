"""SMARD ingestion pipeline for the German-electricity-pressure project.

Weekend-1 scope: download raw SMARD series, aggregate 15-min -> hourly with the
correct units, compute residual load, stitch the commercial net-export series,
and assemble a UTC-keyed ``fact_hourly`` table.

Every design choice here is traceable to ``docs/data_dictionary.md`` and
``docs/methodology.md`` (all sourced from official SMARD material).
"""

__all__ = ["series", "download", "transform", "build"]
