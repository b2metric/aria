import os
import re
import yaml
import logging
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.models.database import CustomerDBConfig
from backend.app.db.models import DBConfig
from backend.app.db.executor import get_executor

logger = logging.getLogger(__name__)

class VaultSyncService:
    """Service to synchronize Markdown vault schemas with the live database."""

    def __init__(self, workspace_id: str, db_config: DBConfig):
        self.workspace_id = workspace_id
        self.db_config = db_config
        self.settings = get_settings()
        self.vault_path = Path(self.settings.vault_base_path) / workspace_id / "tables"
        self.vault_path.mkdir(parents=True, exist_ok=True)

    async def sync(self) -> dict:
        """Run the full synchronization process."""
        logger.info("Starting vault sync for workspace %s", self.workspace_id)

        # 1. Fetch live DB schema
        live_tables = await self._fetch_live_schema()

        # 2. Parse existing markdown files
        existing_tables = self._read_existing_vault()

        stats = {"added": 0, "updated": 0, "unchanged": 0, "deleted": 0}

        # 3. Compare and generate markdown
        for table_name, live_columns in live_tables.items():
            if table_name in existing_tables:
                # Table exists, check if columns changed
                changed = self._update_markdown_if_changed(table_name, live_columns, existing_tables[table_name])
                if changed:
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            else:
                # New table
                self._generate_new_markdown(table_name, live_columns)
                stats["added"] += 1

        return stats

    async def _fetch_live_schema(self) -> dict:
        """Connect to DB and fetch tables & columns."""
        executor = get_executor(self.db_config)
        tables = {}

        db_type = self.db_config.db_type
        if hasattr(db_type, "value"):
            db_type = db_type.value
        db_type_str = str(db_type)

        if db_type_str == "oracle":
            # Oracle uses ALL_TAB_COLUMNS
            sql = """
                SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, NULLABLE
                FROM ALL_TAB_COLUMNS
                WHERE OWNER = :owner
                ORDER BY TABLE_NAME, COLUMN_ID
            """
            owner = self.db_config.username.upper()
            rows = await self._execute_sync_wrap(sql, {"owner": owner})

            for row in rows:
                t_name = row["TABLE_NAME"]
                c_name = row["COLUMN_NAME"]
                c_type = row["DATA_TYPE"]
                nullable = row["NULLABLE"] == "Y"

                if t_name not in tables:
                    tables[t_name] = []
                tables[t_name].append({
                    "name": c_name,
                    "type": c_type,
                    "nullable": nullable,
                    "is_pk": False
                })
        else:
            # PostgreSQL / MySQL / MSSQL (Standard information_schema)
            sql = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' OR table_schema = :schema
                ORDER BY table_name, ordinal_position
            """
            rows = await self._execute_sync_wrap(sql, {"schema": self.db_config.database})
            for row in rows:
                # depending on driver, row could be dict or tuple/object
                t_name = row.get("table_name") if isinstance(row, dict) else getattr(row, "table_name", None)
                if not t_name: continue
                c_name = row.get("column_name") if isinstance(row, dict) else getattr(row, "column_name", None)
                c_type = row.get("data_type") if isinstance(row, dict) else getattr(row, "data_type", None)
                null_val = row.get("is_nullable") if isinstance(row, dict) else getattr(row, "is_nullable", "YES")
                nullable = str(null_val).upper() in ("YES", "TRUE", "1", "Y")

                if t_name not in tables:
                    tables[t_name] = []
                tables[t_name].append({
                    "name": c_name,
                    "type": c_type,
                    "nullable": nullable,
                    "is_pk": False
                })

        return tables

    async def _execute_sync_wrap(self, sql: str, params: dict):
        """Wrapper to run sync executor in async context."""
        import asyncio
        loop = asyncio.get_event_loop()
        executor = get_executor(self.db_config)
        return await loop.run_in_executor(None, lambda: executor.execute(sql, params))

    def _read_existing_vault(self) -> dict:
        """Parse all markdown files in vault to extract existing metadata."""
        import glob
        tables = {}
        files = glob.glob(os.path.join(self.vault_path, "*.md"))

        for f in files:
            table_name = os.path.splitext(os.path.basename(f))[0]
            try:
                with open(f, "r") as fp:
                    content = fp.read()

                # Extract frontmatter and body
                fm_match = re.search(r"^---\n(.*?)\n---(.*)", content, re.DOTALL)
                if not fm_match:
                    continue

                frontmatter_str = fm_match.group(1)
                body = fm_match.group(2)

                try:
                    frontmatter = yaml.safe_load(frontmatter_str) or {}
                except Exception:
                    frontmatter = {}

                # Extract column descriptions from the markdown table
                # Format: | NAME | TYPE | NULL | PK | DESC |
                desc_map = {}
                cols = []
                for line in body.split("\n"):
                    if line.strip().startswith("|") and not line.strip().startswith("| Column") and not line.strip().startswith("|---") and not line.strip().startswith("|--------"):
                        parts = [p.strip() for p in line.split("|")]
                        if len(parts) >= 6:
                            col_name = parts[1].upper()
                            desc_map[col_name] = parts[5]
                            cols.append(parts[1])

                tables[table_name] = {
                    "frontmatter": frontmatter,
                    "body": body,
                    "columns": cols,
                    "desc_map": desc_map
                }
            except Exception as e:
                logger.warning("Failed to read vault file %s: %s", f, e)

        return tables

    def _generate_new_markdown(self, table_name: str, live_columns: list):
        """Create a fresh markdown file for a new table."""
        now_str = datetime.now(timezone.utc).isoformat()
        db_type = self.db_config.db_type
        if hasattr(db_type, "value"):
            db_type = db_type.value
        db_type_str = str(db_type)

        lines = [
            "---",
            f"table: {table_name}",
            f"database: {db_type_str}",
            f"workspace: {self.workspace_id}",
            "keywords: []",
            f"generated_at: '{now_str}'",
            "---",
            "",
            f"# {table_name}",
            "",
            "**Description:** No description provided yet.",
            "",
            "## Columns",
            "",
            "| Column | Type | Nullable | PK | Description |",
            "|--------|------|----------|----|-------------|"
        ]

        for col in live_columns:
            null_mark = "✓" if col["nullable"] else ""
            pk_mark = "✓" if col["is_pk"] else ""
            lines.append(f"| {col['name']} | {col['type']} | {null_mark} | {pk_mark} |  |")

        lines.extend([
            "",
            "## Keywords",
            "",
            "## Business Metadata",
            "",
            "### Column Descriptions"
        ])

        for col in live_columns:
            lines.append(f"- **{col['name']}**: ")

        file_path = self.vault_path / f"{table_name}.md"
        with open(file_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _update_markdown_if_changed(self, table_name: str, live_columns: list, existing: dict) -> bool:
        """Update existing markdown file if columns changed, preserving descriptions and all other blocks."""
        live_col_names = [c["name"].upper() for c in live_columns]
        exist_col_names = [c.upper() for c in existing["columns"]]

        if live_col_names == exist_col_names:
            return False  # No schema changes detected

        logger.info("Schema change detected for %s", table_name)

        now_str = datetime.now(timezone.utc).isoformat()
        fm = existing["frontmatter"]
        fm["enriched_at"] = now_str

        # Rebuild YAML cleanly
        def list_representer(dumper, data):
            if all(isinstance(item, str) for item in data):
                return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data)
        yaml.add_representer(list, list_representer)

        fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False).strip()

        body = existing["body"]
        desc_map = existing["desc_map"]

        # Build new columns table
        new_table_lines = [
            "| Column | Type | Nullable | PK | Description |",
            "|--------|------|----------|----|-------------|"
        ]
        for col in live_columns:
            null_mark = "✓" if col["nullable"] else ""
            pk_mark = "✓" if col["is_pk"] else ""
            desc = desc_map.get(col['name'].upper(), "")
            new_table_lines.append(f"| {col['name']} | {col['type']} | {null_mark} | {pk_mark} | {desc} |")

        new_table_str = "\n".join(new_table_lines)

        # Replace existing Markdown table gracefully
        table_pattern = r"(\| Column \| Type.*?(?:\n\n|\Z))"
        if re.search(table_pattern, body, re.DOTALL):
            body = re.sub(table_pattern, new_table_str + "\n\n", body, count=1, flags=re.DOTALL)

        # Re-build and Replace `### Column Descriptions` list at the bottom
        col_desc_pattern = r"(### Column Descriptions\s*\n)(.*)"
        if re.search(col_desc_pattern, body, re.DOTALL):
            new_list = []
            for col in live_columns:
                desc = desc_map.get(col['name'].upper(), "")
                new_list.append(f"- **{col['name']}**: {desc}")
            body = re.sub(col_desc_pattern, r"\1" + "\n".join(new_list) + "\n", body, count=1, flags=re.DOTALL)

        new_content = f"---\n{fm_str}\n---\n{body}"

        file_path = self.vault_path / f"{table_name}.md"
        with open(file_path, "w") as f:
            f.write(new_content)

        return True
