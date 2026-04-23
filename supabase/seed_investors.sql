-- Seed all 50 investor targets
-- liam_leads = TRUE for Tier 1 (hospitality VCs), Tier 5 (European), Tier 6 (Angels)

INSERT INTO investor_targets (firm_name, investor_type, tier, liam_leads, why_fit, pipeline_stage) VALUES

-- TIER 1 — Hospitality & Travel Tech VCs (liam_leads = TRUE)
('Derive Ventures', 'seed_vc', 1, TRUE,
 'Hospitality-focused VC with deep operator network. Liam opens with operator credibility and references their portfolio. Ideal first approach.',
 'identified'),

('Thayer Ventures', 'seed_vc', 1, TRUE,
 'Travel and hospitality technology specialist. Strong fit given First Wave AI''s pilot proof in hotel operations.',
 'identified'),

('Branded Hospitality Ventures', 'seed_vc', 1, TRUE,
 'Operator-backed hospitality VC. Credibility match: Liam''s A&O/Selina background speaks directly to their investment thesis.',
 'identified'),

('Journey Ventures', 'seed_vc', 1, TRUE,
 'Travel tech and hospitality investor. First Wave AI''s unanswered-call proof point aligns with their guest experience focus.',
 'identified'),

('Jaws Ventures', 'seed_vc', 1, TRUE,
 'Hospitality and travel VC. Relevant portfolio in CX and operations tech for hotel groups.',
 'identified'),

('JetBlue Technology Ventures', 'cvc', 1, TRUE,
 'Travel-sector CVC investing in operational AI and CX. Guest experience angle is directly relevant.',
 'identified'),

('MairDuMont Ventures', 'seed_vc', 1, TRUE,
 'European travel and hospitality investor. Strong relevance for DACH market expansion strategy.',
 'identified'),

('Fifth Wall', 'seed_vc', 1, TRUE,
 'Real estate and hospitality tech investor with significant hotel operator relationships in their network.',
 'identified'),

('Howzat Partners', 'seed_vc', 1, TRUE,
 'Hospitality-focused fund with portfolio companies in hotel tech. Peer outreach from Liam makes sense.',
 'identified'),

('Big Rock Ventures', 'seed_vc', 1, TRUE,
 'Travel and hospitality VC. Operator credibility story resonates with their typical investment framework.',
 'identified'),

-- TIER 2 — Vertical AI / B2B SaaS Pre-Seed (liam_leads = FALSE)
('Outlander VC', 'pre_seed', 2, FALSE,
 'Pre-seed B2B SaaS investor. Lead with market size and defensible hybrid moat vs. pure AI commoditisation.',
 'identified'),

('Ascend VC', 'pre_seed', 2, FALSE,
 'Vertical SaaS and AI pre-seed. Highlight pilot traction and unit economics vs. traditional outsourcing.',
 'identified'),

('Pear VC', 'pre_seed', 2, FALSE,
 'Pre-seed to seed B2B SaaS. Strong track record in vertical AI. Traction-led narrative fits their criteria.',
 'identified'),

('Amplify Partners', 'pre_seed', 2, FALSE,
 'Developer tools and infrastructure investor expanding into vertical AI. Technical differentiation angle.',
 'identified'),

('Audacious VC', 'pre_seed', 2, FALSE,
 'Pre-seed vertical AI investor. $750K ask with clear ARR path and pilot proof is within their sweet spot.',
 'identified'),

('2048 Ventures', 'pre_seed', 2, FALSE,
 'Pre-seed B2B SaaS. They back contrarian theses — human+AI hybrid is the contrarian bet against pure automation.',
 'identified'),

('Forum Ventures', 'pre_seed', 2, FALSE,
 'B2B SaaS accelerator and pre-seed fund. Apply through intake form while pursuing warm intro simultaneously.',
 'identified'),

('Precursor Ventures', 'pre_seed', 2, FALSE,
 'Invests at the earliest stage in B2B SaaS. Founder-first philosophy; Philip''s AWS background is compelling.',
 'identified'),

('Founder Collective', 'pre_seed', 2, FALSE,
 'Pre-seed B2B. Portfolio includes CX and vertical SaaS. Operator credentials plus pilot traction match their bar.',
 'identified'),

('Beta Boom', 'pre_seed', 2, FALSE,
 'Diversity-focused pre-seed fund investing in underserved markets. Strong mission fit with accessible hospitality AI.',
 'identified'),

-- TIER 3 — Accelerators (liam_leads = FALSE — Philip leads)
('Y Combinator', 'accelerator', 3, FALSE,
 'Top global accelerator. Philip leads the application. Liam referenced for domain credibility and pilot proof.',
 'identified'),

('Techstars', 'accelerator', 3, FALSE,
 'Global accelerator with hospitality and travel verticals. Strong corporate sponsor network in hotel sector.',
 'identified'),

('500 Global', 'accelerator', 3, FALSE,
 'Global accelerator with strong EMEA presence. Relevant for European market expansion narrative.',
 'identified'),

('a16z START', 'accelerator', 3, FALSE,
 'Andreessen Horowitz accelerator program for early AI companies. High bar, high reward for category definition.',
 'identified'),

('NFX', 'accelerator', 3, FALSE,
 'Network-effects focused fund and accelerator. Guest experience platform has genuine network effects at scale.',
 'identified'),

-- TIER 4 — Enterprise AI / CX (liam_leads = FALSE)
('First Round Capital', 'seed_vc', 4, FALSE,
 'Tier 1 seed fund with strong B2B SaaS portfolio. Higher bar but strong signal if they engage.',
 'identified'),

('SaaStr Fund', 'seed_vc', 4, FALSE,
 'Jason Lemkin''s B2B SaaS seed fund. Revenue-focused; $80K ARR with clear path to $500K is the hook.',
 'identified'),

('Salesforce Ventures', 'cvc', 4, FALSE,
 'CRM and CX-adjacent CVC. First Wave AI''s post-call workflow automation integrates naturally with CRM stack.',
 'identified'),

('HubSpot Ventures', 'cvc', 4, FALSE,
 'Inbound marketing and CX CVC. Guest communication and lead capture angle is directly relevant.',
 'identified'),

('FirstMark Capital', 'seed_vc', 4, FALSE,
 'NYC-based seed to Series A with SaaS focus. AI-native CX is a core thesis area.',
 'identified'),

('Glasswing Ventures', 'seed_vc', 4, FALSE,
 'Enterprise AI specialist. Technical differentiation (AWS infrastructure + human oversight) fits their thesis.',
 'identified'),

('Lerer Hippeau', 'seed_vc', 4, FALSE,
 'NYC seed fund with consumer and enterprise SaaS. Hospitality at intersection of consumer and B2B.',
 'identified'),

('White Star Capital', 'seed_vc', 4, FALSE,
 'Transatlantic fund with European presence. Strong fit for Berlin-based operation targeting EU hotel groups.',
 'identified'),

('HOF Capital', 'seed_vc', 4, FALSE,
 'NYC seed fund. B2B AI and SaaS focus. Pilot economics ($2,496/month savings) are a compelling headline.',
 'identified'),

('Trinity Ventures', 'seed_vc', 4, FALSE,
 'Enterprise SaaS seed fund. Operational AI with measurable ROI fits their investment criteria.',
 'identified'),

-- TIER 5 — European VCs (liam_leads = TRUE)
('Seedcamp', 'seed_vc', 5, TRUE,
 'Pan-European pre-seed and seed. Liam''s European operator network gives a credible warm intro path.',
 'identified'),

('Heartcore Capital', 'seed_vc', 5, TRUE,
 'Copenhagen-based consumer and B2B fund. Strong Nordics network aligns with Liam''s Priority 1 geographies.',
 'identified'),

('Playfair Capital', 'seed_vc', 5, TRUE,
 'London-based pre-seed. B2B SaaS thesis. UK hospitality market is Priority 1 for client pipeline too.',
 'identified'),

('Earlybird Ventures', 'seed_vc', 5, TRUE,
 'Pan-European early-stage VC with DACH strength. Berlin-based operations match Liam''s location advantage.',
 'identified'),

('Partech', 'seed_vc', 5, TRUE,
 'Franco-German VC with strong enterprise SaaS portfolio. European hospitality operator credibility is the angle.',
 'identified'),

('Icebreaker.vc', 'pre_seed', 5, TRUE,
 'Nordic pre-seed fund. Hospitality is a significant sector in the Nordics. Personal outreach from Liam.',
 'identified'),

('TheVentureCity', 'seed_vc', 5, TRUE,
 'European and LatAm early-stage fund. Globalisation of hospitality AI is a credible expansion story.',
 'identified'),

('Stride.VC', 'pre_seed', 5, TRUE,
 'London-based pre-seed. B2B SaaS and AI focus. UK hotel group pipeline makes this immediately relevant.',
 'identified'),

-- TIER 6 — Angels (liam_leads = TRUE)
('Ryan Hoover', 'angel', 6, TRUE,
 'Product Hunt founder and angel investor. Consumer-facing AI and hospitality experience are adjacent interests.',
 'identified'),

('Gokul Rajaram', 'angel', 6, TRUE,
 'Ex-Google, Facebook, DoorDash. Operator angel with deep knowledge of unit economics and scaling CX.',
 'identified'),

('AngelList Hospitality Syndicates', 'angel', 6, TRUE,
 'Curated syndicates of hospitality-focused angels. Direct relevance; collective check size can be meaningful.',
 'identified'),

('Alumni Ventures', 'angel', 6, TRUE,
 'Alumni-network fund investing in early-stage companies. Broad network for warm intro sourcing.',
 'identified'),

('Golden Seeds', 'angel', 6, TRUE,
 'Women-led angel network investing in diverse founding teams. Respectful one-liner outreach from Liam.',
 'identified'),

('Regional Angel Networks', 'angel', 6, TRUE,
 'DACH and UK regional angel groups with hospitality operator members. Liam''s network has natural overlap.',
 'identified'),

('Launch Capital', 'angel', 6, TRUE,
 'Jason Calacanis''s early-stage fund. High volume dealflow; concise one-liner and pilot traction is the pitch.',
 'identified');
