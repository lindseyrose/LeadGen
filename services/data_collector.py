import os
import re
import logging
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
import aiohttp
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urljoin

@dataclass
class ValidationMessage:
    """Structured validation message with context and suggestions"""
    message: str
    context: str
    impact: str
    suggestion: str
    priority: int

@dataclass
class ValidationResult:
    """Stores validation results for a contact"""
    is_valid: bool
    errors: List[ValidationMessage]
    warnings: List[ValidationMessage]
    confidence_score: float  # 0.0 to 1.0
    suggested_fixes: Dict[str, str]

class ContactValidationLevel(Enum):
    """Validation levels for contact information"""
    STRICT = 'strict'
    MODERATE = 'moderate'
    LENIENT = 'lenient'

class DataCollector:
    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # API endpoints and sources (focusing on publicly accessible ones)
        self.sources = {
            'usa.gov': {
                'base_url': 'https://www.usa.gov/federal-agencies/a',
                'auth_required': False,
                'type': 'agency_info'
            },
            'challenge.gov': {
                'base_url': 'https://www.challenge.gov/api/challenges',
                'auth_required': False,
                'type': 'challenge'
            },
            'digital.gov': {
                'base_url': 'https://digital.gov/topics',
                'auth_required': False,
                'type': 'tech_info'
            }
        }
        
        # Keywords for AI-related content
        self.ai_keywords = [
            'artificial intelligence',
            'machine learning',
            'deep learning',
            'neural network',
            'AI',
            'ML',
            'data science',
            'computer vision',
            'natural language processing',
            'NLP',
            'automation',
            'robotics',
            'algorithm',
            'analytics',
            'big data',
            'cloud',
            'digital',
            'innovation',
            'research',
            'technology',
            'transformation',
            'modernization',
            'cyber',
            'security',
            'IT',
            'software',
            'computing',
            'emerging tech',
            'emerging technology'
        ]
        
        # Load API keys from environment variables
        self.api_keys = self._load_api_keys()
        
        # Initialize rate limiting settings
        self.rate_limits = {
            'sam.gov': {'calls_per_minute': 60},
            'grants.gov': {'calls_per_minute': 30},
            'fedbizopps': {'calls_per_minute': 100},
            'itdashboard.gov': {'calls_per_minute': 50},
            'acquisition.gov': {'calls_per_minute': 40},
            'usaspending.gov': {'calls_per_minute': 120},
            'sbir.gov': {'calls_per_minute': 30},
            'usa.gov': {'calls_per_minute': 30}
        }
        
        # Cache for agency information
        self.agency_cache: Dict[str, Dict] = {}
    
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment variables"""
        return {}
    
    async def scan_opportunities(self) -> List[Dict[str, Any]]:
        """Scan sources for AI-related opportunities"""
        opportunities = []
        timeout = aiohttp.ClientTimeout(total=30)  # 30 seconds total timeout
        self.logger.info("Starting opportunity scan...")
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for source_name, config in self.sources.items():
                try:
                    self.logger.info(f"Scanning {source_name}...")
                    source_opps = []
                    
                    for attempt in range(3):  # Try up to 3 times
                        try:
                            async with session.get(config['base_url']) as response:
                                if response.status != 200:
                                    raise aiohttp.ClientError(f"HTTP {response.status}")
                                    
                                text = await response.text()
                                soup = BeautifulSoup(text, 'html.parser')
                                
                                if source_name == 'usa.gov':
                                    source_opps = self._parse_agency_index(soup)
                                elif source_name == 'challenge.gov':
                                    source_opps = self._parse_challenge_gov_content(soup)
                                elif source_name == 'digital.gov':
                                    source_opps = self._parse_digital_gov_content(soup)
                                else:
                                    self.logger.warning(f"Unknown source: {source_name}")
                                    source_opps = []
                                opportunities.extend(source_opps)
                                break  # Success, break retry loop
                                
                        except Exception as e:
                            self.logger.error(f"Attempt {attempt + 1} failed for {source_name}: {str(e)}")
                            if attempt == 2:  # Last attempt
                                raise
                            await asyncio.sleep(1)  # Wait before retry
                            
                except Exception as e:
                    self.logger.error(f"Error scanning {source_name}: {str(e)}")
                    continue

        self.logger.info(f"Scan complete. Found {len(opportunities)} total opportunities")
        return self._deduplicate_opportunities(opportunities)
    
    async def _scan_source(self, session: aiohttp.ClientSession, source_name: str, config: Dict) -> List[Dict[str, Any]]:
        """Scan a specific source for opportunities"""
        self.logger.info(f"Scanning {source_name}...")
        
        try:
            async with session.get(config['base_url']) as response:
                if response.status == 200:
                    if source_name == 'usa.gov':
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        return await self._parse_agency_index(soup)
                    elif source_name == 'digital.gov':
                        data = await response.json()
                        return self._parse_digital_gov_content(data)
                    elif source_name == 'challenge.gov':
                        data = await response.json()
                        return self._parse_challenge_opportunities(data)
                    else:
                        return []
                else:
                    self.logger.error(f"Error fetching {source_name}: {response.status}, message='{await response.text()}', url={response.url}")
                    return []
        except Exception as e:
            self.logger.error(f"Error scanning {source_name}: {str(e)}")
            return []
    
    def _parse_agency_index(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse the USA.gov agency index page and extract agency information"""
        self.logger.info("Starting agency parsing...")
        agencies = []
        
        # Try to find the main content area
        main_content = soup.find('main') or soup
        
        # Look for agency sections - they might be in various containers
        agency_sections = []
        for tag in ['section', 'div']:
            agency_sections.extend(main_content.find_all(tag, class_=lambda x: x and any(c in x.lower() for c in ['content', 'agency', 'department'])))
        
        if not agency_sections:
            # Fallback to any div that has a heading and links
            agency_sections = [div for div in main_content.find_all('div') if div.find(['h1', 'h2', 'h3', 'h4']) and div.find('a')]
        
        self.logger.info(f"Found {len(agency_sections)} potential agency sections")
        
        for section in agency_sections:
            try:
                # Look for agency links in this section
                links = section.find_all('a')
                
                for link in links:
                    try:
                        # Skip navigation or utility links
                        if any(x in (link.get('class', []) or []) for x in ['nav', 'menu', 'utility', 'footer']):
                            continue
                            
                        agency_name = link.text.strip()
                        if not agency_name or len(agency_name) < 3:  # Skip empty or very short links
                            continue
                            
                        agency_url = urljoin('https://www.usa.gov', link['href'])
                        
                        # Get description from various possible locations
                        desc_elem = None
                        # Try parent paragraph
                        if link.parent.name == 'p':
                            desc_elem = link.parent
                        # Try next sibling paragraph
                        elif link.find_next_sibling('p'):
                            desc_elem = link.find_next_sibling('p')
                        # Try parent's next sibling if it's a paragraph
                        elif link.parent.find_next_sibling('p'):
                            desc_elem = link.parent.find_next_sibling('p')
                        # Try looking for a description div
                        else:
                            desc_div = link.find_next('div', class_=lambda x: x and 'description' in x.lower())
                            if desc_div:
                                desc_elem = desc_div
                        
                        description = desc_elem.text.strip() if desc_elem else ''
                        
                        # If no description found, use the text from the parent container
                        if not description:
                            container = link.parent
                            while container and container != section:
                                if container.text.strip() != agency_name:
                                    description = container.text.strip()
                                    break
                                container = container.parent
                        
                        self.logger.info(f"Processing agency: {agency_name}")
                        self.logger.debug(f"Description: {description[:100]}...")
                        
                        # Check if AI-related
                        is_ai_related = any(keyword.lower() in description.lower() 
                                          for keyword in self.ai_keywords)
                                          
                        if not is_ai_related:
                            is_ai_related = any(keyword.lower() in agency_name.lower()
                                              for keyword in self.ai_keywords)
                        
                        if not is_ai_related:
                            continue
                            
                        self.logger.info(f"Found AI-related agency: {agency_name}")
                        
                        agencies.append({
                            'id': str(len(agencies) + 1),
                            'name': 'Technology Leadership',
                            'title': 'AI Program Lead',
                            'agency': agency_name,
                            'email': '',
                            'phone': '',
                            'office': 'Technology and Innovation',
                            'dateAdded': datetime.now().isoformat(),
                            'source': 'usa.gov',
                            'contact_info': {
                                'url': agency_url,
                                'email': '',
                                'phone': '',
                            },
                            'description': description
                        })
                        
                    except Exception as e:
                        self.logger.error(f"Error parsing agency link: {str(e)}")
                        continue
                
            except Exception as e:
                self.logger.error(f"Error parsing agency section: {str(e)}")
                continue
                
        self.logger.info(f"Found {len(agencies)} AI-related agencies")
        return agencies
        
    def _parse_challenge_gov_content(self, content: str) -> List[Dict[str, Any]]:
        """Parse Challenge.gov content for AI-related challenges"""
        opportunities = []
        
        try:
            # Parse JSON response
            challenges = json.loads(content)
            self.logger.info(f"Found {len(challenges)} potential challenges")
            
            for idx, challenge in enumerate(challenges):
                try:
                    # Extract challenge details
                    title = challenge.get('title', '').strip()
                    if not title:
                        continue
                        
                    agency = challenge.get('agency', 'Challenge.gov').strip()
                    description = challenge.get('description', '').strip()
                    if not description:
                        description = challenge.get('summary', '').strip()
                        
                    # Get URL
                    url = challenge.get('url', '')
                    if not url:
                        url = f"https://www.challenge.gov/challenge/{challenge.get('slug', '')}" if challenge.get('slug') else ''
                    
                    # Check if AI-related
                    # Also check tags and categories if available
                    is_ai_related = False
                    
                    # Check title and description
                    if self._is_ai_related(title) or self._is_ai_related(description):
                        is_ai_related = True
                        
                    # Check tags
                    if not is_ai_related and challenge.get('tags'):
                        is_ai_related = any(self._is_ai_related(tag) for tag in challenge['tags'])
                        
                    # Check categories
                    if not is_ai_related and challenge.get('categories'):
                        is_ai_related = any(self._is_ai_related(cat) for cat in challenge['categories'])
                    
                    if is_ai_related:
                        self.logger.info(f"Found AI-related challenge: {title}")
                        
                        opportunities.append({
                            'id': str(challenge.get('id', idx)),
                            'name': 'Challenge Manager',
                            'agency': agency,
                            'title': 'Challenge Lead',
                            'email': challenge.get('email', ''),
                            'phone': challenge.get('phone', ''),
                            'office': 'Challenge.gov',
                            'dateAdded': datetime.now().isoformat(),
                            'source': 'challenge.gov',
                            'contact_info': {
                                'url': url,
                                'email': challenge.get('email', ''),
                                'phone': challenge.get('phone', '')
                            },
                            'description': f"{title} - {description}"
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error parsing challenge: {str(e)}")
                    continue
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding Challenge.gov JSON response: {str(e)}")
            # Try parsing as HTML if JSON fails
            soup = BeautifulSoup(content, 'html.parser')
            return self._parse_challenge_gov_html(soup)
        
        self.logger.info(f"Found {len(opportunities)} AI-related challenges")
        return opportunities
        
    def _parse_challenge_gov_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse Challenge.gov HTML content for AI-related challenges"""
        opportunities = []
        
        # Look for cards with links
        cards = soup.find_all(['div', 'article'], class_=lambda x: x and any(c in x.lower() for c in ['card', 'item', 'challenge', 'listing']))
        if not cards:
            # Fallback to any div that has a heading and description
            cards = [div for div in soup.find_all(['div', 'article']) if div.find(['h2', 'h3', 'h4']) and div.find('p')]
            
        self.logger.info(f"Found {len(cards)} potential challenge cards")
        
        for idx, card in enumerate(cards):
            try:
                # Try different ways to find the title
                title_elem = (
                    card.find(['h2', 'h3', 'h4'], class_=lambda x: x and ('title' in x.lower() if x else False)) or
                    card.find(['h2', 'h3', 'h4'])
                )
                
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                if not title:
                    continue
                
                # Try different ways to find the agency
                agency_elem = None
                for tag in ['div', 'span', 'p']:
                    agency_elem = (
                        card.find(tag, class_=lambda x: x and ('agency' in x.lower() or 'department' in x.lower() if x else False)) or
                        card.find(tag, string=lambda x: x and any(word in x.lower() for word in ['agency:', 'department:']))
                    )
                    if agency_elem:
                        break
                        
                agency = agency_elem.text.strip() if agency_elem else 'Challenge.gov'
                if 'agency:' in agency.lower():
                    agency = agency.split(':', 1)[1].strip()
                
                # Try different ways to find the description
                desc_elem = None
                for tag in ['div', 'p', 'span']:
                    desc_elem = (
                        card.find(tag, class_=lambda x: x and any(c in x.lower() for c in ['desc', 'excerpt', 'summary', 'content'] if x)) or
                        card.find(tag, attrs={'data-description': True})
                    )
                    if desc_elem:
                        break
                        
                if not desc_elem:
                    # Try finding the first paragraph that's not the title or agency
                    for p in card.find_all('p'):
                        if p.text.strip() and p != agency_elem:
                            desc_elem = p
                            break
                            
                description = desc_elem.text.strip() if desc_elem else ''
                
                # Get URL
                url = ''
                link = title_elem.find('a')
                if not link:
                    link = card.find('a')
                    
                if link and link.get('href'):
                    url = urljoin('https://www.challenge.gov', link['href'])
                elif card.get('data-url'):
                    url = urljoin('https://www.challenge.gov', card['data-url'])
                
                # Check if AI-related
                if self._is_ai_related(title) or self._is_ai_related(description):
                    self.logger.info(f"Found AI-related challenge: {title}")
                    
                    opportunities.append({
                        'id': str(idx),
                        'name': 'Challenge Manager',
                        'agency': agency,
                        'title': 'Challenge Lead',
                        'email': '',
                        'phone': '',
                        'office': 'Challenge.gov',
                        'dateAdded': datetime.now().isoformat(),
                        'source': 'challenge.gov',
                        'contact_info': {
                            'url': url,
                            'email': '',
                            'phone': ''
                        },
                        'description': f"{title} - {description}"
                    })
                    
            except Exception as e:
                self.logger.error(f"Error parsing challenge card: {str(e)}")
                continue
        
        self.logger.info(f"Found {len(opportunities)} AI-related challenges")
        return opportunities
        
    def _parse_digital_gov_content(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Parse Digital.gov content for AI-related articles"""
        opportunities = []
        
        # Try different ways to find articles
        # First try the main article list
        articles = []
        for tag in ['article', 'div']:
            articles.extend(soup.find_all(tag, class_=lambda x: x and ('post' in x.lower() or 'article' in x.lower())))
            
        self.logger.info(f"Found {len(articles)} potential articles")
        
        for idx, article in enumerate(articles):
            try:
                # Try different ways to find the title
                title_elem = (
                    article.find(['h2', 'h3', 'h4'], class_=lambda x: x and 'title' in x.lower()) or
                    article.find(['h2', 'h3', 'h4'])
                )
                
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                
                # Try different ways to find the description
                desc_elem = (
                    article.find(['div', 'p'], class_=lambda x: x and ('excerpt' in x.lower() or 'summary' in x.lower())) or
                    article.find(['div', 'p'], class_=lambda x: x and 'content' in x.lower()) or
                    article.find('p')
                )
                description = desc_elem.text.strip() if desc_elem else ''
                
                # Get URL
                link = title_elem.find('a') or article.find('a')
                url = urljoin('https://digital.gov', link['href']) if link and link.get('href') else ''
                
                # Try different ways to find the author
                author_elem = (
                    article.find(['div', 'span'], class_=lambda x: x and 'author' in x.lower()) or
                    article.find(['div', 'span'], class_=lambda x: x and 'byline' in x.lower())
                )
                author = author_elem.text.strip() if author_elem else 'Digital.gov Team'
                
                # Try different ways to find the agency
                agency_elem = (
                    article.find(['div', 'span'], class_=lambda x: x and 'agency' in x.lower()) or
                    article.find(['div', 'span'], class_=lambda x: x and 'department' in x.lower())
                )
                agency = agency_elem.text.strip() if agency_elem else 'Digital.gov'
                
                # Since we're on the AI topics page, everything is AI-related
                self.logger.info(f"Found AI-related article: {title}")
                
                opportunities.append({
                    'id': str(idx),
                    'name': author,
                    'agency': agency,
                    'title': 'Digital.gov Author',
                    'email': '',
                    'phone': '',
                    'office': 'Digital.gov',
                    'dateAdded': datetime.now().isoformat(),
                    'source': 'digital.gov',
                    'contact_info': {
                        'url': url,
                        'email': '',
                        'phone': ''
                    },
                    'description': title
                })
                
            except Exception as e:
                self.logger.error(f"Error parsing article: {str(e)}")
                continue
        
        self.logger.info(f"Found {len(opportunities)} AI-related articles")
        return opportunities
        
    def _extract_agency_description(self, soup: BeautifulSoup) -> str:
        """Extract agency description"""
        desc_elem = soup.find('p', class_='usa-intro')
        return desc_elem.text.strip() if desc_elem else ""
        
    def _extract_leadership_info(self, section: BeautifulSoup) -> Dict[str, Any]:
        """Extract leadership information from agency section"""
        leadership = {}
        
        # Look for leadership section
        leadership_section = section.find('div', class_='leadership')
        if not leadership_section:
            return leadership
            
        # Extract leadership positions
        positions = leadership_section.find_all('div', class_='position')
        for position in positions:
            title = position.find('h3')
            name = position.find('p', class_='name')
            if title and name:
                leadership[title.text.strip()] = {
                    'name': name.text.strip(),
                    'title': title.text.strip()
                }
                
        return leadership
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract comprehensive agency contact information"""
        contact_info = {
            'general': {
                'address': '',
                'phone': '',
                'email': '',
                'website': ''
            },
            'leadership': [],
            'departments': {}
        }
        
        # Look for contact section
        contact_section = soup.find('div', class_='contact-info')
        if contact_section:
            # Extract email
            email_elem = contact_section.find(['a', 'span'], href=lambda x: x and '@' in x)
            if email_elem:
                contact_info['general']['email'] = email_elem.get('href', '').replace('mailto:', '')
            
            # Extract phone
            phone_elem = contact_section.find(['a', 'span'], href=lambda x: x and 'tel:' in x)
            if phone_elem:
                contact_info['general']['phone'] = phone_elem.get('href', '').replace('tel:', '')
            
            # Extract address
            address_elem = contact_section.find('address')
            if address_elem:
                contact_info['general']['address'] = address_elem.text.strip()
        
        return contact_info
    
    def _extract_contact_info_from_section(self, section: BeautifulSoup) -> Dict[str, Any]:
        """Extract contact information from a section"""
        contact_info = {
            'name': '',
            'email': '',
            'phone': '',
            'address': ''
        }
        
        # Look for email addresses
        email_elements = section.find_all(['a', 'p', 'div', 'span'], text=re.compile(r'[\w\.-]+@[\w\.-]+\.[\w]+'))
        for element in email_elements:
            text = element.get_text()
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.[\w]+', text)
            if email_match:
                contact_info['email'] = email_match.group(0)
                break
        
        # Look for phone numbers
        phone_patterns = [
            r'\(?([0-9]{3})\)?[-.]?\s*([0-9]{3})[-.]?\s*([0-9]{4})',
            r'([0-9]{10})',
            r'([0-9]{3}[-.]?[0-9]{3}[-.]?[0-9]{4})'
        ]
        
        # First look for phone numbers in specific elements
        phone_elements = section.find_all(['a', 'p', 'div', 'span'], text=re.compile(r'\d{3}[-.)]\s*\d{3}[-.)]\s*\d{4}'))
        for element in phone_elements:
            text = element.get_text()
            for pattern in phone_patterns:
                phone_match = re.search(pattern, text)
                if phone_match:
                    # Format phone number consistently
                    if len(phone_match.groups()) == 3:
                        phone = f"{phone_match.group(1)}-{phone_match.group(2)}-{phone_match.group(3)}"
                    else:
                        phone = phone_match.group(1)
                        phone = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
                    contact_info['phone'] = phone
                    break
            if contact_info['phone']:
                break
        
        # If no phone found in specific elements, try all text
        if not contact_info['phone']:
            text = section.get_text()
        # Look for address
        address_elements = section.find_all(['p', 'div', 'span'], class_=lambda x: x and 'address' in x.lower())
        for element in address_elements:
            text = element.get_text().strip()
            if text and len(text) > 10:  # Basic validation to avoid empty or too short addresses
                contact_info['address'] = text
                break
        
        return contact_info
    
    async def _fetch_agency_details(self, agency_url: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Fetch and parse detailed agency information"""
        try:
            if agency_url in self.agency_cache:
                return self.agency_cache[agency_url]
            
            async with session.get(agency_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract agency details
                    details = {
                        'name': '',
                        'description': '',
                        'contact_info': {},
                        'tech_focus': []
                    }
                    
                    # Get agency name
                    title = soup.find('h1')
                    if title:
                        details['name'] = title.get_text().strip()
                    
                    # Get description
                    description = soup.find('meta', {'name': 'description'})
                    if description:
                        details['description'] = description.get('content', '').strip()
                    
                    # Get contact information
                    contact_section = soup.find('div', class_='contact-info')
                    if contact_section:
                        details['contact_info'] = self._extract_contact_info_from_section(contact_section)
                    
                    # Get technology focus
                    tech_keywords = ['technology', 'digital', 'innovation', 'modernization', 'data', 'artificial intelligence', 'machine learning']
                    content = soup.get_text().lower()
                    details['tech_focus'] = [keyword for keyword in tech_keywords if keyword in content]
                    
                    # Cache the results
                    self.agency_cache[agency_url] = details
                    return details
                else:
                    self.logger.error(f"Failed to fetch agency details from {agency_url}: {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching agency details from {agency_url}: {str(e)}")
            return None
            
        agency_info = {
            'contact': {
                'email': '',
                'website': ''
            },
            'leadership': [],
            'tech_leaders': [],
            'departments': [],
            'social_media': {},
            'additional_contacts': []
        }
        
        return agency_info
        
        # Key technology leadership titles to look for
        tech_leadership_titles = [
            'CIO', 'Chief Information Officer',
            'CTO', 'Chief Technology Officer',
            'CDO', 'Chief Digital Officer',
            'CISO', 'Chief Information Security Officer',
            'IT Director', 'Technology Director',
            'Digital Services',
            'Innovation Officer',
            'Modernization',
            'Data Officer',
            'AI Director', 'Artificial Intelligence'
        ]
        
        # General leadership titles
        leadership_titles = [
            'Secretary', 'Administrator', 'Director',
            'Commissioner', 'Chief', 'Executive',
            'Deputy', 'Assistant Secretary',
            'Under Secretary', 'Principal'
        ]
        
        # Extract general contact information
        contact_section = soup.select_one('div.contact-information')
        if contact_section:
            self._extract_general_contacts(contact_section, contact_info['general'])
        
        # Extract leadership information from various sections
        self._extract_leadership_info(soup, contact_info, tech_leadership_titles, leadership_titles)
        
        # Look for department-specific contacts
        self._extract_department_contacts(soup, contact_info)
        
        # Extract additional contact points
        self._extract_additional_contacts(soup, contact_info)
        
        # Get the main website and look for leadership page if available
        main_website = contact_info['general']['website']
        if main_website:
            leadership_urls = self._find_leadership_urls(main_website)
            if leadership_urls:
                self._extract_leadership_from_urls(leadership_urls, contact_info)
        
        return contact_info
    
    def _extract_general_contacts(self, section: BeautifulSoup, general_info: Dict):
        """Extract general contact information"""
        # Extract phone numbers with labels
        phone_elements = section.select('a[href^="tel:"]')
        for phone_elem in phone_elements:
            label = self._get_element_label(phone_elem)
            phone = phone_elem['href'].replace('tel:', '')
            if label:
                general_info['phone'] = {'number': phone, 'label': label}
    
    def _get_element_label(self, element: BeautifulSoup) -> str:
        """Get the label for a contact element"""
        # Check for label in parent or previous sibling
        label_elem = element.find_previous(['label', 'span'], class_='label')
        if label_elem:
            return label_elem.text.strip()
        
        # Check for label in text content
        text = element.text.strip()
        if ':' in text:
            parts = text.split(':', 1)
            return parts[0].strip()
        
        return ''
    
    def _parse_contact_element(self, element: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Parse a contact element to extract structured information"""
        contact = {}
        
        # Extract name if present
        name_elem = element.find(['h3', 'h4', 'strong'])
        if name_elem:
            contact['name'] = name_elem.text.strip()
        
        # Extract role/title
        title_elem = element.find('p', class_='title')
        if title_elem:
            contact['title'] = title_elem.text.strip()
        
        # Extract email
        email_elem = element.find('a', href=lambda x: x and '@' in x)
        if email_elem:
            contact['email'] = email_elem['href'].replace('mailto:', '')
        
        # Extract phone
        phone_elem = element.find('a', href=lambda x: x and 'tel:' in x)
        if phone_elem:
            contact['phone'] = phone_elem['href'].replace('tel:', '')
        
        return contact if contact else None
    
    def _validate_office(self, office: str) -> ValidationResult:
        """Validate office location format and content"""
        errors = []
        warnings = []
        suggested_fixes = {}

        # Basic validation
        if not office:
            errors.append(ValidationMessage(
                message="Office location is missing",
                context="No office location provided",
                impact="Cannot determine physical location",
                suggestion="Add office location",
                priority=1
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                confidence_score=0.0,
                suggested_fixes=suggested_fixes
            )

        # Length validation
        confidence = 1.0
        if len(office) < 5:
            errors.append(ValidationMessage(
                message="Office location too short",
                context=f"Location '{office}' is only {len(office)} characters",
                impact="May be incomplete",
                suggestion="Provide full address",
                priority=2
            ))
            confidence -= 0.3
        elif len(office) > 200:
            warnings.append(ValidationMessage(
                message="Office location unusually long",
                context=f"Location '{office}' is {len(office)} characters",
                impact="May contain extra information",
                suggestion="Consider shortening or splitting",
                priority=3
            ))
            confidence -= 0.1

        # Format validation
        if not office[0].isupper():
            warnings.append(ValidationMessage(
                message="Location should be capitalized",
                context=f"Location '{office}' starts with lowercase",
                impact="Non-standard formatting",
                suggestion="Capitalize first letter",
                priority=3
            ))
            suggested_fixes[office] = office[0].upper() + office[1:]

        # Common abbreviations
        abbrev_map = {
            'St': 'Street',
            'Ave': 'Avenue',
            'Rd': 'Road',
            'Blvd': 'Boulevard',
            'Ln': 'Lane',
            'Dr': 'Drive',
            'Ct': 'Court',
            'Pl': 'Place',
            'Sq': 'Square',
            'Ste': 'Suite',
            'Rm': 'Room',
            'Fl': 'Floor',
            'Bldg': 'Building',
            'Dept': 'Department'
        }

        for abbrev, full in abbrev_map.items():
            if abbrev in office and full not in office:
                warnings.append(ValidationMessage(
                    message=f"Found abbreviation '{abbrev}'",
                    context=f"Consider using full form '{full}'",
                    impact="May be unclear to some readers",
                    suggestion=f"Replace with '{full}'",
                    priority=3
                ))
                suggested_fixes[office] = office.replace(abbrev, full)
                confidence -= 0.05

        # Calculate final confidence
        confidence = max(0.0, min(1.0, confidence))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=confidence,
            suggested_fixes=suggested_fixes
        )        # Calculate overall confidence score
        contact['validation']['confidence_score'] = self._calculate_confidence_score(contact)
        
        return contact
    
    def _validate_field_relationships(self, contact: Dict[str, Any]) -> None:
        """Validate relationships between different contact fields"""
        if not contact.get('validation'):
            contact['validation'] = {'warnings': []}

        # Check for missing name but present email/phone
        if not contact.get('name'):
            if contact.get('email') or contact.get('phone'):
                contact['validation']['warnings'].append(
                    ValidationMessage(
                        message="Contact has email/phone but no name",
                        context="Email or phone present without associated name",
                        impact="Incomplete contact information",
                        suggestion="Add name for this contact",
                        priority=2
                    )
                )

        # Check for inconsistent department assignments
        dept = contact.get('department', '')
        role = contact.get('role', '')
        if dept and role and dept.lower() not in role.lower():
            contact['validation']['warnings'].append(
                ValidationMessage(
                    message="Department and role mismatch",
                    context=f"Department '{dept}' not reflected in role '{role}'",
                    impact="Possible incorrect department assignment",
                    suggestion="Verify department and role alignment",
                    priority=2
                )
            )

        # Check for mismatched phone area code and office location
        if contact.get('phone') and contact.get('office'):
            area_code = self._extract_area_code(contact.get('phone', ''))
            if area_code:
                office_location = self._get_location_from_area_code(area_code)
                if office_location and office_location.lower() not in contact['office'].lower():
                    contact['validation']['warnings'].append(
                        ValidationMessage(
                            message="Phone area code and office location mismatch",
                            context=f"Area code suggests {office_location} but office is {contact['office']}",
                            impact="Possible incorrect location or phone number",
                            suggestion="Verify phone and office location match",
                            priority=2
                        )
                    )

    def _get_agency_domains(self) -> Dict[str, List[str]]:
        """Get mapping of agency names to their email domains"""
        return {
            # Defense and Intelligence
            'Department of Defense': [
                'mail.mil', 'dod.gov', 'army.mil', 'navy.mil', 'af.mil',
                'marines.mil', 'uscg.mil', 'defense.gov', 'disa.mil',
                'dla.mil', 'darpa.mil', 'nro.mil', 'nsa.gov'
            ],
            'Defense Intelligence Agency': ['dia.mil'],
            'National Security Agency': ['nsa.gov'],
            'Central Intelligence Agency': ['cia.gov'],
            'National Reconnaissance Office': ['nro.gov'],
            'National Geospatial-Intelligence Agency': ['nga.mil', 'nga.gov'],
            
            # Science and Technology
            'Department of Energy': [
                'energy.gov', 'doe.gov', 'science.energy.gov',
                'anl.gov', 'bnl.gov', 'lanl.gov', 'llnl.gov', 'ornl.gov',
                'pnnl.gov', 'sandia.gov', 'nrel.gov'
            ],
            'NASA': [
                'nasa.gov', 'jpl.nasa.gov', 'gsfc.nasa.gov',
                'arc.nasa.gov', 'jsc.nasa.gov', 'ksc.nasa.gov',
                'msfc.nasa.gov', 'larc.nasa.gov'
            ],
            'National Science Foundation': ['nsf.gov', 'research.gov'],
            'National Institute of Standards and Technology': ['nist.gov'],
            
            # Security and Law Enforcement
            'Department of Homeland Security': [
                'dhs.gov', 'fema.gov', 'tsa.gov', 'ice.gov',
                'cbp.gov', 'uscis.gov', 'secret.service.gov',
                'cisa.gov', 'coast.guard.gov'
            ],
            'Department of Justice': [
                'usdoj.gov', 'justice.gov', 'fbi.gov', 'atf.gov',
                'dea.gov', 'bop.gov', 'usmarshals.gov'
            ],
            'Federal Bureau of Investigation': ['fbi.gov', 'ic.fbi.gov'],
            
            # Economic and Financial
            'Department of Commerce': [
                'commerce.gov', 'doc.gov', 'noaa.gov', 'census.gov',
                'uspto.gov', 'trade.gov', 'ntia.gov', 'nist.gov'
            ],
            'Department of Treasury': [
                'treasury.gov', 'irs.gov', 'fiscal.treasury.gov',
                'fincen.gov', 'ttb.gov', 'usmint.gov'
            ],
            'Federal Reserve System': ['frb.gov', 'federalreserve.gov'],
            'Securities and Exchange Commission': ['sec.gov'],
            
            # Health and Human Services
            'Department of Health and Human Services': [
                'hhs.gov', 'nih.gov', 'cdc.gov', 'fda.gov',
                'cms.gov', 'acf.hhs.gov', 'hrsa.gov', 'samhsa.gov'
            ],
            'National Institutes of Health': [
                'nih.gov', 'cancer.gov', 'nci.nih.gov', 'nlm.nih.gov',
                'nhlbi.nih.gov', 'niaid.nih.gov', 'nimh.nih.gov'
            ],
            'Centers for Disease Control': ['cdc.gov'],
            'Food and Drug Administration': ['fda.gov'],
            
            # Transportation and Infrastructure
            'Department of Transportation': [
                'dot.gov', 'faa.gov', 'fhwa.dot.gov', 'fra.dot.gov',
                'fta.dot.gov', 'nhtsa.dot.gov'
            ],
            'Federal Aviation Administration': ['faa.gov'],
            'Federal Highway Administration': ['fhwa.dot.gov'],
            
            # Environment and Agriculture
            'Environmental Protection Agency': [
                'epa.gov', 'energy.gov', 'water.epa.gov',
                'air.epa.gov', 'waste.epa.gov'
            ],
            'Department of Agriculture': [
                'usda.gov', 'fs.fed.us', 'ars.usda.gov',
                'nrcs.usda.gov', 'fns.usda.gov'
            ],
            
            # Administrative and Support
            'General Services Administration': ['gsa.gov', 'usa.gov'],
            'Office of Personnel Management': ['opm.gov', 'usajobs.gov'],
            'Social Security Administration': ['ssa.gov', 'socialsecurity.gov'],
            'United States Postal Service': ['usps.gov', 'uspis.gov'],
            
            # Other Major Departments
            'Department of State': [
                'state.gov', 'usaid.gov', 'america.gov',
                'foreignservice.gov'
            ],
            'Department of Education': ['ed.gov', 'education.gov'],
            'Department of Housing and Urban Development': ['hud.gov'],
            'Department of the Interior': [
                'doi.gov', 'nps.gov', 'blm.gov', 'fws.gov',
                'usgs.gov', 'bia.gov'
            ],
            'Department of Labor': ['dol.gov', 'osha.gov', 'bls.gov'],
            'Department of Veterans Affairs': ['va.gov', 'vba.gov', 'cem.va.gov'],
            
            # Independent Agencies
            'Central Bank': ['federalreserve.gov', 'frbservices.org'],
            'Federal Communications Commission': ['fcc.gov'],
            'Federal Trade Commission': ['ftc.gov'],
            'National Archives': ['nara.gov', 'archives.gov'],
            'Nuclear Regulatory Commission': ['nrc.gov'],
            'Small Business Administration': ['sba.gov'],
            'United States Courts': ['uscourts.gov'],
            
            # Legislative Branch
            'Congress': ['senate.gov', 'house.gov', 'congress.gov'],
            'Government Accountability Office': ['gao.gov'],
            'Library of Congress': ['loc.gov', 'copyright.gov'],
            
            # State and Local Government Patterns
            'State Governments': ['.state.*.us'],
            'County Governments': ['.co.*.*.us'],
            'City Governments': ['.ci.*.*.us', '.city.*.*.us']
        }
    
    def _extract_area_code(self, phone: str) -> Optional[str]:
        """Extract area code from phone number"""
        clean_phone = re.sub(r'[^0-9]', '', phone)
        if len(clean_phone) >= 10:
            return clean_phone[:3]
        return None
    
    def _get_location_from_area_code(self, area_code: str) -> Optional[str]:
        """Get location information from area code"""
        # Sample mapping of area codes to regions (would need to be expanded)
        area_code_map = {
            '202': 'Washington DC',
            '703': 'Northern Virginia',
            '301': 'Maryland',
            '571': 'Northern Virginia',
            '240': 'Maryland',
            '757': 'Virginia Beach',
            '410': 'Baltimore',
            '212': 'New York City',
            '312': 'Chicago',
            '415': 'San Francisco',
            '310': 'Los Angeles'
        }
        return area_code_map.get(area_code)
    
    def _calculate_contact_scores(self, contact: Dict[str, Any]) -> Dict[str, float]:
        """Calculate comprehensive contact scoring metrics"""
        title = contact['title'].lower()
        email = contact['email'].lower()
        hierarchy_level = contact['role_info'].get('category', '')
        tech_focus = contact['role_info'].get('tech_focus', [])
        
        scores = {
            'ai_relevance': 0.0,      # AI/ML relevance
            'tech_influence': 0.0,    # Technology decision-making influence
            'innovation_focus': 0.0,   # Innovation/transformation focus
            'data_expertise': 0.0,    # Data/analytics expertise
            'implementation': 0.0,     # Implementation/execution capability
            'strategic_level': 0.0     # Strategic decision-making level
        }
        
        # AI/ML Relevance Score
        def _is_ai_related(self, text: str) -> bool:
            """Check if text is related to AI"""
            if not text:
                return False
            
            ai_terms = [
                'artificial intelligence', 'machine learning', 'deep learning', 'neural network',
                'ai ', ' ai', 'ai,', 'ai.', 'ai)', 'ai-', 
                'natural language processing', 'nlp', 'computer vision', 'robotics',
                'automation', 'predictive analytics', 'data science', 'cognitive computing',
                'autonomous systems', 'intelligent automation', 'machine intelligence',
                'digital transformation', 'modernization', 'innovation',
                'technology', 'software', 'cloud', 'infrastructure'
            ]
            
            text_lower = text.lower()
            return any(term in text_lower for term in ai_terms)
        
        scores['ai_relevance'] = self._calculate_term_relevance(title, ai_terms)
        
        # Technology Influence Score
        influence_factors = {
            'title_weight': {
                'chief': 1.0, 'director': 0.8, 'head': 0.7,
                'manager': 0.6, 'lead': 0.5, 'senior': 0.4
            },
            'role_weight': {
                'Technology Executive': 1.0, 'AI Leadership': 0.9,
                'Innovation Leader': 0.8, 'Research Leadership': 0.7,
                'Technical Expert': 0.6, 'Project Management': 0.5
            },
            'domain_weight': {
                'technology': 1.0, 'digital': 0.9, 'innovation': 0.8,
                'strategy': 0.7, 'operations': 0.6, 'policy': 0.5
            }
        }
        
        scores['tech_influence'] = self._calculate_influence_score(
            title, hierarchy_level, influence_factors)
        
        # Innovation Focus Score
        innovation_terms = {
            'primary': [
                'innovation', 'transformation', 'modernization',
                'digital strategy', 'change leadership'
            ],
            'secondary': [
                'agile', 'lean', 'continuous improvement',
                'process optimization', 'digital adoption'
            ],
            'related': [
                'strategy', 'initiative', 'program', 'portfolio',
                'roadmap', 'vision'
            ]
        }
        
        scores['innovation_focus'] = self._calculate_term_relevance(title, innovation_terms)
        
        # Data Expertise Score
        data_terms = {
            'primary': [
                'data science', 'analytics', 'big data', 'data engineering',
                'data architecture', 'business intelligence'
            ],
            'secondary': [
                'data management', 'data governance', 'data quality',
                'data integration', 'data modeling'
            ],
            'related': [
                'reporting', 'metrics', 'kpi', 'visualization',
                'dashboard', 'analysis'
            ]
        }
        
        scores['data_expertise'] = self._calculate_term_relevance(title, data_terms)
        
        # Implementation Score
        impl_terms = {
            'primary': [
                'engineer', 'architect', 'developer', 'implementation',
                'deployment', 'operations'
            ],
            'secondary': [
                'technical', 'system', 'infrastructure', 'platform',
                'solution', 'delivery'
            ],
            'related': [
                'support', 'maintenance', 'integration', 'testing',
                'quality', 'performance'
            ]
        }
        
        scores['implementation'] = self._calculate_term_relevance(title, impl_terms)
        
        # Strategic Level Score
        strategic_level = {
            'Executive': 1.0,
            'Technology Executive': 0.9,
            'Innovation Leader': 0.8,
            'AI Leadership': 0.8,
            'Research Leadership': 0.7,
            'Policy Leadership': 0.7,
            'Technical Expert': 0.6,
            'Project Management': 0.5,
            'Operations': 0.4
        }
        
        scores['strategic_level'] = strategic_level.get(hierarchy_level, 0.3)
        
        # Apply context modifiers
        self._apply_context_modifiers(scores, contact)
        
        return scores
    
    def _calculate_term_relevance(self, text: str, term_dict: Dict[str, List[str]]) -> float:
        """Calculate relevance score based on term matching"""
        score = 0.0
        text = text.lower()
        
        # Primary terms (0.6)
        if any(term in text for term in term_dict['primary']):
            score += 0.6
        
        # Secondary terms (0.3)
        if any(term in text for term in term_dict['secondary']):
            score += 0.3
        
        # Related terms (0.1)
        if any(term in text for term in term_dict['related']):
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_influence_score(
        self, title: str, hierarchy_level: str,
        influence_factors: Dict[str, Dict[str, float]]
    ) -> float:
        """Calculate influence score based on multiple factors"""
        score = 0.0
        title = title.lower()
        
        # Title weight
        for key, weight in influence_factors['title_weight'].items():
            if key in title:
                score += weight
                break
        
        # Role weight
        role_weight = influence_factors['role_weight'].get(hierarchy_level, 0.3)
        score += role_weight
        
        # Domain weight
        for domain, weight in influence_factors['domain_weight'].items():
            if domain in title:
                score += weight
                break
        
        return min(1.0, score / 3)  # Normalize by number of factors
    
    def _apply_context_modifiers(self, scores: Dict[str, float], contact: Dict[str, Any]) -> None:
        """Apply context-specific score modifiers"""
        email = contact.get('email', '').lower()
        office = contact.get('office', '').lower()
        
        # Boost scores for .gov/.mil emails
        if any(domain in email for domain in ['.gov', '.mil']):
            for key in scores:
                scores[key] = min(1.0, scores[key] * 1.2)
        
        # Boost for specific office locations
        tech_hubs = ['silicon', 'digital', 'innovation', 'technology', 'research']
        if any(hub in office for hub in tech_hubs):
            scores['tech_influence'] = min(1.0, scores['tech_influence'] * 1.15)
            scores['innovation_focus'] = min(1.0, scores['innovation_focus'] * 1.15)
    
    def _get_title_hierarchy_level(self, title: str) -> Optional[str]:
        """Determine hierarchy level and role from job title"""
        title_lower = title.lower()
        
        # Define hierarchy levels and their keywords
        hierarchy_levels = {
            # Executive Leadership
            'Executive': [
                'secretary', 'administrator', 'director', 'chief',
                'ceo', 'cio', 'cto', 'cfo', 'ciso', 'executive',
                'commissioner', 'superintendent', 'president',
                'chairman', 'chairwoman', 'chairperson'
            ],
            
            # Technology Leadership
            'Technology Executive': [
                'chief technology', 'chief information', 'chief digital',
                'chief innovation', 'chief data', 'chief artificial intelligence',
                'chief machine learning', 'chief analytics', 'chief science',
                'director of technology', 'director of innovation',
                'director of artificial intelligence', 'director of ai',
                'head of technology', 'head of innovation', 'head of ai'
            ],
            
            # Innovation and Transformation
            'Innovation Leader': [
                'innovation officer', 'transformation officer',
                'modernization officer', 'digital transformation',
                'technology transformation', 'innovation lead',
                'change manager', 'innovation strategist',
                'digital strategist', 'modernization lead'
            ],
            
            # AI and Data Science
            'AI Leadership': [
                'ai director', 'machine learning lead', 'ai architect',
                'data science director', 'ai program manager',
                'ai strategy', 'ai policy', 'ai governance',
                'machine learning director', 'ai research director',
                'ai operations', 'ai engineering lead'
            ],
            
            # Technology Management
            'Technology Management': [
                'it director', 'it manager', 'technology manager',
                'systems director', 'infrastructure manager',
                'operations director', 'program director',
                'portfolio manager', 'delivery manager',
                'technical program manager'
            ],
            
            # Research and Development
            'Research Leadership': [
                'research director', 'principal investigator',
                'research lead', 'senior scientist', 'chief scientist',
                'laboratory director', 'research manager',
                'r&d director', 'scientific director',
                'technical director'
            ],
            
            # Policy and Strategy
            'Policy Leadership': [
                'policy director', 'strategic planning',
                'policy advisor', 'senior advisor',
                'chief strategist', 'policy lead',
                'program strategist', 'policy analyst',
                'strategy director'
            ],
            
            # Technical Specialists
            'Technical Expert': [
                'solutions architect', 'enterprise architect',
                'principal engineer', 'senior engineer',
                'technical architect', 'systems architect',
                'data architect', 'security architect',
                'cloud architect', 'integration architect'
            ],
            
            # AI/ML Specialists
            'AI Specialist': [
                'ai engineer', 'machine learning engineer',
                'data scientist', 'ai researcher',
                'ml researcher', 'ai developer',
                'nlp engineer', 'computer vision engineer',
                'ai consultant', 'machine learning specialist'
            ],
            
            # Innovation Specialists
            'Innovation Specialist': [
                'innovation specialist', 'digital specialist',
                'transformation specialist', 'modernization specialist',
                'change specialist', 'innovation consultant',
                'digital consultant', 'transformation consultant'
            ],
            
            # Project Management
            'Project Management': [
                'project manager', 'program manager',
                'scrum master', 'agile coach',
                'delivery lead', 'implementation manager',
                'project lead', 'technical project manager'
            ],
            
            # Operations and Support
            'Operations': [
                'operations manager', 'service manager',
                'support manager', 'technical support',
                'systems administrator', 'devops engineer',
                'site reliability engineer', 'platform engineer'
            ]
        }
        
        for level, keywords in hierarchy_levels.items():
            if any(keyword.lower() in title.lower() for keyword in keywords):
                return level

        # Calculate confidence
        confidence = 1.0
        confidence -= len(errors) * 0.3
        confidence -= len(warnings) * 0.1
        confidence = max(0.0, min(1.0, confidence))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=confidence,
            suggested_fixes=suggested_fixes
        )

    def _validate_office(self, office: str) -> ValidationResult:
        """Validate office location"""
        errors = []
        warnings = []
        suggested_fixes = {}

        # Basic validation
        if not office:
            errors.append(ValidationMessage(
                message="Office location is missing",
                context="No office location provided",
                impact="Cannot determine physical location",
                suggestion="Add the office location",
                priority=2
            ))
            return ValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                confidence_score=0.0,
                suggested_fixes=suggested_fixes
            )

        # Length validation
        if len(office) < 5:
            warnings.append(ValidationMessage(
                message="Office location seems too short",
                context=f"Location '{office}' is only {len(office)} characters",
                impact="May be incomplete",
                suggestion="Provide full office location",
                priority=3
            ))
        elif len(office) > 200:
            warnings.append(ValidationMessage(
                message="Office location unusually long",
                context=f"Location '{office}' is {len(office)} characters",
                impact="May contain extra information",
                suggestion="Consider shortening or splitting",
                priority=3
            ))

        # Format validation
        if not office[0].isupper():
            warnings.append(ValidationMessage(
                message="Location should be capitalized",
                context=f"Location '{office}' starts with lowercase",
                impact="Non-standard formatting",
                suggestion="Capitalize first letter",
                priority=3
            ))
            suggested_fixes[office] = office[0].upper() + office[1:]

        # Common abbreviations
        abbrev_map = {
            'St': 'Street',
            'Ave': 'Avenue',
            'Rd': 'Road',
            'Blvd': 'Boulevard',
            'Ln': 'Lane',
            'Dr': 'Drive',
            'Ct': 'Court',
            'Pl': 'Place',
            'Sq': 'Square',
            'Ste': 'Suite',
            'Rm': 'Room',
            'Fl': 'Floor',
            'Bldg': 'Building',
            'Dept': 'Department'
        }

        for abbrev, full in abbrev_map.items():
            if abbrev in office and full not in office:
                warnings.append(ValidationMessage(
                    message=f"Found abbreviation '{abbrev}'",
                    context=f"Consider using full form '{full}'",
                    impact="May be unclear to some readers",
                    suggestion=f"Replace with '{full}'",
                    priority=3
                ))
                suggested_fixes[office] = office.replace(abbrev, full)

        # Calculate confidence
        confidence = 1.0
        confidence -= len(errors) * 0.3
        confidence -= len(warnings) * 0.1
        confidence = max(0.0, min(1.0, confidence))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            confidence_score=confidence,
            suggested_fixes=suggested_fixes
        )

    def _deduplicate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate opportunities based on title and agency"""
        seen = set()
        unique_opportunities = []
        
        for opp in opportunities:
            key = (opp.get('title', ''), opp.get('agency', ''))
            if key not in seen:
                seen.add(key)
                unique_opportunities.append(opp)
        
        return sorted(unique_opportunities, key=lambda x: x.get('posted_date', '') or '', reverse=True)
