"""
Chance and Community Chest card management.
Pokemon-themed cards for Pokemon Monopoly.
"""
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.enums import CardType


class CardAction(Enum):
    """Types of actions a card can trigger."""
    COLLECT_MONEY = auto()      # Collect from bank
    PAY_MONEY = auto()          # Pay to bank
    COLLECT_FROM_PLAYERS = auto()  # Collect from each player
    PAY_TO_PLAYERS = auto()     # Pay each player
    MOVE_TO = auto()            # Move to specific position
    MOVE_FORWARD = auto()       # Move forward X spaces
    MOVE_BACK = auto()          # Move backward X spaces
    GO_TO_JAIL = auto()         # Go directly to jail
    GET_OUT_OF_JAIL = auto()    # Get out of jail free card
    REPAIRS = auto()            # Pay per house/hotel


@dataclass
class Card:
    """Represents a Chance or Community Chest card."""
    
    card_type: CardType
    text_template: str  # Template with {pokemon_XX} placeholders
    action: CardAction
    value: int = 0  # Money amount or position
    per_house: int = 0  # For repairs
    per_hotel: int = 0  # For repairs
    keep: bool = False  # Get out of jail free cards are kept
    
    def get_display_text(self, pokemon_names: Optional[Dict[int, str]] = None) -> str:
        """
        Get the display text with Pokemon names substituted.
        
        Args:
            pokemon_names: Dict mapping board position to Pokemon name
            
        Returns:
            Card text with placeholders replaced
        """
        if pokemon_names is None:
            return self.text_template
        
        text = self.text_template
        # Replace all {pokemon_XX} placeholders
        for position, name in pokemon_names.items():
            placeholder = f"{{pokemon_{position}}}"
            text = text.replace(placeholder, name)
        
        return text
    
    @property
    def text(self) -> str:
        """For backwards compatibility - returns template."""
        return self.text_template
    
    def to_dict(self, pokemon_names: Optional[Dict[int, str]] = None) -> dict:
        """Convert card to dictionary."""
        return {
            "card_type": self.card_type.value,
            "text": self.get_display_text(pokemon_names),
            "text_template": self.text_template,
            "action": self.action.name,
            "value": self.value,
            "per_house": self.per_house,
            "per_hotel": self.per_hotel,
            "keep": self.keep,
        }


# ============================================================
# POKEMON-THEMED CHANCE CARDS (16 cards: ~8 lose, ~8 gain/neutral)
# ============================================================
CHANCE_CARDS = [
    # === GAIN/NEUTRAL CARDS (8) ===
    
    # Movement - positive/neutral
    Card(
        CardType.CHANCE,
        "Professor Oak needs you! Fly to GO and collect $200.",
        CardAction.MOVE_TO,
        value=0
    ),
    Card(
        CardType.CHANCE,
        "{pokemon_11} wants to battle! Advance to {pokemon_11}'s location. If you pass GO, collect $200.",
        CardAction.MOVE_TO,
        value=11  # St. Charles Place - mid-tier property
    ),
    Card(
        CardType.CHANCE,
        "Abra used Teleport! Go back 3 spaces.",
        CardAction.MOVE_BACK,
        value=3
    ),
    Card(
        CardType.CHANCE,
        "Fly to the first Pokémon Center! If you pass GO, collect $200.",
        CardAction.MOVE_TO,
        value=5  # Reading Railroad
    ),
    
    # Money - gain
    Card(
        CardType.CHANCE,
        "You won the Pokémon League lottery! Collect $50.",
        CardAction.COLLECT_MONEY,
        value=50
    ),
    Card(
        CardType.CHANCE,
        "Your Meowth used Pay Day! Collect $100.",
        CardAction.COLLECT_MONEY,
        value=100
    ),
    Card(
        CardType.CHANCE,
        "Found a rare Pokémon card in your old collection! Collect $25.",
        CardAction.COLLECT_MONEY,
        value=25
    ),
    
    # Jail - get out free
    Card(
        CardType.CHANCE,
        "Dugtrio used Dig! Get Out of Jail Free.",
        CardAction.GET_OUT_OF_JAIL,
        keep=True
    ),
    
    # === LOSE CARDS (8) ===
    
    # Movement - to railroads (pay rent)
    Card(
        CardType.CHANCE,
        "All aboard the Magnet Train! Advance to nearest Pokémon Center. If unowned, you may buy it. If owned, pay double the usual fee.",
        CardAction.MOVE_TO,
        value=-2  # Special: nearest railroad
    ),
    Card(
        CardType.CHANCE,
        "Hop on your Bicycle! Advance to the nearest Pokémon Center. If unowned, you may buy it. If owned, pay double.",
        CardAction.MOVE_TO,
        value=-2  # Special: nearest railroad
    ),
    Card(
        CardType.CHANCE,
        "Your PokéNav detects a rare Pokémon! Advance to nearest Power Plant. If unowned, you may catch it. If owned, pay 10x your dice roll.",
        CardAction.MOVE_TO,
        value=-1  # Special: nearest utility
    ),
    
    # Money - lose
    Card(
        CardType.CHANCE,
        "Speeding on your Bike! Officer Jenny fines you $75.",
        CardAction.PAY_MONEY,
        value=75
    ),
    Card(
        CardType.CHANCE,
        "You've been elected Pokémon League Champion! Pay each trainer $50 for autographs.",
        CardAction.PAY_TO_PLAYERS,
        value=50
    ),
    Card(
        CardType.CHANCE,
        "Your Gyarados went on a rampage! Pay $100 for damages.",
        CardAction.PAY_MONEY,
        value=100
    ),
    
    # Repair card
    Card(
        CardType.CHANCE,
        "Your Pokémon damaged the property during training! Pay $25 per Poké Ball (house) and $100 per Ultra Ball (hotel) for repairs.",
        CardAction.REPAIRS,
        per_house=25,
        per_hotel=100
    ),
    
    # Jail
    Card(
        CardType.CHANCE,
        "Team Rocket catches you! Go directly to Jail. Do not pass GO, do not collect $200.",
        CardAction.GO_TO_JAIL
    ),
]

# ============================================================
# POKEMON-THEMED COMMUNITY CHEST CARDS (16 cards: ~8 lose, ~8 gain/neutral)
# ============================================================
COMMUNITY_CHEST_CARDS = [
    # === GAIN CARDS (8) ===
    
    # Movement - positive
    Card(
        CardType.COMMUNITY_CHEST,
        "Professor Elm calls you back to the lab! Advance to GO and collect $200.",
        CardAction.MOVE_TO,
        value=0
    ),
    
    # Money - gain
    Card(
        CardType.COMMUNITY_CHEST,
        "Pokémon Bank error in your favor! Collect $75.",
        CardAction.COLLECT_MONEY,
        value=75
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You sold a rare Pokémon card! Collect $50.",
        CardAction.COLLECT_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Your Pokémon won a contest! Collect $100.",
        CardAction.COLLECT_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You found a Nugget! Collect $50.",
        CardAction.COLLECT_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Gym Leader consultation fee! Collect $25.",
        CardAction.COLLECT_MONEY,
        value=25
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "It's your birthday! Every trainer gives you $10.",
        CardAction.COLLECT_FROM_PLAYERS,
        value=10
    ),
    
    # Jail - get out free
    Card(
        CardType.COMMUNITY_CHEST,
        "Sandshrew used Dig! Get Out of Jail Free.",
        CardAction.GET_OUT_OF_JAIL,
        keep=True
    ),
    
    # === LOSE CARDS (8) ===
    
    # Money - lose
    Card(
        CardType.COMMUNITY_CHEST,
        "Pokémon Center bill for healing your team. Pay $50.",
        CardAction.PAY_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Your Pokémon needs emergency treatment! Pay $100.",
        CardAction.PAY_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Trainer School tuition. Pay $75.",
        CardAction.PAY_MONEY,
        value=75
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "You broke a display case at the PokéMart! Pay $50.",
        CardAction.PAY_MONEY,
        value=50
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Your Snorlax blocked traffic! Pay $100 fine.",
        CardAction.PAY_MONEY,
        value=100
    ),
    Card(
        CardType.COMMUNITY_CHEST,
        "Pokémon storage fees are due. Pay $25.",
        CardAction.PAY_MONEY,
        value=25
    ),
    
    # Repair card
    Card(
        CardType.COMMUNITY_CHEST,
        "Earthquake damaged your properties! Pay $40 per Poké Ball (house) and $115 per Ultra Ball (hotel).",
        CardAction.REPAIRS,
        per_house=40,
        per_hotel=115
    ),
    
    # Jail
    Card(
        CardType.COMMUNITY_CHEST,
        "Team Rocket framed you! Go directly to Jail. Do not pass GO, do not collect $200.",
        CardAction.GO_TO_JAIL
    ),
]


@dataclass
class CardDeck:
    """Manages a deck of cards."""
    
    card_type: CardType
    cards: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)
    _initialized: bool = False
    
    def __post_init__(self):
        """Initialize and shuffle the deck."""
        if not self._initialized:
            self.reset()
    
    def reset(self) -> None:
        """Reset deck to initial shuffled state."""
        if self.card_type == CardType.CHANCE:
            self.cards = [Card(
                card_type=c.card_type,
                text_template=c.text_template,
                action=c.action,
                value=c.value,
                per_house=c.per_house,
                per_hotel=c.per_hotel,
                keep=c.keep
            ) for c in CHANCE_CARDS]
        else:
            self.cards = [Card(
                card_type=c.card_type,
                text_template=c.text_template,
                action=c.action,
                value=c.value,
                per_house=c.per_house,
                per_hotel=c.per_hotel,
                keep=c.keep
            ) for c in COMMUNITY_CHEST_CARDS]
        
        random.shuffle(self.cards)
        self.discard = []
        self._initialized = True
    
    def draw(self) -> Card:
        """
        Draw a card from the deck.
        
        Returns:
            The drawn card
        """
        if not self.cards:
            # Reshuffle discard pile
            self.cards = self.discard
            self.discard = []
            random.shuffle(self.cards)
        
        card = self.cards.pop(0)
        
        # Non-keepable cards go to discard
        if not card.keep:
            self.discard.append(card)
        
        return card
    
    def return_card(self, card: Card) -> None:
        """Return a kept card (Get Out of Jail Free) to the deck."""
        self.discard.append(card)
    
    def to_dict(self) -> dict:
        """Convert deck state to dictionary."""
        return {
            "card_type": self.card_type.value,
            "cards_remaining": len(self.cards),
            "discard_count": len(self.discard),
        }


@dataclass
class CardManager:
    """Manages both card decks."""
    
    chance: CardDeck = field(default_factory=lambda: CardDeck(CardType.CHANCE))
    community_chest: CardDeck = field(default_factory=lambda: CardDeck(CardType.COMMUNITY_CHEST))
    _pokemon_names: Dict[int, str] = field(default_factory=dict)
    
    def set_pokemon_names(self, pokemon_assignments: Dict[int, dict]) -> None:
        """
        Set Pokemon names for card text substitution.
        
        Args:
            pokemon_assignments: Dict from board position to Pokemon data dict
        """
        self._pokemon_names = {
            pos: data.get("name", f"Pokemon #{pos}")
            for pos, data in pokemon_assignments.items()
        }
    
    def draw_chance(self) -> Card:
        """Draw a Chance card."""
        return self.chance.draw()
    
    def draw_community_chest(self) -> Card:
        """Draw a Community Chest card."""
        return self.community_chest.draw()
    
    def get_card_display_text(self, card: Card) -> str:
        """Get display text for a card with Pokemon names substituted."""
        return card.get_display_text(self._pokemon_names)
    
    def return_jail_card(self, card_type: CardType) -> None:
        """Return a Get Out of Jail Free card to appropriate deck."""
        if card_type == CardType.CHANCE:
            self.chance.return_card(Card(
                CardType.CHANCE,
                "Dugtrio used Dig! Get Out of Jail Free.",
                CardAction.GET_OUT_OF_JAIL,
                keep=True
            ))
        else:
            self.community_chest.return_card(Card(
                CardType.COMMUNITY_CHEST,
                "Sandshrew used Dig! Get Out of Jail Free.",
                CardAction.GET_OUT_OF_JAIL,
                keep=True
            ))
    
    def reset(self) -> None:
        """Reset both decks."""
        self.chance.reset()
        self.community_chest.reset()
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chance": self.chance.to_dict(),
            "community_chest": self.community_chest.to_dict(),
        }
