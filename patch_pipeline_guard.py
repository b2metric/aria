import re

with open("backend/app/query/pipeline.py", "r") as f:
    content = f.read()

guard_call = """
    # Security: Verify query is read-only before doing anything
    from backend.app.query.guards import verify_read_only_sql
    verify_read_only_sql(sql)
"""

# Find where _execute_sql starts and place the guard
target = '    """Execute a generated SQL query against the customer\'s database.'

# Insert the guard right after the docstring
parts = content.split(target)
# parts[1] will have the rest of the docstring. Find the end of the docstring.
end_docstring = parts[1].find('    """') + 7
new_content = parts[0] + target + parts[1][:end_docstring] + "\n" + guard_call + parts[1][end_docstring:]

with open("backend/app/query/pipeline.py", "w") as f:
    f.write(new_content)
