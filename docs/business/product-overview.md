# ARIA — Ürüne Genel Bakış (Business & Sales)

> Teknik olmayan paydaşlar için. Teknik detay: [`../technical-architecture.md`](../technical-architecture.md).

## 1. Tek bakışta

**ARIA**, iş kullanıcısının doğal dilde sorduğu soruyu, müşterinin **kendi veri ambarına**
karşı güvenli SQL'e çevirip **cevap + grafik + iş yorumu** olarak dönen sektör-farkında bir
**Conversational BI / AI Data Analyst** platformudur.

> **Ask. Reason. Illuminate. Act.** — Sor. Akıl yürüt. Aydınlat. Aksiyon al.

## 2. Hangi problemi çözer?

| Bugünkü acı | ARIA ile |
|-------------|----------|
| İş birimleri her rapor/sorgu için data ekibine bağımlı → **backlog ve gecikme** | Kullanıcı **kendi sorusunu** doğal dilde sorar, saniyeler içinde cevap + grafik alır |
| Klasik BI araçları (dashboard) **önceden tanımlı** sorulara cevap verir; yeni soru = yeni geliştirme | Açık uçlu, **ad-hoc** sorular; dashboard beklemeden |
| SQL bilmeyen kullanıcı veriye erişemez | SQL bilgisi **gerekmez**; isteyen rol SQL'i görebilir, istemeyen sadece cevabı görür |
| Şema/tablo isimleri kurumdan kuruma farklı → araçlar **özelleştirme/kod** ister | **Kod yazmadan** uyarlanır (aşağıya bakın) |
| LLM'ler "uydurma SQL" üretip yanlış sonuç riski taşır | **SQL guard + dry-run + self-correction** ile denetimli üretim |

## 3. Kimin için?

- **İş kullanıcısı / birim yöneticisi:** "Geçen ay gelir nasıldı?" deyip cevabı kendi alır.
- **Data / analytics ekibi:** tekrarlayan ad-hoc sorgu yükünden kurtulur; yönetişimi elinde tutar.
- **IT / güvenlik (alıcı):** veri kurumun kendi ambarında kalır; rol/erişim/limit kontrolleri yerleşik.

## 4. Nasıl çalışır? (sade anlatım)

1. **Sor** — Kullanıcı sohbet arayüzüne doğal dilde yazar: *"Show me total revenue by month."*
2. **Niyeti anla** — ARIA sorunun niyetini çözer (toplam mı, adet mi, trend mi).
3. **Doğru tabloyu bul** — Teknik tablo ismi bilmeye gerek yok: **semantic knowledge graph / vault**
   metadatasından (keywords, öncelik/`order`, açıklama) doğru tabloyu eşleştirir. Sektör
   terminolojisine hakimdir (Telekom *recharge*, Finans *top-up*).
4. **Güvenli SQL üret** — Kural-tabanlı motor yetmezse iş **LLM'e devredilir** (fallback);
   üretilen SQL **guard + dry-run (EXPLAIN)** ile denetlenir, hata olursa **kendini düzeltir**.
5. **Çalıştır & göster** — Sorgu müşterinin veri ambarında çalışır; sonuç **grafiğe** dönüşür ve
   ARIA **iş yorumu (insight)** ekler. Tüm akış **streaming** ile adım adım gösterilir (beyaz ekran yok).

> Somut senaryolar: [`../business-test-cases.md`](../business-test-cases.md) (TC-01…TC-06).

## 5. Neden farklı? (ayrışma noktaları)

- **Sektör-farkındalık:** veriyi sadece tablo ismiyle değil, sektör anlamıyla okur (semantic vault).
- **Kod yazmadan uyarlama:** yeni veri ambarı/şema eklendiğinde **kod yazılmaz** — sadece vault
  `.md` dosyalarındaki `keywords`, `order`, `insights` güncellenir.
- **Denetimli AI:** kural-tabanlı + LLM fallback; SQL guard, dry-run, self-correction → "uydurma" riski düşürülür.
- **Sadece sayı değil, yorum:** grafiğin yanında vault'ta tanımlı stratejik yönergelere uygun iş yorumu.
- **Yerleşik yönetişim:** RBAC, SQL görünürlüğü, satır/token limitleri (aşağıda).
- **Çok-kaynaklı:** müşterinin kendi veri ambarına (ör. Oracle, PostgreSQL) bağlanır.

## 6. Güvenlik & Yönetişim (alıcı/IT için)

| Konu | ARIA'da |
|------|---------|
| **Kimlik & erişim** | Keycloak OIDC + SSO; roller: **admin / team_lead / analyst / viewer** |
| **SQL görünürlüğü** | SQL sorgusu ve ham sonuç yalnızca yetkili roller için (varsayılan: admin/team_lead/analyst); diğerleri yalnızca cevap + grafik görür |
| **Satır limiti** | Müşteri bazında admin-ayarlı (varsayılan 10K). Aşan büyük raporlar arka planda üretilip **MinIO'da süreli (3 gün) link** olarak saklanır; yetkisiz aşım engellenir |
| **Token kotası** | 3 katman — oturum (100K) / kullanıcı (500K) / takım (2M), admin-ayarlı; yerel LLM'ler de sayılır → **maliyet kontrolü** |
| **Hafıza (memory)** | Uzun-dönem hafıza kullanıcı + takım bazında; **insanlı onay** (team_lead) ve admin CRUD paneli |
| **Veri yeri** | Sorgular müşterinin **kendi veri ambarında** çalışır |
| **Silme güvenliği** | Kritik tablolar (müşteri, sorgu, token kullanımı, arka plan işleri) **silinmeden önce MinIO'ya JSON yedek**; kullanıcı/hafıza kayıtları otomatik silinmez |
| **Çok kiracılık** | customers → teams → users hiyerarşisi; kullanıcı ↔ takım **1–1** |

## 7. Desteklenen ortam

- **Veri kaynağı:** müşterinin ilişkisel veri ambarı (ör. Oracle, PostgreSQL) — bağlantı müşteri bazında yapılandırılır.
- **Arayüz:** web tabanlı sohbet + admin paneli + dashboard.
- **Kurulum:** Docker tabanlı; kurumun kendi altyapısı arkasında çalışabilir.

## 8. Kapsam & sınırlar (dürüst beklenti)

- ARIA bir **soru-cevap / ad-hoc analiz** katmanıdır; klasik dashboard araçlarının yerine değil,
  **doğal dil katmanı** olarak konumlanır.
- Bazı entegrasyonlar (ör. Teams / PowerBI köprüsü) **MVP sonrası** yol haritasındadır.
- Sonuç kalitesi, vault metadatasının (keywords/order/insights) doğru kurgulanmasına bağlıdır —
  bu onboarding'in bir parçasıdır ve kod gerektirmez.

> Yol haritası, fiyatlandırma ve pazar konumlandırma: GTM profili
> (`~/projects/b2metric-aria-gtm/docs/`). Bu doküman yalnızca **mevcut ürünü** anlatır.
