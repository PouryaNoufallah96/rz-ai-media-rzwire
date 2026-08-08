# Industrial Token - confirmed market identity

Source authority: CoinMarketCap listing confirmed directly by the project owner on 2026-08-08, with pool identity resolved through GeckoTerminal for the verified Market Analytics pipeline.

## Stable identity

- CoinMarketCap listing: https://coinmarketcap.com/currencies/industrial/
- CoinMarketCap ID: `35883`
- Name: Industrial
- Symbol: INDUSTRIAL
- Chain: BNB Smart Chain
- Token standard: BEP-20
- Contract: `0x9e06e1203bdc3747ee3ab5fa9488619bcf2a2666`
- Verified Market Analytics provider: GeckoTerminal public API
- GeckoTerminal network: `bsc`
- Resolved liquidity pool: `0xd5916c07de3ffbb728a07e118fa89b5452ea9602`
- Pool name: Industrial / MGC
- Token side in the pool: base

## Usage rules

- Market Analytics must use this exact contract and pool identity for INDUSTRIAL price history.
- Do not identify a token by symbol alone; `INDUSTRIAL` must resolve through this contract.
- CoinMarketCap prices, market cap, rank, volume, holder count, and supply figures are volatile. Fetch them at runtime only; do not store or reuse them as evergreen facts.
- Do not use the whitepaper's base price or base market-cap illustration as live market data.
