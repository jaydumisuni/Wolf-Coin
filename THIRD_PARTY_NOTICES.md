# Third-Party Notices and Provenance Register

Wolf-Coin studies open-source trading, automation, and review systems. This file is the repository-level register for code or assets that are actually adapted, vendored, or distributed with Wolf-Coin.

**Current status:** No third-party source code or binary asset has yet been committed to Wolf-Coin. The repository currently contains original planning documents only.

## Rules

For every accepted third-party component, add:

- project name;
- repository URL;
- exact commit, tag, or package version;
- copyright holder(s);
- license and full notice requirements;
- Wolf-Coin files containing adapted or vendored material;
- whether the material was modified;
- source-evaluation record;
- distribution or source-offer obligations where applicable.

Do not treat a mention in `docs/SOURCE_RESEARCH_MAP.md` as proof that code was reused.

## Planned research sources — no code imported yet

The following sources are currently research candidates only:

- `jaydumisuni/Sergeant`
- `jaydumisuni/openclaw`
- `Ichinga-Samuel/aiomql`
- `geraked/metatrader5`
- `codedpro/mt5-trade-split-manager`
- `freqtrade/freqtrade`
- `hummingbot/hummingbot`
- `jesse-ai/jesse`
- `Drakkar-Software/OctoBot`
- `enarjord/passivbot`
- `nautechsystems/nautilus_trader`
- `QuantConnect/Lean`
- `Lumiwealth/lumibot`
- TradingAgents and FinRL-family research repositories
- Additional repositories discovered through the GitHub `forex-bot` topic

Before any source material is accepted, create a commit-specific evaluation under `research/sources/` and update this file.

## Entry template

```markdown
## <Project name>

- Source: <repository URL>
- Version/commit: <exact identifier>
- Copyright: <holder and years from source>
- License: <SPDX identifier and license file>
- Wolf-Coin use: <concept/code/asset and destination files>
- Modified: yes/no
- Evaluation: <research record path>
- Required notices: <summary>
```
