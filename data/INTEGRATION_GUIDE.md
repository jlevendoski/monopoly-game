# Pokemon Data Integration Guide

## Overview

This document describes the `pokemon_enhanced.json` data file and how to integrate it into your project. The file contains data for all 1025 Pokemon (Generations 1-9) including names, types, evolution chains, and image URLs.

---

## File Location

```
pokemon-scraper/pokemon_enhanced.json
```

---

## Data Structure

The JSON file is a dictionary keyed by National Pokedex number (as strings):

```json
{
  "1": {
    "name": "Bulbasaur",
    "types": ["Grass", "Poison"],
    "evolves_from": null,
    "evolves_to": ["Ivysaur"],
    "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/1.png"
  },
  "2": {
    "name": "Ivysaur",
    "types": ["Grass", "Poison"],
    "evolves_from": "Bulbasaur",
    "evolves_to": ["Venusaur"],
    "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/2.png"
  },
  "25": {
    "name": "Pikachu",
    "types": ["Electric"],
    "evolves_from": "Pichu",
    "evolves_to": ["Raichu"],
    "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png"
  },
  "133": {
    "name": "Eevee",
    "types": ["Normal"],
    "evolves_from": null,
    "evolves_to": ["Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon", "Leafeon", "Glaceon", "Sylveon"],
    "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/133.png"
  }
}
```

---

## Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | The Pokemon's English name (e.g., "Bulbasaur", "Mr. Mime") |
| `types` | `string[]` | Array of 1-2 types (e.g., `["Fire"]` or `["Grass", "Poison"]`) |
| `evolves_from` | `string \| null` | Name of the Pokemon this evolves from, or `null` if it's a base form |
| `evolves_to` | `string[]` | Array of Pokemon names this can evolve into (empty `[]` if fully evolved) |
| `image_url` | `string` | URL to the official artwork PNG image (475x475 pixels, transparent background) |

---

## Pokemon Types

All possible type values:

```
Normal, Fire, Water, Electric, Grass, Ice, Fighting, Poison,
Ground, Flying, Psychic, Bug, Rock, Ghost, Dragon, Dark, Steel, Fairy
```

---

## Common Usage Patterns

### Python

```python
import json

# Load the data
with open('pokemon_enhanced.json', 'r', encoding='utf-8') as f:
    pokemon = json.load(f)

# Get a Pokemon by dex number
bulbasaur = pokemon["1"]
print(bulbasaur["name"])  # "Bulbasaur"

# Get a Pokemon by name
def find_by_name(name):
    for dex_num, poke in pokemon.items():
        if poke["name"].lower() == name.lower():
            return dex_num, poke
    return None, None

dex, pikachu = find_by_name("Pikachu")
print(f"#{dex}: {pikachu['name']}")  # "#25: Pikachu"

# Get all Pokemon of a specific type
fire_pokemon = [
    (dex, p) for dex, p in pokemon.items() 
    if "Fire" in p["types"]
]

# Get all fully evolved Pokemon (nothing evolves from them)
fully_evolved = [
    p for p in pokemon.values() 
    if not p["evolves_to"]
]

# Get evolution chain for a Pokemon
def get_evolution_chain(pokemon_data, start_name):
    """Returns the full evolution chain as a list."""
    chain = []
    current_name = start_name
    
    # Go backwards to find the base
    while current_name:
        dex, poke = None, None
        for d, p in pokemon_data.items():
            if p["name"] == current_name:
                dex, poke = d, p
                break
        if poke:
            chain.insert(0, current_name)
            current_name = poke.get("evolves_from")
        else:
            break
    
    # Go forwards from the last Pokemon in chain
    while True:
        dex, poke = None, None
        for d, p in pokemon_data.items():
            if p["name"] == chain[-1]:
                dex, poke = d, p
                break
        if poke and poke.get("evolves_to"):
            # Just take first evolution for linear chains
            chain.append(poke["evolves_to"][0])
        else:
            break
    
    return chain

print(get_evolution_chain(pokemon, "Ivysaur"))  
# ["Bulbasaur", "Ivysaur", "Venusaur"]
```

### JavaScript / TypeScript

```javascript
// Load the data
const pokemon = require('./pokemon_enhanced.json');
// or: import pokemon from './pokemon_enhanced.json';

// Get a Pokemon by dex number
const bulbasaur = pokemon["1"];
console.log(bulbasaur.name);  // "Bulbasaur"

// Get a Pokemon by name
function findByName(name) {
    return Object.entries(pokemon).find(
        ([dex, p]) => p.name.toLowerCase() === name.toLowerCase()
    );
}

const [dex, pikachu] = findByName("Pikachu");
console.log(`#${dex}: ${pikachu.name}`);  // "#25: Pikachu"

// Get all Pokemon of a specific type
const firePokemon = Object.entries(pokemon).filter(
    ([dex, p]) => p.types.includes("Fire")
);

// Get random Pokemon
function getRandomPokemon() {
    const keys = Object.keys(pokemon);
    const randomKey = keys[Math.floor(Math.random() * keys.length)];
    return { dex: randomKey, ...pokemon[randomKey] };
}
```

### TypeScript Type Definition

```typescript
interface Pokemon {
    name: string;
    types: string[];
    evolves_from: string | null;
    evolves_to: string[];
    image_url: string;
}

type PokemonDatabase = Record<string, Pokemon>;
```

---

## Fetching Images

The `image_url` field points to official artwork hosted on GitHub (via PokeAPI's sprite repository). These images are:

- **Format:** PNG with transparent background
- **Size:** ~475x475 pixels
- **Hosted:** GitHub raw content (reliable, fast CDN)

### Python Example

```python
from urllib.request import urlopen
from PIL import Image
from io import BytesIO

def fetch_pokemon_image(pokemon_entry):
    """Fetch and return a PIL Image for a Pokemon."""
    url = pokemon_entry["image_url"]
    with urlopen(url) as response:
        return Image.open(BytesIO(response.read()))

# Usage
image = fetch_pokemon_image(pokemon["25"])  # Pikachu
image.save("pikachu.png")
```

### JavaScript Example (Node.js)

```javascript
const https = require('https');
const fs = require('fs');

function fetchPokemonImage(pokemonEntry, outputPath) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(outputPath);
        https.get(pokemonEntry.image_url, (response) => {
            response.pipe(file);
            file.on('finish', () => {
                file.close();
                resolve(outputPath);
            });
        }).on('error', reject);
    });
}

// Usage
await fetchPokemonImage(pokemon["25"], "pikachu.png");
```

### Caching Images Locally

For games or applications that need offline support or faster loading:

```python
import os
from pathlib import Path
from urllib.request import urlopen

def download_all_sprites(pokemon_data, output_dir="sprites"):
    """Download all Pokemon sprites to a local directory."""
    Path(output_dir).mkdir(exist_ok=True)
    
    for dex_num, poke in pokemon_data.items():
        output_path = Path(output_dir) / f"{dex_num.zfill(4)}.png"
        
        if output_path.exists():
            continue  # Skip already downloaded
        
        print(f"Downloading {poke['name']}...")
        with urlopen(poke["image_url"]) as response:
            output_path.write_bytes(response.read())

# After downloading, update your code to load locally:
def get_local_sprite_path(dex_num):
    return f"sprites/{str(dex_num).zfill(4)}.png"
```

---

## Special Cases

### Pokemon with Branching Evolutions

Some Pokemon can evolve into multiple different Pokemon. The `evolves_to` array will contain all possibilities:

```json
{
  "133": {
    "name": "Eevee",
    "evolves_to": ["Vaporeon", "Jolteon", "Flareon", "Espeon", "Umbreon", "Leafeon", "Glaceon", "Sylveon"]
  }
}
```

### Pokemon with No Evolutions

Pokemon that don't evolve (legendaries, single-stage Pokemon) have:
- `evolves_from`: `null`
- `evolves_to`: `[]`

```json
{
  "150": {
    "name": "Mewtwo",
    "evolves_from": null,
    "evolves_to": []
  }
}
```

### Pokemon with Special Characters in Names

Some Pokemon have special characters that are preserved:

| Pokemon | Name in JSON |
|---------|--------------|
| Nidoran♀ | `"Nidoran♀"` |
| Nidoran♂ | `"Nidoran♂"` |
| Mr. Mime | `"Mr. Mime"` |
| Farfetch'd | `"Farfetch'd"` |
| Flabébé | `"Flabébé"` |
| Type: Null | `"Type: Null"` |

When searching by name, consider normalizing:

```python
def normalize_name(name):
    return name.lower().replace(" ", "").replace(".", "").replace("'", "").replace(":", "")
```

---

## Dex Number Ranges by Generation

| Generation | Dex Range | Count |
|------------|-----------|-------|
| Gen 1 (Kanto) | 1-151 | 151 |
| Gen 2 (Johto) | 152-251 | 100 |
| Gen 3 (Hoenn) | 252-386 | 135 |
| Gen 4 (Sinnoh) | 387-493 | 107 |
| Gen 5 (Unova) | 494-649 | 156 |
| Gen 6 (Kalos) | 650-721 | 72 |
| Gen 7 (Alola) | 722-809 | 88 |
| Gen 8 (Galar) | 810-905 | 96 |
| Gen 9 (Paldea) | 906-1025 | 120 |

```python
# Get all Gen 1 Pokemon
gen1 = {k: v for k, v in pokemon.items() if 1 <= int(k) <= 151}
```

---

## Integration Checklist

When integrating into your project:

- [ ] Copy `pokemon_enhanced.json` to your project's data/assets directory
- [ ] Add JSON loading code appropriate to your language/framework
- [ ] Decide on image loading strategy (fetch on demand vs. pre-download)
- [ ] Handle the `null` case for `evolves_from` (base Pokemon)
- [ ] Handle the empty array case for `evolves_to` (fully evolved)
- [ ] Consider caching images locally for offline/performance
- [ ] Add error handling for network requests when fetching images

---

## File Regeneration

If you need to regenerate `pokemon_enhanced.json` (e.g., after PokeAPI updates):

```bash
cd pokemon-scraper

# 1. Download fresh data from PokeAPI
./download_pokeapi.sh

# 2. Run the enhancement script
python3 enhance_pokemon.py

# 3. Output will be in pokemon_enhanced.json
```

---

## License & Attribution

- Pokemon data sourced from [PokeAPI](https://pokeapi.co/) (free, open API)
- Pokemon images from [PokeAPI Sprites](https://github.com/PokeAPI/sprites)
- Pokemon is © Nintendo/Game Freak/The Pokemon Company

For commercial use, please review Nintendo's guidelines on fan projects.
