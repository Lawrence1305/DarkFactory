"""
Skill - Skill definition and data model
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import yaml


@dataclass
class Skill:
    """
    Skill Definition

    Skills are procedural memories - reusable approaches extracted from experience.

    Structure:
    - name: Skill name (kebab-case)
    - description: Brief description
    - trigger: When to use this skill
    - steps: Execution steps
    - pitfalls: Known traps to avoid
    - verification: How to verify success
    - examples: Usage examples
    - metadata: Additional data

    Based on hermes-agent's skill system
    """

    name: str
    description: str
    trigger: Dict[str, Any] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)
    verification: Dict[str, str] = field(default_factory=dict)
    examples: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    source_task_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0.0"
    times_used: int = 0
    times_successful: int = 0

    # Skill type classification
    skill_type: str = "general"  # general, coding, debugging, testing, etc.

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger,
            "steps": self.steps,
            "pitfalls": self.pitfalls,
            "verification": self.verification,
            "examples": self.examples,
            "metadata": self.metadata,
            "source_task_id": self.source_task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "times_used": self.times_used,
            "times_successful": self.times_successful,
            "skill_type": self.skill_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        """Create from dictionary"""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            trigger=data.get("trigger", {}),
            steps=data.get("steps", []),
            pitfalls=data.get("pitfalls", []),
            verification=data.get("verification", {}),
            examples=data.get("examples", []),
            metadata=data.get("metadata", {}),
            source_task_id=data.get("source_task_id"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            version=data.get("version", "1.0.0"),
            times_used=data.get("times_used", 0),
            times_successful=data.get("times_successful", 0),
            skill_type=data.get("skill_type", "general"),
        )

    def to_skill_md(self) -> str:
        """
        Convert to SKILL.md format

        YAML frontmatter + Markdown body
        """
        # Frontmatter
        frontmatter = {
            "name": self.name,
            "description": self.description,
            "trigger": self.trigger,
            "version": self.version,
            "created": self.created_at,
            "type": self.skill_type,
        }

        fm_yaml = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)

        # Body
        lines = ["---\n"]
        lines.append(fm_yaml)
        lines.append("---\n\n")
        lines.append(f"# {self.name}\n\n")
        lines.append(f"{self.description}\n\n")

        if self.steps:
            lines.append("## Steps\n")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"{i}. {step}\n")
            lines.append("\n")

        if self.pitfalls:
            lines.append("## Pitfalls\n")
            for pitfall in self.pitfalls:
                lines.append(f"- {pitfall}\n")
            lines.append("\n")

        if self.verification:
            lines.append("## Verification\n")
            for k, v in self.verification.items():
                lines.append(f"- **{k}**: {v}\n")
            lines.append("\n")

        if self.examples:
            lines.append("## Examples\n")
            for i, example in enumerate(self.examples, 1):
                lines.append(f"### Example {i}\n")
                if "input" in example:
                    lines.append(f"Input: {example['input']}\n")
                if "output" in example:
                    lines.append(f"Output: {example['output']}\n")
            lines.append("\n")

        if self.metadata:
            lines.append("## Metadata\n")
            for k, v in self.metadata.items():
                lines.append(f"- {k}: {v}\n")

        return "".join(lines)

    @classmethod
    def from_skill_md(cls, content: str) -> "Skill":
        """Parse from SKILL.md format"""
        # Split frontmatter and body
        parts = content.split("---", 2)
        if len(parts) < 3:
            # No frontmatter, use entire content as description
            return cls(name="unknown", description=content)

        frontmatter_raw = parts[1].strip()
        body = parts[2].strip()

        # Parse frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_raw) or {}
        except:
            frontmatter = {}

        # Extract frontmatter fields
        name = frontmatter.get("name", "unknown")
        description = frontmatter.get("description", "")
        trigger = frontmatter.get("trigger", {})
        version = frontmatter.get("version", "1.0.0")
        created = frontmatter.get("created", datetime.now().isoformat())
        skill_type = frontmatter.get("type", "general")

        # Parse body - simple markdown parsing
        steps = []
        pitfalls = []
        verification = {}
        examples = []

        current_section = None
        lines = body.split("\n")

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("## Steps"):
                current_section = "steps"
            elif line.startswith("## Pitfalls"):
                current_section = "pitfalls"
            elif line.startswith("## Verification"):
                current_section = "verification"
            elif line.startswith("## Examples"):
                current_section = "examples"
            elif line.startswith("## Metadata"):
                current_section = "metadata"
            elif line.startswith("### Example"):
                if current_section == "examples":
                    examples.append({})
            elif line.startswith("- "):
                content = line[2:]
                if current_section == "pitfalls":
                    pitfalls.append(content)
                elif current_section == "verification":
                    if ": " in content:
                        k, v = content.split(": ", 1)
                        verification[k.strip("*")] = v
                elif current_section == "metadata":
                    if ": " in content:
                        k, v = content.split(": ", 1)
                        # Skip metadata for now
                        pass
            elif current_section == "steps" and line[0].isdigit() and ". " in line:
                step = line.split(". ", 1)[1]
                steps.append(step)

        return cls(
            name=name,
            description=description,
            trigger=trigger,
            steps=steps,
            pitfalls=pitfalls,
            verification=verification,
            examples=examples,
            version=version,
            created_at=created,
            skill_type=skill_type,
        )

    def update_success(self) -> None:
        """Record successful use"""
        self.times_used += 1
        self.times_successful += 1
        self.updated_at = datetime.now().isoformat()

    def update_failure(self) -> None:
        """Record failed use"""
        self.times_used += 1
        self.updated_at = datetime.now().isoformat()

    def add_pitfall(self, pitfall: str) -> None:
        """Add a new pitfall"""
        if pitfall not in self.pitfalls:
            self.pitfalls.append(pitfall)
            self.updated_at = datetime.now().isoformat()

    def get_success_rate(self) -> float:
        """Get success rate"""
        if self.times_used == 0:
            return 0.0
        return self.times_successful / self.times_used
