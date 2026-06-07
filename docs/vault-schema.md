# ARIA — Semantic Vault Schema

> **Version:** 1.0 | **Date:** 2026-06-07

Bu doküman Obsidian vault'taki tablo metadata dosyalarının yapısını tanımlar.

## Vault Dizin Yapısı

```
docs/vaults/
├── {workspace_id}/
│   └── tables/
│       ├── TABLE_NAME_1.md
│       ├── TABLE_NAME_2.md
│       ├── ...
│       └── _relationships.md    (opsiyonel, cross-table)
│
├── stc-kuwait/                  (örnek workspace)
│   └── tables/
│       ├── SALES_FACT.md
│       ├── DIM_CUSTOMER.md
│       ├── DIM_TIME.md
│       └── DIM_REGION.md
│
└── demo/                        (demo workspace)
    └── tables/
        └── ...
```

## Tablo Dosya Formatı

Her tablo için bir `.md` dosyası. Dosya adı = tablo adı (büyük harf, underscore).

### Tam Örnek: SALES_FACT.md

```markdown
---
table: SALES_FACT
schema: STC
database: ORACLE
description: Satış işlemleri fact tablosu - her satır bir satış transaction'ı

keywords:
  - revenue
  - sales
  - income
  - gelir
  - satış
  - ciro
  - toplam satış

columns:
  - name: TRANSACTION_ID
    type: NUMBER
    primary_key: true
    description: Unique transaction identifier

  - name: CUSTOMER_ID
    type: NUMBER
    foreign_key: DIM_CUSTOMER.CUSTOMER_ID
    description: Müşteri referansı
    keywords:
      - customer
      - müşteri

  - name: PRODUCT_ID
    type: NUMBER
    foreign_key: DIM_PRODUCT.PRODUCT_ID
    description: Ürün referansı

  - name: TIME_ID
    type: NUMBER
    foreign_key: DIM_TIME.TIME_ID
    description: Zaman dimension referansı

  - name: REGION_ID
    type: NUMBER
    foreign_key: DIM_REGION.REGION_ID
    description: Bölge referansı

  - name: AMOUNT
    type: NUMBER(18,2)
    description: Satış tutarı (KWD)
    keywords:
      - revenue
      - total
      - toplam
      - tutar
      - gelir
      - ciro

  - name: QUANTITY
    type: NUMBER
    description: Satılan adet
    keywords:
      - count
      - adet
      - miktar

  - name: DISCOUNT_AMOUNT
    type: NUMBER(18,2)
    description: Uygulanan indirim tutarı
    keywords:
      - discount
      - indirim

  - name: TRANSACTION_DATE
    type: DATE
    description: İşlem tarihi
    keywords:
      - date
      - tarih
      - when
      - ne zaman

  - name: CREATED_AT
    type: TIMESTAMP
    description: Kayıt oluşturma zamanı

relationships:
  - target: DIM_CUSTOMER
    type: many-to-one
    join: CUSTOMER_ID = CUSTOMER_ID
    description: Her satış bir müşteriye ait

  - target: DIM_PRODUCT
    type: many-to-one
    join: PRODUCT_ID = PRODUCT_ID

  - target: DIM_TIME
    type: many-to-one
    join: TIME_ID = TIME_ID

  - target: DIM_REGION
    type: many-to-one
    join: REGION_ID = REGION_ID

row_count: 15000000
last_updated: 2026-06-01
owner: data_engineering
---

# SALES_FACT

Ana satış fact tablosu. Tüm retail kanallarından gelen satış transaction'larını içerir.

## Business Context

- **Granularity:** Her satır = 1 satış transaction'ı
- **Update Frequency:** Daily batch (gece 02:00 UTC)
- **Retention:** 5 yıl
- **Primary Use:** Revenue reporting, sales analytics

## Common Query Patterns

### Aylık Toplam Gelir
```sql
SELECT 
    t.MONTH_NAME,
    t.YEAR,
    SUM(s.AMOUNT) as TOTAL_REVENUE
FROM SALES_FACT s
JOIN DIM_TIME t ON s.TIME_ID = t.TIME_ID
GROUP BY t.MONTH_NAME, t.YEAR
ORDER BY t.YEAR, t.MONTH_NUM
```

### Bölgeye Göre Satış
```sql
SELECT 
    r.REGION_NAME,
    SUM(s.AMOUNT) as REVENUE,
    COUNT(*) as TRANSACTION_COUNT
FROM SALES_FACT s
JOIN DIM_REGION r ON s.REGION_ID = r.REGION_ID
GROUP BY r.REGION_NAME
ORDER BY REVENUE DESC
```

### Top 10 Müşteri
```sql
SELECT 
    c.CUSTOMER_NAME,
    SUM(s.AMOUNT) as TOTAL_SPENT
FROM SALES_FACT s
JOIN DIM_CUSTOMER c ON s.CUSTOMER_ID = c.CUSTOMER_ID
GROUP BY c.CUSTOMER_NAME
ORDER BY TOTAL_SPENT DESC
FETCH FIRST 10 ROWS ONLY
```

## Notes

- AMOUNT her zaman KWD (Kuveyt Dinarı) cinsinden
- DISCOUNT_AMOUNT negatif değer içermez
- NULL DISCOUNT_AMOUNT = indirim uygulanmamış
- Tarih filtreleri için TRANSACTION_DATE kullan, CREATED_AT değil

## Data Quality Rules

- AMOUNT > 0 (negatif satış yok, iadeler ayrı tabloda)
- QUANTITY >= 1
- CUSTOMER_ID NOT NULL (anonim satış yok)
```

## YAML Frontmatter Alanları

### Zorunlu Alanlar

| Alan | Tip | Açıklama |
|------|-----|----------|
| `table` | string | Tablo adı (database'deki gibi) |
| `schema` | string | Schema/owner adı |
| `columns` | array | Kolon tanımları listesi |

### Opsiyonel Alanlar

| Alan | Tip | Default | Açıklama |
|------|-----|---------|----------|
| `database` | string | - | Database tipi (ORACLE, POSTGRESQL, MYSQL, MSSQL) |
| `description` | string | - | Tablo açıklaması |
| `keywords` | array | [] | Tablo seviyesi anahtar kelimeler (TR/EN) |
| `relationships` | array | [] | Foreign key ilişkileri |
| `row_count` | number | - | Yaklaşık satır sayısı |
| `last_updated` | date | - | Son güncelleme tarihi |
| `owner` | string | - | Sorumlu ekip/kişi |

### Column Alanları

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| `name` | string | ✅ | Kolon adı |
| `type` | string | ✅ | Veri tipi (NUMBER, VARCHAR2, DATE, etc.) |
| `description` | string | ❌ | Kolon açıklaması |
| `keywords` | array | ❌ | Kolon için anahtar kelimeler |
| `primary_key` | bool | ❌ | Primary key mi? |
| `foreign_key` | string | ❌ | FK referansı: `TABLE.COLUMN` |
| `nullable` | bool | ❌ | NULL olabilir mi? (default: true) |
| `default` | string | ❌ | Default değer |

### Relationship Alanları

| Alan | Tip | Zorunlu | Açıklama |
|------|-----|---------|----------|
| `target` | string | ✅ | Hedef tablo adı |
| `join` | string | ✅ | Join koşulu: `LOCAL_COL = TARGET_COL` |
| `type` | string | ❌ | İlişki tipi: `one-to-one`, `one-to-many`, `many-to-one`, `many-to-many` |
| `description` | string | ❌ | İlişki açıklaması |

## Keyword Best Practices

### Çok Dilli Keyword'ler
Hem İngilizce hem Türkçe (veya müşteri dili) keyword ekle:

```yaml
keywords:
  - revenue        # EN
  - sales          # EN
  - gelir          # TR
  - satış          # TR
  - ciro           # TR
```

### Synonym'ler
Farklı ifade şekillerini ekle:

```yaml
keywords:
  - customer
  - müşteri
  - client
  - alıcı
  - buyer
```

### Domain-Specific Terms
Sektöre özel terimleri ekle:

```yaml
# Telco için
keywords:
  - subscriber
  - abone
  - MSISDN
  - telefon numarası

# Retail için
keywords:
  - SKU
  - ürün kodu
  - barkod
```

## Dimension Table Örneği: DIM_TIME.md

```markdown
---
table: DIM_TIME
schema: STC
database: ORACLE
description: Zaman dimension tablosu - tarih hiyerarşisi

keywords:
  - time
  - date
  - tarih
  - zaman
  - when
  - ne zaman

columns:
  - name: TIME_ID
    type: NUMBER
    primary_key: true
    description: Surrogate key

  - name: FULL_DATE
    type: DATE
    description: Tam tarih
    keywords:
      - date
      - tarih

  - name: DAY_OF_WEEK
    type: NUMBER
    description: Haftanın günü (1=Pazartesi)
    keywords:
      - day
      - gün

  - name: DAY_NAME
    type: VARCHAR2(20)
    description: Gün adı (Monday, Tuesday, ...)
    keywords:
      - day name
      - gün adı

  - name: MONTH_NUM
    type: NUMBER
    description: Ay numarası (1-12)

  - name: MONTH_NAME
    type: VARCHAR2(20)
    description: Ay adı
    keywords:
      - month
      - ay

  - name: QUARTER
    type: NUMBER
    description: Çeyrek (1-4)
    keywords:
      - quarter
      - çeyrek
      - Q1
      - Q2
      - Q3
      - Q4

  - name: YEAR
    type: NUMBER
    description: Yıl
    keywords:
      - year
      - yıl
      - sene

  - name: FISCAL_YEAR
    type: NUMBER
    description: Mali yıl
    keywords:
      - fiscal
      - mali yıl

  - name: IS_WEEKEND
    type: NUMBER(1)
    description: Hafta sonu mu? (0/1)
    keywords:
      - weekend
      - hafta sonu

  - name: IS_HOLIDAY
    type: NUMBER(1)
    description: Resmi tatil mi? (0/1)
    keywords:
      - holiday
      - tatil
      - bayram

relationships: []

row_count: 36500
last_updated: 2026-01-01
---

# DIM_TIME

Tarih dimension tablosu. 100 yıllık tarih aralığını kapsar (1970-2070).

## Hierarchy

```
YEAR
  └── QUARTER
        └── MONTH_NUM / MONTH_NAME
              └── FULL_DATE
                    └── DAY_OF_WEEK / DAY_NAME
```

## Common Filters

- **Bu ay:** `MONTH_NUM = EXTRACT(MONTH FROM SYSDATE) AND YEAR = EXTRACT(YEAR FROM SYSDATE)`
- **Son 12 ay:** `FULL_DATE >= ADD_MONTHS(SYSDATE, -12)`
- **Bu yıl:** `YEAR = EXTRACT(YEAR FROM SYSDATE)`
- **Geçen yıl:** `YEAR = EXTRACT(YEAR FROM SYSDATE) - 1`
```

## _relationships.md (Cross-Table)

Karmaşık join'ler veya birden fazla tablo arasındaki ilişkiler için:

```markdown
---
workspace: stc-kuwait
description: Cross-table relationships and common join patterns
---

# Common Join Patterns

## Star Schema: SALES_FACT Center

```
                    DIM_TIME
                       │
                       │ TIME_ID
                       ▼
DIM_CUSTOMER ──── SALES_FACT ──── DIM_PRODUCT
      │                │                │
      │ CUSTOMER_ID    │                │ PRODUCT_ID
      ▼                │                ▼
                       │
                       │ REGION_ID
                       ▼
                  DIM_REGION
```

## Multi-Hop Joins

### Customer → Sales → Product Category
```sql
SELECT 
    c.CUSTOMER_SEGMENT,
    p.CATEGORY_NAME,
    SUM(s.AMOUNT) as REVENUE
FROM DIM_CUSTOMER c
JOIN SALES_FACT s ON c.CUSTOMER_ID = s.CUSTOMER_ID
JOIN DIM_PRODUCT p ON s.PRODUCT_ID = p.PRODUCT_ID
GROUP BY c.CUSTOMER_SEGMENT, p.CATEGORY_NAME
```

## Alias Conventions

| Table | Alias |
|-------|-------|
| SALES_FACT | s, sf |
| DIM_CUSTOMER | c, dc |
| DIM_PRODUCT | p, dp |
| DIM_TIME | t, dt |
| DIM_REGION | r, dr |
```

## Pipeline'da Kullanımı

SemanticMatcher bu dosyaları şu şekilde kullanır:

1. **Keyword Matching:** User query'deki kelimeler → tablo/kolon keyword'leri
2. **Semantic Similarity:** Query embedding vs tablo description embedding
3. **Relationship Traversal:** İlgili dimension'ları otomatik dahil etme
4. **SQL Template:** Common query patterns'dan yararlanma

```python
# Örnek matching flow
query = "show monthly revenue by region"

# 1. Keyword hit: "revenue" → SALES_FACT.AMOUNT
# 2. Keyword hit: "monthly" → DIM_TIME.MONTH_NAME
# 3. Keyword hit: "region" → DIM_REGION.REGION_NAME
# 4. Relationship: SALES_FACT → DIM_TIME, SALES_FACT → DIM_REGION

# Result: 3 tablo matched, join paths determined
```

## Vault Sync

### MinIO ↔ Local Obsidian

```
MinIO (Primary)                    Local Obsidian
vaults/{workspace}/tables/    ←→   docs/vaults/{workspace}/tables/
        │                                    │
        │ ARIA UI edit                       │ Manual edit
        ▼                                    ▼
    S3 PUT                              File watcher
        │                                    │
        └──────────── Sync ──────────────────┘
```

### Sync Commands

```bash
# MinIO'dan local'e çek
mc mirror minio/aria-vaults/stc-kuwait docs/vaults/stc-kuwait

# Local'den MinIO'ya push
mc mirror docs/vaults/stc-kuwait minio/aria-vaults/stc-kuwait
```

## Validation

Vault dosyaları için schema validation:

```python
# backend/app/schema_discovery/vault_validator.py

REQUIRED_FIELDS = ["table", "schema", "columns"]
COLUMN_REQUIRED = ["name", "type"]

def validate_vault_file(path: str) -> list[str]:
    """Returns list of validation errors, empty if valid."""
    errors = []
    
    with open(path) as f:
        content = f.read()
    
    # Parse YAML frontmatter
    if not content.startswith("---"):
        errors.append("Missing YAML frontmatter")
        return errors
    
    frontmatter = yaml.safe_load(content.split("---")[1])
    
    for field in REQUIRED_FIELDS:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")
    
    for col in frontmatter.get("columns", []):
        for req in COLUMN_REQUIRED:
            if req not in col:
                errors.append(f"Column missing {req}: {col}")
    
    return errors
```

## CLI Araçları

```bash
# Yeni workspace vault oluştur
python -m backend.cli.vault init stc-kuwait

# Database'den vault oluştur (introspection)
python -m backend.cli.vault discover stc-kuwait --schema STC

# Vault validate
python -m backend.cli.vault validate docs/vaults/stc-kuwait

# Vault stats
python -m backend.cli.vault stats docs/vaults/stc-kuwait
# Output: 34 tables, 287 columns, 45 relationships
```
