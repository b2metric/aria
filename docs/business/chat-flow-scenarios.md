# ARIA — Son Kullanıcı Chat Akışı: Senaryolar

> Bu doküman, bir kullanıcı sohbete soru yazdığında ARIA'nın **adım adım** ne yaptığını
> gerçek pipeline'a dayanarak anlatır. Hedef: business + sales + pre-sales ekiplerinin akışı
> uçtan uca anlaması. Teknik referans: [`../pipeline-flow.md`](../pipeline-flow.md),
> [`../technical-architecture.md`](../technical-architecture.md).

## Adım lejantı

| İşaret | Anlamı |
|--------|--------|
| ✅ | **Canlı** — şu an çalışıyor |
| 🔜 | **Planlı** — gelecek sprint; tasarımda var, kodda henüz enforce edilmiyor |

> 🔜 işaretli adımlar bugün **atlanır** (veya basit haliyle geçilir); akış yine de tamamlanır.
> Bunları senaryolara koyduk ki hedef mimari net olsun.

## Pipeline tek bakışta (SSE aşamaları)

```
Kullanıcı sorusu
   │  (Frontend → /query/stream, Server-Sent Events)
   ▼
1) THINKING          ✅  girdi doğrulama + niyet
2) GENERATING_SQL    ✅  memory lookup → vault eşleştirme → SQL üretimi
        ├─ Memory: user → team → cache (Mem0 + Qdrant)        ✅
        ├─ Vault:  docs/vaults/{workspace}/tables/*.md         ✅
        ├─ SQL:    rule-based  ──(düşük güven)──▶ LLM fallback ✅
        ├─ Guard:  SELECT-only / DDL-DML reddi                 ✅
        └─ Dry-run: EXPLAIN + satır tahmini                    🔜
3) SQL_READY         ✅  SQL önizleme (role'e göre görünür)
4) SQL_EXECUTING     ✅  customer DB'de çalıştır
        ├─ DB parolası decrypt                                 ✅
        ├─ Execution Hata (ORA-00904 vs) → Akıllı Self-Correction (Sütun uydurmayı düzelt) ✅
        └─ Yüksek satır → Prefect arka plan → MinIO link       🔜
5) RENDERING_CHART   ✅  Recharts (JSON) çizim · MinIO artifact: CSV (+ PNG 🔜 kaleido)
6) COMPLETE          ✅  cevap + grafik + iş yorumu (insight)
```

> **Grafik render & artifact (önemli):** İnteraktif grafik **client-side Recharts** ile çizilir
> (SSE'deki `chart_data` JSON'undan; `ChartArea`). MinIO'ya **artifact** olarak **CSV** (her zaman)
> ve **statik PNG** (Plotly/Kaleido — yalnızca `kaleido` kurulu ise) yazılır. **Plotly HTML iframe
> kaldırıldı**; Plotly artık sadece opsiyonel PNG export için kullanılır. (PNG için `kaleido`
> bağımlılığı henüz kurulu değil → şu an MinIO'da CSV var, PNG 🔜.)

---

## Senaryo A — Tanıdık soru (Memory **cache HIT**)

**Kullanıcı:** *"Show me total revenue by month"* (bu workspace'te daha önce sorulmuş)

| # | Adım | Durum |
|---|------|-------|
| 1 | `THINKING` — soru alınır, SSE açılır | ✅ |
| 2 | **Memory lookup** (Mem0+Qdrant, embedding ile semantic search): | ✅ |
| 2a | → **User memory** (`{ws}:{user}`): kullanıcının chart tercihi vb. | ✅ |
| 2b | → **Team memory** (`{ws}:team:{team}`): ortak terminoloji/tanımlar | ✅ |
| 2c | → **Query cache** (`{ws}:query_cache`): benzer NL→SQL eşleşmesi **bulundu** (similarity ≥ 0.7) | ✅ |
| 3 | Cache'teki SQL + bağlam yeniden kullanılır → vault/LLM turu kısalır | ✅ |
| 4 | `SQL_EXECUTING` → customer DB'de çalışır | ✅ |
| 5 | `RENDERING_CHART` → çizgi grafik + MinIO artifact | ✅ |
| 6 | `COMPLETE` → cevap + grafik + iş yorumu; kullanıcı saniyeler içinde sonucu görür | ✅ |

> **İş değeri:** tekrarlanan sorular hızlanır; LLM maliyeti düşer.

---

## Senaryo B — Yeni basit soru (cache MISS, **rule-based** SQL)

**Kullanıcı:** *"How many subscribers do we have?"*

| # | Adım | Durum |
|---|------|-------|
| 1 | `THINKING` — niyet: **count** (sum değil) | ✅ |
| 2 | **Memory lookup**: user → team → cache; cache MISS (benzer sorgu yok) | ✅ |
| 3 | `GENERATING_SQL` — **Vault eşleştirme**: `docs/vaults/{ws}/tables/*.md` taranır; keyword + öncelik (`order`) ile en uygun tablo seçilir (ör. `fct_prep_master`) | ✅ |
| 4 | Tek tablo + basit agregasyon → **rule-based generator** (`COUNT`), LLM'e gerek yok | ✅ |
| 5 | **SQL guard** — DDL/DML reddi, sadece SELECT'e izin | ✅ |
| 6 | **Dry-run** — `EXPLAIN` + satır sayısı tahmini | 🔜 |
| 7 | `SQL_READY` — SQL önizleme (yetkili role görünür) | ✅ |
| 8 | `SQL_EXECUTING` → dialect transform (Oracle/PG/…) → customer DB (Hata durumunda Self-Correction devreye girer) | ✅ |
| 8a | DB parolası **decrypt** (şu an düz metin kullanılıyor) | ✅ |
| 9 | `RENDERING_CHART` → tek değer/küçük tablo → uygun görsel | ✅ |
| 10 | `COMPLETE` → cevap + grafik + yorum | ✅ |

---

## Senaryo C — Karmaşık soru (**LLM fallback** + JOIN)

**Kullanıcı:** *"Compare the average top-up value between local and roaming users"*

| # | Adım | Durum |
|---|------|-------|
| 1 | `THINKING` — çapraz karşılaştırma niyeti | ✅ |
| 2 | **Memory lookup**: user → team → cache (team memory'de "top-up=recharge" gibi tanım varsa eşleşir) | ✅ |
| 3 | **Vault eşleştirme**: kural-tabanlı eşleşme güveni düşük (karmaşık çapraz sorgu) | ✅ |
| 4 | Güven eşiğin altında → iş **LLM SQL generator**'a devredilir (schema + memory context ile prompt) | ✅ |
| 5 | LLM doğru **JOIN** + `GROUP BY` + NULL yönetimi ile SQL üretir; sözdizimi doğrulanır | ✅ |
| 6 | SQL guard (SELECT-only) | ✅ |
| 7 | Dry-run (EXPLAIN + satır tahmini) | 🔜 |
| 8 | `SQL_EXECUTING` → customer DB | ✅ |
| 9 | `RENDERING_CHART` → karşılaştırmalı bar/grafik + MinIO | ✅ |
| 10 | `COMPLETE` → cevap + grafik + **domain insight** (vault `insights` yönergesine uygun yorum) | ✅ |

> **İş değeri:** kuralın göremediği karmaşık soru, stabiliteyi bozmadan LLM'e düşer.

---

## Senaryo D — Şirket terminolojisi (**Team memory** devrede)

**Kullanıcı:** *"What's our ARPU trend this year?"* ("ARPU" şirkete özel kısaltma)

| # | Adım | Durum |
|---|------|-------|
| 1 | `THINKING` | ✅ |
| 2 | **Memory lookup** → **Team memory**'de "ARPU = ortalama gelir / abone" tanımı bulunur | ✅ |
| 3 | Bu tanım vault eşleştirmeyi + SQL üretimini yönlendirir (doğru ölçü/tablo) | ✅ |
| 4 | SQL üretimi (rule veya LLM) → guard ✅ → dry-run 🔜 → execute | ✅ / 🔜 |
| 5 | `COMPLETE` → trend grafiği + yorum | ✅ |

> Team memory tanımları **admin/team_lead** tarafından yönetilir (insanlı onay; admin CRUD paneli). Onay akışı kısmen canlı, genişletme 🔜.

---

## Senaryo E — Kullanıcı tercihi & düzeltme (**User memory** yazımı)

**E1 — Düzeltme:** Kullanıcı *"no, I meant by region"* yazar.

| # | Adım | Durum |
|---|------|-------|
| 1 | **Correction detection** — "no/not … meant/use …" (TR/EN) kalıbı yakalanır | ✅ |
| 2 | Önceki sorgu region kırılımıyla yeniden çalıştırılır | ✅ |

**E2 — Tercih:** Kullanıcı *"always show as bar chart"* yazar.

| # | Adım | Durum |
|---|------|-------|
| 1 | **Chart preference detection** → "bar" çıkarılır | ✅ |
| 2 | Tercih **user memory**'ye yazılır (sonraki grafiklerde uygulanır) | ✅ |
| 3 | Başarılı sorgudan NL→SQL eşleşmesi **query cache**'e yazılır (Senaryo A'yı besler) | ✅ |

---

## Senaryo F — Büyük sonuç & **satır yönetişimi**

**Kullanıcı:** *"Export all transactions for last year"* (sonuç > satır limiti, varsayılan 10K)

| # | Adım | Rol | Durum |
|---|------|-----|-------|
| 1 | Dry-run satır tahmini limiti aşıyor | — | 🔜 |
| 2 | **admin / team_lead** → **Prefect arka plan işi** → rapor üretilir → **MinIO süreli (3 gün) link** | admin/lead | 🔜 |
| 3 | **analyst / viewer** → limit aşımı **engellenir**, uyarı gösterilir | analyst/viewer | 🔜 (politika), engelleme ✅ |
| 4 | Limit yalnızca **admin** tarafından değiştirilebilir | admin | ✅ |

> Not: satır limiti aşımında inline gösterim yok; büyük çıktı her zaman MinIO link + log olarak saklanır.

---

## Senaryo G — Yetki & **SQL görünürlüğü**

**Aynı soru, farklı roller:**

| Rol | Cevap + grafik | SQL + ham sonuç | Durum |
|-----|----------------|------------------|-------|
| admin | ✅ görür | ✅ görür | ✅ |
| team_lead | ✅ görür | ✅ görür | ✅ |
| analyst | ✅ görür | ✅ görür | ✅ |
| viewer | ✅ görür | ❌ **gizli** | ✅ |

> SQL görünürlüğü role bağlı + kullanıcı bazında override edilebilir. Kimlik: Keycloak OIDC + SSO.

---

## Senaryo H — Hatalı SQL & **self-correction**

**Kullanıcı:** belirsiz/zor bir soru; ilk SQL DB'de hata verir.

| # | Adım | Durum |
|---|------|-------|
| 1 | SQL üretilir; sözdizimi doğrulama | ✅ |
| 2 | Çalıştırmada hata → **self-correction**: hata mesajıyla SQL yeniden üretilir (sınırlı tur) | ✅ (temel) |
| 3 | Guard (SELECT-only) + dry-run ile hatadan **önce** yakalama | ✅ / 🔜 |
| 4 | Başarısızsa kullanıcıya anlaşılır hata + öneri | ✅ |

---

## Streaming UX (her senaryoda ortak)

Kullanıcı beyaz ekran görmez; her aşama SSE ile akar:

```
"Analyzing your question…"      (THINKING)            ✅
"Generating SQL…"               (GENERATING_SQL)      ✅
[SQL preview]                   (SQL_READY)           ✅  (role'e göre)
"Running query…"                (SQL_EXECUTING)       ✅
"Building chart…"               (RENDERING_CHART)     ✅
[grafik + cevap + insight]      (COMPLETE)            ✅
```

---

## Özet: bugün vs gelecek sprint

| Yetenek | Durum |
|---------|-------|
| Memory (user→team→cache), vault eşleştirme, rule+LLM SQL, dialect, execute, chart+MinIO, insight, streaming, correction/preference, SQL görünürlüğü, self-correction (temel) | ✅ Canlı |
| **SELECT-only / read-only SQL guard** (DDL/DML reddi) | ✅ Canlı |
| **DB parolası decrypt** (şu an düz metin) | ✅ Canlı |
| **EXPLAIN dry-run + satır tahmini** doğrulaması | 🔜 Gelecek sprint |
| **Yüksek-satır → Prefect arka plan → MinIO süreli link** | 🔜 Gelecek sprint |

## 2. Vault Re-Sync (Yaşayan Müşteri Veritabanına Adaptasyon)
Müşteri veritabanlarındaki yapı değiştiğinde (yeni tablo eklendiğinde, kolon eklendiğinde veya değiştiğinde) `docs/vaults` klasörü altındaki verinin **otomatik olarak senkronize edilmesi (Re-sync)** gerekir. Bu süreç için planlanan akış (🔜):
1. **Zamanlanmış Görev (Cron/Prefect):** Sistem, belirlenen saatlerde (örneğin her gece 03:00) müşteri DB'sine readonly bağlanıp şema dökümünü (`information_schema` vb.) alır.
2. **Diff (Fark) Algılama:** Mevcut vault `.md` dosyaları ile yeni gelen schema karşılaştırılır. Yeni eklenen kolonlar md tablolarına otomatik işlenir. 
3. **Manuel "Sync Schema" Tetikleme:** `/admin/schema` UI ekranına eklenecek olan bir "Re-Sync Now" butonuyla backend'deki schema discovery modülü `BackgroundTasks` (FastAPI) veya Celery/Prefect üzerinden asenkron tetiklenerek anında güncelleme sağlanacaktır.

> Yol haritası önceliği ve tarihler GTM/sprint planında tutulur; bu doküman yalnızca akışı ve
> mevcut/planlı durumu gösterir. Yeni iddia eklemeden önce kodla doğrulayın.
