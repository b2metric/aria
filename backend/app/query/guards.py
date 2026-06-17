import re

def verify_read_only_sql(sql: str) -> None:
    """Ensure the SQL query only contains safe, read-only SELECT statements.
    
    Raises:
        ValueError: If the query contains DML/DDL or does not start with SELECT/WITH/EXPLAIN.
    """
    if not sql or not sql.strip():
        raise ValueError("Security Exception: Empty SQL query.")

    # 1. Strip string literals (single and double quotes) to avoid false positives
    # E.g., SELECT 'UPDATE my table' FROM dual -> SELECT '' FROM dual
    sql_no_strings = re.sub(r"'[^']*'|\"[^\"]*\"", "", sql)
    
    # 2. Strip block comments /* ... */
    sql_no_comments = re.sub(r"/\*.*?\*/", "", sql_no_strings, flags=re.DOTALL)
    
    # 3. Strip line comments -- ...
    sql_no_comments = re.sub(r"--.*?\n", "\n", sql_no_comments)
    
    # Normalize
    sql_upper = sql_no_comments.upper().strip()

    # 4. Check for restricted keywords (DDL / DML)
    # Using word boundaries \b to avoid matching sub-words (e.g. "UPDATED_AT")
    unsafe_keywords = [
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bINSERT\b",
        r"\bDROP\b",
        r"\bTRUNCATE\b",
        r"\bALTER\b",
        r"\bCREATE\b",
        r"\bREPLACE\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
        r"\bMERGE\b",
        r"\bEXEC\b",
        r"\bEXECUTE\b",
        r"\bCALL\b",
        r"\bCOMMIT\b",
        r"\bROLLBACK\b",
    ]
    
    for pattern in unsafe_keywords:
        if re.search(pattern, sql_upper):
            raise ValueError(f"Security Exception: Unsafe SQL keyword detected. Only read-only queries are allowed.")
            
    # 5. Must start with a read-only command
    first_word = sql_upper.split()[0] if sql_upper.split() else ""
    if first_word not in ("SELECT", "WITH", "EXPLAIN"):
        raise ValueError(f"Security Exception: SQL must begin with SELECT or WITH. Found: '{first_word}'")
