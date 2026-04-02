"""
classifiers.py
Rules-based classifiers for Content Type (URL/Page level) and Entity Type (Domain level).
"""
import os
import yaml

import json

RULES_PATH = os.path.join(os.path.dirname(__file__), "classification_rules.json")

def load_rules():
    if os.path.exists(RULES_PATH):
        with open(RULES_PATH, 'r') as f:
            return json.load(f)
    return {}

RULES = load_rules()
ENTITY_TYPES = RULES.get("entity_types", [])
ENTITY_TYPE_DESCRIPTIONS = RULES.get("entity_type_descriptions", {})

class ContentClassifier:
    def classify(self, url, soup, headers):
        """
        Classifies content type based on URL, HTML content (BeautifulSoup object), and Headers.
        Returns: (content_type, confidence, evidence_list)
        """
        evidence = []
        patterns = RULES.get("content_patterns", {})

        # 1. PDF Check (High Confidence)
        if url.lower().endswith('.pdf') or (headers and 'application/pdf' in headers.get('Content-Type', '')):
            return 'pdf', 1.0, ["url_extension_or_header"]

        # 2. Directory / Listing (High Confidence)
        # URL patterns
        if any(x in url.lower() for x in patterns.get("directory_url", [])):
            evidence.append("url_pattern_directory")
            return 'directory', 0.8, evidence

        if not soup:
            return 'unknown', 0.0, ["no_content"]

        text = soup.get_text(" ", strip=True).lower()
        title = soup.title.string.lower() if soup.title and soup.title.string else ""

        # Content patterns for directories
        if "top 10" in title or ("best " in title and " in " in title):
            evidence.append("title_list_pattern")
            return 'directory', 0.7, evidence

        # 3. News (High Confidence)
        if soup.find("meta", property="article:published_time"):
            evidence.append("meta_article_published")
            return 'news', 0.8, evidence

        # 4. Service Page (Medium Confidence)
        service_signals = patterns.get("service_signals", [])
        # Check top of page
        service_matches = [s for s in service_signals if s in text[:5000]]
        if len(service_matches) >= 2:
            evidence.append(f"service_keywords:{','.join(service_matches)}")
            return 'service', 0.7, evidence

        # 5. Guide / Resource (Medium Confidence)
        guide_titles = patterns.get("guide_titles", [])
        if any(t in title for t in guide_titles):
            evidence.append("title_informational")
            return 'guide', 0.8, evidence

        # Heuristic: Long content often indicates a guide
        word_count = len(text.split())
        if word_count > 1500:
            evidence.append("high_word_count")
            return 'guide', 0.6, evidence

        # Default
        return 'other', 0.5, ["fallback"]


class EntityClassifier:
    def __init__(self, override_file="domain_overrides.yml"):
        self.overrides = {}
        if os.path.exists(override_file):
            try:
                with open(override_file, 'r') as f:
                    self.overrides = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load domain overrides: {e}")

    def classify(self, domain, soup):
        """
        Classifies entity type based on domain and HTML content.
        Returns: (entity_type, confidence, evidence_list)
        """
        evidence = []
        patterns = RULES.get("entity_patterns", {})
        domain_l = (domain or "").lower()
        text = soup.get_text(" ", strip=True).lower() if soup else ""

        # 0. Manual Override
        if domain in self.overrides:
            return self.overrides[domain], 1.0, ["manual_override"]
        if domain_l in self.overrides:
            return self.overrides[domain_l], 1.0, ["manual_override"]

        # 1. TLD Signals
        if (
            domain_l.endswith('.gov')
            or '.gov.' in domain_l
            or domain_l.endswith('.gc.ca')
            or domain_l.endswith('canada.ca')
        ):
            return 'government', 1.0, ["tld_gov"]
        if domain_l.endswith('.edu') or any(d in domain_l for d in ["ubc.ca", "sfu.ca"]):
            return 'education', 1.0, ["tld_edu"]
        if domain_l.endswith('.org'):
            evidence.append("tld_org")  # Weak signal, need more

        # 2. Directory Signals (Domain level)
        if any(d in domain_l for d in patterns.get("directory_domains", [])):
            return 'directory', 0.9, ["known_directory_domain"]

        if any(d in domain_l for d in patterns.get("professional_association_domains", [])):
            return 'professional_association', 0.95, ["known_professional_association_domain"]

        if any(d in domain_l for d in patterns.get("media_domains", [])):
            return 'media', 0.9, ["known_media_domain"]

        if any(term in domain_l for term in patterns.get("legal_terms", [])):
            return 'legal', 0.85, ["domain_legal_pattern"]

        if any(term in domain_l for term in patterns.get("counselling_terms", [])):
            return 'counselling', 0.8, ["domain_counselling_pattern"]

        if not soup:
            if "tld_org" in evidence:
                return 'nonprofit', 0.6, evidence
            return 'N/A', 0.0, ["fallback_no_content"]

        # 2. Nonprofit Signals
        if any(k in text[:5000] for k in patterns.get("nonprofit_keywords", [])):
            evidence.append("nonprofit_keywords")
            return 'nonprofit', 0.8, evidence

        if any(k in text[:5000] for k in patterns.get("association_keywords", [])):
            return 'professional_association', 0.8, ["association_keywords"]

        if any(k in text[:5000] for k in patterns.get("legal_keywords", [])):
            return 'legal', 0.75, ["legal_keywords"]

        if any(k in text[:5000] for k in patterns.get("counselling_keywords", [])):
            return 'counselling', 0.7, ["counselling_keywords"]

        return 'N/A', 0.0, ["fallback_unknown"]
