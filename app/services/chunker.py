"""
AST-aware code chunker.

Why this exists: naive chunking (split every N tokens) cuts functions in
half, which wrecks embedding quality because the embedding for that chunk
represents half a function's logic with no surrounding context. This
chunker parses each file into an AST with tree-sitter and emits one chunk
per semantic unit (function, method, class), so every chunk is a complete,
self-contained piece of code.

tree_sitter_languages bundles pre-built grammars for many languages, so
there's no separate compilation step needed for each language binding.
"""

from dataclasses import dataclass
from pathlib import Path
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser

PY_LANGUAGE   = Language(tree_sitter_python.language(), "python")
JS_LANGUAGE   = Language(tree_sitter_javascript.language(), "javascript")
TS_LANGUAGE   = Language(tree_sitter_typescript.language_typescript(), "typescript")


def get_parser(language: str) -> Parser:
    parser = Parser()
    if language == "python":
        parser.set_language(PY_LANGUAGE)
    elif language == "javascript":
        parser.set_language(JS_LANGUAGE)
    elif language in ("typescript",):
        parser.set_language(TS_LANGUAGE)
    return parser


CHUNK_NODE_TYPES = {
    "typescript": ["function_declaration", "method_definition", "class_declaration", "arrow_function"],
    "javascript": ["function_declaration", "method_definition", "class_declaration", "arrow_function"],
    "python": ["function_definition", "class_definition"],
}

EXTENSION_TO_LANGUAGE = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".py": "python",
}

@dataclass
class CodeChunk:
    file_path:str
    start_line:int
    end_line:int
    language:str
    symbol_name:str | None
    symbol_type:str
    content:str

def _extract_symbol_name(node)->str | None:
    """Pulls a human readable name out of a decleration node"""
    name_node=node.child_by_field_name("name")
    if name_node:
        return name_node.text.decode("utf-8")
    if node.type=="arrow_function" and node.parent and node.parent.type=="variable_declarator":
        parent_name=node.parent.child_by_field_name("name")
        if parent_name:
            return parent_name.text.decode("utf-8")
    return None

def chunk_file(file_path:str)->list[CodeChunk]:
    """Parses a single file and returns one codechunk per semantic unit"""
    ext=Path(file_path).suffix
    language=EXTENSION_TO_LANGUAGE.get(ext)
    if language is None:
        return []
    
    source=Path(file_path).read_text(encoding="utf-8",errors="ignore")
    parser=get_parser(language)
    tree=parser.parse(bytes(source,"utf-8"))
    target_types=CHUNK_NODE_TYPES[language]
    chunks:list[CodeChunk]=[]

    def visit(node):
        if node.type in target_types:
            chunks.append(
                CodeChunk(
                    file_path=file_path,
                    start_line=node.start_point[0]+1,
                    end_line=node.end_point[0]+1,
                    language=language,
                    symbol_name=_extract_symbol_name(node),
                    symbol_type=node.type.replace("_declaration", "").replace("_definition", ""),
                    content=node.text.decode("utf-8")
                )
            )
            if node.type in ("class_declaration", "class_definition"):
                for child in node.children:
                    visit(child)
            return
        for child in node.children:
            visit(child)
        
    visit(tree.root_node)

    if not chunks:
        chunks.append(
            CodeChunk(
                file_path=file_path,
                start_line=1,
                end_line=len(source.splitlines()),
                language=language,
                symbol_name=None,
                symbol_type="module",
                content=source,
            )
        )

    return chunks