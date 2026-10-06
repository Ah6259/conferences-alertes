# -*- coding: utf-8 -*-
"""
Classement des conférences : grands domaines, spécialités, pays et continents (français, anglais, arabe).

Une seule liste pour tout le site (pages, filtres, flux, Telegram) et pour le dépôt PRIVÉ des abonnés
(son tools/classement.py est une COPIE de DOMAINES et SPECIALITES : à garder identiques).
"""
import re
import unicodedata

# (adresse, français, anglais, arabe, couleur)
DOMAINES = [
    # Thèmes mis en avant en premier (demande d'Ahmed du 06/10/2026 : comptabilité, finance et SURTOUT finance islamique)
    ("comptabilite", "Comptabilité et audit", "Accounting & auditing", "المحاسبة والتدقيق", "#1F7A6D"),
    ("finance", "Finance", "Finance", "المالية", "#1E5AA8"),
    ("finance-islamique", "Finance islamique", "Islamic finance", "التمويل الإسلامي", "#0B7A3E"),
    ("informatique", "Informatique et IA", "Computer science & AI", "الإعلامية والذكاء الاصطناعي", "#3F51B5"),
    ("ingenierie", "Ingénierie et robotique", "Engineering & robotics", "الهندسة والروبوتيك", "#C26A1B"),
    ("physique", "Physique et astronomie", "Physics & astronomy", "الفيزياء وعلم الفلك", "#6B3FA0"),
    ("vie-sante", "Sciences de la vie et santé", "Life sciences & health", "علوم الحياة والصحة", "#C2412F"),
    ("mathematiques", "Mathématiques", "Mathematics", "الرياضيات", "#0E7C86"),
    ("shs", "Sciences humaines et sociales", "Humanities & social sciences", "العلوم الإنسانية والاجتماعية", "#8A6A2F"),
    ("economie", "Économie et gestion", "Economics & management", "الاقتصاد والتصرف", "#2E8B57"),
    ("terre-environnement", "Terre, environnement et chimie", "Earth, environment & chemistry", "الأرض والبيئة والكيمياء", "#3D7A3D"),
]
D_PAR_SLUG = {d[0]: d for d in DOMAINES}

# (adresse, domaine, français, anglais, arabe)
SPECIALITES = [
    ("compta-generale", "comptabilite", "Recherche comptable (général)", "Accounting research (general)", "البحث المحاسبي (عام)"),
    ("compta-financiere", "comptabilite", "Comptabilité financière et normes IFRS", "Financial accounting & IFRS", "المحاسبة المالية والمعايير الدولية"),
    ("compta-gestion", "comptabilite", "Comptabilité de gestion et contrôle", "Management accounting & control", "المحاسبة الإدارية والرقابة"),
    ("audit", "comptabilite", "Audit et assurance", "Auditing & assurance", "التدقيق والمراجعة"),
    ("fiscalite", "comptabilite", "Fiscalité", "Taxation", "الجباية والضرائب"),
    ("gouvernance", "comptabilite", "Gouvernance et reporting durable", "Governance & sustainability reporting", "الحوكمة والتقارير المستدامة"),
    ("finance-generale", "finance", "Finance (général)", "Finance (general)", "المالية (عام)"),
    ("finance-entreprise", "finance", "Finance d'entreprise", "Corporate finance", "مالية الشركات"),
    ("marches", "finance", "Marchés financiers et gestion d'actifs", "Financial markets & asset pricing", "الأسواق المالية وإدارة الأصول"),
    ("banque", "finance", "Banque et intermédiation financière", "Banking & financial intermediation", "البنوك والوساطة المالية"),
    ("fintech", "finance", "FinTech et IA en finance", "FinTech & AI in finance", "التكنولوجيا المالية والذكاء الاصطناعي في المالية"),
    ("economie-islamique", "finance-islamique", "Économie et finance islamiques (général)", "Islamic economics & finance (general)", "الاقتصاد والتمويل الإسلامي (عام)"),
    ("banque-islamique", "finance-islamique", "Banque islamique", "Islamic banking", "المصارف الإسلامية"),
    ("sukuk", "finance-islamique", "Sukuk et marchés de capitaux islamiques", "Sukuk & Islamic capital markets", "الصكوك وأسواق رأس المال الإسلامية"),
    ("takaful", "finance-islamique", "Takaful (assurance islamique)", "Takaful (Islamic insurance)", "التكافل (التأمين الإسلامي)"),
    ("zakat-waqf", "finance-islamique", "Zakat, waqf et finance sociale islamique", "Zakat, waqf & Islamic social finance", "الزكاة والوقف والمالية الاجتماعية الإسلامية"),
    ("aaoifi-charia", "finance-islamique", "Normes AAOIFI et gouvernance charia", "AAOIFI standards & Shariah governance", "معايير أيوفي والحوكمة الشرعية"),
    ("ia-apprentissage", "informatique", "IA et apprentissage automatique", "AI & machine learning", "الذكاء الاصطناعي والتعلم الآلي"),
    ("vision", "informatique", "Vision par ordinateur", "Computer vision", "الرؤية الحاسوبية"),
    ("langage", "informatique", "Traitement du langage et de la parole", "Language & speech processing", "معالجة اللغة والكلام"),
    ("donnees", "informatique", "Données, fouille et recherche d'information", "Data mining & information retrieval", "البيانات والتنقيب واسترجاع المعلومات"),
    ("reseaux", "informatique", "Réseaux et télécommunications", "Networks & communications", "الشبكات والاتصالات"),
    ("securite", "informatique", "Sécurité et cryptographie", "Security & cryptography", "الأمن والتشفير"),
    ("genie-logiciel", "informatique", "Génie logiciel", "Software engineering", "هندسة البرمجيات"),
    ("systemes", "informatique", "Systèmes, architecture et calcul parallèle", "Systems, architecture & HPC", "الأنظمة والمعمارية والحوسبة المتوازية"),
    ("theorie", "informatique", "Informatique théorique", "Theoretical computer science", "الإعلامية النظرية"),
    ("graphisme", "informatique", "Graphisme et multimédia", "Graphics & multimedia", "الرسوميات والوسائط المتعددة"),
    ("ihm", "informatique", "Interaction humain-machine", "Human-computer interaction", "التفاعل بين الإنسان والحاسوب"),
    ("info-interdisciplinaire", "informatique", "Informatique interdisciplinaire", "Interdisciplinary computing", "الإعلامية متعددة التخصصات"),
    ("robotique", "ingenierie", "Robotique et automatique", "Robotics & control", "الروبوتيك والتحكم الآلي"),
    ("signal", "ingenierie", "Traitement du signal", "Signal processing", "معالجة الإشارة"),
    ("particules", "physique", "Physique des particules", "Particle physics", "فيزياء الجسيمات"),
    ("astro", "physique", "Astrophysique, cosmologie et gravitation", "Astrophysics, cosmology & gravitation", "الفيزياء الفلكية وعلم الكون والجاذبية"),
    ("nucleaire", "physique", "Physique nucléaire", "Nuclear physics", "الفيزياء النووية"),
    ("quantique", "physique", "Physique quantique", "Quantum physics", "فيزياء الكم"),
    ("instrumentation", "physique", "Accélérateurs et instrumentation", "Accelerators & instrumentation", "المسرّعات والأجهزة العلمية"),
    ("physique-theorique", "physique", "Physique théorique et mathématique", "Theoretical & mathematical physics", "الفيزياء النظرية والرياضية"),
    ("matiere-condensee", "physique", "Matière condensée", "Condensed matter", "فيزياء المادة المكثفة"),
    ("calcul-physique", "physique", "Calcul et données en physique", "Computing & data in physics", "الحوسبة والبيانات في الفيزياء"),
    ("physique-generale", "physique", "Physique générale", "General physics", "الفيزياء العامة"),
    ("neurosciences", "vie-sante", "Neurosciences", "Neuroscience", "علوم الأعصاب"),
    ("bioinformatique", "vie-sante", "Bioinformatique et génomique", "Bioinformatics & genomics", "المعلوماتية الحيوية وعلم الجينوم"),
    ("medecine", "vie-sante", "Médecine et cardiologie", "Medicine & cardiology", "الطب وأمراض القلب"),
    ("biologie", "vie-sante", "Biologie", "Biology", "علم الأحياء"),
    ("maths", "mathematiques", "Mathématiques", "Mathematics", "الرياضيات"),
    ("education", "shs", "Éducation", "Education", "التربية والتعليم"),
    ("lettres-langues", "shs", "Lettres, langues et linguistique", "Literature, languages & linguistics", "الآداب واللغات واللسانيات"),
    ("histoire-societe", "shs", "Histoire, société et droit", "History, society & law", "التاريخ والمجتمع والقانون"),
    ("economie-gestion", "economie", "Économie et gestion", "Economics & management", "الاقتصاد والتصرف"),
    ("environnement", "terre-environnement", "Terre, environnement et chimie", "Earth, environment & chemistry", "الأرض والبيئة والكيمياء"),
]
S_PAR_SLUG = {s[0]: s for s in SPECIALITES}

# Types d'événement (français, anglais, arabe)
TYPES = {
    "conference": ("Conférence", "Conference", "مؤتمر"),
    "atelier": ("Atelier", "Workshop", "ورشة عمل"),
    "ecole": ("École scientifique", "School", "مدرسة علمية"),
}
MODES = {
    "presentiel": ("Sur place", "In person", "حضوري"),
    "en-ligne": ("En ligne", "Online", "عن بعد"),
    "hybride": ("Hybride", "Hybrid", "هجين"),
}

# Continents (adresse, français, anglais, arabe)
CONTINENTS = [
    ("afrique", "Afrique", "Africa", "إفريقيا"),
    ("europe", "Europe", "Europe", "أوروبا"),
    ("asie", "Asie et Moyen-Orient", "Asia & Middle East", "آسيا والشرق الأوسط"),
    ("amerique-nord", "Amérique du Nord", "North America", "أمريكا الشمالية"),
    ("amerique-sud", "Amérique latine", "Latin America", "أمريكا اللاتينية"),
    ("oceanie", "Océanie", "Oceania", "أوقيانوسيا"),
    ("en-ligne", "En ligne", "Online", "عن بعد"),
]
C_PAR_SLUG = {c[0]: c for c in CONTINENTS}

# Pays : code ISO -> (français, anglais, arabe, continent, autres noms anglais/locaux reconnus dans les lieux)
PAYS = {
    "TN": ("Tunisie", "Tunisia", "تونس", "afrique", []),
    "DZ": ("Algérie", "Algeria", "الجزائر", "afrique", []),
    "MA": ("Maroc", "Morocco", "المغرب", "afrique", []),
    "EG": ("Égypte", "Egypt", "مصر", "afrique", []),
    "ZA": ("Afrique du Sud", "South Africa", "جنوب إفريقيا", "afrique", []),
    "MG": ("Madagascar", "Madagascar", "مدغشقر", "afrique", []),
    "KE": ("Kenya", "Kenya", "كينيا", "afrique", []),
    "NG": ("Nigeria", "Nigeria", "نيجيريا", "afrique", []),
    "SN": ("Sénégal", "Senegal", "السنغال", "afrique", []),
    "RW": ("Rwanda", "Rwanda", "رواندا", "afrique", []),
    "GH": ("Ghana", "Ghana", "غانا", "afrique", []),
    "ET": ("Éthiopie", "Ethiopia", "إثيوبيا", "afrique", []),
    "FR": ("France", "France", "فرنسا", "europe", ["FX"]),
    "DE": ("Allemagne", "Germany", "ألمانيا", "europe", []),
    "IT": ("Italie", "Italy", "إيطاليا", "europe", []),
    "ES": ("Espagne", "Spain", "إسبانيا", "europe", []),
    "PT": ("Portugal", "Portugal", "البرتغال", "europe", []),
    "GB": ("Royaume-Uni", "United Kingdom", "المملكة المتحدة", "europe", ["UK", "England", "Scotland", "Wales", "Great Britain", "Northern Ireland"]),
    "IE": ("Irlande", "Ireland", "أيرلندا", "europe", []),
    "NL": ("Pays-Bas", "Netherlands", "هولندا", "europe", ["The Netherlands", "Holland"]),
    "BE": ("Belgique", "Belgium", "بلجيكا", "europe", []),
    "LU": ("Luxembourg", "Luxembourg", "لوكسمبورغ", "europe", []),
    "CH": ("Suisse", "Switzerland", "سويسرا", "europe", []),
    "AT": ("Autriche", "Austria", "النمسا", "europe", []),
    "DK": ("Danemark", "Denmark", "الدنمارك", "europe", []),
    "SE": ("Suède", "Sweden", "السويد", "europe", []),
    "NO": ("Norvège", "Norway", "النرويج", "europe", []),
    "FI": ("Finlande", "Finland", "فنلندا", "europe", []),
    "IS": ("Islande", "Iceland", "آيسلندا", "europe", []),
    "PL": ("Pologne", "Poland", "بولندا", "europe", []),
    "CZ": ("Tchéquie", "Czech Republic", "التشيك", "europe", ["Czechia"]),
    "SK": ("Slovaquie", "Slovakia", "سلوفاكيا", "europe", []),
    "HU": ("Hongrie", "Hungary", "المجر", "europe", []),
    "RO": ("Roumanie", "Romania", "رومانيا", "europe", []),
    "BG": ("Bulgarie", "Bulgaria", "بلغاريا", "europe", []),
    "GR": ("Grèce", "Greece", "اليونان", "europe", []),
    "HR": ("Croatie", "Croatia", "كرواتيا", "europe", []),
    "SI": ("Slovénie", "Slovenia", "سلوفينيا", "europe", []),
    "RS": ("Serbie", "Serbia", "صربيا", "europe", []),
    "EE": ("Estonie", "Estonia", "إستونيا", "europe", []),
    "LV": ("Lettonie", "Latvia", "لاتفيا", "europe", []),
    "LT": ("Lituanie", "Lithuania", "ليتوانيا", "europe", []),
    "MT": ("Malte", "Malta", "مالطا", "europe", []),
    "CY": ("Chypre", "Cyprus", "قبرص", "europe", []),
    "UA": ("Ukraine", "Ukraine", "أوكرانيا", "europe", []),
    "RU": ("Russie", "Russia", "روسيا", "europe", ["Russian Federation"]),
    "TR": ("Turquie", "Turkey", "تركيا", "asie", ["Türkiye", "Turkiye"]),
    "AE": ("Émirats arabes unis", "United Arab Emirates", "الإمارات العربية المتحدة", "asie", ["UAE", "Dubai", "Abu Dhabi"]),
    "SA": ("Arabie saoudite", "Saudi Arabia", "السعودية", "asie", []),
    "QA": ("Qatar", "Qatar", "قطر", "asie", ["Doha"]),
    "JO": ("Jordanie", "Jordan", "الأردن", "asie", []),
    "LB": ("Liban", "Lebanon", "لبنان", "asie", []),
    "IL": ("Israël", "Israel", "إسرائيل", "asie", []),
    "IR": ("Iran", "Iran", "إيران", "asie", []),
    "IN": ("Inde", "India", "الهند", "asie", []),
    "PK": ("Pakistan", "Pakistan", "باكستان", "asie", []),
    "BD": ("Bangladesh", "Bangladesh", "بنغلاديش", "asie", []),
    "LK": ("Sri Lanka", "Sri Lanka", "سريلانكا", "asie", []),
    "NP": ("Népal", "Nepal", "نيبال", "asie", []),
    "CN": ("Chine", "China", "الصين", "asie", ["P.R. China", "PR China", "People's Republic of China"]),
    "HK": ("Hong Kong", "Hong Kong", "هونغ كونغ", "asie", ["Hong Kong SAR", "Hong Kong, China"]),
    "MO": ("Macao", "Macau", "ماكاو", "asie", ["Macao"]),
    "TW": ("Taïwan", "Taiwan", "تايوان", "asie", []),
    "JP": ("Japon", "Japan", "اليابان", "asie", []),
    "KR": ("Corée du Sud", "South Korea", "كوريا الجنوبية", "asie", ["Korea", "Republic of Korea", "Korea, Republic of"]),
    "SG": ("Singapour", "Singapore", "سنغافورة", "asie", []),
    "MY": ("Malaisie", "Malaysia", "ماليزيا", "asie", []),
    "TH": ("Thaïlande", "Thailand", "تايلاند", "asie", []),
    "VN": ("Viêt Nam", "Vietnam", "فيتنام", "asie", ["Viet Nam"]),
    "ID": ("Indonésie", "Indonesia", "إندونيسيا", "asie", []),
    "PH": ("Philippines", "Philippines", "الفلبين", "asie", []),
    "KZ": ("Kazakhstan", "Kazakhstan", "كازاخستان", "asie", []),
    "AM": ("Arménie", "Armenia", "أرمينيا", "asie", []),
    "GE": ("Géorgie", "Georgia (country)", "جورجيا", "asie", []),
    "US": ("États-Unis", "United States", "الولايات المتحدة", "amerique-nord", ["USA", "U.S.A.", "U.S.", "US", "United States of America"]),
    "CA": ("Canada", "Canada", "كندا", "amerique-nord", []),
    "MX": ("Mexique", "Mexico", "المكسيك", "amerique-sud", []),
    "PR": ("Porto Rico", "Puerto Rico", "بورتوريكو", "amerique-nord", []),
    "BR": ("Brésil", "Brazil", "البرازيل", "amerique-sud", ["Brasil"]),
    "AR": ("Argentine", "Argentina", "الأرجنتين", "amerique-sud", []),
    "CL": ("Chili", "Chile", "تشيلي", "amerique-sud", []),
    "CO": ("Colombie", "Colombia", "كولومبيا", "amerique-sud", []),
    "PE": ("Pérou", "Peru", "البيرو", "amerique-sud", []),
    "UY": ("Uruguay", "Uruguay", "الأوروغواي", "amerique-sud", []),
    "CR": ("Costa Rica", "Costa Rica", "كوستاريكا", "amerique-sud", []),
    "CU": ("Cuba", "Cuba", "كوبا", "amerique-sud", []),
    "GP": ("Guadeloupe (France)", "Guadeloupe (France)", "غوادلوب (فرنسا)", "amerique-sud", ["Guadeloupe"]),
    "KH": ("Cambodge", "Cambodia", "كمبوديا", "asie", []),
    "KW": ("Koweït", "Kuwait", "الكويت", "asie", []),
    "BH": ("Bahreïn", "Bahrain", "البحرين", "asie", []),
    "OM": ("Oman", "Oman", "عُمان", "asie", ["Sultanate of Oman"]),
    "MU": ("Maurice", "Mauritius", "موريشيوس", "afrique", []),
    "PA": ("Panama", "Panama", "بنما", "amerique-sud", []),
    "AU": ("Australie", "Australia", "أستراليا", "oceanie", []),
    "NZ": ("Nouvelle-Zélande", "New Zealand", "نيوزيلندا", "oceanie", []),
}

# États, provinces et villes fréquents dans les listes (sans le pays écrit)
ETATS_US = ("Alabama AL Alaska AK Arizona AZ Arkansas AR California CA Colorado CO Connecticut CT Delaware DE Florida FL "
            "Georgia GA Hawaii HI Idaho ID Illinois IL Indiana IN Iowa IA Kansas KS Kentucky KY Louisiana LA Maine ME "
            "Maryland MD Massachusetts MA Michigan MI Minnesota MN Mississippi MS Missouri MO Montana MT Nebraska NE Nevada NV "
            "New_Hampshire NH New_Jersey NJ New_Mexico NM New_York NY North_Carolina NC North_Dakota ND Ohio OH Oklahoma OK "
            "Oregon OR Pennsylvania PA Rhode_Island RI South_Carolina SC South_Dakota SD Tennessee TN Texas TX Utah UT "
            "Vermont VT Virginia VA Washington WA West_Virginia WV Wisconsin WI Wyoming WY D.C. DC").replace("_", " ").split(" ")
PROVINCES_CA = ["Quebec", "Québec", "Ontario", "British Columbia", "Alberta", "Manitoba", "Nova Scotia", "QC", "ON", "BC", "AB"]
VILLES = {
    "seoul": "KR", "busan": "KR", "daejeon": "KR", "incheon": "KR", "jeju": "KR", "gyeongju": "KR",
    "tokyo": "JP", "kyoto": "JP", "osaka": "JP", "yokohama": "JP", "nagoya": "JP", "sapporo": "JP", "okinawa": "JP",
    "beijing": "CN", "shanghai": "CN", "shenzhen": "CN", "hangzhou": "CN", "guangzhou": "CN", "chengdu": "CN", "nanjing": "CN",
    "wuhan": "CN", "xi'an": "CN", "suzhou": "CN", "macau": "MO", "macao": "MO", "hong kong": "HK", "taipei": "TW",
    "singapore": "SG", "bangkok": "TH", "hanoi": "VN", "kuala lumpur": "MY", "bali": "ID", "dubai": "AE", "abu dhabi": "AE",
    "doha": "QA", "paris": "FR", "lyon": "FR", "marseille": "FR", "toulouse": "FR", "nice": "FR", "london": "GB",
    "edinburgh": "GB", "manchester": "GB", "berlin": "DE", "munich": "DE", "vienna": "AT", "rome": "IT", "milan": "IT",
    "barcelona": "ES", "madrid": "ES", "lisbon": "PT", "porto": "PT", "amsterdam": "NL", "brussels": "BE", "geneva": "CH",
    "zurich": "CH", "lausanne": "CH", "prague": "CZ", "copenhagen": "DK", "stockholm": "SE", "helsinki": "FI", "oslo": "NO",
    "athens": "GR", "istanbul": "TR", "tunis": "TN", "cairo": "EG", "marrakech": "MA", "rabat": "MA", "algiers": "DZ",
    "sydney": "AU", "melbourne": "AU", "brisbane": "AU", "auckland": "NZ", "toronto": "CA", "montreal": "CA", "montréal": "CA",
    "vancouver": "CA", "ottawa": "CA", "rio de janeiro": "BR", "sao paulo": "BR", "são paulo": "BR", "mexico city": "MX",
    "cancun": "MX", "santiago": "CL", "buenos aires": "AR", "bogota": "CO", "lima": "PE", "new york": "US", "san francisco": "US",
    "boston": "US", "seattle": "US", "chicago": "US", "los angeles": "US", "san diego": "US", "honolulu": "US",
    "new orleans": "US", "vancouver, canada": "CA", "hyderabad": "IN", "bangalore": "IN", "bengaluru": "IN", "delhi": "IN",
    "new delhi": "IN", "mumbai": "IN", "chennai": "IN", "kolkata": "IN", "jerusalem": "IL", "tel aviv": "IL", "riyadh": "SA", "bruges": "BE", "brugge": "BE",
    "hsinchu": "TW", "phoenix": "US", "siem reap": "KH", "panama city": "PA", "austin": "US", "atlanta": "US", "denver": "US",
    "vienna, austria": "AT", "kraków": "PL", "krakow": "PL", "warsaw": "PL", "dublin": "IE", "glasgow": "GB", "porto alegre": "BR",
}

_NOMS = {}
for _code, (_fr, _en, _ar, _cont, _autres) in PAYS.items():
    for _n in [_fr, _en, _code] + _autres:
        _NOMS[_n.lower()] = _code


def sans_accents(t):
    return "".join(c for c in unicodedata.normalize("NFKD", str(t or "")) if not unicodedata.combining(c))


def code_pays(nom):
    """Code ISO à partir d'un nom de pays (anglais, français) ou d'un code ; "" si inconnu."""
    n = re.sub(r"\s+", " ", str(nom or "")).strip().strip(".").lower()
    if not n:
        return ""
    if n in _NOMS:
        return _NOMS[n]
    n2 = sans_accents(n)
    for k, v in _NOMS.items():
        if sans_accents(k) == n2:
            return v
    return ""


def lire_lieu(texte):
    """« Montréal, Québec, Canada » -> (ville, code pays, mode). Mode : presentiel / en-ligne / hybride.
    On ne devine JAMAIS un pays absent du texte (sauf État américain, province canadienne ou ville connue)."""
    t = re.sub(r"\s+", " ", str(texte or "")).strip()
    bas = t.lower()
    mode = "presentiel"
    if re.search(r"\bhybrid", bas):
        mode = "hybride"
    elif re.search(r"\b(virtual|online|en ligne|remote)\b", bas) and not re.search(r",", re.sub(r"\(.*?\)", "", bas)):
        mode = "en-ligne"
    elif re.search(r"\b(virtual|online)\b", bas):
        mode = "hybride"
    propre = re.sub(r"\((?:hybrid|virtual|online)[^)]*\)", "", t, flags=re.I)
    propre = re.sub(r"\b(?:hybrid|virtual|online)\b\s*(?:/|&|and|\+)?", "", propre, flags=re.I).strip(" ,;/-+&")
    morceaux = [m.strip() for m in re.split(r"[,;]", propre) if m.strip()]
    code = ""
    if morceaux:
        dernier = morceaux[-1]
        if len(morceaux) >= 2 and re.fullmatch(r"[A-Z]{2}", dernier) and dernier in ETATS_US:
            code = "US"                     # « San Diego, CA » = Californie, pas le Canada
        elif len(morceaux) >= 2 and dernier in ("QC", "ON", "BC", "AB"):
            code = "CA"
        else:
            code = code_pays(dernier)
        if not code and len(morceaux) >= 2:
            if morceaux[-1] in ETATS_US:
                code = "US"
            elif morceaux[-1] in PROVINCES_CA:
                code = "CA"
        if not code:
            for m in reversed(morceaux):
                code = code_pays(m) or VILLES.get(m.lower(), "")
                if code:
                    break
    ville = ""
    if morceaux:
        ville = morceaux[0]
        if code_pays(ville) == code and len(morceaux) == 1:
            ville = ""
    if mode == "en-ligne":
        ville, code = "", ""
    return ville[:80], code, mode


def continent(code, mode):
    if mode == "en-ligne" or not code:
        return "en-ligne" if mode == "en-ligne" else ""
    return PAYS.get(code, ("", "", "", "", []))[3]


# ---- domaines et spécialités -------------------------------------------------------------------
MOTS = [   # (expression régulière sur le titre/les mots-clés, spécialité) — anglais, français et arabe
    # finance islamique d'abord (sinon « finance » l'emporterait), puis comptabilité, puis finance
    (r"\b(takaful)\b|تكافل", "takaful"),
    (r"\b(sukuk)\b|صكوك", "sukuk"),
    (r"\b(zakat|zakah|waqf|awqaf|islamic social finance|finance sociale islamique)\b|زكاة|الزكاة|وقف|الوقف|الأوقاف", "zakat-waqf"),
    (r"\b(aaoifi|ifsb|shari.?ah|sharia|charia|fiqh)\b|أيوفي|الشريعة|شرعي", "aaoifi-charia"),
    (r"\b(islamic bank\w*|banque islamique|banques islamiques|islamic financial institutions?)\b|المصارف الإسلامية|الصيرفة الإسلامية|البنوك الإسلامية", "banque-islamique"),
    (r"\b(islamic financ\w*|islamic econom\w*|finance islamique|economie islamique|halal|participation financ\w*|partnership financ\w*)\b"
     r"|التمويل الإسلامي|المالية الإسلامية|مالية إسلامية|الاقتصاد الإسلامي|المال الإسلامي", "economie-islamique"),
    (r"\b(audit\w*|commissariat aux comptes)\b|التدقيق|المراجعة", "audit"),
    (r"\b(ifrs|iasb|financial reporting|financial accounting|comptabilite financiere|normes comptables)\b|المحاسبة المالية|المعايير المحاسبية", "compta-financiere"),
    (r"\b(management accounting|managerial accounting|cost accounting|controle de gestion|comptabilite de gestion)\b|المحاسبة الإدارية|محاسبة التكاليف", "compta-gestion"),
    (r"\b(tax|taxation|fiscalite|fiscal)\b|الجباية|الضرائب", "fiscalite"),
    (r"\b(corporate governance|gouvernance|esg reporting|sustainability reporting|integrated reporting)\b|الحوكمة", "gouvernance"),
    (r"\b(accounting|accountancy|comptabilite|comptable)\b|المحاسبة|محاسبة", "compta-generale"),
    (r"\b(fintech|financial technology|digital finance|cryptocurrenc\w*|blockchain)\b|التكنولوجيا المالية", "fintech"),
    (r"\b(banking|banque|financial intermediation)\b|البنوك|المصارف", "banque"),
    (r"\b(asset pricing|financial markets?|marches financiers|stock markets?)\b|الأسواق المالية|البورصة", "marches"),
    (r"\b(corporate finance|finance d.entreprise)\b|مالية الشركات", "finance-entreprise"),
    (r"\b(finance|financial)\b|المالية|التمويل", "finance-generale"),
    (r"\b(vision|image|visual|cvpr|iccv|eccv|bmvc|accv|wacv|3dv|pattern recognition)\b", "vision"),
    (r"\b(language|linguistic|nlp|acl|emnlp|naacl|coling|eacl|speech|interspeech|lrec|semantic)\b", "langage"),
    (r"\b(robot|robotics|icra|iros|humanoid|automation|control)\b", "robotique"),
    (r"\b(signal|icassp|acoustic)\b", "signal"),
    (r"\b(bioinformatics|genom|genetic|protein|computational biology|recomb|ismb)\w*", "bioinformatique"),
    (r"\b(neuro\w*|brain|cognitive)\b", "neurosciences"),
    (r"\b(medical|medicine|clinical|cardio\w*|health|miccai|surgery)\b", "medecine"),
    (r"\b(security|privacy|crypt\w*)\b", "securite"),
    (r"\b(data mining|kdd|database|information retrieval|web search|recommend\w*|sigir|wsdm|knowledge graph)\b", "donnees"),
    (r"\b(?<!neural )(networks?|networking|communications?|wireless|mobile computing|internet)\b", "reseaux"),
    (r"\b(software|programming)\b", "genie-logiciel"),
    (r"\b(graphics|multimedia|siggraph|visualization)\b", "graphisme"),
    (r"\b(human[- ]computer|hci|chi|interaction|user interface|uist|cscw)\b", "ihm"),
    (r"\b(machine learning|learning|artificial intelligence|neural|ai|reinforcement)\b", "ia-apprentissage"),
    (r"\b(education|teaching|pedagog\w*)\b", "education"),
    (r"\b(economic\w*|management|business)\b", "economie-gestion"),
    (r"\b(mathematic\w*|algebra|geometry|topology|probability)\b", "maths"),
]
SOUS_CCF = {"AI": "ia-apprentissage", "CG": "graphisme", "CT": "theorie", "DB": "donnees", "DS": "systemes",
            "HI": "ihm", "MX": "info-interdisciplinaire", "NW": "reseaux", "SC": "securite", "SE": "genie-logiciel"}
ETIQUETTES_HF = {
    "machine-learning": "ia-apprentissage", "machine learning": "ia-apprentissage", "deep learning": "ia-apprentissage",
    "reinforcement-learning": "ia-apprentissage", "representation-learning": "ia-apprentissage", "large-language-models": "langage",
    "lifelong-learning": "ia-apprentissage", "reasoning": "ia-apprentissage", "fairness": "ia-apprentissage",
    "knowledge representation": "ia-apprentissage", "computer-vision": "vision", "computer vision": "vision",
    "image processing": "vision", "image-processing": "vision", "visual information processing": "vision",
    "pattern-recognition": "vision", "natural-language-processing": "langage", "speech": "langage",
    "data-mining": "donnees", "web-search": "donnees", "web mining": "donnees", "retrieval": "donnees",
    "information-retrieval": "donnees", "recommendation": "donnees", "knowledge-graphs": "donnees",
    "semantics and knowledge": "donnees", "content analysis": "donnees", "information-systems": "donnees",
    "robotics": "robotique", "computer-graphics": "graphisme", "human-computer-interaction": "ihm",
    "signal-processing": "signal", "signal processing": "signal", "software engineering": "genie-logiciel",
    "mathematics": "maths", "optimization-methods": "maths",
}
CATEGORIES_INSPIRE = {
    "Phenomenology-HEP": "particules", "Experiment-HEP": "particules", "Theory-HEP": "particules", "Lattice": "particules",
    "Gravitation and Cosmology": "astro", "Astrophysics": "astro", "Experiment-Nucl": "nucleaire", "Theory-Nucl": "nucleaire",
    "Quantum Physics": "quantique", "Instrumentation": "instrumentation", "Accelerators": "instrumentation",
    "Computing": "calcul-physique", "Data Analysis and Statistics": "calcul-physique",
    "Math and Math Physics": "physique-theorique", "Condensed Matter": "matiere-condensee", "General Physics": "physique-generale",
    "Other": "physique-generale",
}
SOUS_BIO = {"BIOINFO": "bioinformatique", "GEN": "bioinformatique", "PROT": "bioinformatique", "CLIN": "medecine",
            "CVD": "medecine", "BANK": "bioinformatique", "ML": "ia-apprentissage"}


def specialites_par_mots(texte):
    t = " " + sans_accents(str(texte or "")).lower() + " "
    res = []
    for motif, s in MOTS:
        if re.search(sans_accents(motif), t) and s not in res:     # même normalisation (hamza arabe, accents) des deux côtés
            res.append(s)
    if any(S_PAR_SLUG[s][1] == "finance-islamique" for s in res):   # « Islamic finance » n'est pas de la finance générale
        res = [s for s in res if s != "finance-generale"]
    return res


def domaines_de(specs):
    res = []
    for s in specs:
        d = S_PAR_SLUG[s][1]
        if d not in res:
            res.append(d)
    return res


def type_evenement(titre):
    t = sans_accents(str(titre or "")).lower()
    if re.search(r"\bschool\b|\becole\b|\bwinter school|\bsummer school", t):
        return "ecole"
    if re.search(r"\bworkshop\b|\batelier\b", t):
        return "atelier"
    return "conference"
