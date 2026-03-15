# Digital Twins Tracker 👥

Track Twin.fun share prices, check your holdings, and get AI-generated market
commentary — all with verifiable on-chain proof of the AI analysis.

---

## What are Digital Twins?

[Twin.fun](https://twin.fun) is OpenGradient's platform where AI personas are
tokenized as shares on a bonding curve. Each twin is a unique AI identity:
- **Price** is determined by a bonding curve: more holders = higher price
- **Shares** can be bought/sold like any token
- **Access** to the twin's AI is gated by share ownership

---

## Architecture

```
DigitalTwinSharesV1 Contract (Base Sepolia)
  0x065fb766051c9a212218c9D5e8a9B83fb555C17c
        │
        ▼
  getBuyPrice() ──────────── bonding curve price
  protocolFeePercent() ───── fee calculation
  sharesBalance() ────────── your holdings
        │
        ▼
  OpenGradient TEE LLM ───── AI price commentary
        │                    + payment_hash proof
        ▼
  buyShares() / sellShares() ── optional execution
```

---

## Setup

```bash
cd boilerplates/digital-twins-tracker
pip install -r requirements.txt
cp ../../.env.example .env
# Edit .env with OG_PRIVATE_KEY and SAMPLE_TWIN_ID
```

Find a twin ID at [twin.fun](https://twin.fun) — it's the bytes16 hex in the URL.

## Run

```bash
# Read-only price check (safe)
python tracker.py

# Check a specific twin
python tracker.py --twin 85f4f72079114bfcac1003134e5424f4

# Buy 1 share (prompts for confirmation)
python tracker.py --twin <twin_id> --buy 1

# Sell 1 share
python tracker.py --twin <twin_id> --sell 1
```

---

## Sample Output

```
==============================================================
👥 Digital Twin Tracker — Twin.fun (Base Sepolia)
==============================================================
  Twin ID  : 85f4f72079114bfcac1003134e5424f4
  Wallet   : 0xYourWallet...
  Contract : 0x065fb766051c9a212218c9D5e8a9B83fb555C17c
==============================================================

📊 Fetching price data from bonding curve...

  Buy Price (base)  : 0.000100 ETH
  Protocol Fee      : 0.000005 ETH
  Subject Fee       : 0.000005 ETH
  ──────────────────────────────────
  Total Buy Cost    : 0.000110 ETH
  Sell Proceeds     : 0.000095 ETH
  Price Spread      : 0.000015 ETH
  Your Holdings     : 0 shares

🤖 Generating AI commentary (TEE-verified)...

  Commentary: This twin shows a tight spread of 0.000015 ETH between
  buy cost and sell proceeds, suggesting reasonable liquidity. The 10%
  total fee load (5% protocol + 5% subject) is standard for early-stage
  twins. Current price suggests limited holders — high risk, high upside.

  💰 Payment Hash : 0xabc123...
  🔗 Verify proof : https://sepolia.basescan.org/tx/0xabc123...
```

---

## Common Errors

| Error | Fix |
|-------|-----|
| `Insufficient value` | The buy price moved — tracker adds 2% buffer automatically |
| `Creation guard` | First buy must meet `minSharesToCreate` (usually ≥1) |
| `Owner required` | Twin is pre-claimed; owner must do the first buy |

---

## Security Checklist

- ✅ Always confirm buy/sell transactions before executing
- ✅ Check ETH balance before buying (tracker shows required cost)
- ✅ Start with `amount=1` to test price discovery
- ⚠️ Bonding curves have price slippage for large orders
- ⚠️ This boilerplate is for Base Sepolia testnet — verify contract address before mainnet use
