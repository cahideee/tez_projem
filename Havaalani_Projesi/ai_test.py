import google.generativeai as genai

# Anahtarını buraya hatasız yapıştır
api_key = "AIzaSyAOMSnHPI4HO1BU8hp-rpA94YgCAOx_deQ".strip()
genai.configure(api_key=api_key)

print("--- Desteklenen Modeller Listeleniyor ---")
try:
    # Bilgisayarındaki kütüphanenin tanıdığı modelleri buluyoruz
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    for model_name in available_models:
        print(f"Desteklenen Model: {model_name}")

    # Genellikle 'models/gemini-1.5-flash-latest' veya 'models/gemini-pro' çalışır
    # Listedeki ilk uygun modeli seçiyoruz
    chosen_model = available_models[0]
    print(f"\nSeçilen Model: {chosen_model}")
    
    model = genai.GenerativeModel(chosen_model)
    
    print("Sistem: Test mesajı gönderiliyor...")
    response = model.generate_content("Selam! Bu mesajı hangi model ile cevaplıyorsun?")
    
    print("\n--- YAPAY ZEKA CEVABI ---")
    print(response.text)
    print("------------------------")
    print("\nBAĞLANTI TAMAMLANDI!")

except Exception as e:
    print(f"\nHata oluştu: {e}")