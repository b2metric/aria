# ARIA — Business & Sales Enablement

Bu klasör, **business** ve **sales** ekipleri için ARIA ürün-enablement dokümanlarını içerir.
Amaç: teknik olmayan paydaşların ürünü doğru anlaması ve sahaya **tutarlı** anlatması.

> **Kapsam notu (code ↔ business ayrımı):** Burada yalnızca **ürünü anlatan** referans
> dokümanlar bulunur (ne yapar, nasıl konuşulur). **GTM stratejisi, pazar araştırması,
> fiyatlandırma stratejisi ve product-design** bu repo'da DEĞİL — GTM profilinde durur:
> `~/projects/b2metric-aria-gtm/docs/` (`gtm-strategy.md`, `market-research.md`, `product-design.md`).
> Sahada fiyat/pazar/rakip verisi gerektiğinde oraya bakın.

## Tek cümlede ARIA

İş kullanıcısının **doğal dilde** sorduğu soruyu, müşterinin **kendi veri ambarına** karşı
**güvenli SQL'e** çevirip **cevap + grafik + iş yorumu** olarak dönen, **sektör-farkında**
bir Conversational BI / AI Data Analyst platformu.

> **Ask. Reason. Illuminate. Act.**

## İçindekiler

| Doküman | Hedef | İçerik |
|---------|-------|--------|
| [product-overview.md](product-overview.md) | Business + Sales | ARIA nedir, hangi problemi çözer, nasıl çalışır, neden farklı, güvenlik & yönetişim |
| [sales-playbook.md](sales-playbook.md) | Sales | Personalar, değer önermesi, keşif soruları, demo akışı, itiraz karşılama, kalifikasyon |
| [../business-test-cases.md](../business-test-cases.md) | Business + Pre-sales | Ürünün iş değerini kanıtlayan somut test senaryoları (TC-01…TC-06) |

## Nasıl kullanılır

- **Sales/SDR:** önce `product-overview.md` (ürünü anla) → sonra `sales-playbook.md` (sahada konuş).
- **Pre-sales/Demo:** `sales-playbook.md` demo akışı + `business-test-cases.md` senaryoları.
- **Business/operasyon:** `product-overview.md` "Güvenlik & Yönetişim" ve "Sınırlar" bölümleri.

> Bu dokümanlar ürünün **gerçekte yaptığını** anlatır (mock değil). Yeni özellik/iddia
> eklemeden önce `docs/technical-architecture.md` ile doğrulayın.
