# ARIA: Business and Customer Test Cases

Bu doküman, ARIA platformunun (NL2SQL ve AI Data Analyst) yeteneklerini bir müşteri veya İş Birimi (Business) perspektifinden test etmek için oluşturulmuştur. Testler, sistemin teknik özelliklerini değil, ürettiği "İş Değerini (Business Value)" hedefler.

## 1. Domain Awareness (Sektörel Bağlam Analizi)

ARIA, veritabanını sadece teknik tablo isimleriyle okumaz. "Semantic Knowledge Graph" yapısıyla sektör terminolojisine (Örn: Telekom'da *Recharge*, Finans'ta *Top-up*) hakimdir.

| Test ID | Soru (Prompt) | Beklenen Çıktı / Davranış | Neyi Doğrular? |
|---------|---------------|---------------------------|-----------------|
| **TC-01** | "Show me total revenue by month" | Sistem, `fct_prep_rev` isimli tabloyu doğrudan hedefler. (Hardcode SQL yazmadan, sadece metadata üzerinden "revenue" kelimesini eşleştirir). | Pure Lexical Metadata Matching. (Veritabanında revenue kelimesi geçmese bile, vault'taki `description` veya `keywords` alanından eşleşme). |
| **TC-02** | "How many people recharged their phones today?" | `fct_prep_recharge` tablosunu bulur, `sum(amount)` yerine `count` veya benzersiz kullanıcı (subscriber) sayısını alır. | NL2SQL motorunun `wants_count` vs `wants_sum` niyetini doğru anlaması. |

## 2. Table Collision Priority (Zaman / Öncelik Yönetimi)

Aynı konuya ait birden fazla tablo olabilir (Güncel tablo vs Geçmiş veri tablosu). ARIA hangisini kullanacağını "Order (Öncelik)" kurallarına göre bilir.

| Test ID | Soru (Prompt) | Beklenen Çıktı / Davranış | Neyi Doğrular? |
|---------|---------------|---------------------------|-----------------|
| **TC-03** | "Get me the subscriber demographics" | İki tablo (Örn: `fct_prep_master` ve `fct_prep_master_hist`) tamamen aynı kelimeleri içerse bile, güncel olanı (`order: 1` olan `fct_prep_master`) seçer. | Vault `order` mantığının kusursuz çalışmasını (Business Priority). |

## 3. Semantic Fallback (Karmaşık İş Mantığı)

Müşteri, tabloda direkt karşılığı olmayan, eş anlamlı kelimeler veya karmaşık çapraz sorgular sorabilir.

| Test ID | Soru (Prompt) | Beklenen Çıktı / Davranış | Neyi Doğrular? |
|---------|---------------|---------------------------|-----------------|
| **TC-04** | "Compare the average top-up value between local and roaming users" | Kural tabanlı (Rule-based) sistem bu karmaşık çapraz eşleşmeyi göremeyeceğinden (confidence < 15), işi anında LLM'e (AI Engine) devreder. LLM, doğru JOIN'leri ve Group By'ı yapar. | LLM Fallback yapısının stabiliteyi koruyarak devreye girmesi. |

## 4. LLM Business Insights (Akıllı Yorumlama)

Grafik çizildikten sonra, ARIA'dan "veriyi yorumlaması" beklenir. Bu yorumlar genel geçer cümleler değil, Business Vault içerisinde o tablo için önceden tanımlanmış stratejik `insights` yönergelerine uygun olmalıdır.

| Test ID | Soru (Prompt) | Beklenen Çıktı / Davranış | Neyi Doğrular? |
|---------|---------------|---------------------------|-----------------|
| **TC-05** | "Show monthly prepaid revenue trend" | Çizgi grafiğinin yanında LLM şu tarz bir özet geçer: *"According to the telecom revenue topic guidelines: Prepaid revenue shows a sharp drop on [Date], mostly driven by Offer ID [X]. Postpaid seems stable."* | Vault'ta tanımlı `domain: telecom` ve `insights` direktiflerinin LLM Output'una (NLG) başarıyla yansıması. |

## 5. Streaming UI Experience (Akışkan UX)

Kullanıcı saniyelerce beyaz ekran izlemez, her aşamada bilgilendirilir.

| Test ID | Davranış (UX) | Beklenen Çıktı | Neyi Doğrular? |
|---------|---------------|----------------|----------------|
| **TC-06** | Arayüze soru yazılıp Enter'a basıldığında | 1. "Analyzing your question..." <br> 2. "Generating SQL..." <br> 3. SQL Preview'ın gelmesi <br> 4. "Building chart..." <br> 5. Grafiğin çizilmesi. | Server-Sent Events (SSE) streaming altyapısının bloklanmadan çalıştığını. |

---

### Müşteriye Not:
ARIA platformu, sizin veri ambarı veya tablolarınızın isimlendirme standartlarına (%100 özel veya karmaşık olsa dahi) "Hardcode" mantıklarla bağımlı değildir. Yeni bir veri ambarı eklendiğinde veya tablo isimleri değiştiğinde **sisteme hiçbir kod yazılmaz**. Sadece Vault (`.md` dosyaları) içerisindeki `keywords`, `order`, ve `insights` parametreleri güncellenir.
