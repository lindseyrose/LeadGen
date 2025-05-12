from sklearn.preprocessing import MinMaxScaler
import numpy as np
from datetime import datetime
import re

class LeadScorer:
    def __init__(self):
        self.scaler = MinMaxScaler()
        
        # Define scoring weights for different factors
        self.scoring_factors = {
            'ai_readiness': 0.30,      # Decreased slightly to accommodate new factor
            'academic_partnerships': 0.15, # New factor for academic collaborations
            'budget_potential': 0.20,   # Adjusted weight
            'tech_initiatives': 0.15,   # Current tech modernization efforts
            'engagement_signals': 0.15, # Recent relevant activities
            'accessibility': 0.05       # Ease of reaching decision makers
        }
        
        # AI-related keywords and their importance weights
        self.ai_keywords = {
            'artificial intelligence': 1.0,
            'machine learning': 1.0,
            'ai transformation': 1.0,
            'data science': 0.8,
            'digital transformation': 0.7,
            'automation': 0.6,
            'analytics': 0.5,
            'modernization': 0.4,
            'innovation': 0.3
        }
        
        # Budget indicators and their weights
        self.budget_indicators = {
            'enterprise': 1.0,
            'multi-year': 0.9,
            'million': 0.8,
            'phase': 0.6,
            'pilot': 0.4
        }
        
        # Academic partnership indicators and their weights
        self.academic_indicators = {
            'university': 1.0,
            'research partnership': 1.0,
            'academic collaboration': 1.0,
            'research institute': 0.9,
            'college': 0.9,
            'academic': 0.8,
            'research center': 0.8,
            'laboratory': 0.7,
            'fellowship': 0.6,
            'internship': 0.5,
            'student program': 0.5
        }
        
        # Top research universities (add more as needed)
        self.top_universities = [
            'mit', 'stanford', 'harvard', 'carnegie mellon', 'berkeley',
            'georgia tech', 'caltech', 'princeton', 'illinois', 'michigan',
            'purdue', 'texas', 'ucla', 'ucsd', 'columbia', 'cornell',
            'washington', 'maryland', 'penn state', 'virginia tech', 'johns hopkins'
        ]
        
        # Universities with special government relationships
        self.special_universities = {
            'johns hopkins': {
                'weight': 1.0,
                'relationship_keywords': [
                    'existing partnership',
                    'ongoing collaboration',
                    'current contract',
                    'active project',
                    'jhu partnership',
                    'apl',  # Applied Physics Laboratory
                    'applied physics laboratory'
                ]
            }
        }
    
    def score_lead(self, lead_data):
        """
        Score a potential lead based on various factors
        
        Args:
            lead_data (dict): Dictionary containing lead information with keys:
                - description: Text description of the opportunity
                - budget_info: Available budget information
                - tech_initiatives: List of current tech initiatives
                - recent_activities: List of recent activities with dates
                - contact_info: Dictionary of contact information
        
        Returns:
            dict: Scoring results including total score and factor breakdowns
        """
        scores = {}
        
        # Calculate individual factor scores
        for factor, weight in self.scoring_factors.items():
            factor_score = self._calculate_factor_score(lead_data, factor)
            scores[factor] = factor_score * weight
        
        # Calculate final score (0-100 scale)
        final_score = sum(scores.values()) * 100
        
        return {
            'total_score': round(final_score, 2),
            'factor_scores': {k: round(v * 100, 2) for k, v in scores.items()},
            'analysis': self._generate_analysis(scores)
        }
    
    def _calculate_factor_score(self, lead_data, factor):
        """
        Calculate the score for a specific factor
        """
        if factor == 'ai_readiness':
            return self._score_ai_readiness(lead_data.get('description', ''))
        elif factor == 'academic_partnerships':
            return self._score_academic_partnerships(lead_data)
        elif factor == 'budget_potential':
            return self._score_budget_potential(lead_data.get('budget_info', ''))
        elif factor == 'tech_initiatives':
            return self._score_tech_initiatives(lead_data.get('tech_initiatives', []))
        elif factor == 'engagement_signals':
            return self._score_engagement_signals(lead_data.get('recent_activities', []))
        elif factor == 'accessibility':
            return self._score_accessibility(lead_data.get('contact_info', {}))
        return 0.0
    
    def _score_ai_readiness(self, description):
        """
        Score based on AI-related keywords in description
        """
        if not description:
            return 0.0
            
        description = description.lower()
        score = 0.0
        max_possible = sum(self.ai_keywords.values())
        
        for keyword, weight in self.ai_keywords.items():
            if keyword in description:
                score += weight
                
        return min(score / max_possible, 1.0)
    
    def _score_budget_potential(self, budget_info):
        """
        Score based on budget indicators
        """
        if not budget_info:
            return 0.0
            
        budget_info = budget_info.lower()
        score = 0.0
        max_possible = sum(self.budget_indicators.values())
        
        # Look for specific budget amounts
        amount_pattern = r'\$\s*(\d+(?:\.\d+)?)[\s-]*(million|k|thousand)'
        matches = re.findall(amount_pattern, budget_info)
        if matches:
            for amount, unit in matches:
                amount = float(amount)
                if unit == 'million':
                    score += min(amount / 10, 1.0)  # Scale based on size
                elif unit in ['k', 'thousand']:
                    score += min(amount / 10000, 1.0)
        
        # Check for budget indicators
        for indicator, weight in self.budget_indicators.items():
            if indicator in budget_info:
                score += weight
                
        return min(score / max_possible, 1.0)
    
    def _score_tech_initiatives(self, initiatives):
        """
        Score based on current technology initiatives
        """
        if not initiatives:
            return 0.0
            
        # Count initiatives that suggest AI readiness
        ai_ready_count = sum(1 for init in initiatives 
                            if any(kw in init.lower() 
                                  for kw in self.ai_keywords))
        
        # Score based on number of relevant initiatives
        return min(ai_ready_count / 5, 1.0)  # Cap at 5 initiatives
    
    def _score_engagement_signals(self, activities):
        """
        Score based on recent relevant activities
        """
        if not activities:
            return 0.0
            
        current_time = datetime.now()
        score = 0.0
        
        for activity in activities:
            # Check recency (within last 6 months)
            activity_date = activity.get('date')
            if activity_date:
                days_ago = (current_time - activity_date).days
                if days_ago <= 180:  # 6 months
                    recency_score = 1 - (days_ago / 180)
                    score += recency_score
        
        return min(score / 3, 1.0)  # Cap at 3 recent activities
    
    def _score_accessibility(self, contact_info):
        """
        Score based on availability of decision maker contact information
        """
        if not contact_info:
            return 0.0
            
        score = 0.0
        
        # Check for key contact information
        if contact_info.get('email'):
            score += 0.4
        if contact_info.get('phone'):
            score += 0.3
        if contact_info.get('title'):
            score += 0.3
            
        return score
    
    def _score_academic_partnerships(self, lead_data):
        """
        Score based on academic partnerships and research collaborations
        """
        score = 0.0
        max_possible = 4.0  # Increased maximum to account for special relationships
        
        # Check description for academic partnerships
        description = lead_data.get('description', '').lower()
        partnerships = lead_data.get('partnerships', [])
        initiatives = lead_data.get('tech_initiatives', [])
        
        # Combine all text sources
        all_text = ' '.join([description] + 
                           [p.lower() for p in partnerships] + 
                           [i.lower() for i in initiatives])
        
        # Score based on academic partnership indicators
        for indicator, weight in self.academic_indicators.items():
            if indicator in all_text:
                score += weight
        
        # Bonus points for partnerships with top universities
        for university in self.top_universities:
            if university in all_text:
                score += 0.5  # Additional points for top universities
        
        # Special scoring for universities with strong government relationships
        for univ, data in self.special_universities.items():
            if univ in all_text:
                # Check for existing relationship indicators
                relationship_found = any(
                    keyword in all_text 
                    for keyword in data['relationship_keywords']
                )
                if relationship_found:
                    score += data['weight']  # Additional points for existing relationship
                    # Add relationship details to analysis
                    self.partnership_details = {
                        'university': univ,
                        'relationship_type': 'existing',
                        'score_impact': data['weight']
                    }
        
        # Check for active research programs
        if any('research' in text and ('ongoing' in text or 'active' in text) 
               for text in [description] + partnerships):
            score += 0.5
        
        return min(score / max_possible, 1.0)
    
    def _generate_analysis(self, scores):
        """
        Generate a brief analysis of the scoring results
        """
        analysis = []
        
        # Analyze each factor
        for factor, score in scores.items():
            if score >= 0.8:
                analysis.append(f"Strong {factor.replace('_', ' ')}: {score*100:.1f}%")
            elif score <= 0.3:
                analysis.append(f"Weak {factor.replace('_', ' ')}: {score*100:.1f}%")
        
        # Special analysis for academic partnerships
        if 'academic_partnerships' in scores:
            score = scores['academic_partnerships']
            if hasattr(self, 'partnership_details'):
                univ = self.partnership_details['university']
                if self.partnership_details['relationship_type'] == 'existing':
                    analysis.append(f"Existing strong relationship with {univ.title()} detected")
            
            if score >= 0.8:
                analysis.append("Strong academic collaboration potential")
            elif score >= 0.5:
                analysis.append("Moderate academic engagement")
            elif score > 0:
                analysis.append("Limited academic partnerships - opportunity for growth")
            
            # Clear partnership details for next analysis
            if hasattr(self, 'partnership_details'):
                del self.partnership_details
        
        return analysis
