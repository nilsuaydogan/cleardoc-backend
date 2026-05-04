from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import json
import requests

load_dotenv()

print("ENV PATH TEST:", os.getcwd())
print("API KEY GELDİ Mİ:", os.getenv("OPENROUTER_API_KEY") is not None)

app = FastAPI()


# Request modeli
class AnalyzeRequest(BaseModel):
    text: str
    mode: str


# Health check
@app.get("/")
def home():
    return {"status": "ok"}


# ANALYZE ENDPOINT
@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    api_key = os.getenv("OPENROUTER_API_KEY")
    text = (req.text or "").strip()

    if not text:
        return {
            "analysisType": req.mode,
            "summary": "Metin boş geldi. Lütfen metin yapıştır.",
            "riskLevel": "low",
            "items": []
        }

    if not api_key:
        return {
            "analysisType": req.mode,
            "summary": "OpenRouter API anahtarı bulunamadı.",
            "riskLevel": "low",
            "items": []
        }

    prompt = f"""
Sen ClearDoc adlı uygulamanın analiz motorusun.

Kullanıcının seçtiği mod: {req.mode}

Aşağıdaki metni analiz et ve SADECE geçerli JSON döndür.
Ek açıklama yazma.
Markdown kullanma.
```json gibi etiketler yazma.

Beklenen JSON formatı:
{{
  "analysisType": "{req.mode}",
  "summary": "kısa ve anlaşılır özet",
  "riskLevel": "low",
  "items": ["madde 1", "madde 2", "madde 3"]
}}

Kurallar:
- summary kısa, net ve kullanıcı dostu olsun.
- items kısa maddeler halinde olsun.
- Eğer metinde tek taraflı değişiklik, ceza, faiz, fesih, ek ücret gibi riskli ifadeler varsa riskLevel "medium" veya "high" olabilir.
- Eğer kullanıcı modu "Özetle" ise summary güçlü olsun.
- Eğer kullanıcı modu "Sadeleştir" ise items sade anlatım cümleleri olsun.
- Eğer kullanıcı modu "Risk Analizi" ise items risk maddeleri olsun.

Analiz edilecek metin:
{text}
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-OpenRouter-Title": "ClearDoc",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "Sen resmi metinleri, sözleşmeleri ve karmaşık belgeleri sadeleştiren bir analiz yardımcısısın."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            },
            timeout=60,
        )

        data = response.json()

        if "choices" not in data:
            return {
                "analysisType": req.mode,
                "summary": f"OpenRouter cevabı beklenenden farklı geldi: {data}",
                "riskLevel": "low",
                "items": []
            }

        raw_text = data["choices"][0]["message"]["content"].strip()

        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(raw_text)

        return {
            "analysisType": parsed.get("analysisType", req.mode),
            "summary": parsed.get("summary", ""),
            "riskLevel": parsed.get("riskLevel", "low"),
            "items": parsed.get("items", [])
        }

    except Exception as e:
        return {
            "analysisType": req.mode,
            "summary": f"Hata oluştu: {str(e)}",
            "riskLevel": "low",
            "items": []
        }