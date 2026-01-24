"""
Pokemon data management for Pokemon-themed Monopoly.

Handles loading Pokemon data, finding evolution chains, and
generating random Pokemon assignments for game properties.
Also handles item data for railroads (Poké Balls) and utilities
(healing items, teaching items).
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PokemonInfo:
    """Information about a single Pokemon."""
    dex_number: str
    name: str
    types: List[str]
    image_url: str
    evolves_from: Optional[str]
    evolves_to: List[str]
    
    def to_dict(self) -> dict:
        return {
            "dex_number": self.dex_number,
            "name": self.name,
            "types": self.types,
            "image_url": self.image_url,
        }
    
    @classmethod
    def from_dict(cls, data: dict, dex_number: str = "") -> "PokemonInfo":
        return cls(
            dex_number=data.get("dex_number", dex_number),
            name=data["name"],
            types=data.get("types", []),
            image_url=data.get("image_url", ""),
            evolves_from=data.get("evolves_from"),
            evolves_to=data.get("evolves_to", []),
        )


@dataclass
class ItemInfo:
    """Information about a single item (Poké Ball, healing item, or TM)."""
    item_id: str
    name: str
    api_name: str
    image_url: str
    flavor_text: Optional[str]
    effect: Optional[str]
    cost: int
    teaches_move: Optional[str] = None  # Only for TMs
    
    def to_dict(self) -> dict:
        result = {
            "item_id": self.item_id,
            "name": self.name,
            "api_name": self.api_name,
            "image_url": self.image_url,
            "flavor_text": self.flavor_text,
            "effect": self.effect,
            "cost": self.cost,
        }
        if self.teaches_move:
            result["teaches_move"] = self.teaches_move
        return result
    
    @classmethod
    def from_dict(cls, data: dict, item_id: str = "") -> "ItemInfo":
        return cls(
            item_id=data.get("item_id", item_id),
            name=data["name"],
            api_name=data.get("api_name", ""),
            image_url=data.get("image_url", ""),
            flavor_text=data.get("flavor_text"),
            effect=data.get("effect"),
            cost=data.get("cost", 0),
            teaches_move=data.get("teaches_move"),
        )


class PokemonDatabase:
    """
    Manages Pokemon data and provides methods for finding
    evolution chains suitable for Monopoly property groups.
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the Pokemon database.
        
        Args:
            data_path: Path to pokemon_enhanced.json. If None, uses default location.
        """
        self._pokemon: Dict[str, PokemonInfo] = {}
        self._name_to_dex: Dict[str, str] = {}
        self._two_stage_chains: List[List[str]] = []
        self._three_stage_chains: List[List[str]] = []
        self._single_pokemon: List[str] = []
        
        if data_path is None:
            # Default path relative to this file
            data_path = Path(__file__).parent.parent.parent / "data" / "pokemon_enhanced.json"
        
        self._load_data(data_path)
        self._analyze_evolution_chains()
    
    def _load_data(self, data_path: Path) -> None:
        """Load Pokemon data from JSON file."""
        if not data_path.exists():
            raise FileNotFoundError(f"Pokemon data file not found: {data_path}")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        for dex_num, poke_data in raw_data.items():
            pokemon = PokemonInfo(
                dex_number=dex_num,
                name=poke_data["name"],
                types=poke_data.get("types", []),
                image_url=poke_data.get("image_url", ""),
                evolves_from=poke_data.get("evolves_from"),
                evolves_to=poke_data.get("evolves_to", []),
            )
            self._pokemon[dex_num] = pokemon
            self._name_to_dex[pokemon.name] = dex_num
    
    def _analyze_evolution_chains(self) -> None:
        """Analyze all Pokemon to categorize evolution chains."""
        seen_pokemon = set()
        
        for dex_num, pokemon in self._pokemon.items():
            if pokemon.name in seen_pokemon:
                continue
            
            chain = self._get_full_evolution_chain(pokemon.name)
            
            # Mark all Pokemon in this chain as seen
            for name in chain:
                seen_pokemon.add(name)
            
            # Categorize by chain length
            if len(chain) == 1:
                self._single_pokemon.append(chain[0])
            elif len(chain) == 2:
                self._two_stage_chains.append(chain)
            elif len(chain) >= 3:
                # For chains longer than 3, just take the first 3
                self._three_stage_chains.append(chain[:3])
    
    def _get_full_evolution_chain(self, pokemon_name: str) -> List[str]:
        """
        Get the full linear evolution chain for a Pokemon.
        
        For Pokemon with branching evolutions (like Eevee), only follows
        the first evolution path to keep chains linear.
        """
        chain = []
        
        # Go backwards to find the base Pokemon
        current_name = pokemon_name
        while current_name:
            chain.insert(0, current_name)
            dex = self._name_to_dex.get(current_name)
            if dex and self._pokemon[dex].evolves_from:
                current_name = self._pokemon[dex].evolves_from
            else:
                break
        
        # Go forwards from the last Pokemon in chain
        while True:
            last_name = chain[-1]
            dex = self._name_to_dex.get(last_name)
            if dex:
                evolves_to = self._pokemon[dex].evolves_to
                if evolves_to:
                    # Take first evolution only for linear chains
                    chain.append(evolves_to[0])
                else:
                    break
            else:
                break
        
        return chain
    
    def get_pokemon(self, dex_number: str) -> Optional[PokemonInfo]:
        """Get Pokemon by dex number."""
        return self._pokemon.get(dex_number)
    
    def get_pokemon_by_name(self, name: str) -> Optional[PokemonInfo]:
        """Get Pokemon by name."""
        dex = self._name_to_dex.get(name)
        return self._pokemon.get(dex) if dex else None
    
    def get_random_two_stage_chain(self) -> List[PokemonInfo]:
        """Get a random 2-stage evolution chain."""
        if not self._two_stage_chains:
            raise ValueError("No 2-stage evolution chains available")
        
        chain_names = random.choice(self._two_stage_chains)
        return [self.get_pokemon_by_name(name) for name in chain_names]
    
    def get_random_three_stage_chain(self) -> List[PokemonInfo]:
        """Get a random 3-stage evolution chain."""
        if not self._three_stage_chains:
            raise ValueError("No 3-stage evolution chains available")
        
        chain_names = random.choice(self._three_stage_chains)
        return [self.get_pokemon_by_name(name) for name in chain_names]
    
    def get_random_single_pokemon(self, count: int = 1) -> List[PokemonInfo]:
        """Get random Pokemon that have no evolutions."""
        if len(self._single_pokemon) < count:
            raise ValueError(f"Not enough single Pokemon available (need {count}, have {len(self._single_pokemon)})")
        
        names = random.sample(self._single_pokemon, count)
        return [self.get_pokemon_by_name(name) for name in names]
    
    @property
    def two_stage_chain_count(self) -> int:
        return len(self._two_stage_chains)
    
    @property
    def three_stage_chain_count(self) -> int:
        return len(self._three_stage_chains)
    
    @property
    def single_pokemon_count(self) -> int:
        return len(self._single_pokemon)


# Property group configurations
# Maps property group to (positions in order, chain_type)
# chain_type: 2 = 2-stage evolution, 3 = 3-stage evolution, 0 = random singles
PROPERTY_GROUP_CONFIG = {
    "BROWN": {
        "positions": [1, 3],
        "chain_type": 2,  # 2-stage evolution
    },
    "LIGHT_BLUE": {
        "positions": [6, 8, 9],
        "chain_type": 3,  # 3-stage evolution
    },
    "PINK": {
        "positions": [11, 13, 14],
        "chain_type": 3,
    },
    "ORANGE": {
        "positions": [16, 18, 19],
        "chain_type": 3,
    },
    "RED": {
        "positions": [21, 23, 24],
        "chain_type": 3,
    },
    "YELLOW": {
        "positions": [26, 27, 29],
        "chain_type": 3,
    },
    "GREEN": {
        "positions": [31, 32, 34],
        "chain_type": 3,
    },
    "DARK_BLUE": {
        "positions": [37, 39],
        "chain_type": 0,  # Random singles (no evolution)
    },
}


def generate_pokemon_assignments(database: Optional[PokemonDatabase] = None) -> Dict[int, dict]:
    """
    Generate random Pokemon assignments for all property positions.
    
    Returns:
        Dictionary mapping board position to Pokemon data dict:
        {
            position: {
                "dex_number": str,
                "name": str,
                "types": List[str],
                "image_url": str,
            }
        }
    """
    if database is None:
        database = PokemonDatabase()
    
    assignments: Dict[int, dict] = {}
    
    # Track which chains we've used to avoid duplicates
    used_two_stage = set()
    used_three_stage = set()
    used_singles = set()
    
    for group_name, config in PROPERTY_GROUP_CONFIG.items():
        positions = config["positions"]
        chain_type = config["chain_type"]
        
        if chain_type == 3:
            # Get a 3-stage evolution chain
            attempts = 0
            while attempts < 100:
                chain = database.get_random_three_stage_chain()
                chain_key = tuple(p.name for p in chain)
                if chain_key not in used_three_stage:
                    used_three_stage.add(chain_key)
                    break
                attempts += 1
            
            # Assign Pokemon to positions in evolution order
            for i, pos in enumerate(positions):
                if i < len(chain):
                    assignments[pos] = chain[i].to_dict()
        
        elif chain_type == 2:
            # Get a 2-stage evolution chain
            attempts = 0
            while attempts < 100:
                chain = database.get_random_two_stage_chain()
                chain_key = tuple(p.name for p in chain)
                if chain_key not in used_two_stage:
                    used_two_stage.add(chain_key)
                    break
                attempts += 1
            
            for i, pos in enumerate(positions):
                if i < len(chain):
                    assignments[pos] = chain[i].to_dict()
        
        elif chain_type == 0:
            # Get random single Pokemon (no evolutions)
            attempts = 0
            pokemon_list = []
            while len(pokemon_list) < len(positions) and attempts < 100:
                singles = database.get_random_single_pokemon(len(positions))
                pokemon_list = [p for p in singles if p.name not in used_singles]
                attempts += 1
            
            for i, pos in enumerate(positions):
                if i < len(pokemon_list):
                    used_singles.add(pokemon_list[i].name)
                    assignments[pos] = pokemon_list[i].to_dict()
    
    return assignments


# Singleton database instance (lazy loaded)
_database_instance: Optional[PokemonDatabase] = None


def get_pokemon_database() -> PokemonDatabase:
    """Get the singleton Pokemon database instance."""
    global _database_instance
    if _database_instance is None:
        _database_instance = PokemonDatabase()
    return _database_instance


class ItemDatabase:
    """
    Manages item data for railroads and utilities.
    Loads Poké Balls, healing items, and teaching items (TMs).
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the Item database.
        
        Args:
            data_dir: Path to directory containing item JSON files.
                      If None, uses default location.
        """
        self._pokeballs: Dict[str, ItemInfo] = {}
        self._healing_items: Dict[str, ItemInfo] = {}
        self._teaching_items: Dict[str, ItemInfo] = {}
        
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        
        self._load_data(data_dir)
    
    def _load_items_from_file(self, file_path: Path) -> Dict[str, ItemInfo]:
        """Load items from a JSON file."""
        items = {}
        if not file_path.exists():
            return items
        
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        for item_id, item_data in raw_data.items():
            # Skip metadata keys like "_NOTE"
            if item_id.startswith("_"):
                continue
            items[item_id] = ItemInfo(
                item_id=item_id,
                name=item_data["name"],
                api_name=item_data.get("api_name", ""),
                image_url=item_data.get("image_url", ""),
                flavor_text=item_data.get("flavor_text"),
                effect=item_data.get("effect"),
                cost=item_data.get("cost", 0),
                teaches_move=item_data.get("teaches_move"),
            )
        
        return items
    
    def _load_data(self, data_dir: Path) -> None:
        """Load all item data from JSON files."""
        self._pokeballs = self._load_items_from_file(data_dir / "pokeballs.json")
        self._healing_items = self._load_items_from_file(data_dir / "healing_items.json")
        self._teaching_items = self._load_items_from_file(data_dir / "teaching_items.json")
    
    def get_random_pokeballs(self, count: int = 4) -> List[ItemInfo]:
        """Get random Poké Balls for railroad spaces."""
        if len(self._pokeballs) < count:
            raise ValueError(f"Not enough Poké Balls available (need {count}, have {len(self._pokeballs)})")
        
        item_ids = random.sample(list(self._pokeballs.keys()), count)
        return [self._pokeballs[item_id] for item_id in item_ids]
    
    def get_random_healing_item(self) -> ItemInfo:
        """Get a random healing item for utility space."""
        if not self._healing_items:
            raise ValueError("No healing items available")
        
        item_id = random.choice(list(self._healing_items.keys()))
        return self._healing_items[item_id]
    
    def get_random_teaching_item(self) -> ItemInfo:
        """Get a random teaching item (TM) for utility space."""
        if not self._teaching_items:
            raise ValueError("No teaching items available")
        
        item_id = random.choice(list(self._teaching_items.keys()))
        return self._teaching_items[item_id]
    
    @property
    def pokeball_count(self) -> int:
        return len(self._pokeballs)
    
    @property
    def healing_item_count(self) -> int:
        return len(self._healing_items)
    
    @property
    def teaching_item_count(self) -> int:
        return len(self._teaching_items)


# Railroad positions on the board
RAILROAD_POSITIONS = [5, 15, 25, 35]

# Utility positions on the board
UTILITY_POSITIONS = {
    "healing": 12,   # Electric Company -> Healing item
    "teaching": 28,  # Water Works -> Teaching item (TM)
}


def generate_item_assignments(database: Optional[ItemDatabase] = None) -> Dict[int, dict]:
    """
    Generate random item assignments for railroads and utilities.
    
    Returns:
        Dictionary mapping board position to item data dict:
        {
            position: {
                "item_id": str,
                "name": str,
                "api_name": str,
                "image_url": str,
                "flavor_text": str,
                "effect": str,
                "cost": int,
                "teaches_move": str (only for TMs),
                "item_type": str ("pokeball", "healing", or "teaching"),
            }
        }
    """
    if database is None:
        database = ItemDatabase()
    
    assignments: Dict[int, dict] = {}
    
    # Assign Poké Balls to railroads
    pokeballs = database.get_random_pokeballs(len(RAILROAD_POSITIONS))
    for position, pokeball in zip(RAILROAD_POSITIONS, pokeballs):
        item_dict = pokeball.to_dict()
        item_dict["item_type"] = "pokeball"
        assignments[position] = item_dict
    
    # Assign healing item to first utility
    healing_item = database.get_random_healing_item()
    healing_dict = healing_item.to_dict()
    healing_dict["item_type"] = "healing"
    assignments[UTILITY_POSITIONS["healing"]] = healing_dict
    
    # Assign teaching item to second utility
    teaching_item = database.get_random_teaching_item()
    teaching_dict = teaching_item.to_dict()
    teaching_dict["item_type"] = "teaching"
    assignments[UTILITY_POSITIONS["teaching"]] = teaching_dict
    
    return assignments


# Singleton item database instance (lazy loaded)
_item_database_instance: Optional[ItemDatabase] = None


def get_item_database() -> ItemDatabase:
    """Get the singleton Item database instance."""
    global _item_database_instance
    if _item_database_instance is None:
        _item_database_instance = ItemDatabase()
    return _item_database_instance
