from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class PageMetadata:
    index: int
    image: str
    text: str = ""
    markdown: str = ""
    elements: Optional[list] = None