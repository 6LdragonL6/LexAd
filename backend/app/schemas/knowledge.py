from pydantic import BaseModel

class LawItem(BaseModel):
    id: str
    title: str
    path: str

class IndustryRuleItem(BaseModel):
    id: str
    title: str
    industry: str

class CaseItem(BaseModel):
    id: str
    title: str
    province: str
    penalty_amount: str = ""

class PlatformRuleItem(BaseModel):
    platform: str
    category: str
    title: str

class TemplateItem(BaseModel):
    id: str
    category: str
    original: str
    replacement: str
