Project handoff: Local resolved wiki generator for modpacks

I want to build a local, browsable wiki generator for heavily modded game modpacks. The first target is Terraria/tModLoader, specifically an ultramodded Infernum-style modpack called Infernal Eclipse of Ragnarok.

The goal is not to mirror existing wikis. The goal is to generate a new local wiki that combines information from multiple upstream wikis and resolves conflicts/overwrites so the final pages describe what is actually true in the combined modpack.

Think of this as a modpack-aware documentation compiler.

Source wikis are inputs.
The generated local wiki is the compiled output.

Relevant source wikis include, but are not limited to:

- Infernal Eclipse of Ragnarok wiki
- Calamity Mod wiki
- Calamity Infernum wiki
- Thorium Mod wiki
- Thorium Crossmod wiki
- Secrets of the Shadows wiki
- Consolaria wiki
- Ragnarok Mod wiki

Prefer wiki.gg and official/mod-maintained documentation. Avoid fandom wikis unless there is no better alternative.

The core project is the merge/resolution layer.

Existing wikis usually describe individual mods in isolation. In a large modpack, the final behavior may be changed by other mods, compatibility layers, difficulty modes, configs, progression edits, or pack-specific balancing.

The generated local wiki should not merely place all source information side by side. It should resolve the information into a coherent final view for the actual modpack.

Examples of things that may need resolution:

- base Calamity boss behavior vs Infernum boss behavior
- base mod recipes vs crossmod or modpack recipe changes
- source mod item stats vs pack-adjusted item stats
- vanilla progression vs Calamity progression vs modpack progression
- individual mod class setup advice vs final pack availability
- Thorium Healer/Bard content interacting with Calamity and crossmod support
- boss drops, shops, shimmer transformations, crafting chains, and suche 
- multiplayer-relevant strategy vs solo-oriented wiki advice
- stale wiki information vs newer changelogs or observed pack behavior

The most important question the system should answer is:

“What is true in this specific modpack?”

A successful generated page should also be able to explain:

- which sources contributed to this result
- which source won when sources conflicted
- why that source won
- whether a claim is verified, inferred, generated, curated, or uncertain
- whether an apparent conflict is a real contradiction or a context-specific override
- whether a recommendation is actually available at the relevant progression point

The final wiki should be browsable like a normal wiki, with pages for things such as:

- bosses
- items
- weapons
- armor
- accessories
- recipes
- materials
- crafting stations
- NPCs
- shops
- drops
- biomes
- buffs/debuffs
- mechanics
- progression stages
- class setups
- role-specific strategy pages

However, correctness matters more than coverage. A small set of trustworthy resolved pages is more valuable than a large generated wiki full of subtle errors.

Manual curation should be considered part of the baseline, not a failure.

The realistic goal is not full automation immediately. The system should support curated corrections, local notes, and manually enforced override decisions. These curated decisions should survive future source updates and should be treated as high-priority local truth unless explicitly reviewed or changed.

The generated wiki should clearly distinguish between:

- resolved factual data
- source-derived claims
- generated synthesis
- manually curated corrections
- uncertain or unverified claims
- conflicts that were resolved
- conflicts that still need review

LLMs may be useful for semantic resolution, especially when deciding how prose from different sources relates. But an LLM should not be treated as the source of truth. It should operate with constrained context, explicit source information, and project-specific rules. Its outputs should preserve provenance and should be reviewable.

The system should avoid the failure mode:

source pages → LLM → polished generated page

That would likely create convincing but unreliable documentation.

The desired conceptual flow is closer to:

source pages → extracted information → grouped claims/entities/topics → resolution using rules, context, LLMs, and curation → generated local wiki pages with provenance

The exact architecture is intentionally open. The important constraint is that the merge/resolution result must be auditable and not just opaque generated prose.

For Terraria specifically, wiki scraping alone may be enough for an early prototype, but it will not be enough for high-trust structured facts forever. Recipes, item stats, shops, drops, shimmer transformations, NPC data, and progression gates may eventually need to come from the actual loaded tModLoader modpack or another authoritative game-data export. Wiki text remains valuable for explanations, mechanics, strategy, and context.

The project should support the idea that different fact categories have different authority rules.

For example:

- Infernum-specific boss behavior should generally supersede base Calamity boss behavior.
- Modpack-specific documentation should generally supersede individual mod documentation.
- Manual local curation should generally supersede scraped wiki text.
- Extracted game data, if added later, should generally supersede wiki text for structured facts like recipes, drops, shops, and item stats.
- Strategy sections may require synthesis and should not be treated the same as numeric item data.
- Class setup recommendations should be constrained by actual progression availability.

A major stretch goal is an update watcher.

The update watcher should monitor upstream wiki changes and safely update the generated local wiki. It should not blindly overwrite curated truth or regenerate unrelated pages unnecessarily. It should be able to detect that source material changed, determine what local knowledge may be affected, rerun the relevant resolution work, and produce a review report when necessary.

Important update-watcher behavior:

- upstream changes should not automatically override manual curation
- changes touching already-curated topics should create review items
- source freshness and revision information should be preserved
- generated pages should be reproducible from source data and curation
- the system should support stable/local builds rather than constantly mutating trusted pages without review

The project is worthwhile only if the merge/resolution engine is treated as the core product.

Scraping is ingestion.
The local wiki frontend is presentation.
The resolver, curation layer, provenance model, and conflict handling are the actual value.

Major failure modes to avoid:

- generating pages that look authoritative but are subtly wrong
- merging entities only by display name and accidentally combining unrelated things
- treating all source wikis as equally authoritative
- averaging contradictory claims instead of applying overwrite semantics
- losing source provenance
- allowing upstream updates to erase local corrections
- recommending gear or strategies unavailable in the actual pack progression
- confusing base mod behavior with Infernum or modpack behavior
- hiding uncertainty
- producing a large wiki before the generated information is trustworthy

The guiding quality principles:

- correctness over coverage
- provenance over polish
- explicit uncertainty over invented certainty
- curated truth over blind automation
- reproducibility over one-off generated pages
- modpack-specific truth over generic wiki aggregation
- semantic resolution over text concatenation

The first target domain is Terraria Infernal Eclipse of Ragnarok, but the broader concept should not be unnecessarily Terraria-locked. The underlying idea could apply to other heavily modded games where documentation from multiple mods must be merged into a final pack-specific truth.

The long-term vision:

A local, provenance-aware, modpack-specific wiki compiler that combines multiple upstream documentation sources, resolves overwrites and conflicts, supports curated corrections, tracks why claims were chosen, and generates a browsable wiki that is more useful for actual play than reading each individual mod wiki separately.