from datetime import date, datetime
import re

# Your Pydantic models
from app.ingestion.parsers.base import ReleaseNotesParser
from app.schemas.chunk import Chunk, ChunkMetadata

from docutils.core import publish_doctree
from docutils import nodes
from docutils.parsers.rst import roles

class DjangoParser(ReleaseNotesParser):

    @staticmethod
    def sphinx_role_handler(name, rawtext, text, lineno, inliner, options=None, content=None):
        if options is None: options = {}
        if content is None: content = []
        clean_text = text.lstrip('~')
        formatted_string = f"{name} - {clean_text}"
        node = nodes.literal(rawtext, formatted_string, **options)
        return [node], []

    def parse_doctree(self, text: str) -> nodes.document:
        SPHINX_ROLES = [
            'class', 'meth', 'func', 'ref', 'ticket', 'setting', 
            'attr', 'mod', 'exc', 'data', 'const', 'obj', 'term',
            'doc', 'ttag'
        ]
        for role in SPHINX_ROLES:
            roles.register_local_role(role, self.sphinx_role_handler)
        return publish_doctree(text)

    def _extract_version_parts(self, version_str: str) -> tuple[int, int, int]:
        """
        Extracts major, minor, and patch integers from a version string.
        E.g., "4.2" -> (4, 2, 0), "6.0.8" -> (6, 0, 8), "4.2rc1" -> (4, 2, 0)
        """
        # Find all contiguous digits in the string
        parts = [int(p) for p in re.findall(r'\d+', version_str)]
        
        major = parts[0] if len(parts) > 0 else 0
        minor = parts[1] if len(parts) > 1 else 0
        patch = parts[2] if len(parts) > 2 else 0
        
        return major, minor, patch

    def parse(self, text: str) -> list[Chunk]:
        doctree = self.parse_doctree(text)
        chunks = []
        
        # --- 1. Auto-detect version ---
        version = "0.0.0"
        first_title = doctree.next_node(nodes.title)
        if first_title:
            title_text = first_title.astext()
            match = re.search(r'Django\s+([\d\.]+)', title_text, re.IGNORECASE)
            if match:
                version = match.group(1).rstrip('.')
                
        # --- 2. Auto-detect release date ---
        parsed_date = None
        # Target the very first paragraph in the document, which immediately follows the title
        first_paragraph = doctree.next_node(nodes.paragraph)
        
        if first_paragraph:
            date_text = first_paragraph.astext()
            date_match = re.search(
                r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})', 
                date_text
            )
            
            if date_match:
                clean_date_str = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}"
                try:
                    parsed_date = datetime.strptime(clean_date_str, "%B %d %Y").date()
                except ValueError:
                    pass # Fails safely, leaving parsed_date as None

        # --- 3. Walk the tree ---
        self._walk_tree(
            node=doctree,
            path=[],
            chunks=chunks,
            is_breaking=False,
            version=version,
            release_date=parsed_date
        )
        
        return chunks

    def _walk_tree(self, node, path, chunks, is_breaking, version, release_date):
        for child in node.children:
            if isinstance(child, nodes.section):
                title_node = child.next_node(nodes.title)
                section_title = title_node.astext() if title_node else "Untitled"
                new_path = path + [section_title]
                
                title_lower = section_title.lower()
                
                # Top-down flag: evaluates to True if the parent was breaking OR if this header is breaking
                section_is_breaking = is_breaking or ("backward" in title_lower and "incompatible" in title_lower)
                
                section_text_parts = []
                
                for item in child.children:
                    if isinstance(item, nodes.section):
                        continue
                        
                    elif isinstance(item, nodes.bullet_list):
                        # --- MODIFIED: Sub-chunk Bugfixes, Improvements, OR Breaking Changes ---
                        # Using "bugfix" and "improvement" catches both singular and plural forms
                        if "bugfix" in title_lower or "improvement" in title_lower or section_is_breaking:
                            for list_item in item.children:
                                item_text = list_item.astext().strip()
                                if item_text:
                                    self._create_chunk(
                                        text=item_text, 
                                        path=new_path, 
                                        # Automatically passes True for lists under breaking changes
                                        is_breaking=section_is_breaking, 
                                        version=version, 
                                        release_date=release_date, 
                                        chunks=chunks
                                    )
                        else:
                            # Keep lists bundled with standard paragraphs for all other sections
                            list_text = item.astext().strip()
                            if list_text:
                                section_text_parts.append(list_text)
                                
                    elif not isinstance(item, nodes.title):
                        text = item.astext().strip()
                        if text:
                            section_text_parts.append(text)
                
                if section_text_parts:
                    body = "\n\n".join(section_text_parts)
                    self._create_chunk(
                        text=body, 
                        path=new_path, 
                        is_breaking=section_is_breaking, 
                        version=version, 
                        release_date=release_date, 
                        chunks=chunks
                    )
                
                self._walk_tree(child, new_path, chunks, section_is_breaking, version, release_date)

    def _create_chunk(self, text: str, path: list[str], is_breaking: bool, version: str, release_date: date | None, chunks: list[Chunk]):
        hierarchy = " > ".join(path)
        chunk_text = f"Context: Django {version} > {hierarchy}\n\n{text}"
        
        # --- NEW: Text-body fallback detection ---
        # If the section header didn't catch it, check the actual chunk text.
        text_lower = text.lower()
        if not is_breaking and "backward" in text_lower and "incompatible" in text_lower:
            is_breaking = True
            
        major, minor, patch = self._extract_version_parts(version)
        
        # Instantiate the strict Pydantic Metadata model
        metadata = ChunkMetadata(
            technology="django",
            version=version,
            version_major=major,
            version_minor=minor,
            version_patch=patch,
            release_date=release_date,
            is_breaking=is_breaking,
            section_title=path[-1] if path else "General"
        )
        
        # Instantiate the root Chunk model and append
        chunks.append(Chunk(text=chunk_text, metadata=metadata))