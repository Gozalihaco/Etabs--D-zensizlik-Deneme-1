# ETABS Düzensizlik Kontrolü (ASCE 7-16 / 7-22)

Açık ve analiz edilmiş ETABS modelinin deprem case sonuçlarıyla yatay ve düşey düzensizlik kontrollerini ve göreli kat ötelemesi kontrolünü yapar. Sonuçları PDF rapor olarak verir.

## Kullanıcılar için (Python gerekmez)

1. `ETABS-Duzensizlik-Kurulum.exe` dosyasını çalıştırın. Yönetici yetkisi gerekmez.
2. Windows "bilgisayarınızı korudu" uyarısı verirse **Ek bilgi → Yine de çalıştır** seçin. Program dijital imzalı olmadığı için bu uyarı normaldir.
3. ETABS'te modelinizi açıp analiz edin.
4. Masaüstündeki **ETABS Düzensizlik Kontrolü** simgesine tıklayın. Siyah bir pencere açılır ve program tarayıcıda başlar. Program siz siyah pencereyi kapatana kadar çalışır.

Kurulum istemeyenler `ETABS-Duzensizlik-Tasinabilir.zip` dosyasını bir klasöre açıp `ETABS-Duzensizlik.exe` dosyasını çalıştırabilir.

**Gereksinimler:** Windows 10/11 64-bit ve ETABS v19, v20 veya v23. İnternet gerekmez.

### Sorun giderme
- **"ETABS API bulunamadı":** ETABS kurulum klasöründeki (ör. `C:\Program Files\Computers and Structures\ETABS 23\`) `RegisterETABS.exe` dosyasına sağ tıklayıp **Yönetici olarak çalıştırın**. Bu işlem bir kez yapılır.
- **"Çalışan bir ETABS bulunamadı":** ETABS açık olmalı ve model yüklü olmalı. ETABS ile program aynı yetkiyle çalışmalı; ETABS'i yönetici olarak açtıysanız programı da yönetici olarak açın.
- **Antivirüs exe'yi engelliyor:** Paketlenmiş Python programlarında bu sık görülen bir yanlış alarmdır. Programı antivirüs istisnalarına ekleyin.

## Geliştirici: exe ve kurulum dosyasını üretmek

Derleme yalnızca bir kez, Windows'ta yapılır. Çıkan dosyaları paylaşırsınız.

### Yöntem A: Kendi bilgisayarınızda
1. 64-bit [Python 3.12](https://www.python.org/downloads/) kurun. Kurulumda "Add python.exe to PATH" seçeneğini işaretleyin.
2. Kurulum dosyası da istiyorsanız [Inno Setup 6](https://jrsoftware.org/isdl.php) kurun. Kurmazsanız yalnızca taşınabilir zip üretilir.
3. `build_exe.bat` dosyasına çift tıklayın.
4. Sonuçlar `cikti` klasöründe oluşur: `ETABS-Duzensizlik-Kurulum.exe` ve `ETABS-Duzensizlik-Tasinabilir.zip`.

### Yöntem B: Python kurmadan, GitHub ile
1. github.com'da bir depo oluşturun ve bu klasördeki dosyaların tamamını yükleyin. `.github` klasörü de yüklenmeli.
2. Depoda **Actions → "Windows kurulum dosyasini derle" → Run workflow** seçin.
3. Derleme yaklaşık 5 dakika sürer. Bitince çalışma sayfasının altındaki **Artifacts** bölümünden zip'i indirin.

## Dosyalar
| Dosya | Görevi |
|---|---|
| `etabs_duzensizlik.html` | Arayüz, ASCE kontrolleri ve PDF rapor |
| `etabs_bridge.py` | ETABS'e COM API ile bağlanan yerel sunucu |
| `build_exe.bat` | Exe, taşınabilir zip ve kurulum dosyasını üretir |
| `installer.iss` | Inno Setup kurulum sihirbazı |
| `requirements-build.txt` | Derleme paketleri |
| `app.ico` | Program simgesi |
| `.github/workflows/build.yml` | GitHub'da otomatik derleme |

Sürüm numarası `etabs_bridge.py` (`APP_VERSION`) ve `installer.iss` (`AppVersion`) dosyalarında birlikte güncellenir.
