"""
classifiers.py
Rules-based classifiers for Content Type (URL/Page level) and Entity Type (Domain level).
"""
import os
import yaml

ENTITY_TYPES = [
    "counselling",
    "legal",
    "directory",
    "nonprofit",
    "government",
    "media",
    "professional_association",
    "education",
]

ENTITY_TYPE_DESCRIPTIONS = {
    "counselling": "Direct counselling or therapy service providers.",
    "legal": "Law firms, legal services, or legal information sources.",
    "directory": "Practitioner directories and listing platforms.",
    "nonprofit": "Nonprofit or charity organizations.",
    "government": "Government sites and public-sector service sources.",
    "media": "Editorial, social, video, book, or news/media platforms.",
    "professional_association": "Associations, colleges, and regulatory bodies.",
    "education": "Universities, colleges, and research institutions.",
}


class ContentClassifier:
    def classify(self, url, soup, headers):
        """
        Classifies content type based on URL, HTML content (BeautifulSoup object), and Headers.
        Returns: (content_type, confidence, evidence_list)
        """
        evidence = []

        # 1. PDF Check (High Confidence)
        if url.lower().endswith('.pdf') or (headers and 'application/pdf' in headers.get('Content-Type', '')):
            return 'pdf', 1.0, ["url_extension_or_header"]

        # 2. Directory / Listing (High Confidence)
        # URL patterns
        if any(x in url.lower() for x in ['/directory/', '/list/', '/find-', '/best-', '-near-me']):
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
        service_signals = ['book appointment', 'schedule consultation',
                           'our services', 'pricing', 'contact us']
        # Check top of page
        service_matches = [s for s in service_signals if s in text[:5000]]
        if len(service_matches) >= 2:
            evidence.append(f"service_keywords:{','.join(service_matches)}")
            return 'service', 0.7, evidence

        # 5. Guide / Resource (Medium Confidence)
        if "how to" in title or "guide" in title or "what is" in title:
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
        directory_domains = [
            "yelp.ca",
            "yellowpages.ca",
            "psychologytoday.com",
            "healthgrades.com",
            "counsellingbc.com",
            "therapytribe.com",
            "theravive.com",
            "firstsession.com",
            "luminohealth.sunlife.ca",
            "ratemds.com",
        ]
        if any(d in domain_l for d in directory_domains):
            return 'directory', 0.9, ["known_directory_domain"]

        professional_association_domains = [
            "bcacc.ca",
        ]
        if any(d in domain_l for d in professional_association_domains):
            return 'professional_association', 0.95, ["known_professional_association_domain"]

        media_domains = [
            "reddit.com",
            "youtube.com",
            "amazon.ca",
            "cbc.ca",
            "vancouversun.com",
            "canadianaffairs.news",
        ]
        if any(d in domain_l for d in media_domains):
            return 'media', 0.9, ["known_media_domain"]

        legal_terms = ["law", "legal", "lawyer", "lawyers", "attorney", "attorneys", "estate", "litigation"]
        if any(term in domain_l for term in legal_terms):
            return 'legal', 0.85, ["domain_legal_pattern"]

        counselling_terms = [
            "counselling", "counseling", "therapy", "therapist",
            "psychology", "psychotherapy", "mentalhealth", "wellness",
        ]
        if any(term in domain_l for term in counselling_terms):
            return 'counselling', 0.8, ["domain_counselling_pattern"]

        if not soup:
            if "tld_org" in evidence:
                return 'nonprofit', 0.6, evidence
            return 'N/A', 0.0, ["fallback_no_content"]

        # 2. Nonprofit Signals
        nonprofit_keywords = ["registered charity",
                              "non-profit organization", "donate", "volunteer"]
        if any(k in text[:5000] for k in nonprofit_keywords):
            evidence.append("nonprofit_keywords")
            return 'nonprofit', 0.8, evidence

        association_keywords = [
            "professional association", "regulatory body", "college of",
            "registered clinical counsellors association", "licensing body",
        ]
        if any(k in text[:5000] for k in association_keywords):
            return 'professional_association', 0.8, ["association_keywords"]

        if any(k in text[:5000] for k in ["lawyer", "law firm", "family law", "legal advice", "custody", "estate planning"]):
            return 'legal', 0.75, ["legal_keywords"]

        if any(k in text[:5000] for k in ["counselling", "counseling", "therapy", "psychotherapy", "book appointment", "registered clinical counsellor"]):
            return 'counselling', 0.7, ["counselling_keywords"]

        return 'N/A', 0.0, ["fallback_unknown"]
