import json
import os
from typing import List
from src.extractors.base import BaseExtractor
from src.models import RawFact

class GitHubExtractor(BaseExtractor):
    def can_extract(self, file_path: str, content: bytes) -> bool:
        name = os.path.basename(file_path).lower()
        return 'github' in name and file_path.lower().endswith('.json')

    def extract(self, file_path: str, content: bytes) -> List[RawFact]:
        facts = []
        source = os.path.basename(file_path)
        try:
            data = json.loads(content.decode('utf-8'))
        except Exception as e:
            print(f"Error parsing GitHub JSON {source}: {e}")
            return facts

        name = data.get("name")
        if name:
            facts.append(RawFact(field="full_name", value=name.strip(), source=source, method="github_field", confidence=0.8))

        bio = data.get("bio")
        if bio:
            # Can also treat bio as a headline fact if no other headline is found
            facts.append(RawFact(field="headline", value=bio.strip(), source=source, method="github_bio", confidence=0.7))

        url = data.get("github_url")
        if url:
            facts.append(RawFact(field="github_link", value=url.strip(), source=source, method="github_field", confidence=1.0))

        # Languages as skills
        for lang in data.get("languages", []):
            facts.append(RawFact(field="skill", value=lang, source=source, method="github_languages", confidence=0.8))

        # Repositories can enrich projects or skills (e.g. languages)
        for repo in data.get("repositories", []):
            repo_name = repo.get("name")
            repo_langs = repo.get("languages", [])
            for lang in repo_langs:
                facts.append(RawFact(field="skill", value=lang, source=source, method="github_repo_languages", confidence=0.8))
            
            # Record repository as a raw project or skill fact
            if repo_name:
                facts.append(RawFact(
                    field="project_item", 
                    value={
                        "name": repo_name.replace('-', ' '),
                        "description": f"GitHub repository with {repo.get('stars', 0)} stars.",
                        "link": f"{url}/{repo_name}" if url else None,
                        "technologies": repo_langs
                    }, 
                    source=source, 
                    method="github_repo", 
                    confidence=0.8
                ))

        return facts
