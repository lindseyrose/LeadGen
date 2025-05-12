from datetime import datetime
from .data_collector import DataCollector
import asyncio

async def get_leads():
    """Return leads from the data collector service"""
    print("Starting leads collection...")
    # Initialize the data collector
    collector = DataCollector()
    
    try:
        print("Running opportunity scan...")
        opportunities = await collector.scan_opportunities()
        print(f"Found {len(opportunities)} opportunities")
    except Exception as e:
        print(f"Error scanning opportunities: {e}")
        opportunities = []
    
    # Convert opportunities to leads format
    print("Converting opportunities to leads...")
    leads = []
    for idx, opp in enumerate(opportunities):
        contact_info = opp.get('contact_info', {})
        
        # Clean up agency name
        agency = opp.get('agency', '')
        if '(' in agency and ')' in agency:
            # Extract acronym
            name_parts = agency.split('(', 1)
            agency_name = name_parts[0].strip()
            agency_acronym = name_parts[1].split(')', 1)[0].strip()
            agency = f"{agency_name} ({agency_acronym})"
        
        # Create validation messages
        validation_messages = [
            {
                'type': 'info',
                'message': f"Found via {opp.get('source', 'unknown')}: {opp.get('title', '')}"
            }
        ]
        
        # Add contact info validation
        if contact_info.get('url'):
            validation_messages.append({
                'type': 'info',
                'message': f"Contact page available: {contact_info['url']}"
            })
        
        leads.append({
            'id': str(idx + 1),
            'name': opp.get('name', 'Chief Technology Officer'),
            'title': opp.get('title', 'Technology Director'),
            'agency': agency,
            'email': contact_info.get('email', ''),
            'phone': contact_info.get('phone', ''),
            'office': opp.get('office', 'Technology'),
            'dateAdded': opp.get('dateAdded', datetime.now().isoformat()),
            'validationMessages': validation_messages
        })
    
    return {
        "leads": leads,
        "total": len(leads)
    }
