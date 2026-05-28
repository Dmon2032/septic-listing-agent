# Real Estate Data Provider Evaluation

## For the Septic Listing Agent — Southern California, Non-Agent Use

Last updated: May 26, 2026

-----

## TL;DR

**Start with RentCast.** Free tier (50 calls/mo), permissive commercial ToS, an Active Listings endpoint covering all 50 states, and pay-as-you-go pricing. Build the whole pipeline on RentCast, prove the use case, then graduate to a heavier provider (PropertyRadar for CA-deep features, or ATTOM if you scale) only if the data turns out to be insufficient.

**Avoid:** anything that “scrapes” Zillow, Realtor.com, or Redfin — including third-party APIs that wrap those scrapes. You inherit the ToS exposure. More on this at the bottom.

-----

## The licensing reality you need to understand first

This is the part most blog posts skip. There are three separate “data worlds” in U.S. real estate, and they have very different rules:

### 1. Direct MLS feeds (MLS Grid, Bridge Interactive, Spark API)

These are the “true source” feeds — the same data your local Realtor sees. They sound appealing, but they are **mostly off the table for you** as a non-agent:

- Only licensed real estate professionals or technology companies with proper licensing can access these APIs. Mortgage and insurance professionals, among others, are not eligible unless they hold a valid MLS license.
- MLS licensing policies require the head broker (broker of record) to sign the data license agreement and authorize access for agents in their brokerage. Individual agents cannot access MLS data independently, even with an active real estate license.
- And critically: MLS vendors with data licenses can only create products and services for participating MLS members, not their own products and services.

Translation: even if you partnered with a licensed broker, the MLS data you receive is for serving licensed-agent customers — not for running your own lead-gen list. **Cross this whole tier off unless you’re a licensed CA broker or partnering with one as your customer.**

### 2. Authorized aggregators (RentCast, ATTOM, PropertyRadar, PropStream, BatchData)

These companies have signed their own data licenses with MLSs and public-record sources, then re-license to end users with much more permissive terms — including non-agents doing lead gen. This is where you live.

### 3. Public records (county assessors, recorder’s offices)

Free in theory, brutal to assemble in practice (every county has different formats and many lack APIs). The aggregators above already do this work for you.

-----

## The shortlist

### RentCast — recommended starting point ⭐

- **What it has:** 140M+ property records, owner details, active sale & rental listings, AVM estimates, market data. The RentCast API provides access to 140 million property records, owner details, home value and rent estimates, comparable properties, active listings, as well as aggregate real estate market data.
- **Listings endpoint:** the “/listings” endpoints allow you to search for and retrieve active and inactive sale and rental listings in all 50 US states.
- **Septic filter:** the listings endpoint exposes a `features` object with structured fields. Confirm via `/v1/listings/sale?zipCode=92024&limit=1` that `sewer` or `sewage` shows up — listings have a `features` block with attributes like architecture, foundation, heating, cooling, **sewer**, water source. If `sewer` isn’t present for SoCal listings (data quality varies), you fall back to keyword scanning the description, which the spec already handles.
- **Owner data:** the Property Records endpoint retrieves property attributes, features, property tax data, and property owner information for residential and commercial properties. Two-call enrichment: get listings, then look up owner per address.
- **ToS / licensing:** the most beginner-friendly in this whole list. Their API Terms of Use provide sufficient flexibility to support a wide range of use cases and applications. They allow you to use the data for commercial purposes, creating derivative works, combining it with other data sources, storing it on your systems, and displaying it to end-users of your applications. You can start using the API with no contracts or commitments through the self-serve API dashboard.
- **Pricing:** free tier exists for development; paid tiers scale per request. Self-serve, no sales calls, no contracts. Rate limit of 20 requests per second per API key.
- **Why it wins for you:** API-first design, no contract or sales call, permissive ToS for lead gen, free tier means you can prototype for $0, and the data model is exactly what the spec assumes.

### PropertyRadar — strong CA backup if RentCast data is thin

- **What it has:** the deepest California property data set, partly because the company started as ForeclosureRadar in California. Strong owner records, court data (probate, divorce, eviction), foreclosure timing.
- **Septic filter:** PropertyRadar’s UI has explicit filter criteria for sewer type including septic / OWTS — they treat it as a first-class searchable attribute, not just a description keyword. That’s unusual and valuable for your use case. Worth a demo just to see this.
- **API:** PropertyRadar offers an API, but it’s positioned as add-on/enterprise rather than self-serve. Pricing is via sales contact.
- **Pricing:** the platform itself runs roughly $100–$400/month for the SaaS tiers, depending on volume; API pricing is contract-based and you’ll have to ask.
- **Why it’s #2:** if RentCast’s listing data turns out to be missing the sewer field in SoCal listings often enough, PropertyRadar’s native OWTS filter solves the problem cleanly. The cost is real money and a sales conversation.

### ATTOM Data — the enterprise option

- **What it has:** the most comprehensive U.S. property dataset. 155 million residential and commercial properties; detailed property information such as tax assessments, sales history, zoning data, and property characteristics, plus neighborhood data like crime rates, school ratings, and environmental hazards.
- **Septic filter:** structured property attributes include sewer type. Strong field coverage.
- **API:** real, well-documented, RESO-aligned.
- **Pricing:** enterprise. Subscription-based pricing structure with different plans that include a fixed number of monthly “report credits” — prices range from $112.50/month for 60 reports a year to $360/month for 400 reports a year. Contact the company directly for enterprise licenses with API, Bulk Files, Match & Append, and Multi-seat Plans.
- **Why not #1:** overkill for a weekly per-ZIP scan, more expensive than RentCast, and requires more sales-side handholding. Right answer if you scale to multiple states or want owner records as your primary product.

### BatchData — owner-records specialist

- **What it has:** strong skip-tracing, owner contact info, mailing addresses. Lighter on the live-listings side, heavier on the “who owns this and how do I reach them” side.
- **Septic filter:** not really their angle. You’d use them as an *enrichment* layer, not as your listings source.
- **When to add them:** if RentCast’s homeowner names turn out to be thin in SoCal and you need better owner enrichment — wire BatchData into the `enrichment/owner.py` module from the spec.

### PropStream — popular but no public API for this

- Heavy in real estate investor circles, big web app with great filters, but the API surface for programmatic weekly pulls isn’t where they put their effort. You’d end up doing manual exports. Skip for an automated agent.

-----

## What to avoid

### Anything that scrapes Zillow, Realtor.com, Redfin, or Trulia

Several services market “real estate APIs” that are actually scraping public listing sites. Bright Data, ScrapingBee’s “MLS scraper,” ApiScrapy, and others fall in this bucket. Three problems:

1. **Site ToS.** Those sites explicitly prohibit scraping. Even if you’re not the one running the scraper, you’re a downstream consumer of ToS-violating data and that’s a real legal exposure for a business.
1. **Reliability.** Scrapers break whenever the source site changes layout. You don’t want your Monday morning email to silently stop arriving.
1. **Data freshness and completeness.** Scraped listings often miss the structured fields (like the sewer field) that you specifically need.

### Zillow Public API for listings

Functionally deprecated for new developers wanting bulk listing access. Zillow provides access to listing-level and rental market data through approved channels and partnerships, best suited for consumer-facing platforms rather than deep historical or ownership research. Translation: not for your use case.

-----

## Specific test before you commit to any provider

Don’t pay anyone until you’ve run this test:

1. **Sign up for the free or trial tier** (RentCast: free; PropertyRadar: 3-day trial; ATTOM: contact sales for sample).
1. **Pull 20 known recent listings** in your target ZIPs that you can verify on Zillow/Realtor manually.
1. **Check three things:**
- Does the response include a structured `sewer` / `sewage` field? How often is it populated vs. null?
- When septic is mentioned in the description but not in structured fields, does the description text actually come through in the API response?
- For matched listings, does owner-of-record show up?
1. **Score it:** match rate, null rate, latency. The spec’s filter handles both structured + description paths, so even partial structured coverage is fine — but you want to know what you’re working with.

This is the same advice the industry gives: before committing, run match-rate and null-rate tests on real addresses, measure latency, and model cost at 10× scale.

-----

## Recommended path

|Phase                      |Provider                                                                       |Purpose                                |Approximate cost                                  |
|---------------------------|-------------------------------------------------------------------------------|---------------------------------------|--------------------------------------------------|
|1. Prototype               |RentCast free tier                                                             |Build & test pipeline against real data|$0                                                |
|2. Pilot (3 ZIPs, ~6 weeks)|RentCast paid (lowest tier)                                                    |Validate match quality + email workflow|~$20–60/mo, exact figure on rentcast.io/api       |
|3. Production (10+ ZIPs)   |RentCast continued, **OR** add PropertyRadar if structured septic field is thin|Daily reliability, expanded coverage   |RentCast scaled tier OR PropertyRadar $100–$300/mo|
|4. Scale (if applicable)   |Add ATTOM or migrate to it                                                     |Multi-state, higher volume             |Enterprise contract                               |

-----

## How this plugs into the agent

The spec already designed for this. The `providers/base.py` interface means you swap in `providers/rentcast.py` once you have a key and the pipeline doesn’t change. If a year from now you migrate to ATTOM, you write `providers/attom.py` and change one config line. **You’re not locked in** to whoever you pick first — that was a deliberate design choice in the spec.

The kickoff prompt you already have tells Claude Code to build the mock provider first. After that’s working and tested, your next Claude Code session is:

> Read SPEC.md and the existing `providers/mock.py`. Implement `providers/rentcast.py` against the RentCast API (<https://developers.rentcast.io>). It must satisfy the same `ListingProvider` interface. Map the RentCast response fields to our `Listing` model. Skip listings missing required fields with a warning. Add the API key as `LISTINGS_API_KEY` per the spec’s secrets section. Don’t change anything else — main.py shouldn’t need edits. Stop when done and show me the new file + any test data you ran it against.

-----

## One non-data note

Whatever provider you pick, write **good outreach copy** before you start contacting homeowners or agents at scale. CA has specific rules about real estate solicitation (the CCPA applies to consumer data; the TCPA applies to phone calls/SMS; CAN-SPAM applies to email). For a personal Monday-morning lead list you review yourself, you’re fine. For automated outreach, talk to a CA real estate attorney first — that’s outside what this agent should do without you reviewing each contact.