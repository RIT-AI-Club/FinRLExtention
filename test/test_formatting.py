from src.backend.mcp_servers.mcp_formatting.server import *
import pytest
import re
from bs4 import BeautifulSoup, Comment, Doctype
import tinycss2


def test_html_only():

    path = Path("latest_report.html")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    # --- 1. Allow only HTML constructs at the top level ---
    for node in soup.contents:
        if isinstance(node, Doctype):
            continue
        if isinstance(node, Comment):
            continue
        if getattr(node, "name", None) == "html":
            continue
        if isinstance(node, str) and node.strip() == "":
            continue

        raise AssertionError(f"Illegal top-level content: {repr(node)}")

    # --- 2. Reject <script> tags ---
    if soup.find("script"):
        raise AssertionError("JavaScript <script> tags are not allowed")

    # --- 3. Reject inline JS event handlers (onclick, onload, etc.) ---
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            if attr.lower().startswith("on"):
                raise AssertionError(f"Inline JS event handler found: {attr}")

    # --- 4. Validate CSS inside <style> tags ---
    for style_tag in soup.find_all("style"):
        css = style_tag.string or ""
        if not css.strip():
            continue

        rules = tinycss2.parse_stylesheet(
            css,
            skip_comments=False,
            skip_whitespace=True,
        )

        # CSS comments appear as tokens with type "comment"
        errors = [r for r in rules if r.type == "error"]
        if errors:
            raise AssertionError(f"Invalid CSS found: {errors}")

    # --- 5. Reject stray text outside tags (comments allowed) ---
    for node in soup.descendants:
        if isinstance(node, Comment):
            continue

        if isinstance(node, str):
            text = node.strip()
            if not text:
                continue

            # Allow CSS text inside <style>
            if node.parent and node.parent.name == "style":
                continue

            # Allow normal HTML text inside tags
            if node.parent and node.parent.name not in ["style"]:
                continue

            raise AssertionError(f"Stray text found: {text}")



def test_same_text():
    # Setup: input text
    text_blocks = []

    # Prepare html to be scanned
    def extract_text(html: str) -> str:
        # Remove HTML tags
        no_tags = re.sub(r"<[^>]+>", " ", html)
 
        # Collapse whitespace
        return re.sub(r"\s+", " ", no_tags).strip()
    def tokenize(s: str) -> list[str]:
        # Split on whitespace and punctuation
        return re.findall(r"[A-Za-z0-9]+", s)

    # Invoke: call tool
    html_path = Path("latest_report.html")
    html = html_path.read_text(encoding="utf-8")

    # Extract text from html
    extracted_text = extract_text(html)

    # Tokenize text
    html_tokens = tokenize(extracted_text)

    # Tokenize text blocks
    for block in text_blocks:
        block_tokens = tokenize(block)

        # Assert: make sure each text block appears in HTML unchanged
        index = 0
        for token in block_tokens:
            try:
                index = html_tokens.index(token, index) + 1
            except ValueError:
                raise AssertionError(f"Missing token: {token!r} from block: {block!r}")
