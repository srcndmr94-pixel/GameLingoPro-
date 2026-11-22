# GameLingo V6 — mimari geliştirme hattı

Bu dal, çalışan 5.6.x sürümlerinden bağımsız bir **V6 test uygulaması** üretir. Amaç her yeni oyun satırına özel yama yazmak değil, ölçülebilir kalite kazanımlarını sürüm boyunca korumaktır.

## Doğrulanmış ilk temel

- Android paket kimliği: `com.gamelingo.pro.v6test` (sonraki V6 testlerinde **değişmeyecek**).
- `versionCode` CI koşu numarasıyla artar; test uygulaması önceki V6'nın üzerine güncellenebilir.
- Her çalıştırmada aynı **test anahtarı** kullanılır. `v6/signing/v6-debug.jks.b64` sadece geliştirici/test imzasıdır, gizli değildir; **yayın imzası için kullanılmamalıdır.**
- GameTranslator v1.8.49 Android kaynakları ve Google GTX → ML Kit sırası değiştirilmez.
- `V6CaptionAudit` OCR'dan gelen metni gölgede sınıflandırır: konuşma, iki konuşmacı çakışması, görev, şüpheli OCR ve boş.
- `V6TranslationAudit` boş sonuç, aynı İngilizce metin, değişen konuşmacı ve anormal uzunluk riskini kaydeder. **Çeviriyi engellemez**; bu aşamada kaliteden emin olmadan replik silmiyoruz.
- 42 kısa kullanıcı-kaydı/sentetik test vakası `v6/fixtures/` altında. Kotlin JVM testleri CI'da yürür.
- Ekran yakalama, harita sabitleme, altyazı görünürlüğü ve eski uygulamalar korunur.

## Ölçüm referansı (gerçek Pixel 9 Pro kayıtlarından)

5.6.7'nin paylaşılan 27 ölçümünde toplam gecikme ortalama **1.422 ms**, ortanca **1.485 ms**, %90 dilim **1.915 ms**. **5/27** örnek 1 saniyenin altındaydı. Bu değerler V6 performansı değildir.

V6 hedefleri:
- Toplam gecikmede cihazda ölçülen p50 < 800 ms, p90 < 1.500 ms.
- Görünür diyalogların atlanmaması, yanlış konuşmacı karışmaması.
- Özel adların, deyimlerin ve argo/küfrün bağlama göre korunması.
- Harita çevirisinin açık menüde kalması, gerçek menü kapanışında temizlenmesi.
- Her hedefin aynı video ve cihaz koşullarında A/B ölçümüyle doğrulanması.

## Geliştirme aşamaları

1. **Temel ve gözlem (bu sürüm):** Tek test paketi, sabit imza, 42 vakalık regresyon, gölge denetim, otomatik derleme.
2. **Gerçek ekran tekrar testleri:** Kaydedilmiş test karelerinden OCR çıktısı/konum/süre toplama. Video içeriği ve kişiler ancak gerekli izinlerle saklanır; cihaz dışına kişisel ekran görüntüsü göndermek zorunlu değildir.
3. **Tek, modüler OCR→aday→çeviri→overlay yönlendiricisi:** Aynı karenin çift doğrulama yerine sayılmasını engelleme, konuşmacı sınırları, görev bildirimini ayrı işleme, iptal edilen isteklerin güncel sonucu ezmesini önleme.
4. **Bağlam ve kalite:** Önceki 3 repliği ayrı bağlam olarak taşıma, özel isim sözlüğü, şüpheli sonuçları güvenli biçimde yeniden deneme. Ek ücretli API, Gemini ya da token varsayılmaz. Google GTX ağ gecikmesi garanti edilemez.
5. **Sürüm kapısı:** Regresyon testleri + gerçek cihaz gecikme/kaçan replik raporu başarılı olmadan yeni davranışı varsayılan açmama.

## Bilinen sınır

V6'nın ilk APK'sı henüz **mimarinin tam dönüşümü değildir**: mevcut çeviri hâlâ 5.6.8'in kanıtlanmış yolundan geçer. Gölge sınıflandırma ve kalite kontrolleri performansı iyileştirdiği iddiasında bulunmaz. Bu temelin amacı, bir sonraki değişiklikten itibaren sağlam A/B karşılaştırması ve güvenli yükseltme olanağıdır.

## Derleme

Bu dalda `.github/workflows/android.yml` push ile çalışır. Başarılı koşu iki çıktı üretir: `GameLingo-V6-Test-APK` ve `GameLingo-V6-Foundation-Kaynak`.

**Lisans:** GameTranslator koduna ait AGPL-3.0-or-later bildirimleri korunmalıdır. Proje dağıtımında buna uyulmalıdır.
