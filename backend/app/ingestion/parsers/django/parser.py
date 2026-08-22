from datetime import date, datetime
import re

# Your Pydantic models & base parser interface
from app.ingestion.parsers.base import ReleaseNotesParser
from app.schemas.chunk import Chunk, ChunkMetadata

from docutils.core import publish_doctree
from docutils import nodes
from docutils.parsers.rst import roles

class DjangoParser(ReleaseNotesParser):

    @staticmethod
    def sphinx_role_handler(name, rawtext, text, lineno, inliner, options=None, content=None):
        """
        Custom Sphinx role handler to prevent docutils parsing crashes.
        Strips inline tilde markers and formats roles (e.g., :class:`View`) as literal strings.
        """
        if options is None: options = {}
        if content is None: content = []
        clean_text = text.lstrip('~')
        formatted_string = f"{name} - {clean_text}"
        node = nodes.literal(rawtext, formatted_string, **options)
        return [node], []

    def parse_doctree(self, text: str) -> nodes.document:
        """
        Registers custom Sphinx documentation roles and parses raw reST text 
        into an Abstract Syntax Tree (AST) document object.
        """
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
        Used for semantic version range filtering in ChromaDB.
        """
        parts = [int(p) for p in re.findall(r'\d+', version_str)]
        
        major = parts[0] if len(parts) > 0 else 0
        minor = parts[1] if len(parts) > 1 else 0
        patch = parts[2] if len(parts) > 2 else 0
        
        return major, minor, patch

    def parse(self, text: str) -> list[Chunk]:
        """
        Orchestrates the entire document parsing workflow:
        1. Generates the AST doctree.
        2. Auto-detects framework version from the document title.
        3. Auto-detects release date from the introductory paragraph.
        4. Recursively walks the AST tree to generate atomic Chunks.
        """
        doctree = self.parse_doctree(text)
        chunks = []
        
        # --- 1. Auto-detect version from the primary document title ---
        version = "0.0.0"
        first_title = doctree.next_node(nodes.title)
        if first_title:
            title_text = first_title.astext()
            match = re.search(r'Django\s+([\d\.]+)', title_text, re.IGNORECASE)
            if match:
                version = match.group(1).rstrip('.')
                
        # --- 2. Auto-detect release date from the opening paragraph ---
        parsed_date = None
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

        # --- 3. Trigger recursive AST tree traversal ---
        self._walk_tree(
            node=doctree,
            path=[],
            chunks=chunks,
            is_breaking=False,
            version=version,
            release_date=parsed_date
        )
        
        return chunks

    """
    ====================================================================
    RECURSIVE TREE-WALKING & CHUNKING WORKFLOW CHART:
    ====================================================================
    
    [Start: parse()] --> Generates AST DocTree
                             │
                             ▼
            [ _walk_tree() / Recursive Traversal ]
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
  [Is Node a Section?]                 [Is Node a Standard Paragraph/List?]
         │                                       │
         ├─ Extract Section Title                ├─ Track hierarchical breadcrumbs (`path`)
         ├─ Check Title for "Backward Incompatible" ├─ Bundle text or item elements
         └─ Cascade `is_breaking` Flag Down      └─ Pass to `_create_chunk()`
                                                         │
                                                         ▼
                                            [ _create_chunk() ]
                                                         │
                                                         ├─ Build Context String ("Context: Django X > Title > ...")
                                                         ├─ Run Fallback Text Check for Breaking Changes
                                                         ├─ Extract Version Integers (Major, Minor, Patch)
                                                         ├─ Initialize Pydantic `ChunkMetadata` (Auto-calculates Unix Timestamp)
                                                         └─ Append Type-Safe `Chunk` Object to Output List
    ====================================================================
    """
    def _walk_tree(self, node, path, chunks, is_breaking, version, release_date):
        """
        Recursively traverses the document nodes, tracking hierarchical path breadcrumbs,
        detecting breaking-change boundaries, and separating bullet lists from body paragraphs.
        """
        for child in node.children:
            if isinstance(child, nodes.section):
                title_node = child.next_node(nodes.title)
                section_title = title_node.astext() if title_node else "Untitled"
                new_path = path + [section_title]
                
                title_lower = section_title.lower()
                
                # Top-down inheritance flag: True if parent was breaking OR current header indicates breaking changes
                section_is_breaking = is_breaking or ("backward" in title_lower and "incompatible" in title_lower)
                
                section_text_parts = []
                
                for item in child.children:
                    if isinstance(item, nodes.section):
                        continue # Nested sections handled in recursive callback step
                        
                    elif isinstance(item, nodes.bullet_list):
                        # Granular sub-chunking: Break down individual items under bugfixes, improvements, or breaking changes
                        if "bugfix" in title_lower or "improvement" in title_lower or section_is_breaking:
                            for list_item in item.children:
                                item_text = list_item.astext().strip()
                                if item_text:
                                    self._create_chunk(
                                        text=item_text, 
                                        path=new_path, 
                                        is_breaking=section_is_breaking, 
                                        version=version, 
                                        release_date=release_date, 
                                        chunks=chunks
                                    )
                        else:
                            # Keep general bullet lists bundled with standard section text
                            list_text = item.astext().strip()
                            if list_text:
                                section_text_parts.append(list_text)
                                
                    elif not isinstance(item, nodes.title):
                        text = item.astext().strip()
                        if text:
                            section_text_parts.append(text)
                
                # Flush accumulated section text body as a single chunk if present
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
                
                # Recursive call for nested subsections
                self._walk_tree(child, new_path, chunks, section_is_breaking, version, release_date)

    def _create_chunk(self, text: str, path: list[str], is_breaking: bool, version: str, release_date: date | None, chunks: list[Chunk]):
        """
        Constructs the final chunk string with hierarchical context prefixes, 
        validates breaking change flags via text-body fallback checks, 
        and packages metadata into a strict Pydantic model before appending.
        """
        hierarchy = " > ".join(path)
        chunk_text = f"Context: Django {version} > {hierarchy}\n\n{text}"
        
        # Text-body fallback detector: catches unflagged breaking changes in the text content
        text_lower = text.lower()
        if not is_breaking and "backward" in text_lower and "incompatible" in text_lower:
            is_breaking = True
            
        major, minor, patch = self._extract_version_parts(version)
        
        # Instantiate strict Pydantic Metadata model (model validator automatically populates release_date_ts)
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
        
        # Append finalized Chunk object
        chunks.append(Chunk(text=chunk_text, metadata=metadata))