"""
LinkedIn service using direct HTTP API (without MCP)
"""
from typing import Dict, Any, List, Optional
import requests
from app.config import Config


class LinkedInServiceHTTP:
    """Service for interacting with LinkedIn via HTTP API"""
    
    def __init__(self):
        self.api_key = Config.LINKEDIN_MCP_API_KEY
        self.base_url = "https://ligo.ertiqah.com/api/mcp"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_my_profile(self) -> Dict[str, Any]:
        """
        Get current user's LinkedIn profile via HTTP API
        
        Returns:
            Profile data dictionary
        """
        try:
            response = requests.post(
                f"{self.base_url}/linkedin/profile",
                headers=self.headers,
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    profile = data.get("profile", {})
                    return {
                        "headline": profile.get("headline", ""),
                        "summary": profile.get("summary", ""),
                        "experience": profile.get("experience", []),
                        "education": profile.get("education", [])
                    }
                else:
                    return {
                        "error": data.get("error", "Failed to fetch profile"),
                        "headline": "",
                        "summary": "",
                        "experience": [],
                        "education": []
                    }
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "headline": "",
                    "summary": "",
                    "experience": [],
                    "education": []
                }
                
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Network error: {str(e)}",
                "headline": "",
                "summary": "",
                "experience": [],
                "education": []
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "headline": "",
                "summary": "",
                "experience": [],
                "education": []
            }
    
    def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for jobs via HTTP API
        
        Args:
            query: Job role or title
            location: Location filter
            keywords: Additional keywords
            
        Returns:
            List of job dictionaries
        """
        try:
            # Build search query
            search_parts = [f"Найди вакансии для позиции {query}"]
            
            if location:
                if location.lower() == "remote":
                    search_parts.append("с возможностью удалённой работы")
                else:
                    search_parts.append(f"в локации {location}")
            
            if keywords:
                search_parts.append(f"с навыками: {', '.join(keywords)}")
            
            search_query = " ".join(search_parts)
            
            # Call analyze chat API
            response = requests.post(
                f"{self.base_url}/analyze-linkedin-chat",
                headers=self.headers,
                json={
                    "query": search_query,
                    "conversation_history": []
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("reply"):
                    # Return as single informational job
                    return [{
                        "title": f"Результаты поиска: {query}",
                        "company": "LinkedIn",
                        "location": location or "Не указано",
                        "type": "Информация из профиля",
                        "description": str(data.get("reply")),
                        "url": "https://www.linkedin.com/jobs/"
                    }]
            
            return []
            
        except Exception as e:
            print(f"Error searching jobs: {e}")
            return []
    
    def set_linkedin_url(self, linkedin_url: str) -> Dict[str, Any]:
        """Set LinkedIn profile URL"""
        try:
            # Correct endpoint based on cli.js
            response = requests.post(
                f"{self.base_url}/linkedin/set-url",
                headers=self.headers,
                json={"linkedin_url": linkedin_url},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", False),
                    "message": data.get("message", "URL set"),
                    "error": data.get("error")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def refresh_profile(self) -> Dict[str, Any]:
        """Refresh LinkedIn profile data"""
        try:
            response = requests.post(
                f"{self.base_url}/linkedin/refresh-profile",
                headers=self.headers,
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", False),
                    "message": data.get("message", "Profile refreshed"),
                    "error": data.get("error")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


