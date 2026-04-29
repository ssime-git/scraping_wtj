import pytest
from unittest.mock import AsyncMock
from wttj_models.job import JobDetail, JobListing
from wttj_scraper.detail import parse_summary_metadata, scrape_detail


@pytest.fixture
def base_listing():
    return JobListing(
        title="Dev Python",
        url="https://www.welcometothejungle.com/fr/companies/acme/jobs/dev-python",
        snippet="Acme · Paris",
    )


@pytest.fixture
def mock_detail_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "Dev Python | Acme | Welcome to the Jungle",
            "text_preview": "Nous recherchons un développeur Python confirmé...",
            "company_name": "Theraclion",
            "contract_type": "Alternance",
            "remote_level": "Télétravail occasionnel",
            "city": "Malakoff",
            "company_sectors": ["MedTech", "AI"],
            "languages_required": ["French", "English"],
            "description_raw": "Description section",
            "missions_raw": "Mission section",
            "profile_raw": "Profile section",
        }
    )
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_context_detail(mock_detail_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_detail_page)
    return context


@pytest.mark.asyncio
async def test_scrape_detail_returns_job_detail(mock_context_detail, base_listing):
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.url == base_listing.url
    assert result.title == base_listing.title
    assert result.page_title == "Dev Python | Acme | Welcome to the Jungle"
    assert "développeur" in result.text_preview
    assert result.company_name == "Theraclion"
    assert result.contract_type == "Alternance"
    assert result.remote_level == "Télétravail occasionnel"
    assert result.city == "Malakoff"
    assert result.languages_required == ["French", "English"]
    assert result.error is None


@pytest.mark.asyncio
async def test_scrape_detail_stores_error_on_timeout(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.goto = AsyncMock(side_effect=TimeoutError("page timeout"))
    result = await scrape_detail(mock_context_detail, base_listing)

    assert isinstance(result, JobDetail)
    assert result.error is not None
    assert "timeout" in result.error.lower()
    assert result.page_title is None


@pytest.mark.asyncio
async def test_scrape_detail_closes_page(mock_context_detail, mock_detail_page, base_listing):
    await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_scrape_detail_closes_page_on_error(mock_context_detail, mock_detail_page, base_listing):
    mock_detail_page.evaluate = AsyncMock(side_effect=RuntimeError("js error"))
    result = await scrape_detail(mock_context_detail, base_listing)
    mock_detail_page.close.assert_awaited_once()
    assert result.error is not None


def test_parse_summary_metadata_extracts_atomic_fields():
    summary = (
        "Groupe SII Alternance Assistant communication H/F Siege Alternance Paris "
        "Teletravail non autorise Salaire : Non specifie Education : Bac +5 / Master "
        "avant-hier"
    )
    metadata = parse_summary_metadata(summary)
    assert metadata["contract_type"] == "Alternance"
    assert metadata["city"] == "Paris"
    assert metadata["remote_level"] == "Teletravail non autorise"
    assert metadata["date_posted_label"] == "avant-hier"


def test_parse_summary_metadata_extracts_wttj_header_facts():
    summary = """
    Chargé(e) de communication RSE/Événementiel H/F
    Résumé du poste
    CDI
    Paris
    Télétravail fréquent
    Salaire :
    Non spécifié
    Début :
    23 avril 2026
    Expérience :
    > 5 ans
    Éducation :
    Bac +5 / Master
    Compétences & expertises
    Gestion des entretiens
    Efficacité opérationnelle
    """

    metadata = parse_summary_metadata(summary)

    assert metadata["contract_type"] == "CDI"
    assert metadata["city"] == "Paris"
    assert metadata["remote_level"] == "Télétravail fréquent"
    assert metadata["salary_label"] == "Non spécifié"
    assert metadata["salary_visible"] is False
    assert metadata["start_date"] == "23 avril 2026"
    assert metadata["experience_label"] == "> 5 ans"
    assert metadata["education_level"] == "Bac +5"
    assert metadata["skills_hard"] == ["Gestion des entretiens", "Efficacité opérationnelle"]


def test_parse_summary_metadata_rejects_faq_question_as_remote_level():
    summary = """
    Alternance - Chargée ou Chargé de Communication et Marketing Digital- Master F/H
    Alternance
    Marseille
    Le télétravail est-il possible pour ce poste ?
    Salaire :
    Non spécifié
    """

    metadata = parse_summary_metadata(summary)

    assert metadata["contract_type"] == "Alternance"
    assert metadata["city"] == "Marseille"
    assert metadata["remote_level"] is None
    assert metadata["salary_label"] == "Non spécifié"


def test_parse_summary_metadata_supports_observed_contracts_and_cities():
    metadata = parse_summary_metadata(
        "Chargé de mission Abeille Assurances Autres Bois-Colombes Télétravail non autorisé"
    )

    assert metadata["contract_type"] == "Autres"
    assert metadata["city"] == "Bois-Colombes"
    assert metadata["remote_level"] == "Télétravail non autorisé"

    assert parse_summary_metadata("Alternance Levallois-Perret Télétravail fréquent")["city"] == "Levallois-Perret"
    assert parse_summary_metadata("Alternance Fontenay-sous-Bois Télétravail fréquent")["city"] == "Fontenay-sous-Bois"
    assert parse_summary_metadata("Alternance Puteaux Télétravail fréquent")["city"] == "Puteaux"
    assert parse_summary_metadata("CDI Grenoble Télétravail occasionnel")["city"] == "Grenoble"


def test_parse_summary_metadata_filters_skill_noise():
    summary = """
    CDI
    Boulogne-Billancourt
    Télétravail non autorisé
    Compétences & expertises
    Communication
    Communication
    PostulerSauvegarderavant-hierPartagerCopier le lien
    Postuler
    Sauvegarder
    """

    metadata = parse_summary_metadata(summary)

    assert metadata["skills_hard"] == ["Communication"]


def test_parse_summary_metadata_filters_observed_skill_tail_noise():
    summary = """
    CDI
    Paris
    Télétravail fréquent
    Compétences & expertises
    Gestion des entretiensEfficacité opérationnelle
    Gestion des entretiens
    Efficacité opérationnelle
    hier
    La Banque Postale
    Cette offre vous tente ?
    """

    metadata = parse_summary_metadata(summary)

    assert metadata["skills_hard"] == ["Gestion des entretiens", "Efficacité opérationnelle"]


@pytest.mark.asyncio
async def test_scrape_detail_uses_detail_facts_for_wttj_header_metadata(base_listing):
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "Chargé(e) de communication RSE/Événementiel H/F",
            "text_preview": "",
            "company_name": "La Banque Postale",
            "contract_type": "Entreprise CDI Paris Télétravail fréquent Salaire : Non spécifié Postuler Sauvegarder",
            "city": "Entreprise CDI Paris Télétravail fréquent Salaire : Non spécifié Postuler Sauvegarder",
            "remote_level": "Entreprise CDI Paris Télétravail fréquent Salaire : Non spécifié Postuler Sauvegarder",
            "company_sectors": [],
            "facts_raw": [
                "Résumé du poste",
                "CDI",
                "Paris",
                "Télétravail fréquent",
                "Salaire :",
                "Non spécifié",
                "Début :",
                "23 avril 2026",
                "Expérience :",
                "> 5 ans",
                "Éducation :",
                "Bac +5 / Master",
                "Compétences & expertises",
                "Gestion des entretiens",
                "Efficacité opérationnelle",
            ],
        }
    )
    page.close = AsyncMock()
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    listing = base_listing.model_copy(update={"snippet": None})

    result = await scrape_detail(context, listing)

    assert result.contract_type == "CDI"
    assert result.city == "Paris"
    assert result.remote_level == "Télétravail fréquent"
    assert result.salary_label == "Non spécifié"
    assert result.salary_visible is False
    assert result.start_date == "23 avril 2026"
    assert result.experience_label == "> 5 ans"
    assert result.education_level == "Bac +5"
    assert result.skills_hard == ["Gestion des entretiens", "Efficacité opérationnelle"]


@pytest.mark.asyncio
async def test_scrape_detail_clears_noisy_remote_when_no_clean_value(base_listing):
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "Alternance communication",
            "text_preview": "",
            "company_name": "EDF",
            "contract_type": "Alternance",
            "city": "Marseille",
            "remote_level": '{ "@context": "https://schema.org", "@type": "FAQPage", "name": "Le télétravail est-il possible ?" }',
            "company_sectors": [],
            "facts_raw": ["Alternance", "Marseille", "Salaire :", "Non spécifié"],
        }
    )
    page.close = AsyncMock()
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    listing = base_listing.model_copy(
        update={
            "snippet": "Alternance communication EDF Alternance Marseille avant-hier",
        }
    )

    result = await scrape_detail(context, listing)

    assert result.contract_type == "Alternance"
    assert result.city == "Marseille"
    assert result.remote_level is None


@pytest.mark.asyncio
async def test_scrape_detail_listing_summary_overrides_wrong_detail_contract(base_listing):
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_timeout = AsyncMock()
    page.evaluate = AsyncMock(
        return_value={
            "page_title": "CDI - Assistant RH & Communication",
            "text_preview": "Un contenu de page qui mentionne aussi stage et stages.",
            "company_name": "Hermès",
            "contract_type": "Stage",
            "city": "Bourgoin-Jallieu",
            "remote_level": '{ "@context": "https://schema.org", "@type": "FAQPage", "name": "Le télétravail est-il possible ?" }',
            "company_sectors": [],
            "facts_raw": ["Stage", "Bourgoin-Jallieu"],
        }
    )
    page.close = AsyncMock()
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    listing = base_listing.model_copy(
        update={
            "snippet": (
                "CDI - Assistant RH & Communication Hermès CDI Bourgoin-Jallieu "
                "Salaire : Non spécifié il y a 16 heures"
            ),
        }
    )

    result = await scrape_detail(context, listing)

    assert result.contract_type == "CDI"
    assert result.city == "Bourgoin-Jallieu"
    assert result.remote_level is None
