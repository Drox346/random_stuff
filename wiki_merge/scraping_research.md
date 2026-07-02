# Wiki scraping research: vanilla Terraria + Calamity

Research date: 2026-07-02

Target sources:

- Vanilla Terraria: `https://terraria.wiki.gg`
- Calamity Mod: `https://calamitymod.wiki.gg`

Both are wiki.gg MediaWiki instances. The useful base endpoints are:

- `https://terraria.wiki.gg/api.php`
- `https://calamitymod.wiki.gg/api.php`
- `https://terraria.wiki.gg/rest.php/v1/page/{title}/html`
- `https://calamitymod.wiki.gg/rest.php/v1/page/{title}/html`

## High-level findings

The main ingestion path should be the MediaWiki API, not browser HTML scraping.

Both wikis expose:

- MediaWiki 1.43.6
- `action=query` revision/content APIs
- `action=parse` rendered page APIs
- Parsoid/REST HTML
- Cargo/LIBRARIAN
- Scribunto/Lua templates
- DynamicPageList
- Portable Infobox

This gives us several data layers with different trust/shape:

1. Raw wikitext revisions are best for provenance and exact source content.
2. `action=parse` is best for sections, resolved categories, links, templates, and rendered HTML fragments.
3. `action=parse&prop=parsetree` is useful for template-aware extraction without writing a full wikitext parser immediately.
4. Cargo is the best early source for structured facts where a table exists.
5. Parsoid REST HTML is a good fallback for rendered tables/infobox text and includes revision IDs in response headers.

## Site shape

Siteinfo probes:

```text
Terraria Wiki:
  base: https://terraria.wiki.gg/
  server: https://terraria.wiki.gg
  articlepath: /wiki/$1
  generator: MediaWiki 1.43.6

Calamity Mod Wiki:
  base: https://calamitymod.wiki.gg/
  server: https://calamitymod.wiki.gg
  articlepath: /wiki/$1
  generator: MediaWiki 1.43.6
```

Relevant shared extensions observed:

- `LIBRARIAN` / Cargo
- `PageSummaries`
- `Parsoid`
- `Scribunto`
- `DynamicPageList3`
- `Portable Infobox`

## Useful API calls

Raw page content with revision metadata:

```text
api.php?action=query
  &prop=revisions|categories|pageprops|templates
  &titles=Zenith|Moon Lord|Guide:Class setups
  &rvprop=ids|timestamp|size|sha1|comment|content
  &rvslots=main
  &format=json
  &formatversion=2
```

Rendered/expanded page metadata:

```text
api.php?action=parse
  &page=Zenith
  &prop=displaytitle|sections|categories|links|templates|text
  &format=json
  &formatversion=2
```

Template-aware parse tree:

```text
api.php?action=parse
  &page=Ark of the Cosmos
  &prop=parsetree
  &format=json
  &formatversion=2
```

Parsoid HTML:

```text
rest.php/v1/page/Zenith/html
rest.php/v1/page/Ark_of_the_Cosmos/html
```

Parsoid responses returned `content-revision-id` headers, which is useful for provenance.

## Cargo table discovery

Cargo table names differ by wiki.

Vanilla Terraria tables discovered:

- `Drops`
- `Equipinfo`
- `Exclusive`
- `History`
- `Imageinfo`
- `Items`
- `Modifiers`
- `NPCs`
- `Recipes`
- `Weapon_source`
- `_pageData`
- `_fileData`

Calamity tables discovered:

- `ClassSetups`
- `DebuffResistances`
- `Debuffs`
- `Dedicated`
- `Drops`
- `Imageinfo`
- `Immunities`
- `ItemImmunities`
- `NpcDebuffs`
- `Recipes`
- `Summoned`

Important implication: vanilla has a general `Items` Cargo table; Calamity does not appear to expose a general `Items` table. Calamity item stats must come from infobox/template extraction or rendered infobox parsing unless another data source is found.

## Structured data examples

### Vanilla item stats

Cargo query:

```text
terraria.wiki.gg/api.php?action=cargoquery
  &tables=Items
  &fields=_pageName,itemid,name,internalname,type,damage,damagetype,usetime,knockback,rare,sell,tooltip,hardmode
  &where=name="Zenith"
  &limit=5
  &format=json
```

Observed result shape:

```json
{
  "_pageName": "Zenith",
  "itemid": "4956",
  "name": "Zenith",
  "internalname": "Zenith",
  "type": "weapon",
  "damage": "190",
  "damagetype": "Melee",
  "usetime": "30",
  "knockback": "6.5",
  "rare": "10",
  "sell": "<span class=\"coin\" ...>...</span>",
  "tooltip": "",
  "hardmode": "1"
}
```

Vanilla `Items` fields include at least:

- `itemid`
- `name`
- `internalname`
- `image`
- `imagefile`
- `autoswing`
- `stack`
- `consumable`
- `hardmode`
- `type`
- `listcat`
- `tag`
- `damage`
- `damagetype`
- `defense`
- `velocity`
- `knockback`
- `research`
- `rare`
- `buy`
- `sell`
- `axe`
- `pick`
- `hammer`
- `fishing`
- `bait`
- `bonus`
- `toolspeed`
- `usetime`
- `unobtainable`
- `critical`
- `tooltip`
- `placeable`
- `mana`
- `hheal`
- `mheal`
- `bodyslot`
- `buffs`
- `debuffs`

### Recipes

Both wikis expose `Recipes`, but schemas and separators differ.

Vanilla recipe query:

```text
terraria.wiki.gg/api.php?action=cargoquery
  &tables=Recipes
  &fields=_pageName,result,resultid,amount,version,station,ingredients,ings,args,legacy
  &where=result="Zenith"
  &limit=10
  &format=json
```

Observed vanilla row:

```json
{
  "_pageName": "Recipes/Hardmode Anvil/register",
  "result": "Zenith",
  "resultid": "4956",
  "amount": "1",
  "version": "",
  "station": "Mythril Anvil",
  "ingredients": "¦Terra Blade¦^¦Meowmere¦^...",
  "ings": "¦Bee Keeper¦1^¦Copper Shortsword¦1^...",
  "args": "Terra Blade¦1^Meowmere¦1^...",
  "legacy": "0"
}
```

Calamity recipe query:

```text
calamitymod.wiki.gg/api.php?action=cargoquery
  &tables=Recipes
  &fields=_pageName,result,amount,historical,version,station,ingredients,ings,args
  &where=result="Ark of the Cosmos"
  &limit=10
  &format=json
```

Observed Calamity row:

```json
{
  "_pageName": "Recipes/Cosmic Anvil/register",
  "result": "Ark of the Cosmos",
  "amount": "1",
  "historical": "",
  "version": "",
  "station": "Cosmic Anvil",
  "ingredients": "‡Ark of the Elements‡^‡Auric Bar‡^‡Galaxia‡",
  "ings": "‡Ark of the Elements‡1^‡Auric Bar‡5^‡Galaxia‡1",
  "args": "Galaxia‡1^Ark of the Elements‡1^Auric Bar‡5"
}
```

Normalizer needed:

- Split ingredient entries on `^`.
- Vanilla uses `¦` between item and quantity.
- Calamity uses `‡` between item and quantity.
- Prefer `args` or `ings` for amounts.
- Preserve raw strings because edge cases may include images, aliases, or historical markers.

### Drops

Vanilla `Drops` schema:

- `nameraw`
- `id`
- `name`
- `item`
- `quantity`
- `rate`
- `custom`
- `isfromnpc`
- `normal`
- `expert`
- `master`

Vanilla Moon Lord drop rows are clean enough to use, but include HTML in some rates:

```json
{
  "_pageName": "Moon Lord",
  "nameraw": "Moon Lord",
  "item": "Luminite",
  "quantity": "70-90",
  "rate": "100%",
  "normal": "1",
  "expert": "0",
  "master": "0"
}
```

Expert/master and treasure bag rows are represented as separate rows. Some rate fields contain rendered wiki HTML for mode indicators.

Calamity `Drops` schema:

- `Item`
- `Npc`
- `Amount`
- `Chance`

Calamity drop data is much less normalized. `Npc`, `Amount`, and `Chance` often contain wiki markup/HTML:

```json
{
  "_pageName": "Cosmilite Brick",
  "Item": "Cosmilite Brick",
  "Npc": "[[The Devourer of Gods]]",
  "Amount": "155-265&#32;/&#32;'''<abbr class=\"expert_value\" ...>205-335</abbr>''' ...",
  "Chance": "100%"
}
```

Some Calamity rows combine multiple NPCs or progression conditions in the `Npc` field, for example:

```text
[[Butcher]]<br/>[[Deadly Sphere]]<br/>...<br/>(Post-[[File:Devourer of Gods map.png|25px|link=Devourer of Gods]])
```

So Calamity drops should be treated as semi-structured claims, not clean authoritative database rows.

### NPC / boss stats

Vanilla has an `NPCs` table with fields:

- `name`
- `nameraw`
- `image`
- `type`
- `environment`
- `ai`
- `damage`
- `life`
- `defense`
- `knockback`
- `banner`
- `money`
- `npcid`
- `immunities`

Exact query for `name="Moon Lord"` failed because rendered `name` includes HTML. Searching `name LIKE "%Moon%"` found rows for:

- `Moon Lord`
- `Moon Lord's Core`
- `Moon Lord's Hand`
- `Moon Leech Clot`

For Moon Lord, `life` is rendered HTML containing normal/expert/master values, so we need mode-aware HTML cleanup.

Calamity boss stats are not obviously available via a general NPC table. The Devourer of Gods page has a rich raw `npc infobox`, for example:

```text
{{npc infobox
| name = The Devourer of Gods
| type = Boss
| type2 = Burrowing Enemy
| life = {{dv|750,000|1,200,000|1,440,000|1,530,000|1,836,000}}
...
}}
```

That means Calamity boss stats should initially be extracted from raw wikitext/parsetree and/or rendered infobox HTML.

### Class setups

Vanilla `Guide:Class setups` is a large single page. Sample revision size observed: about 150 KB.

Calamity `Guide:Class setups` is a small index page that links to subpages such as:

- `Guide:Class_setups/Pre-Hardmode`
- `Guide:Class_setups/Hardmode`

Calamity also exposes a `ClassSetups` Cargo table with fields:

- `class`
- `progression`
- `type`
- `item`

Example query:

```text
calamitymod.wiki.gg/api.php?action=cargoquery
  &tables=ClassSetups
  &fields=_pageName,class,progression,type,item
  &where=progression="pre-boss"
  &limit=12
  &format=json
```

Observed rows include categories like:

- `accessoryDefense`
- `accessoryMobility`
- `accessoryMobilityPrimary`
- `accessoryOffense`
- `armor`
- `buff`

The `item` field contains rendered-ish wiki markup, images, links, and tooltip annotations. This is useful but needs cleanup into:

- recommended item links
- display labels
- class
- progression stage
- slot/category
- annotations such as "difficult to obtain", "upgrade also viable", "new set bonus"

## Raw wikitext versus rendered output

Item pages are the easiest early target.

Vanilla `Zenith` raw page starts with:

```text
{{item infobox
| auto = 4956
| listcat = projectile melee{{!}}+ / wall-piercing weapons
| hardmode = yes
| sound1 = Item 169.wav
| soundcaption1 = Use
}}
```

Calamity `Ark of the Cosmos` raw page starts with direct item stats:

```text
{{item infobox
| type = Weapon
| damage = 1800
| damagetype = melee
| use = 15
| velocity = 28
| critical = 19%
| knockback = 9.5
| auto = yes
...
}}
```

Boss pages are harder. They often use section-transcluded infoboxes, wrapper templates, mode templates, and expression templates.

Vanilla `Moon Lord` has an `npc infobox` with mode expressions and source-code-derived template calls. Calamity `The Devourer of Gods` has direct-looking fields, but values use Calamity mode templates like `{{dv|...}}`.

## Recommended ingestion strategy

Implement a shared `WikiGGMediaWikiClient` first:

- fetch siteinfo
- fetch raw revisions by title
- fetch parse metadata by title
- fetch parsetree by title
- fetch Cargo table names
- run Cargo queries
- fetch Parsoid HTML if needed
- cache responses by source, page title, revision id, and URL

Then implement source-specific extractors:

- `TerrariaWikiExtractor`
- `CalamityWikiExtractor`

Initial fact-category priorities:

1. Recipes via Cargo
2. Vanilla item stats via Cargo
3. Calamity item stats via infobox parsetree
4. Drops via Cargo, with cleanup and confidence tags
5. Boss stats via infobox parsetree/rendered HTML
6. Class setups via Calamity Cargo and rendered markup cleanup
7. Strategy/prose sections via section extraction and later LLM-assisted claim extraction

## Data quality notes

Structured does not always mean clean.

- Cargo values can contain HTML, wikitext, mode indicators, images, and aliases.
- Exact string matching often fails because fields contain rendered markup.
- Prefer `_pageName`, raw fields like `nameraw`, and canonical page titles where available.
- Calamity Cargo field names use uppercase in some tables (`Item`, `Npc`, `Amount`, `Chance`) and lowercase in others (`result`, `station`, `args`).
- Vanilla Cargo field names are mostly lowercase.
- Recipes are much cleaner than drops.
- Class setup recommendations need availability/progression validation before being trusted.
- Boss behavior/prose still needs semantic extraction; Cargo will not solve it.

## MVP scraper shape

For the first prototype, build a narrow vertical slice around a few pages:

- Vanilla item: `Zenith`
- Vanilla boss: `Moon Lord`
- Calamity item: `Ark of the Cosmos`
- Calamity boss: `The Devourer of Gods`
- Calamity class setup stage: `pre-boss`

For each title, store:

- source id
- canonical title
- page id
- revision id
- timestamp
- sha1 or content hash
- raw wikitext
- parse sections/categories/links/templates
- Cargo rows relevant to the page/entity
- normalized claims
- raw field values alongside normalized values

Do not discard raw values after normalization. They are necessary for provenance, review, and fixing parser edge cases.

## Exotic crossmod source: Unofficial Calamity Bard & Healer

Source page:

- `https://terrariamods.wiki.gg/wiki/Thorium_Crossmod/Unofficial_Calamity_Bard_%26_Healer`

This page lives on Terraria Mods Wiki:

- `https://terrariamods.wiki.gg/api.php`
- site: `Terraria Mods Wiki`
- generator: `MediaWiki 1.43.6`
- extensions include `LIBRARIAN`, `Parsoid`, `Scribunto`, `DynamicPageList3`, and `Portable Infobox`

This source is important because it represents the awkward crossmod case: an unofficial compatibility/addon mod that adds Bard and Healer class content to Calamity and also has extra crossmod content with Catalyst, Hunt of the Old Gods, and Infernum. It can change expected item behavior, class availability, and recipes across mod boundaries.

The main page is a sparse hub rather than a dense data page. Raw revision sample:

```text
title: Thorium Crossmod/Unofficial Calamity Bard & Healer
pageid: 98665
revid: 219685
timestamp: 2025-07-22T15:52:29Z
size: 2481
sha1: 1145cb815fc3111c78eadc8b19921dc5c8212603
```

The hub page says:

```text
A mod that adds Bard and Healer class content to Calamity
Additionally, this mod has extra cross-mod content with Catalyst, Hunt of the Old Gods, and Infernum
Latest version: 0.9.9
tModLoader: 2025.6 stable
```

Rendered parse output for the hub has no normal sections. Useful structure comes from infocards and page links.

Linked content pages include:

- `Thorium Crossmod/Accessories (Calamity Bard and Healer)`
- `Thorium Crossmod/Weapons (Calamity Bard and Healer)`
- `Thorium Crossmod/Materials (Calamity Bard and Healer)`
- `Thorium Crossmod/Recipes (Calamity Bard and Healer)` appears linked, but the exact English page queried as this title was missing during research.
- `Thorium Crossmod/Bard Empowerment Changes (Calamity Bard and Healer)`
- `Thorium Crossmod/Exhumed Items (Calamity Bard and Healer)`
- `Thorium Crossmod/Item Changes (Calamity Bard and Healer)`
- `Thorium Crossmod/Mechanics (Calamity Bard and Healer)` appears linked, but the exact English page query did not return parse data during research.

Category membership and search expose many individual item pages, for example:

- `Thorium Crossmod/Dry Mouth`
- `Thorium Crossmod/Gelatin Therapy`
- `Thorium Crossmod/Blooming Saintess Statue`
- `Thorium Crossmod/Aquaius' Advice`
- `Thorium Crossmod/Blood of Greater Sand Sharks`
- `Thorium Crossmod/Cold Shoulder`
- `Thorium Crossmod/Cotton Mouth`
- `Thorium Crossmod/Disaster`
- `Thorium Crossmod/Singularity`
- `Thorium Crossmod/Wulfrum Weed Wacker`

### Terraria Mods Cargo

Terraria Mods Wiki exposes only a small Cargo surface:

- `Imageinfo`
- `Recipes0`
- `_pageData`
- `_fileData`

`Recipes0` is global across many mods, so filtering is required.

Fields observed:

- `modname`
- `result`
- `resultid`
- `resultimage`
- `resulttext`
- `amount`
- `station`
- `ingredients`
- `ings`
- `args`
- `note`
- `_pageName`

Example filtered query:

```text
terrariamods.wiki.gg/api.php?action=cargoquery
  &tables=Recipes0
  &fields=_pageName,modname,result,amount,station,ingredients,ings,args,note
  &where=modname="Thorium Crossmod"
  &limit=20
  &format=json
```

Observed row:

```json
{
  "_pageName": "Thorium Crossmod/Recipes/Ancient Manipulator/register",
  "modname": "Thorium Crossmod",
  "result": "§Birthplace of Stars",
  "amount": "1",
  "station": "Ancient Manipulator",
  "ingredients": "¦§Gelatin Therapy¦^¦§Lost Oasis¦^¦§Metanova Bar@Catalyst¦",
  "ings": "¦§Gelatin Therapy¦1^¦§Lost Oasis¦1^¦§Metanova Bar@Catalyst¦5",
  "args": "§Gelatin Therapy¦1^§Lost Oasis¦1^§Metanova Bar@Catalyst¦5",
  "note": ""
}
```

Important normalizer details:

- Uses vanilla-style `¦` separators.
- Uses `^` between ingredient entries.
- Uses `§` prefixes to mark mod-scoped/crossmod items in result and ingredient strings.
- Uses `@Catalyst` suffixes for at least some dependency/crossmod ingredient references.
- Includes localized `/zh` register pages in Cargo results, so query filters should exclude `_pageName LIKE "%/zh"` for English-only builds.
- `modname="Thorium Crossmod"` is not specific enough by itself. It includes multiple Thorium Crossmod addons. We need further scoping by page path, item categories, hub-linked pages, result names, or source page provenance.

### Individual item pages

Individual item pages are the best extraction surface.

Example: `Thorium Crossmod/Dry Mouth`

```text
pageid: 124849
revid: 274176
timestamp: 2026-04-04T22:54:11Z
size: 955
sha1: 10051eaffa68bfccdddb9fc513bf3531ec467b16
```

Raw page sample:

```text
{{Item infobox (thorium)
|type=Weapon
|type2=Healer
|type3=Scythe
|damage=12
|damagetype=Radiant
|stack=1
|auto=yes
|research=1
|tooltip=Grants 2 soul essence on direct hit<br/>Ignores 5 points of defense<br/>This scythe is swung directionally instead of spun<br/>Shoots a miniature dust storm every swing
|buff=Soul Essence
|bufftip=Upon reaching 5 stacks of soul essence, you recover (<[[Additional healing|Bonus Healing]]>) health and (<3 × Bonus Healing>) mana
|use=44
|knockback=6.5
|rare=2
|sell={{value|0|0|40|0}}
|hardmode=no
|listcat=Scythes
}}

{{drop infobox
|Desert Scourge|1|25%
|Treasure Bag (Desert Scourge)|1|33.33%
}}
```

This gives useful claims:

- entity: Dry Mouth
- mod/source namespace: Thorium Crossmod / Calamity Bard and Healer
- item type: Weapon, Healer, Scythe
- damage: 12
- damage type: Radiant
- use time: 44
- knockback: 6.5
- rarity: 2
- source/drop: Desert Scourge, 25%
- source/drop: Treasure Bag (Desert Scourge), 33.33%
- behavior: directional scythe, shoots miniature dust storm, grants Soul Essence

Example: `Thorium Crossmod/Blooming Saintess Statue`

```text
{{item infobox
|type=Accessory
|type2=Crafting material
|tooltip=Maximum life increased by 20<br/>Maximum mana increased by 20<br/>12% increased healing speed<br/>14% increased radiant damage<br/>6% increased radiant casting speed<br/>8% increased radiant critical strike chance<br/>Healing spells will heal an additional 2 life<br/>Empowers radiant attacks with daybroken
|debuff=Daybroken
|rare=turquoise
|post-ml=yes
}}
```

This produces both item-stat claims and behavior claims. It also has recipes through `Recipes0`:

```json
{
  "_pageName": "Thorium Crossmod/Recipes/Ancient Manipulator/register",
  "result": "§Blooming Saintess Statue",
  "amount": "1",
  "station": "Ancient Manipulator",
  "args": "Archangel's Heart¦1^Archdemon's Curse¦1^Uelibloom Bar¦4"
}
```

Example: `Thorium Crossmod/Gelatin Therapy`

```text
{{item infobox
|type=Tool
|type2=Crafting material
|type3=Healer
|hheal = 13 + [[additional healing|Bonus Healing]]
|mana=25
|tooltip=Shoots a bouncy sludge ball that can heal and cure any player including youself
|use=36
|velocity=10
|rare=4
|projectile=Therapeutic Sludge
|hardmode=no
}}
```

This demonstrates why item infobox extraction cannot be purely numeric: `hheal` can contain expressions and links, and tooltip text contains mechanical behavior.

### Item-change pages

`Thorium Crossmod/Item Changes (Calamity Bard and Healer)` is especially important because it describes modifications to existing Calamity and Thorium items.

Unlike the hub, this page has real sections:

- `Reworks`
- `Anahita's Arpeggio`
- `Belching Saxophone`
- `Face Melter`
- `Armor`
- `Wings`
- `Other`

The rendered links include existing Calamity/Thorium concepts such as:

- `Anahita's Arpeggio`
- `Belching Saxophone`
- `Face Melter`
- `Astral Breastplate`
- `Demonshade Greaves`
- `Omega Blue armor`
- `Celestial Carrier`
- `Dragon's Wings`
- `Shooting Star armor`
- `Blood Harvest`
- `Bone Baton`

This should be treated as a source of override/patch claims, not just new-item claims. For example, if the page says an existing Calamity weapon has been reworked into a Bard weapon, the resolver should record a crossmod override:

```text
subject: Anahita's Arpeggio
claim type: item_behavior_override / class_conversion
context: Unofficial Calamity Bard & Healer enabled
source: Terraria Mods Wiki page section
authority: crossmod source, lower than game-data export, higher than generic Calamity wiki for this addon context if pack includes the addon
```

### Extraction strategy for this source

The normal wiki.gg adapter still works, but the extractor needs a source-specific layer:

1. Fetch hub page and parse hub links.
2. Expand category membership for `Category:Thorium Crossmod`.
3. Filter to pages related to the Calamity Bard and Healer addon:
   - hub-linked pages
   - item pages linked from `Weapons`, `Accessories`, `Materials`, `Exhumed Items`, `Item Changes`
   - pages whose categories include Calamity Bard/Healer-specific item groups when available
   - recipe rows whose result/ingredients contain `§`-prefixed linked items found in this addon
4. Extract item infobox templates from raw wikitext/parsetree:
   - `item infobox`
   - `Item infobox (thorium)`
5. Extract `drop infobox` templates from raw wikitext/parsetree.
6. Query `Recipes0` with `modname="Thorium Crossmod"`, exclude localized pages, then map recipes back to known addon items.
7. Parse prose sections from item-change/mechanics pages as override claims.
8. Preserve sparse/uncertain status aggressively.

Recommended confidence handling:

- Direct infobox field: medium-high wiki claim.
- Cargo `Recipes0` row mapped to known addon item: medium-high wiki claim.
- `drop infobox` direct template: medium wiki claim.
- DPL-generated list membership: medium-low until confirmed by the linked item page.
- Item-change prose: medium, but semantically important; mark as crossmod override and queue for review if it conflicts with Calamity/Thorium pages.
- Missing linked pages: review item, not hard failure.

This source is exactly why the system needs source provenance and context-specific override semantics. It adds facts that are false for plain Calamity, false for plain Thorium, and true only when this crossmod addon is enabled.

## Sources checked

- `https://terraria.wiki.gg/api.php`
- `https://calamitymod.wiki.gg/api.php`
- `https://terraria.wiki.gg/wiki/Special:CargoTables`
- `https://calamitymod.wiki.gg/wiki/Special:CargoTables`
- `https://terraria.wiki.gg/wiki/Special:CargoTables/Items`
- `https://terraria.wiki.gg/wiki/Special:CargoTables/Recipes`
- `https://terraria.wiki.gg/wiki/Special:CargoTables/Drops`
- `https://terraria.wiki.gg/wiki/Special:CargoTables/NPCs`
- `https://calamitymod.wiki.gg/wiki/Special:CargoTables/Recipes`
- `https://calamitymod.wiki.gg/wiki/Special:CargoTables/Drops`
- `https://calamitymod.wiki.gg/wiki/Special:CargoTables/ClassSetups`
- `https://calamitymod.wiki.gg/wiki/Special:CargoTables/Summoned`
- `https://terrariamods.wiki.gg/api.php`
- `https://terrariamods.wiki.gg/wiki/Thorium_Crossmod/Unofficial_Calamity_Bard_%26_Healer`
- `https://terrariamods.wiki.gg/wiki/Special:CargoTables`
- `https://terrariamods.wiki.gg/wiki/Special:CargoTables/Recipes0`
