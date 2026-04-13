"""
Skill Store - Persistent storage for skills
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import shutil

from .skill import Skill


class SkillStore:
    """
    Skill Store

    Manages skill storage, retrieval, and indexing.

    Skills are stored as individual directories under skills/:
        skills/
        ├── coding/
        │   ├── test-validator/
        │   │   └── SKILL.md
        │   └── bug-fixer/
        │       └── SKILL.md
        ├── system/
        │   └── memory-maintainer/
        │       └── SKILL.md
        └── skill-index.json
    """

    SKILL_INDEX = "skill-index.json"

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        self._skill_index: Dict[str, Skill] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load skill index from disk"""
        index_path = self.skills_dir / self.SKILL_INDEX
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for skill_data in data.get("skills", []):
                        skill = Skill.from_dict(skill_data)
                        self._skill_index[skill.name] = skill
            except Exception:
                pass

    def _save_index(self) -> None:
        """Save skill index to disk"""
        index_path = self.skills_dir / self.SKILL_INDEX

        data = {
            "skills": [
                skill.to_dict()
                for skill in self._skill_index.values()
            ]
        }

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_skill_path(self, skill: Skill) -> Path:
        """Get file path for a skill"""
        # Group by skill type
        skill_type = skill.skill_type or "general"
        type_dir = self.skills_dir / skill_type
        type_dir.mkdir(parents=True, exist_ok=True)

        skill_dir = type_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        return skill_dir / "SKILL.md"

    def store_skill(self, skill: Skill) -> None:
        """
        Store a skill to disk

        Args:
            skill: Skill to store
        """
        # Update timestamp
        skill.updated_at = skill.created_at

        # Save skill file
        skill_path = self._get_skill_path(skill)
        skill_path.write_text(skill.to_skill_md(), encoding="utf-8")

        # Update index
        self._skill_index[skill.name] = skill
        self._save_index()

    def load_skill(self, name: str) -> Optional[Skill]:
        """
        Load a skill by name

        Args:
            name: Skill name

        Returns:
            Skill or None if not found
        """
        # Check index first
        if name in self._skill_index:
            skill = self._skill_index[name]

            # Refresh from disk
            skill_path = self._get_skill_path(skill)
            if skill_path.exists():
                try:
                    content = skill_path.read_text(encoding="utf-8")
                    return Skill.from_skill_md(content)
                except Exception:
                    pass

            return skill

        # Search all directories
        for skill_dir in self.skills_dir.rglob("*/SKILL.md"):
            try:
                content = skill_dir.read_text(encoding="utf-8")
                skill = Skill.from_skill_md(content)
                if skill.name == name:
                    self._skill_index[skill.name] = skill
                    return skill
            except Exception:
                continue

        return None

    def delete_skill(self, name: str) -> bool:
        """
        Delete a skill

        Args:
            name: Skill name

        Returns:
            True if deleted
        """
        if name not in self._skill_index:
            return False

        skill = self._skill_index[name]
        skill_path = self._get_skill_path(skill)

        # Delete skill file and directory
        if skill_path.exists():
            skill_path.unlink()
            skill_dir = skill_path.parent
            if skill_dir.exists() and not any(skill_dir.iterdir()):
                skill_dir.rmdir()

        # Remove from index
        del self._skill_index[name]
        self._save_index()

        return True

    def list_skills(self, skill_type: Optional[str] = None) -> List[Skill]:
        """
        List all skills

        Args:
            skill_type: Optional filter by type

        Returns:
            List of skills
        """
        skills = list(self._skill_index.values())

        if skill_type:
            skills = [s for s in skills if s.skill_type == skill_type]

        return sorted(skills, key=lambda s: s.name)

    def find_relevant_skills(
        self,
        query: str,
        skill_type: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Tuple[Skill, float]]:
        """
        Find skills relevant to a query

        Simple keyword matching for now.
        Could be enhanced with embeddings.

        Args:
            query: Search query
            skill_type: Optional type filter
            n_results: Max results

        Returns:
            List of (Skill, relevance_score) tuples
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for skill in self._skill_index.values():
            if skill_type and skill.skill_type != skill_type:
                continue

            # Calculate relevance score
            score = 0.0

            # Name match (highest weight)
            if query_lower in skill.name.lower():
                score += 0.5

            # Description match
            if query_lower in skill.description.lower():
                score += 0.3

            # Step keyword match
            for step in skill.steps:
                if query_lower in step.lower():
                    score += 0.1
                    break

            # Pitfall keyword match
            for pitfall in skill.pitfalls:
                if query_lower in pitfall.lower():
                    score += 0.1
                    break

            if score > 0:
                scored.append((skill, min(score, 1.0)))

        # Sort by score
        scored.sort(key=lambda x: -x[1])

        return scored[:n_results]

    def get_statistics(self) -> Dict:
        """Get skill statistics"""
        skills = list(self._skill_index.values())

        type_counts = {}
        total_uses = 0
        total_successes = 0

        for skill in skills:
            stype = skill.skill_type or "general"
            type_counts[stype] = type_counts.get(stype, 0) + 1
            total_uses += skill.times_used
            total_successes += skill.times_successful

        return {
            "total_skills": len(skills),
            "by_type": type_counts,
            "total_uses": total_uses,
            "total_successes": total_successes,
            "overall_success_rate": (
                total_successes / total_uses if total_uses > 0 else 0.0
            ),
        }
