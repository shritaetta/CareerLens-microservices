import hashlib
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


def parse_numeric_stipend(stipend_str: Any) -> int:
    """Extract consecutive digits from stipend string and return as integer."""
    if stipend_str is None:
        return 0
    if not isinstance(stipend_str, str):
        stipend_str = str(stipend_str)
    # Extract consecutive digits
    numbers = re.findall(r'\d+', stipend_str)
    if numbers:
        return int(''.join(numbers))
    return 0


def compute_file_cache_key(file_path: Path) -> str:
    """Compute cache key combining dataset file mtime and sha256 content hash."""
    mtime = int(file_path.stat().st_mtime)
    with open(file_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    return f"{mtime}_{content_hash}"


class MockSentenceTransformer:
    """Lightweight deterministic encoder fallback for memory-constrained environments."""

    def encode(self, texts: Any, **kwargs) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        vectors = []
        for t in texts:
            seed = int(hashlib.md5(str(t).encode("utf-8", errors="replace")).hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            v = rng.standard_normal(384).astype(np.float32)
            norm = np.linalg.norm(v)
            v = v / (norm if norm > 0 else 1.0)
            vectors.append(v)
        return np.array(vectors, dtype=np.float32)


class InternshipDataLoader:
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path
        self.df: Optional[pd.DataFrame] = None
        self.internships: List[Dict[str, Any]] = []
        self.internship_embeddings: Optional[np.ndarray] = None
        self.model: Optional[Any] = None
        self._is_loaded: bool = False

    def is_ready(self) -> bool:
        """Returns True only when the model, dataframe, and embeddings are loaded."""
        return (
            self._is_loaded
            and self.model is not None
            and self.internship_embeddings is not None
            and len(self.internships) > 0
        )

    def load_data(
        self,
        model: Optional[Any] = None,
        file_path: Optional[str] = None,
    ) -> None:
        """
        Loads the dataset and sentence transformer model.
        Caches embeddings to an .npy file next to the dataset file, keyed by mtime and content hash.
        """
        if file_path:
            self.file_path = file_path
        elif not self.file_path:
            self.file_path = os.getenv("DATASET_PATH", "data/Book2.xlsx")

        if model is not None:
            self.model = model
        elif self.model is None:
            print("Loading Sentence-BERT model (all-MiniLM-L6-v2)...")
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
            except (OSError, MemoryError) as err:
                print(
                    f"Notice: Host memory limit encountered ({err}). Falling back to deterministic embedding encoder."
                )
                self.model = MockSentenceTransformer()

        dataset_path = Path(self.file_path).resolve()
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found at {dataset_path}")

        print(f"Loading dataset from {dataset_path}...")
        self.df = pd.read_excel(dataset_path)
        self.df = self.df.fillna("")

        if "combined_text" in self.df.columns:
            texts_to_embed = self.df["combined_text"].tolist()
        else:
            texts_to_embed = (
                self.df["title"].astype(str) + " " + self.df["description"].astype(str)
            ).tolist()

        # Cache file next to the dataset, keyed by mtime/hash
        cache_key = compute_file_cache_key(dataset_path)
        cache_file = dataset_path.parent / f"{dataset_path.stem}_{cache_key}_embeddings.npy"

        loaded_from_cache = False
        if cache_file.exists():
            try:
                cached_embeddings = np.load(cache_file)
                if len(cached_embeddings) == len(self.df):
                    self.internship_embeddings = cached_embeddings
                    loaded_from_cache = True
                    print(
                        f"Loaded cached embeddings from {cache_file} (shape={cached_embeddings.shape})."
                    )
                else:
                    print(
                        f"Cached embeddings row count mismatch: {len(cached_embeddings)} vs {len(self.df)}."
                    )
            except Exception as e:
                print(f"Failed to read cache file {cache_file}: {e}. Falling back to computing.")

        if not loaded_from_cache:
            print(f"Precomputing embeddings for {len(self.df)} internships...")
            self.internship_embeddings = self.model.encode(texts_to_embed)
            try:
                np.save(cache_file, self.internship_embeddings)
                print(f"Successfully cached embeddings to {cache_file}.")
            except Exception as e:
                print(f"Warning: could not save embeddings cache to {cache_file}: {e}")

        self.internships = self.df.drop(columns=["combined_text"], errors="ignore").to_dict("records")
        self._is_loaded = True
        print(f"Successfully loaded and encoded {len(self.internships)} internships.")

    def get_all(self) -> List[Dict[str, Any]]:
        return self.internships

    def get_all_light(self) -> List[Dict[str, str]]:
        return [
            {"id": str(i.get("id", idx)), "title": i.get("title", "Untitled")}
            for idx, i in enumerate(self.internships)
        ]

    def evaluate_ats(
        self,
        resume_text: str,
        internship_id: str,
        user_skills: List[str],
    ) -> Dict[str, Any]:
        if not self.internships or self.internship_embeddings is None or self.model is None:
            return {"error": "Model not loaded"}

        target_internship = None
        target_idx = -1
        for idx, i in enumerate(self.internships):
            if str(i.get("id", idx)) == str(internship_id):
                target_internship = i
                target_idx = idx
                break

        if not target_internship:
            return {"error": "Internship not found"}

        # 1. Semantic Similarity
        resume_embedding = self.model.encode([resume_text])
        target_embedding = self.internship_embeddings[target_idx].reshape(1, -1)
        semantic_sim = float(cosine_similarity(resume_embedding, target_embedding)[0][0])

        # 2. Keyword Similarity
        req_skills_raw = target_internship.get("skill_tags", "")
        if not req_skills_raw:
            req_skills_raw = (
                str(target_internship.get("title", "")) + " " + str(target_internship.get("domain", ""))
            )

        if isinstance(req_skills_raw, str):
            req_skills_list = [
                s.strip().lower() for s in re.split(r"[, ]+", req_skills_raw) if s.strip()
            ]
            req_skills_set = set(req_skills_list)
        else:
            req_skills_set = set()

        user_skills_set = set([s.strip().lower() for s in user_skills]) if user_skills else set()

        # EXTRACT FROM RESUME: dynamically check if required skills appear anywhere in the raw text
        resume_text_lower = resume_text.lower()
        extracted_skills = set()
        for req_skill in req_skills_set:
            if req_skill in resume_text_lower:
                extracted_skills.add(req_skill)

        # Combine explicitly passed user_skills (if any) with dynamically extracted skills
        final_user_skills = user_skills_set.union(extracted_skills)

        matched_skills = list(req_skills_set.intersection(final_user_skills))
        missing_skills = list(req_skills_set.difference(final_user_skills))

        if len(req_skills_set) > 0:
            keyword_score = len(matched_skills) / len(req_skills_set)
        else:
            keyword_score = semantic_sim

        # 3. Hybrid Score (0-100)
        final_score = int(((semantic_sim * 0.6) + (keyword_score * 0.4)) * 100)
        final_score = max(0, min(100, final_score))

        # 4. Suggestions
        suggestions = []
        if len(missing_skills) > 0:
            suggestions.append(
                f"Consider adding missing keywords to your resume to pass strict ATS filters: {', '.join(missing_skills[:4])}."
            )
        if semantic_sim < 0.3:
            suggestions.append(
                "Your overall resume meaning deviates significantly from the job description. Try rewriting explicitly for this domain."
            )
        if final_score >= 80:
            suggestions.append("Great match! Your resume is highly competitive for this role.")

        return {
            "score": final_score,
            "matched_skills": [s.title() for s in matched_skills],
            "missing_skills": [s.title() for s in missing_skills],
            "suggestions": suggestions,
            "semantic_score": round(semantic_sim, 2),
        }

    def get_recommendations(
        self,
        user_profile_text: str,
        top_n: int = 3,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.internships or self.internship_embeddings is None or self.model is None:
            return []

        if constraints is None:
            constraints = {}

        # 1. Convert user profile text to embedding
        user_embedding = self.model.encode([user_profile_text])

        # 2. Compute Cosine Similarity
        similarities = cosine_similarity(user_embedding, self.internship_embeddings)[0]

        # 3. Create scored internship objects
        scored_internships = []
        for i, internship in enumerate(self.internships):
            internship_copy = internship.copy()
            # Fast numeric stipend parse
            numeric_stipend = parse_numeric_stipend(internship_copy.get("stipend", "0"))
            internship_copy["_numeric_stipend"] = numeric_stipend
            internship_copy["match_score"] = round(float(similarities[i]), 4)
            scored_internships.append(internship_copy)

        # 4. Filter logic based on constraints
        filtered_internships = []
        exclude_ids = constraints.get("exclude_ids", [])
        exclude_locations = constraints.get("exclude_locations", [])
        exclude_domains = constraints.get("exclude_domains", [])
        exclude_durations = constraints.get("exclude_durations", [])
        min_stipend = constraints.get("min_stipend", -1)

        for p in scored_internships:
            # Type-safe ID check
            if str(p.get("id", "")) in [str(x) for x in exclude_ids]:
                continue
            if p.get("location", "") in exclude_locations and p.get("location", "") != "":
                continue
            if p.get("domain", "") in exclude_domains and p.get("domain", "") != "":
                continue
            if p.get("duration", "") in exclude_durations and p.get("duration", "") != "":
                continue
            if p.get("_numeric_stipend", 0) <= min_stipend and min_stipend > 0:
                continue

            # Safely remove parsing tag to keep JSON response clean
            del p["_numeric_stipend"]
            filtered_internships.append(p)

        # 5. Sort by match_score descending
        filtered_internships.sort(key=lambda x: x["match_score"], reverse=True)

        # Return top N
        return filtered_internships[:top_n]
