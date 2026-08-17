# Mini Google Lens

Bu proje, Google Lens'in temel mantigini ogrenmek icin hazirlanmis sade bir Python projesidir.

## Neler yapiyor?

- Kameradan goruntu alir.
- OpenCV ile goruntuyu hazirlar.
- YOLO ile nesneleri tanir.
- Tesseract OCR ile yazilari okur.
- Nesne ve metin sonucunu ayni ekranda gosterebilir.

## Klasor yapisi

```text
mini_google_lens/
├── main.py
├── detector.py
├── ocr_reader.py
├── image_utils.py
├── requirements.txt
├── setup_windows.bat
├── run_windows.bat
├── check_install.py
└── output/
```

## 1. Python ortami

Python 3.10 veya 3.11 onerilir.

En kolay yol: `setup_windows.bat` dosyasini calistirmak.

Elle kurmak istersen Windows terminalinde proje klasorunde:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Tesseract OCR kurulumu

Nesne tanima icin Tesseract gerekmez. Metin okuma icin gerekir.

Windows'a Tesseract OCR kurduktan sonra program varsayilan olarak su yolu otomatik kontrol eder:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Turkce metin okuyacaksan Tesseract kurulumunda `tur` dil paketinin de kurulu olmasi gerekir.

## 3. Calistirma

Kamera ile:

```bash
python main.py
```

Turkce + Ingilizce OCR ile:

```bash
python main.py --lang tur+eng
```

Bir fotograf uzerinde:

```bash
python main.py --image fotograf.jpg
```

## Tuslar

- `1`: Normal goruntu
- `2`: Nesne tanima
- `3`: Metin okuma
- `4`: Nesne + metin (Lens modu)
- `S`: Ekrani `output` klasorune kaydet
- `Q` veya `ESC`: Cikis

## Ilk calistirmada ne olur?

YOLO'nun kucuk `yolo11n.pt` modeli ilk calistirmada otomatik indirilebilir. Bu nedenle ilk calistirmada internet baglantisi gerekebilir.

## Mantik

```text
Kamera / Fotograf
       |
       v
    OpenCV
       |
       +------> YOLO ------> Nesne kutulari
       |
       +------> OCR -------> Metin kutulari
       |
       v
 Sonuc ekrani
```
