# Auto Craft of Exile

Automatically executes a [Craft of Exile](https://www.craftofexile.com/?game=poe1) Simulator recipe in [Path of Exile](https://www.pathofexile.com/).

> [!WARNING]
> Auto Craft of Exile controls the mouse and keyboard. Remain at the computer, keep the stop hotkey available, and test new recipes with inexpensive materials first.

## Installation

Python 3.14 or newer is required.

```bash
pip install autocraftofexile
autocraftofexile --help
```

Run an exported recipe explicitly:

```bash
autocraftofexile --recipe ./recipe_export_from_craft_of_exile.json
```

If no recipe path is supplied, the application uses its default recipe location.

## How it works

For every recipe step, Auto Craft of Exile:

1. applies the step's crafting method to the configured item position;
2. copies the resulting item data from Path of Exile;
3. evaluates the step's filters locally;
4. follows the recipe until a step passes or the recipe terminates.

The application does not modify the game client or communicate with the game process. It automates configured screen positions and reads item text copied to the clipboard. Moving the game window, changing the UI layout, or covering the relevant inventory positions can therefore make a configured action unsafe or inaccurate.

## How to use

### 1. Copy the base item

Hover the item in Path of Exile and copy its detailed item data using <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>C</kbd>.

![Copy the base item using Ctrl+Alt+C](data/base-item.png)

### 2. Import the base item into Craft of Exile

![Import the base item in the simulator](data/simulator-import-item.png)

### 3. Compose the recipe

Create the sequence of crafting methods and result conditions that should be executed.

![Compose the recipe to execute](data/simulator-recipe.png)

### 4. Validate and export the recipe

Run the recipe in the simulator first. When it behaves as expected, export it to `data/recipe.json`, or pass another path with `--recipe`.

![Validate and export the recipe](data/simulator-generate-export-data.png)

### 5. Start Auto Craft of Exile

```bash
pip install autocraftofexile
autocraftofexile
```

Useful command-line options include:

```text
--recipe PATH   Path to the exported Craft of Exile recipe
--poecd PATH    Path to the Craft of Exile data file
--gui PATH      Path to the GUI-position configuration
--log PATH      Path to the log file
--speed NUMBER  Maximum number of automated actions per second
-h, --help      Show all available options
```

> [!TIP]
> Use a lower `--speed` if item text is copied before Path of Exile has finished updating the item or if input is occasionally missed.

## First-time setup

During first-time setup, Auto Craft of Exile asks for the screen positions of every crafting component required by the recipe.

> [!IMPORTANT]
> Keep the Auto Craft of Exile terminal focused while answering setup prompts. Do not click or use <kbd>Alt</kbd>+<kbd>Tab</kbd> to focus Path of Exile unless a prompt explicitly asks you to interact with it.

For each required currency or component, hover its stash position and press <kbd>Enter</kbd>:

```text
Move mouse to the Orb of Transmutation and press ENTER.
```

![Move mouse to the Orb of Transmutation and press Enter](data/hover-orb-of-transmutation.png)

The setup then records the position of the item being crafted:

```text
Move mouse to the Item Showcase and press ENTER.
```

![Move mouse to the Item Showcase and press Enter](data/base-item.png)

Finally, press the desired start and stop key combinations. The first detected combination is stored.

```text
Press the start hotkey.
start hotkey: f9

Press the stop hotkey.
stop hotkey: f10
```

The setup is written to `data/gui.json`. Run setup again or remove that file if the game window, display scaling, stash layout, or crafting positions change.

## Begin crafting

Before starting:

- open Path of Exile;
- open the stash tab containing every required crafting component;
- place the base item at the configured item position;
- verify that all configured currency positions are visible and contain enough currency;
- make sure the game window and UI scale match the setup;
- keep the stop hotkey available.

Activate crafting with the configured start hotkey, for example <kbd>F9</kbd>. Use the stop hotkey, for example <kbd>F10</kbd>, to request termination.

> [!CAUTION]
> Do not move the mouse, switch windows, move stash items, or change tabs while a recipe is running. Automation uses absolute screen positions and cannot tell whether a different item or control has moved beneath the cursor.

## Supported crafting methods

A recipe step contains a **crafting method** and zero or more **filters**. Auto Craft of Exile executes methods represented by the Craft of Exile recipe export when a corresponding method handler is available in the installed version.

At startup, the recipe is validated against the registered crafting methods. An unsupported method is reported before automation begins, so no recipe actions are performed with a partially understood recipe.

### Currencies

Currency methods apply the corresponding currency at its configured stash position to the configured item position. For example, a recipe may use an Orb of Transmutation as one step and then evaluate whether the resulting magic item satisfies that step's filters.

Each currency used by the recipe must:

- be visible in the open stash tab;
- occupy the same position recorded in `data/gui.json`;
- have enough remaining uses for the recipe;
- be applicable to the current item state.

The exact set of currency methods is determined by `DEFAULT_CRAFTER_METHODS` in the installed release. This keeps method validation and execution aligned. If Craft of Exile adds or renames a method before Auto Craft of Exile supports it, recipe validation fails instead of guessing which action to perform.

### Special methods

Craft of Exile exports may also contain control or special steps rather than a simple currency click. Auto Craft of Exile accepts only special methods that have an explicit registered handler.

Special steps can alter recipe flow, pass without applying a currency, or represent behavior that needs more context than a single click. Because their meaning is handler-specific, always validate the exported recipe at startup and test it with inexpensive materials before relying on it.

A step with `autopass` enabled, or a step without filters, passes immediately after its method behavior has completed. It does not require an item condition to succeed.

## Recipes

Auto Craft of Exile consumes the JSON recipe exported by Craft of Exile. Editing the export by hand is not recommended because method identifiers, modifier identifiers, thresholds, and ranges are interpreted according to the Craft of Exile data file.

Conceptually, a recipe contains:

- recipe data describing the base item and simulator context;
- an ordered sequence of crafting steps;
- a crafting method for each step;
- optional filters that determine whether the resulting item passes;
- conditions inside each filter;
- optional numeric bounds and thresholds.

After applying a step, Auto Craft of Exile parses the copied item, evaluates its filters in order, and records which conditions and modifiers matched. Invalid filter types, unsupported conditions, and unsupported crafting methods fail validation or raise an explicit error rather than silently passing.

### Filters and operators

The supported filter operators are case-insensitive:

- **`and`**: the current accumulated result and the filter must both pass.
- **`not`**: the filter result is negated, then combined with the accumulated result.
- **`or`**: succeeds when the result accumulated so far already passes or when the current filter passes. Evaluation can stop early once the accumulated result is successful.

Filters are evaluated in export order, so operator order matters. Keep related conditions together and verify non-trivial combinations in the Craft of Exile simulator before exporting.

Within one filter, every condition is evaluated and the number of successful conditions is counted:

- when `treshold` is absent, every condition must pass;
- when `treshold` is present, at least that many conditions must pass.

> [!NOTE]
> `treshold` is intentionally spelled as it appears in the exported recipe model.

A condition may define lower and upper bounds. The computed value must fall within the exported condition range. For a numeric modifier condition, the range is checked against the rolled values captured from the matching modifier text.

### Autopass

A recipe step succeeds without condition evaluation when either of these is true:

- the step has `autopass` enabled;
- the step has no filters.

Use autopass for unconditional setup or transition steps. Do not add it to a step whose result must be inspected before the recipe continues.

## Supported rules

Conditions are dispatched by condition ID. Numeric IDs refer to concrete Craft of Exile modifiers. Named IDs refer to calculated rules implemented by Auto Craft of Exile.

### Modifier presence

A numeric condition ID checks for the corresponding modifier from the Craft of Exile data file. All text templates belonging to that modifier must match the copied item text.

Numeric ranges are applied to captured modifier values. When a filter supplies `treshold`, modifier-presence conditions also require the matched item modifier's tier to be at least that threshold.

### Affix capacity and counts

- `open_affix`: total number of open prefix and suffix slots.
- `open_prefix`: number of open prefix slots.
- `open_suffix`: number of open suffix slots.
- `count_affix`: number of prefix and suffix modifiers.
- `count_prefix`: number of prefix modifiers.
- `count_suffix`: number of suffix modifiers.

### Modifier tags

Only prefix and suffix modifiers are counted for these rules:

- `count_attack`: modifiers with the `Attack` attribute.
- `count_nattack`: modifiers without the `Attack` attribute.
- `count_caster`: modifiers with the `Caster` attribute.
- `count_ncaster`: modifiers without the `Caster` attribute.

### Influenced modifiers

- `count_iaffix`: influenced prefixes and suffixes.
- `count_iprefix`: influenced prefixes.
- `count_isuffix`: influenced suffixes.

Influenced modifiers are identified from the item's known influences and normalized modifier names.

### Resistances

- `pseudo_fire_resist`: total fire resistance.
- `pseudo_cold_resist`: total cold resistance.
- `pseudo_lightning_resist`: total lightning resistance.
- `pseudo_chaos_resist`: total chaos resistance.
- `pseudo_elemental_resists`: combined fire, cold, and lightning resistance.
- `pseudo_total_resists`: combined fire, cold, lightning, and chaos resistance.

Combined resistance modifiers contribute to each affected resistance. For example, a modifier that grants all elemental resistances contributes once each to fire, cold, and lightning when calculating `pseudo_elemental_resists`.

### Attributes

- `pseudo_attributes`: combined strength, dexterity, and intelligence.
- `pseudo_strength`: total strength.
- `pseudo_dexterity`: total dexterity.
- `pseudo_intelligence`: total intelligence.

A modifier affecting multiple attributes contributes once for each requested attribute it affects.

### Damage

- `pseudo_total_dps`: average physical, elemental, and chaos hit damage multiplied by attack rate.
- `pseudo_elemental_dps`: average elemental hit damage multiplied by attack rate.
- `pseudo_physical_dps`: average physical hit damage multiplied by attack rate.
- `pseudo_physical_damage`: average physical hit damage before attack rate.
- `pseudo_elemental_damage`: average elemental hit damage before attack rate.

These values are derived from the copied item's properties and modifiers. They are intended to match recipe conditions, not to replace a full character damage calculation.

### Sockets and links

- `pseudo_socket_count`: total number of sockets across all socket groups.
- `pseudo_link_count`: size of the largest linked socket group.
- `pseudo_socket_white`: total white sockets.
- `pseudo_socket_abyss`: total Abyss sockets.
- `pseudo_socket_red`: total red sockets.
- `pseudo_socket_green`: total green sockets.
- `pseudo_socket_blue`: total blue sockets.
- `pseudo_link_white`: highest number of white sockets in one linked group.
- `pseudo_link_abyss`: highest number of Abyss sockets in one linked group.
- `pseudo_link_red`: highest number of red sockets in one linked group.
- `pseudo_link_green`: highest number of green sockets in one linked group.
- `pseudo_link_blue`: highest number of blue sockets in one linked group.

Socket rules count sockets across the entire item. Link-color rules examine each socket group and return the highest matching-color count found in a single group.

## Troubleshooting

### The wrong item or currency is clicked

Re-run GUI setup after changing window position, resolution, display scaling, UI scale, stash tab, or item placement. Confirm that the correct stash tab is open before pressing the start hotkey.

### Imports fail when running `main.py`

Run the installed command or execute the package as a module instead of launching the source file directly:

```bash
uv run autocraftofexile
# or
uv run python -m autocraftofexile.main
```

### A recipe is rejected

Check the terminal and log for the reported method, filter, or condition. Re-export the recipe using the supported Craft of Exile game mode and update Auto Craft of Exile if the export contains a method introduced by a newer simulator release.

### Crafting stops or reads stale item data

Reduce the action rate:

```bash
autocraftofexile --speed 20
```

Also confirm that Path of Exile remains responsive and that no overlay intercepts mouse or keyboard input.

## Building from source

```bash
git clone https://github.com/ProphetLamb/autocraftofexile.git
cd autocraftofexile

# Create .venv, install locked dependencies and the editable project.
uv sync --locked --extra dev

# Run all tests.
uv run --locked --extra dev pytest

# Start the application.
uv run autocraftofexile
```

Build the distributions locally with:

```bash
uv build --no-sources
```

The wheel and source distribution are written to `dist/`.

## Development notes

- Source code uses the `src/autocraftofexile` package layout.
- Tests live in `tests/` and run with `pytest`.
- Add new condition behavior by implementing a `Rule` and registering it in `DEFAULT_RULES`.
- Add new crafting behavior through the crafting-method registry used by `DEFAULT_CRAFTER_METHODS`.
- Keep `uv.lock` committed so local development and CI resolve the same dependency versions.
