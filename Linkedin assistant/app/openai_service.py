"""
OpenAI integration for intent classification and parameter extraction
"""
from typing import Dict, Any, Optional, List
from openai import OpenAI
from pydantic import BaseModel, Field
from app.config import Config


class JobSearchParams(BaseModel):
    """Parameters for job search"""
    role: str = Field(description="Job title or role to search for")
    location: Optional[str] = Field(None, description="Location (city, country, or 'remote')")
    keywords: Optional[List[str]] = Field(None, description="Additional keywords or skills")


class IntentResult(BaseModel):
    """Result of intent classification"""
    intent: str = Field(description="PROFILE, JOBS, or UNKNOWN")
    confidence: float = Field(description="Confidence score 0-1")
    job_params: Optional[JobSearchParams] = None


class OpenAIService:
    """Service for OpenAI interactions"""
    
    def __init__(self):
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def classify_intent(self, user_message: str) -> IntentResult:
        """
        Classify user intent and extract parameters
        
        Args:
            user_message: User's text message
            
        Returns:
            IntentResult with intent and extracted parameters
        """
        
        system_prompt = """Ты — ассистент для классификации запросов пользователя.
        
Доступные интенты:
- PROFILE: пользователь спрашивает о своём профиле LinkedIn (опыт, навыки, образование)
- JOBS: пользователь ищет вакансии или хочет узнать о доступных работах
- UNKNOWN: любой другой запрос

Для интента JOBS извлеки параметры:
- role: какую должность/роль ищет (обязательно)
- location: город, страна или "remote" (опционально)
- keywords: дополнительные навыки или ключевые слова (опционально)

Примеры:
"Покажи мой профиль" -> PROFILE
"Какой у меня опыт работы?" -> PROFILE
"Найди вакансии Python разработчика" -> JOBS (role: "Python Developer")
"Вакансии в Берлине для дата сайентиста" -> JOBS (role: "Data Scientist", location: "Berlin")
"Удалённая работа frontend" -> JOBS (role: "Frontend Developer", location: "remote")
"Привет, как дела?" -> UNKNOWN
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                functions=[
                    {
                        "name": "classify_intent",
                        "description": "Classify user intent and extract job search parameters if applicable",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "intent": {
                                    "type": "string",
                                    "enum": ["PROFILE", "JOBS", "UNKNOWN"],
                                    "description": "The classified intent"
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence score between 0 and 1"
                                },
                                "job_params": {
                                    "type": "object",
                                    "properties": {
                                        "role": {
                                            "type": "string",
                                            "description": "Job title or role"
                                        },
                                        "location": {
                                            "type": "string",
                                            "description": "Location or 'remote'"
                                        },
                                        "keywords": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Additional keywords"
                                        }
                                    },
                                    "required": ["role"]
                                }
                            },
                            "required": ["intent", "confidence"]
                        }
                    }
                ],
                function_call={"name": "classify_intent"},
                temperature=0.3
            )
            
            # Extract function call result
            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                import json
                result_dict = json.loads(function_call.arguments)
                
                # Convert job_params if present
                if result_dict.get("job_params"):
                    result_dict["job_params"] = JobSearchParams(**result_dict["job_params"])
                
                return IntentResult(**result_dict)
            
            # Fallback
            return IntentResult(intent="UNKNOWN", confidence=0.5)
            
        except Exception as e:
            print(f"Error in OpenAI classification: {e}")
            return IntentResult(intent="UNKNOWN", confidence=0.0)
    
    def format_profile_response(self, profile_data: Dict[str, Any]) -> str:
        """
        Format LinkedIn profile data into a readable response
        
        Args:
            profile_data: Profile data from LinkedIn MCP
            
        Returns:
            Formatted string response
        """
        response_parts = ["📋 Ваш профиль LinkedIn:\n"]
        
        if profile_data.get("headline"):
            response_parts.append(f"🎯 {profile_data['headline']}\n")
        
        if profile_data.get("summary"):
            response_parts.append(f"\n📝 О себе:\n{profile_data['summary'][:300]}...\n")
        
        if profile_data.get("experience"):
            response_parts.append("\n💼 Опыт работы:")
            for exp in profile_data["experience"][:3]:
                title = exp.get("title", "")
                company = exp.get("companyName", "")
                duration = exp.get("duration", "")
                response_parts.append(f"• {title} в {company} ({duration})")
        
        if profile_data.get("education"):
            response_parts.append("\n\n🎓 Образование:")
            for edu in profile_data["education"][:2]:
                school = edu.get("schoolName", edu.get("school", ""))
                degree = edu.get("degree", "")
                field = edu.get("fieldOfStudy", "")
                response_parts.append(f"• {school}: {degree} {field}".strip())
        
        return "\n".join(response_parts)
    
    def format_jobs_response(self, jobs: List[Dict[str, Any]], limit: int = 5) -> str:
        """
        Format job listings into a readable response
        
        Args:
            jobs: List of job listings
            limit: Maximum number of jobs to show
            
        Returns:
            Formatted string response
        """
        if not jobs:
            return "😔 К сожалению, по вашему запросу не найдено подходящих вакансий. Попробуйте изменить параметры поиска."
        
        response_parts = [f"💼 Найдено вакансий: {len(jobs)}\n"]
        
        if len(jobs) > limit:
            response_parts.append(f"Показываю первые {limit} из {len(jobs)}:\n")
        
        for idx, job in enumerate(jobs[:limit], 1):
            title = job.get("title", "Без названия")
            company = job.get("company", "Компания не указана")
            location = job.get("location", "Локация не указана")
            job_type = job.get("type", "")
            url = job.get("url", "")
            
            response_parts.append(f"{idx}. 🏢 {title}")
            response_parts.append(f"   Компания: {company}")
            response_parts.append(f"   📍 {location}")
            
            if job_type:
                response_parts.append(f"   ⏰ {job_type}")
            
            if job.get("description"):
                desc = job["description"][:150].strip()
                response_parts.append(f"   📄 {desc}...")
            
            if url:
                response_parts.append(f"   🔗 {url}")
            
            response_parts.append("")
        
        if len(jobs) > limit:
            response_parts.append(f"\n💡 Чтобы увидеть больше вакансий, уточните запрос (например, добавьте локацию или навыки).")
        
        return "\n".join(response_parts)
