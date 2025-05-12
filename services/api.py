from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from data_collector import DataCollector

app = FastAPI(title="Gov AI Leads API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Frontend dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data collector
collector = DataCollector()

class Lead(BaseModel):
    id: str
    title: str
    agency: str
    description: str
    type: str
    value: Optional[float]
    posted_date: datetime
    due_date: Optional[datetime]
    url: str
    source: str
    validationMessages: List[dict]
    contact: Optional[dict]
    tech_indicators: List[str]

@app.get("/api/leads", response_model=List[Lead])
async def get_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=5, le=100),
    sort_field: str = Query("posted_date", regex="^(title|agency|type|value|posted_date|due_date|source)$"),
    sort_direction: str = Query("desc", regex="^(asc|desc)$"),
    validation_status: Optional[List[str]] = Query(None),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    email_domains: Optional[List[str]] = Query(None)
):
    """
    Get paginated and filtered leads.
    """
    try:
        # Scan for opportunities
        leads = await collector.scan_opportunities()
        
        # Apply filters
        if validation_status:
            leads = [
                lead for lead in leads
                if any(msg["type"] in validation_status for msg in lead["validationMessages"])
            ]
            
        if date_from or date_to:
            leads = [
                lead for lead in leads
                if (not date_from or lead["posted_date"] >= date_from) and
                (not date_to or lead["posted_date"] <= date_to)
            ]
            
        if email_domains:
            leads = [
                lead for lead in leads
                if any(
                    contact.get("email", "").lower().endswith(domain.lower())
                    for contact in lead.get("contact", {}).values()
                    for domain in email_domains
                )
            ]
        
        # Apply sorting
        reverse = sort_direction == "desc"
        leads.sort(
            key=lambda x: (
                x.get(sort_field) 
                if sort_field != "validationStatus" 
                else x["validationMessages"][0]["type"] if x["validationMessages"] else ""
            ),
            reverse=reverse
        )
        
        # Apply pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_leads = leads[start:end]
        
        return paginated_leads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leads/stats")
async def get_leads_stats():
    """
    Get statistics about the leads.
    """
    try:
        leads = await collector.scan_opportunities()
        return {
            "total": len(leads),
            "by_type": {
                type_: len([l for l in leads if l["type"] == type_])
                for type_ in set(l["type"] for l in leads)
            },
            "by_validation": {
                status: len([
                    l for l in leads 
                    if any(msg["type"] == status for msg in l["validationMessages"])
                ])
                for status in ["error", "warning", "info"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
