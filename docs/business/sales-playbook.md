# ARIA — Sales Playbook

> Sahada tutarlı anlatım için. Ürün detayı: [`product-overview.md`](product-overview.md).
> **Fiyat, pazar büyüklüğü ve rakip listesi burada DEĞİL** — GTM profilinde:
> `~/projects/b2metric-aria-gtm/docs/`. Bu playbook ürünün **yapabildiklerine dayanır**.

## 1. 30 saniyelik pitch

> "ARIA, ekiplerinizin veriye **kendi diliyle** soru sormasını sağlar. Data ekibinden rapor
> beklemeden, çalışan *'Geçen ay gelir nasıldı?'* yazar; ARIA doğru tabloyu bulur, **güvenli
> SQL** üretir, sonucu **grafik + iş yorumuyla** döner. Veriniz **kendi ambarınızda** kalır;
> kim SQL görür, kim ne kadar sorgular — hepsi **rol ve limitlerle** kontrol altında."

## 2. Hedef personalar & değer önermesi

| Persona | Acısı | ARIA değer önermesi |
|---------|-------|---------------------|
| **Data / Analytics Lead** | Ad-hoc sorgu/rapor backlog'u ekibi boğuyor | Tekrarlayan soruları self-service'e taşır; yönetişim (rol, görünürlük, limit) **sizde kalır** |
| **İş Birimi Yöneticisi** (pazarlama, operasyon, finans) | Veri için data ekibine bağımlı, yavaş | Saniyeler içinde kendi cevabı + grafik + yorum; SQL bilmeden |
| **IT / Güvenlik** | "AI verimizi nereye taşıyor? Kim ne görüyor?" | Veri **kendi ambarınızda**; SSO, RBAC, SQL görünürlüğü, satır/token limiti, silmeden önce yedek |
| **C-level / Sponsor** | Veri-odaklı kültür istiyor ama araçlar teknik | Tüm kuruma yayılabilir doğal-dil analiz katmanı; ölçülebilir token/maliyet kontrolü |

## 3. İdeal müşteri profili (ICP) — kalifikasyon sinyalleri

✅ İyi uyum:
- Bir **ilişkisel veri ambarı** var (Oracle, PostgreSQL vb.).
- **Ad-hoc rapor backlog'u** / data ekibine bağımlılık şikayeti.
- SQL bilmeyen ama veriye ihtiyaç duyan **çok sayıda iş kullanıcısı**.
- **Yönetişim/güvenlik** hassasiyeti (erişim kontrolü, denetim, maliyet sınırı).
- Sektör terminolojisi yoğun veri (telekom, finans, perakende vb.).

⚠️ Zayıf uyum:
- Sadece statik dashboard ihtiyacı (açık uçlu soru yok).
- Veri ambarı yok / dağınık, modellenmemiş ham kaynaklar.

## 4. Keşif soruları (discovery)

- "Bir iş kullanıcısı yeni bir veri sorusu sorduğunda cevap kaç günde geliyor?"
- "Ad-hoc sorgu/rapor talepleri data ekibinizin ne kadar zamanını alıyor?"
- "Veriye erişimde kim neyi görebiliyor — SQL ve ham veriyi herkes mi görüyor?"
- "Veri ambarınız ne? (Oracle / PostgreSQL / …)"
- "Tablolarınız standart mı, kuruma özel isimlendirme mi var?"
- "AI/LLM kullanımında veri yeri ve maliyet kontrolü sizin için ne kadar kritik?"

## 5. Demo akışı (önerilen)

1. **Basit soru** → *"Show me total revenue by month"* → doğru tablo + grafik (TC-01).
2. **Niyet farkı** → *"How many people recharged today?"* → sum değil count (TC-02).
3. **Kod yazmadan uyarlama** → vault `.md` keywords/order'ı gösterip "yeni şema = kod yok" mesajı.
4. **Karmaşık soru → LLM fallback** → *"Compare avg top-up: local vs roaming"* → JOIN'li doğru sonuç (TC-04).
5. **İş yorumu** → grafiğin yanında ARIA'nın domain insight'ı (TC-05).
6. **Yönetişim** → rol değiştir: viewer SQL görmez; satır limiti aşımında arka plan rapor + link.
7. **Streaming UX** → "Analyzing… → Generating SQL… → Building chart…" adımları (TC-06).

> Senaryo detayları: [`../business-test-cases.md`](../business-test-cases.md).

## 6. İtiraz karşılama (objection handling)

| İtiraz | Yanıt (ürüne dayalı) |
|--------|----------------------|
| *"LLM yanlış/uydurma SQL üretmez mi?"* | Kural-tabanlı motor öncelikli; LLM yalnızca fallback. Üretilen SQL **guard + dry-run (EXPLAIN)** ile denetlenir, hatada **self-correction**. İsteyen rol SQL'i görüp doğrular. |
| *"Verimiz AI'a/dışarı gider mi?"* | Sorgular **sizin veri ambarınızda** çalışır; erişim SSO + RBAC ile; token/maliyet limitli; yerel LLM seçeneği var. |
| *"Herkes her veriyi görür mü?"* | **SQL görünürlüğü role bağlı**; viewer yalnızca cevap + grafik görür. Kullanıcı↔takım 1–1, çok-kiracılı izolasyon. |
| *"Şemamız çok özel / sürekli değişiyor."* | **Kod yazmadan** uyarlanır — sadece vault `.md` (keywords/order/insights) güncellenir. |
| *"Maliyet kontrolden çıkar mı?"* | 3-katmanlı token kotası (oturum/kullanıcı/takım), admin-ayarlı; yerel LLM'ler dahil sayılır. |
| *"Zaten PowerBI/dashboard'umuz var."* | ARIA rakip değil **doğal-dil katmanı**; dashboard'un cevaplamadığı açık uçlu soruları kapatır. (Teams/PowerBI köprüsü yol haritasında.) |
| *"Büyük sonuç setleri?"* | Satır limiti + aşımda **arka plan (Prefect) rapor → süreli MinIO linki**; yetkisiz aşım engellenir. |

## 7. Kapanış / sonraki adım

- **Pilot çerçevesi:** 1 veri ambarı + 1 iş birimi + birkaç vault topic ile hızlı PoC.
- **Başarı kriteri:** "data ekibine sormadan cevaplanan soru sayısı" ve "cevap süresi".
- Demo/PoC talebi → pre-sales ile `business-test-cases.md` senaryolarını müşteri verisine uyarlayın.

---

> **Hatırlatma:** Bu playbook ürünün **mevcut yeteneklerine** dayanır. Fiyatlandırma, pazar
> büyüklüğü, rakip karşılaştırma ve resmi konumlandırma için GTM profili
> (`~/projects/b2metric-aria-gtm/docs/`) tek doğruluk kaynağıdır. Yeni ürün iddiası eklemeden
> önce [`../technical-architecture.md`](../technical-architecture.md) ile doğrulayın.
