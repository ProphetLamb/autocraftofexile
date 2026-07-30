# Auto Craft of Exile

Automatically executes a Craft of Exile Simulator recipe in Path of Exile.

## How to use

### Copy your base item using `[CTRL]+[ALT]+[C]`

![Copy your base item using `[CTRL]+[ALT]+[C]`](data/base-item.png)

### Import the base item in the simulator

![Import the base item in the simulator](data/simulator-import-item.png)

### Compose the recipe to execute

![Compose the recipe to execute](data/simulator-recipe.png)

### Validate your recipe works. Then export the recipe to `data/recipe.json`

![Validate your recipe works. Then export the recipe to `data/recipe.json`](data/simulator-generate-export-data.png)

### Start `autocraftofexile`

Install package from PyPi. Ensure python 3.14 is installed on your system.

```bash
pip install autocraftofexile
autocraftofexile
```

### First time setup

For the first time setup `autocraftofexile` asks the positions of crafting components.
| Info |
| --- |
| Keep `autocraftofexile` focussed. Do not click or `[Alt]+[Tab]` Path of Exile to focus. |

```
Move mouse to the Orb of Transmutation and press ENTER.
```

![Move mouse to the Orb of Transmutation and press ENTER.](data/hover-orb-of-transmutation.png)

Then `autocraftofexile` asks for the position of the item.

```
Move mouse to the Item Showcase and press ENTER.
```

![Move mouse to the Item Showcase and press ENTER.](data/base-item.png)

Finally the setup asks for the start and stop hotkey. The first key-combination pressed is used.

```
Press the start hotkey.
start hotkey: f9

Press the stop hotkey.
stop hotkey: f10
```

The setup is written to `data/gui.json`.

### Begin crafting

Activate `autocraftofexile` crafting by pressing the start hotkey, e.g. `f9`.
| Info |
| --- |
| Ensure the Stash tab is open on the page with the crafting items |


## Building from source

```bash
git clone https://github.com/ProphetLamb/autocraftofexile.git
# activate the python venv
python -m venv .venv
# use activate.bash or activate.fish on linux
.venv\Scripts\Activate.ps1
# install uv
pip install uv
# install autocraftofexile
uv pip install -e .
# start the program
autocraftofexile
```