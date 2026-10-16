import re
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# A basic categorization map to avoid heavy computation for every skill
SKILL_TO_CATEGORY_MAP = {
    # Programming Languages
    "python": "Domain Skills", "java": "Domain Skills", "c++": "Domain Skills",
    "c#": "Domain Skills", "javascript": "Domain Skills", "typescript": "Domain Skills",
    "ruby": "Domain Skills", "golang": "Domain Skills", "swift": "Domain Skills",
    "rust": "Domain Skills",
    
    # Frameworks & Libraries
    "react": "Tools & Technologies", "angular": "Tools & Technologies", "vue.js": "Tools & Technologies",
    "node.js": "Tools & Technologies", "express": "Tools & Technologies", "django": "Tools & Technologies",
    "flask": "Tools & Technologies", "spring boot": "Tools & Technologies",
    
    # Databases
    "sql": "Tools & Technologies", "mysql": "Tools & Technologies", "postgresql": "Tools & Technologies",
    "mongodb": "Tools & Technologies", "redis": "Tools & Technologies", "cassandra": "Tools & Technologies",
    
    # Cloud & DevOps
    "aws": "Tools & Technologies", "azure": "Tools & Technologies", "google cloud": "Tools & Technologies",
    "docker": "Tools & Technologies", "kubernetes": "Tools & Technologies", "git": "Tools & Technologies",
    "linux": "Tools & Technologies", "jenkins": "Tools & Technologies",

    # Soft Skills & Management
    "project management": "Management & Operations", "agile": "Management & Operations", 
    "scrum": "Management & Operations", "leadership": "Soft Skills", "communication": "Soft Skills",
    "problem solving": "Soft Skills", "teamwork": "Soft Skills", "time management": "Soft Skills",
    
    # Design & Creative
    "figma": "Creative & Design", "adobe xd": "Creative & Design", "photoshop": "Creative & Design",
    "ui/ux design": "Creative & Design",
    
    # Data & ML
    "machine learning": "Core Concepts", "deep learning": "Core Concepts", 
    "data analysis": "Core Concepts", "artificial intelligence": "Core Concepts",
    "nlp": "Core Concepts", "computer vision": "Core Concepts"
}

CATEGORY_ANCHORS = {
    "Domain Skills": "programming languages software engineering coding development",
    "Tools & Technologies": "frameworks databases cloud platforms devops tools servers infrastructure",
    "Core Concepts": "theoretical concepts algorithms machine learning artificial intelligence data analysis mathematics",
    "Management & Operations": "project management business operations agile scrum planning strategy",
    "Soft Skills": "personal abilities teamwork communication problem solving leadership interpersonal",
    "Creative & Design": "user interface design user experience graphics visual arts creativity",
    "Manufacturing & Technical": "hardware electronics mechanical engineering manufacturing logistics"
}

# Simple regex patterns to improve action verbs
VERB_IMPROVEMENTS = [
    (r"\b(worked on|did|made)\b", "Developed and implemented"),
    (r"\b(built)\b", "Engineered"),
    (r"\b(helped with|assisted in)\b", "Collaborated on"),
    (r"\b(was responsible for)\b", "Managed"),
    (r"\b(fixed)\b", "Resolved")
]

class ResumeEnhancer:
    def __init__(self, model):
        # We inject the loaded SentenceTransformer to avoid loading it twice
        self.model = model
        print("Initializing Resume Enhancer...")
        # Precompute category embeddings
        self.categories = list(CATEGORY_ANCHORS.keys())
        anchor_texts = list(CATEGORY_ANCHORS.values())
        self.category_embeddings = self.model.encode(anchor_texts)
        
    def categorize_skills(self, skills):
        categorized = {cat: [] for cat in self.categories}
        categorized["Other Details"] = []
        
        for skill in skills:
            if not skill.strip():
                continue
            skill_lower = skill.lower().strip()
            # 1. Rule-based lookup
            if skill_lower in SKILL_TO_CATEGORY_MAP:
                categorized[SKILL_TO_CATEGORY_MAP[skill_lower]].append(skill)
            else:
                # 2. Fallback to Semantic Similarity (locally)
                skill_emb = self.model.encode([skill_lower])
                sims = cosine_similarity(skill_emb, self.category_embeddings)[0]
                best_idx = np.argmax(sims)
                best_score = sims[best_idx]
                if best_score > 0.3: # Threshold to avoid placing gibberish
                    categorized[self.categories[best_idx]].append(skill)
                else:
                    categorized["Other Details"].append(skill)
                    
        # Remove empty categories
        result = [{"category": k, "skills": v} for k, v in categorized.items() if len(v) > 0]
        return result
        
    def improve_description(self, description):
        if not description:
            return ""
        
        improved = description
        for pattern, replacement in VERB_IMPROVEMENTS:
            # Case insensitive replacement
            improved = re.sub(pattern, replacement, improved, flags=re.IGNORECASE)
            
        # Ensure capitalization of first letter of lines/sentences
        lines = improved.split('\n')
        capitalized_lines = []
        for line in lines:
            line = line.strip()
            if line:
                # Capitalize first letter if it's alphanumeric
                line = line[0].upper() + line[1:]
                # Add bullet point if it doesn't have one and looks like a list item
                if not line.startswith('•') and not line.startswith('-') and not line.startswith('◦'):
                    line = f"• {line}"
            capitalized_lines.append(line)
            
        return '\n'.join(capitalized_lines)

    def generate_professional_summary(self, user_data):
        skills = user_data.get('skills', [])
        projects = user_data.get('projects', [])
        experience = user_data.get('experience', [])
        domains = user_data.get('selectedDomains', [])
        
        domain_str = (" and ".join(domains[:2]) + " ") if domains else ""
        skills_str = ", ".join(skills[:3]) if skills else "various technologies"
        
        project_count = len(projects) + len(experience)
        
        summary = f"Highly motivated {domain_str}professional "
        
        if project_count > 0:
            summary += f"with hands-on experience across {project_count} significant projects and roles. "
        else:
            summary += "with a strong foundation in modern engineering principles. "
            
        summary += f"Demonstrated expertise in {skills_str}. "
        summary += "Seeking dynamic opportunities to leverage my technical toolkit and deliver impactful, scalable solutions."
        
        return summary

    def process_profile(self, profile):
        """
        Takes the pre-transformed profile data from frontend and returns a structured, enhanced format
        """
        enhanced = profile.copy()
        
        # 1. Provide generated summary if empty or basic
        if not enhanced.get("professional_summary") or len(enhanced.get("professional_summary", "")) < 50:
             # Just use generic data or if you have raw DB profile passed
             enhanced["professional_summary"] = self.generate_professional_summary(enhanced)
             
        # 2. Skills (Categorized) - replace flat array with nested objects
        flat_skills = enhanced.get("skills", [])
        if flat_skills and isinstance(flat_skills[0], str):
            enhanced["skills"] = self.categorize_skills(flat_skills)
            
        # 3. Text Improvements for Projects & Experience
        if "projects" in enhanced:
            for p in enhanced["projects"]:
                p["description"] = self.improve_description(p.get("description", ""))
                if p.get("tech"):
                    # Clean tech string (e.g. "React, Node.js / AWS" -> "React, Node.js, AWS")
                    tech_list = [t.strip() for t in re.split(r'[,|/]', p["tech"]) if t.strip()]
                    p["tech"] = ", ".join(tech_list)
                
        if "experience" in enhanced:
            for e in enhanced["experience"]:
                e["description"] = self.improve_description(e.get("description", ""))
                
        if "achievements" in enhanced:
            achs = enhanced["achievements"]
            improved_achs = []
            for ach in achs:
                ach_str = str(ach).strip()
                if not ach_str:
                    continue
                # Ensure starts with bullet and space
                if not re.match(r'^[•\-\*◦]\s*', ach_str):
                    ach_str = f"• {ach_str}"
                else:
                    # Standardize to bullet
                    ach_str = re.sub(r'^[•\-\*◦]\s*', '• ', ach_str)
                improved_achs.append(ach_str)
            enhanced["achievements"] = improved_achs

        # 4. Certificates - extract clean course names from raw PDF text
        if "certificates" in enhanced:
            certs = enhanced["certificates"]
            clean_certs = []
            for cert in certs:
                if isinstance(cert, dict):
                    extracted = cert.get("extracted_text", "")
                    fallback = cert.get("display_name", cert.get("filename", "Certificate"))
                    if extracted:
                        course_name = self.extract_course_name_from_text(extracted, fallback)
                    else:
                        course_name = fallback
                    clean_certs.append(course_name)
                elif isinstance(cert, str):
                    clean_certs.append(cert)
            enhanced["certificates"] = clean_certs

        return enhanced

    def extract_course_name_from_text(self, text, fallback_name):
        """Local offline rule-based extraction from certificate PDF text.
        Returns a concise course name string."""
        if not text or not text.strip():
            clean_name = re.sub(r'\.(pdf|png|jpe?g)$', '', fallback_name, flags=re.IGNORECASE)
            return clean_name.replace('-', ' ').replace('_', ' ').title()

        # Pattern 1: "has successfully completed <COURSE NAME>"
        match = re.search(r'(?i)(?:has\s+)?successfully\s+completed\s+(?:the\s+)?(?:online\s+)?(?:course\s+)?(?:on\s+)?(?:in\s+)?([^\n.!]{5,80})', text)
        if match:
            return match.group(1).strip().title()

        # Pattern 2: "certificate of completion ... for <COURSE NAME>"
        match = re.search(r'(?i)certificate\s+of\s+completion.*?(?:for|in)\s+([^\n.!]{5,80})', text, re.DOTALL)
        if match:
            return match.group(1).strip().title()

        # Pattern 3: "Course Name: <NAME>" or "Program: <NAME>"
        match = re.search(r'(?i)(?:course\s*(?:name)?|program|certification)\s*[:\-]\s*([^\n.!]{5,80})', text)
        if match:
            return match.group(1).strip().title()

        # Pattern 4: Smart line-by-line scan (handles NPTEL, Coursera, etc.)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        for line in lines:
            # Skip lines that are clearly NOT course names
            if len(line) < 8 or len(line) > 100:
                continue
            # Skip lines wrapped in parentheses like "(4 week course)"
            if line.startswith('(') and line.endswith(')'):
                continue
            # Skip lines with URLs, dates, credits, scores, IDs
            if re.match(r'^(http|www|©|\d{1,2}[/\-])', line, re.IGNORECASE):
                continue
            if re.match(r'^(name|date|verify|credential|issued|cert|no\.|roll)', line, re.IGNORECASE):
                continue
            # Skip lines that are mostly numbers/scores (e.g. "25/25 59.63/7585")
            if re.match(r'^[\d\s/\.%]+$', line):
                continue
            # Skip lines that look like certificate IDs (e.g. "NPTEL25CS60S447001318")
            if re.match(r'^[A-Z0-9]{10,}$', line):
                continue
            # Skip all-caps short names (likely person names like "E SHRITA")
            if line == line.upper() and len(line.split()) <= 3 and len(line) < 25:
                continue
            # Skip duration/credit metadata
            if re.search(r'(?i)(week\s+course|month\s+course|credits?\s+recommended|duration)', line):
                continue
            # Good candidate: 3-12 words, looks like a course title
            words = line.split()
            if 3 <= len(words) <= 12:
                return line.strip().title()

        # Extreme fallback: use the cleaned filename
        clean_name = re.sub(r'\.(pdf|png|jpe?g)$', '', fallback_name, flags=re.IGNORECASE)
        # Remove trailing parenthetical like "(1)"
        clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name)
        return clean_name.replace('-', ' ').replace('_', ' ').strip().title()
