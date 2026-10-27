"""Curated grounding data for Regulation (EU) 2024/1689 (the EU AI Act).

The classifier must select citations from this table rather than generating
them from the model's own memory — LLMs reliably hallucinate plausible-looking
article numbers, and a fabricated citation is the single most damaging failure
mode for a "know your legal risk" tool. This file is the source of truth it's
constrained to; keep it accurate to the official text (OJ L, 2024/1689,
12.7.2024), not to how the Act is often summarized in blog posts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalProvision:
    id: str
    title: str
    summary: str


@dataclass(frozen=True)
class RiskTier:
    id: str
    label: str
    consequence: str
    provisions: tuple[LegalProvision, ...]
    example_use_cases: tuple[str, ...]
    signal_keywords: tuple[str, ...]


PROHIBITED = RiskTier(
    id="prohibited",
    label="Prohibited",
    consequence=(
        "Banned outright in the EU. No conformity assessment or disclosure can make this "
        "legal — the practice itself is forbidden. Fines up to EUR 35,000,000 or 7% of "
        "global annual turnover, whichever is higher."
    ),
    provisions=(
        LegalProvision(
            id="Art. 5(1)(a)",
            title="Subliminal or manipulative techniques",
            summary=(
                "Deploying subliminal techniques beyond a person's consciousness, or purposefully "
                "manipulative/deceptive techniques, that materially distort behaviour by impairing "
                "informed decision-making and cause significant harm."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(b)",
            title="Exploiting vulnerabilities",
            summary=(
                "Exploiting vulnerabilities due to age, disability, or a specific social or "
                "economic situation, in a way that materially distorts behaviour and causes "
                "significant harm."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(c)",
            title="Social scoring",
            summary=(
                "Evaluating or classifying people over time based on social behaviour or known/"
                "predicted personal traits, leading to detrimental treatment unrelated to the "
                "context in which the data was gathered, or treatment disproportionate to the "
                "social behaviour itself."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(d)",
            title="Individual criminal-offence risk prediction",
            summary=(
                "Assessing or predicting the risk of a natural person committing a criminal "
                "offence based solely on profiling or personality-trait assessment (not "
                "applicable to tools that merely support a human assessment already based on "
                "objective, verifiable facts directly linked to criminal activity)."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(e)",
            title="Untargeted facial-recognition scraping",
            summary=(
                "Untargeted scraping of facial images from the internet or CCTV footage to "
                "build or expand a facial recognition database."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(f)",
            title="Workplace/education emotion recognition",
            summary=(
                "Inferring the emotions of a natural person in the workplace or in education "
                "institutions, except for narrow medical or safety purposes."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(g)",
            title="Biometric categorisation of sensitive attributes",
            summary=(
                "Using biometric data to infer or categorise someone's race, political opinions, "
                "trade union membership, religious or philosophical beliefs, sex life, or sexual "
                "orientation (narrow exceptions exist for labelling lawfully acquired datasets and "
                "for law enforcement)."
            ),
        ),
        LegalProvision(
            id="Art. 5(1)(h)",
            title="Real-time remote biometric identification by law enforcement",
            summary=(
                "Real-time remote biometric identification in publicly accessible spaces for law "
                "enforcement purposes, outside a narrow set of authorised exceptions (e.g. "
                "searching for a specific victim, preventing an imminent threat to life, locating "
                "a suspect in a serious crime)."
            ),
        ),
    ),
    example_use_cases=(
        "Manipulative dark-pattern chatbots designed to override user judgement",
        "A 'trustworthiness' or social-credit score used to gate unrelated services",
        "Predictive-policing tools that flag individuals as future offenders from profile data alone",
        "Facial-recognition database built by scraping social media photos",
        "Emotion-detection software marketed for employee monitoring or student proctoring",
        "Live public CCTV face-matching for general police search",
    ),
    signal_keywords=(
        "social score", "social credit", "predictive policing", "emotion detection",
        "emotion recognition", "employee monitoring", "facial recognition database",
        "real-time biometric", "manipulate behavior", "subliminal",
    ),
)

HIGH_RISK = RiskTier(
    id="high_risk",
    label="High Risk",
    consequence=(
        "Legal to place on the EU market, but only after conformity assessment, registration "
        "in the EU database, and ongoing compliance with a risk-management system, data "
        "governance, technical documentation, human oversight, accuracy/robustness/cybersecurity "
        "requirements, and post-market monitoring (Articles 8-17, 26, 72)."
    ),
    provisions=(
        LegalProvision(
            id="Art. 6(1) + Annex I",
            title="Safety component of a regulated product",
            summary=(
                "The AI system is a safety component of a product (or is itself a product) already "
                "covered by EU product-safety harmonisation legislation (e.g. machinery, toys, "
                "medical devices, lifts) and is required to undergo third-party conformity assessment."
            ),
        ),
        LegalProvision(
            id="Annex III(1)",
            title="Biometrics",
            summary=(
                "Remote biometric identification, biometric categorisation of sensitive attributes, "
                "or emotion recognition systems, insofar as not already prohibited under Article 5."
            ),
        ),
        LegalProvision(
            id="Annex III(2)",
            title="Critical infrastructure",
            summary=(
                "Safety components in the management or operation of critical digital infrastructure, "
                "road traffic, or the supply of water, gas, heating, or electricity."
            ),
        ),
        LegalProvision(
            id="Annex III(3)",
            title="Education and vocational training",
            summary=(
                "Determining access or admission to education, evaluating learning outcomes, "
                "assessing the appropriate level of education for a person, or monitoring/detecting "
                "prohibited behaviour by students during tests."
            ),
        ),
        LegalProvision(
            id="Annex III(4)",
            title="Employment and worker management",
            summary=(
                "Recruitment or selection of candidates, targeted job-ad placement, or decisions on "
                "promotion, termination, task allocation, or performance monitoring/evaluation of "
                "workers."
            ),
        ),
        LegalProvision(
            id="Annex III(5)",
            title="Access to essential services",
            summary=(
                "Eligibility evaluation for public assistance benefits, creditworthiness/credit "
                "scoring, risk assessment or pricing for life and health insurance, or emergency "
                "call dispatch and triage."
            ),
        ),
        LegalProvision(
            id="Annex III(6)",
            title="Law enforcement",
            summary=(
                "Individual risk assessment, polygraph-type tools, evaluating evidence reliability, "
                "profiling, or predicting (re)offending in a law-enforcement context."
            ),
        ),
        LegalProvision(
            id="Annex III(7)",
            title="Migration, asylum, and border control",
            summary=(
                "Polygraph-type tools, risk assessment, examination of asylum/visa applications, or "
                "identification of persons in a migration, asylum, or border-control context."
            ),
        ),
        LegalProvision(
            id="Annex III(8)",
            title="Administration of justice and democratic processes",
            summary=(
                "Assisting a judicial authority in researching and interpreting facts and applying "
                "the law, or systems intended to influence the outcome of an election/referendum or "
                "voting behaviour."
            ),
        ),
    ),
    example_use_cases=(
        "AI-powered CV screening or candidate ranking tool sold to employers",
        "Credit-scoring or loan-approval model",
        "Proctoring software that flags students for cheating during exams",
        "Insurance pricing engine driven by an ML risk model",
        "AI diagnostic support embedded in a certified medical device",
    ),
    signal_keywords=(
        "cv screening", "resume screening", "candidate ranking", "credit scoring",
        "loan approval", "insurance underwriting", "exam proctoring", "hiring automation",
        "worker performance monitoring", "medical device", "critical infrastructure",
    ),
)

LIMITED_RISK = RiskTier(
    id="limited_risk",
    label="Limited Risk",
    consequence=(
        "Legal with no conformity assessment required, but specific transparency obligations "
        "apply — the AI's presence or the artificial nature of its output must be disclosed to "
        "the people it interacts with."
    ),
    provisions=(
        LegalProvision(
            id="Art. 50(1)",
            title="Disclose AI interaction",
            summary=(
                "Providers of AI systems intended to interact directly with natural persons (e.g. "
                "chatbots) must design them so people are informed they are interacting with AI, "
                "unless this is obvious from the context."
            ),
        ),
        LegalProvision(
            id="Art. 50(2)",
            title="Mark synthetic content",
            summary=(
                "Providers of AI systems that generate synthetic audio, image, video, or text "
                "content must mark outputs in a machine-readable format as artificially generated "
                "or manipulated."
            ),
        ),
        LegalProvision(
            id="Art. 50(3)",
            title="Disclose emotion recognition / biometric categorisation",
            summary=(
                "Deployers of an emotion-recognition or biometric-categorisation system must inform "
                "the natural persons exposed to it."
            ),
        ),
        LegalProvision(
            id="Art. 50(4)",
            title="Label deepfakes and AI-generated public-interest text",
            summary=(
                "Deployers of a system generating deep-fake image/audio/video must disclose the "
                "content is artificially generated or manipulated; deployers publishing AI-generated "
                "text on matters of public interest must disclose this unless the text underwent "
                "human review and editorial responsibility."
            ),
        ),
    ),
    example_use_cases=(
        "Customer-support chatbot on a company website",
        "AI voice assistant / IVR system",
        "Image or video generation tool (e.g. marketing content generator)",
        "AI writing assistant whose output is published directly without human editorial review",
    ),
    signal_keywords=(
        "chatbot", "virtual assistant", "voice assistant", "content generator",
        "image generation", "video generation", "text generation", "deepfake",
        "synthetic media", "ai-generated",
    ),
)

MINIMAL_RISK = RiskTier(
    id="minimal_risk",
    label="Minimal Risk",
    consequence=(
        "No obligations under the AI Act itself. Providers are only encouraged, on a voluntary "
        "basis, to apply the codes of conduct referenced in Article 95."
    ),
    provisions=(
        LegalProvision(
            id="Art. 95",
            title="Voluntary codes of conduct",
            summary=(
                "For AI systems that don't fall into the prohibited, high-risk, or limited-risk "
                "tiers, the Act imposes no specific legal obligations; providers are only "
                "encouraged to voluntarily apply codes of conduct."
            ),
        ),
    ),
    example_use_cases=(
        "Spam filters",
        "AI-enabled video game NPCs or difficulty tuning",
        "Inventory or supply-chain optimisation",
        "Product recommendation engines with no significant-decision impact on a person's rights or opportunities",
    ),
    signal_keywords=(
        "spam filter", "recommendation engine", "inventory management",
        "video game ai", "internal tooling", "optimization",
    ),
)

RISK_TIERS: tuple[RiskTier, ...] = (PROHIBITED, HIGH_RISK, LIMITED_RISK, MINIMAL_RISK)
RISK_TIERS_BY_ID: dict[str, RiskTier] = {tier.id: tier for tier in RISK_TIERS}

VALID_CITATION_IDS: frozenset[str] = frozenset(
    provision.id for tier in RISK_TIERS for provision in tier.provisions
)

GENERAL_PURPOSE_AI_NOTE = (
    "Note: general-purpose AI (GPAI) models — foundation models such as large language models "
    "offered on their own, not tied to one of the use cases above — carry a separate obligation "
    "track under Chapter V (Articles 51-56): transparency/documentation duties for all GPAI "
    "providers, plus extra systemic-risk obligations for models trained above the compute "
    "threshold in Article 51(2). A product built on top of a GPAI model should still be classified "
    "into one of the four tiers above based on what it *does*; flag the GPAI angle separately if "
    "the site is itself offering a foundation model."
)


def is_valid_citation(citation_id: str) -> bool:
    return citation_id in VALID_CITATION_IDS


def format_reference_for_prompt() -> str:
    """Render the full reference table as plain text to embed in the classifier's system prompt."""
    lines: list[str] = []
    for tier in RISK_TIERS:
        lines.append(f"## {tier.label} ({tier.id})")
        lines.append(f"Consequence: {tier.consequence}")
        lines.append("Provisions:")
        for provision in tier.provisions:
            lines.append(f"  - [{provision.id}] {provision.title}: {provision.summary}")
        lines.append("Example use cases: " + "; ".join(tier.example_use_cases))
        lines.append("")
    lines.append(GENERAL_PURPOSE_AI_NOTE)
    return "\n".join(lines)
