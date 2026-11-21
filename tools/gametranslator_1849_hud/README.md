# GameLingoPro — GameTranslator v1.8.49 sol görev / sağ HUD çevirileri

Bu dal eski **GameLingo** veya `main` üzerindeki mevcut GameLingoPro APK'sını değiştirmez. Kullanıcının sağladığı GameTranslator v1.8.49 kaynakları temelinde çalışan ayrı bir entegrasyon çalışmasıdır.

## Uygulama
- `HudRegionPipeline.kt`: Tam ekran OCR'dan sol görev/ipucu ve sağ bildirim/ödül alanlarını ayırır. Alttaki diyalog altyazısını etkilemez.
- `apply_hud_patch.py`: Kaynak ZIP'i üzerinden Android Engine, SSE SubtitleServer, Flutter ayarları ve webOS 1.0.14 konumlandırmasını günceller.

Örnek: `python tools/gametranslator_1849_hud/apply_hud_patch.py GameLingoPro-GT-kaynak.zip GameLingoPro-HUD-kaynak.zip`

Girdi ZIP dosyası `GameLingoPro/` kök klasörünü içermelidir. Önceki yerel `GameLingoPro-GameTranslator-1.8.49-Fonksiyonel-Temel.zip` buna örnektir. **Kaynak arşivi bu dala yüklenmediğinden buradaki iş akışı henüz Android APK derlemez.**

## Eşdeğer davranış hedefi
- Sol görev metni ile sağ HUD metnini ayrı tutmak
- OCR koordinatlarını TV'ye `region` SSE olaylarıyla göndermek
- LG webOS'ta uzun sağ bildirimleri sola doğru genişletmek
- Gerektiğinde sadece kaybolan kutuyu silmek; alt diyalog çevirisine dokunmamak
- Ayarlarda aç/kapat seçeneği

## Test sınırı
Bağımsız Kotlin davranış testleri ve webOS JS sözdizimi doğrulandı. Android Flutter+NDK derlemesi, gerçek PS5, MediaProjection ve LG HDMI testi henüz yapılmadı. AGPL-3.0 kaynak ve lisans bildirimleri korunmalıdır.
