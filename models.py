from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class World:
    name: str
    period: str
    description: str
    locations: List[str]
    factions: List[str]
    magic_system: Optional[str] = None
    conflicts: List[str] = None

@dataclass
class Plot:
    theme: str
    protagonist: Dict
    antagonist: Dict
    key_events: List[str]
    ending: str

@dataclass
class Chapter:
    number: int
    title: str
    content: str
    word_count: int
    characters: Dict[str, str]

@dataclass
class NovelConfig:
    genre: str
    style: str
    chapter_count: int
    word_range: tuple