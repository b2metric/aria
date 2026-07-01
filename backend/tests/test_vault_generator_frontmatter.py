"""Defense-in-depth: generate_table_markdown must quote the ``generated_at``
timestamp so YAML reads it back as a string, not a datetime. A bare ISO timestamp
is parsed by yaml.safe_load as datetime, which breaks any reader expecting str
(e.g. VaultTableResponse.generated_at → the /admin/schema "Failed to fetch" 500).
"""

from __future__ import annotations

import yaml

from backend.app.schema_discovery.models import ColumnInfo, TableInfo
from backend.app.schema_discovery.vault_generator import generate_table_markdown


def test_generated_at_is_quoted_and_parses_as_str():
    table = TableInfo(name="FCT_X", columns=[ColumnInfo(name="A", data_type="NUMBER")])
    md = generate_table_markdown(table, workspace_id="ws", db_type="oracle")

    frontmatter = yaml.safe_load(md.split("---", 2)[1])
    assert isinstance(frontmatter["generated_at"], str)  # not datetime
