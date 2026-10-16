# Funding

Grants and funding calls, from the EU and from Romania, that fit the project and the applicant.

## Before searching
The applicant comes from `research.config.md`: who applies (company, NGO, university, person), size, country and
region, what the project is and its stage. Eligibility depends on it; ask if it is missing.

## Find
1. **EU programmes managed by the Commission** (Horizon Europe, Digital Europe, Creative Europe, Erasmus+, CERV,
   LIFE, EU4Health, Single Market…):
   `python3 -I $S/funding.py "<what the project does>"`, with two or three wordings. Add `--programme HORIZON`
   (or DIGITAL, CREA, CERV…) to narrow, and `--cascade` for calls that EU-funded projects open to third parties
   (often smaller grants for SMEs and startups). Only calls with a deadline still ahead are listed.
2. **Romania** (no single database): search the official sites, then open each call's own page.
   - Ministry of Investments and European Projects, `mfe.gov.ro`: the national programmes of the cohesion funds and
     the Recovery and Resilience Plan (PNRR), with calls and applicant guides.
   - Regional development agencies (ADR, one per region): the regional programmes.
   - UEFISCDI, `uefiscdi.gov.ro`: national research and innovation competitions.
   - AFIR, `afir.ro`: rural and agricultural funding.
   - Other ministries or agencies when the topic is theirs (culture, education, environment).
   News sites, consultants and aggregators are leads only: confirm every call on the official page. Some
   official sites refuse automated requests: then use what web search shows of the page and ask the user to
   confirm the details on the site.
3. For each call that might fit, open its page and read: who can apply, the deadline, the grant per project and
   co-financing, the type of action, consortium requirements, what must be delivered.

## Report
A table, most suitable first: call and programme · deadline · grant per project · who can apply · fit (why it
matches, what does not) · link. Mark each one **eligible / check / not eligible** for this applicant, with the
reason. Say when the call's text was not read in full.

## Save
One file per call the user keeps, `research/funding/<call-id>.md` from `templates/funding.md`, with the date it
was checked. Dates and amounts change: check the official page again before relying on a saved file.
