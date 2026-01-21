"""
Player information panel widget.

Shows all players' status: money, properties, jail status, etc.
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPalette, QColor

from client.gui.styles import PLAYER_COLORS, PROPERTY_COLORS
from shared.constants import BOARD_SPACES


class PlayerCard(QWidget):
    """Card showing a single player's information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Name and status row
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        
        self._color_indicator = QLabel()
        self._color_indicator.setFixedSize(12, 12)
        self._color_indicator.setStyleSheet("border-radius: 6px;")
        name_row.addWidget(self._color_indicator)
        
        self._name_label = QLabel()
        self._name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_row.addWidget(self._name_label)
        
        self._status_label = QLabel()
        self._status_label.setFont(QFont("Arial", 8))
        name_row.addWidget(self._status_label)
        
        name_row.addStretch()
        
        # Money on same row as name
        self._money_label = QLabel()
        self._money_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self._money_label.setStyleSheet("color: #27AE60;")
        name_row.addWidget(self._money_label)
        
        layout.addLayout(name_row)
        
        # Info row: position and properties
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        
        self._position_label = QLabel()
        self._position_label.setFont(QFont("Arial", 8))
        info_row.addWidget(self._position_label)
        
        self._properties_label = QLabel()
        self._properties_label.setFont(QFont("Arial", 8))
        info_row.addWidget(self._properties_label)
        
        info_row.addStretch()
        
        # Jail cards on same row
        self._jail_cards_label = QLabel()
        self._jail_cards_label.setFont(QFont("Arial", 8))
        info_row.addWidget(self._jail_cards_label)
        
        layout.addLayout(info_row)
    
    def update_player(
        self, 
        player: dict, 
        color: QColor, 
        is_current: bool,
        is_self: bool,
        board_data: dict
    ) -> None:
        """Update with player data."""
        name = player.get("name", "Unknown")
        money = player.get("money", 0)
        position = player.get("position", 0)
        state = player.get("state", "ACTIVE")
        properties = player.get("properties", [])
        jail_cards = player.get("jail_cards", 0)
        
        # Color indicator
        self._color_indicator.setStyleSheet(
            f"background-color: {color.name()}; border-radius: 6px;"
        )
        
        # Name with markers
        name_text = name
        if is_self:
            name_text += " (You)"
        if is_current:
            name_text = "🎲 " + name_text
        elif state == "IN_JAIL":
            name_text = "🔒 " + name_text
        elif state == "BANKRUPT":
            name_text = "💀 " + name_text
        elif state == "DISCONNECTED":
            name_text = "📴 " + name_text
        self._name_label.setText(name_text)
        
        # Status - simplified, now shown as icon in name
        self._status_label.setText("")
        
        # Money
        self._money_label.setText(f"${money:,}")
        
        # Position - shortened
        space_name = BOARD_SPACES.get(position, {}).get("name", f"Space {position}")
        if len(space_name) > 15:
            space_name = space_name[:13] + ".."
        self._position_label.setText(f"📍 {space_name}")
        
        # Properties - compact count
        if properties:
            prop_text = f"🏠 {len(properties)}"
        else:
            prop_text = ""
        self._properties_label.setText(prop_text)
        
        # Jail cards - compact
        if jail_cards > 0:
            self._jail_cards_label.setText(f"🎫 {jail_cards}")
            self._jail_cards_label.show()
        else:
            self._jail_cards_label.hide()
        
        # Highlight current player or self with subtle background
        if is_current:
            self.setStyleSheet("background-color: #3d5a6e; border-radius: 4px;")
        elif is_self:
            self.setStyleSheet("background-color: #2d4a5e; border-radius: 4px;")
        elif state == "BANKRUPT":
            self.setStyleSheet("background-color: #1A1A1A; border-radius: 4px; color: #666;")
        else:
            self.setStyleSheet("background-color: transparent;")


class PlayerPanel(QFrame):
    """Panel showing all players' information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Single outline around entire panel
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            PlayerPanel {
                border: 2px solid #3498DB;
                border-radius: 8px;
                background-color: #2C3E50;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Title
        title = QLabel("Players")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: white; border: none;")
        layout.addWidget(title)
        
        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3498DB; border: none; max-height: 1px;")
        layout.addWidget(separator)
        
        # Scrollable area for player cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setSpacing(2)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.addStretch()
        
        scroll.setWidget(self._container)
        layout.addWidget(scroll)
        
        self._player_cards: list[PlayerCard] = []
        self._player_id: Optional[str] = None
    
    def set_player_id(self, player_id: str) -> None:
        """Set the current player's ID."""
        self._player_id = player_id
    
    def update_players(self, game_state: dict) -> None:
        """Update with current game state."""
        players = game_state.get("players", [])
        current_player_id = game_state.get("current_player_id")
        board_data = game_state.get("board", {})
        
        # Add/remove cards as needed
        while len(self._player_cards) < len(players):
            card = PlayerCard()
            self._container_layout.insertWidget(
                self._container_layout.count() - 1,  # Before stretch
                card
            )
            self._player_cards.append(card)
        
        while len(self._player_cards) > len(players):
            card = self._player_cards.pop()
            card.deleteLater()
        
        # Update each card
        for i, player in enumerate(players):
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            is_current = player.get("id") == current_player_id
            is_self = player.get("id") == self._player_id
            
            self._player_cards[i].update_player(
                player, color, is_current, is_self, board_data
            )
    
    def clear(self) -> None:
        """Clear all player cards."""
        for card in self._player_cards:
            card.deleteLater()
        self._player_cards.clear()
