"""English and Kiswahili message catalogue."""

from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "sw")

MESSAGES: dict[str, dict[str, str]] = {
    # Categories
    "category.timely": {
        "en": "Within the 6-month registration window",
        "sw": "Ndani ya kipindi cha miezi 6 cha usajili",
    },
    "category.late": {
        "en": "Late registration (more than 6 months after birth)",
        "sw": "Usajili wa kuchelewa (zaidi ya miezi 6 baada ya kuzaliwa)",
    },
    "category.late_adult": {
        "en": "Late registration of an adult",
        "sw": "Usajili wa kuchelewa wa mtu mzima",
    },
    "category.replacement": {
        "en": "Replacement of a lost or damaged birth certificate",
        "sw": "Kubadilisha cheti cha kuzaliwa kilichopotea au kuharibika",
    },
    "category.correction": {
        "en": "Correction of details on a birth certificate",
        "sw": "Kusahihisha maelezo kwenye cheti cha kuzaliwa",
    },
    "category.abroad": {
        "en": "Birth outside Kenya",
        "sw": "Kuzaliwa nje ya Kenya",
    },
    # Steps
    "step.collect_notification": {
        "en": "Get the birth notification (B1) from the hospital before you leave",
        "sw": "Chukua taarifa ya kuzaliwa (B1) kutoka hospitali kabla ya kuondoka",
    },
    "step.report_home_birth": {
        "en": "Report the home birth to your Assistant Chief and get a confirmation letter",
        "sw": "Ripoti kuzaliwa nyumbani kwa Chifu Msaidizi na upate barua ya uthibitisho",
    },
    "step.register_at_office": {
        "en": "Take the documents to the Civil Registration office in your sub-county",
        "sw": "Peleka nyaraka kwenye ofisi ya Usajili wa Raia katika kaunti ndogo yako",
    },
    "step.apply_certificate": {
        "en": "Apply and pay for the birth certificate on eCitizen (ecitizen.go.ke)",
        "sw": "Omba na ulipie cheti cha kuzaliwa kwenye eCitizen (ecitizen.go.ke)",
    },
    "step.collect_certificate": {
        "en": "Collect the certificate when you receive the ready notification",
        "sw": "Chukua cheti utakapopokea ujumbe kuwa kiko tayari",
    },
    "step.get_late_form": {
        "en": "Get the late registration form from the registrar's office",
        "sw": "Chukua fomu ya usajili wa kuchelewa kutoka ofisi ya msajili",
    },
    "step.gather_evidence": {
        "en": "Gather at least one proof of date of birth (clinic card, school record, baptism card or age assessment)",
        "sw": "Kusanya angalau uthibitisho mmoja wa tarehe ya kuzaliwa (kadi ya kliniki, rekodi ya shule, kadi ya ubatizo au makadirio ya umri)",
    },
    "step.submit_late_application": {
        "en": "Submit the form and documents to the registrar for approval",
        "sw": "Wasilisha fomu na nyaraka kwa msajili ili ziidhinishwe",
    },
    "step.await_verification": {
        "en": "Wait for verification; the registrar may call you for an interview",
        "sw": "Subiri uhakiki; msajili anaweza kukuita kwa mahojiano",
    },
    "step.contact_mission": {
        "en": "Register the birth with the nearest Kenyan embassy or high commission",
        "sw": "Sajili kuzaliwa katika ubalozi wa Kenya ulio karibu nawe",
    },
    "step.report_loss": {
        "en": "Report the loss at a police station and get a police abstract",
        "sw": "Ripoti upotevu katika kituo cha polisi na upate abstract ya polisi",
    },
    "step.apply_replacement": {
        "en": "Apply and pay for a replacement certificate on eCitizen",
        "sw": "Omba na ulipie cheti mbadala kwenye eCitizen",
    },
    "step.submit_correction": {
        "en": "Submit the correction request with the original certificate and evidence",
        "sw": "Wasilisha ombi la kusahihisha pamoja na cheti halisi na ushahidi",
    },
    # Warnings
    "warn.deadline_soon": {
        "en": "Only {days} day(s) left to register on time (deadline {deadline}). Go this week.",
        "sw": "Zimebaki siku {days} tu kusajili kwa wakati (mwisho {deadline}). Nenda wiki hii.",
    },
    "warn.deadline_passed": {
        "en": "The 6-month window ended on {deadline}. Late registration needs extra evidence and approval.",
        "sw": "Kipindi cha miezi 6 kiliisha {deadline}. Usajili wa kuchelewa unahitaji ushahidi zaidi na idhini.",
    },
    "warn.father_joint_consent": {
        "en": "Parents are not married: the father's name is entered only at the joint request of both parents.",
        "sw": "Wazazi hawajaoana: jina la baba huandikwa tu kwa ombi la pamoja la wazazi wote wawili.",
    },
    "warn.abroad": {
        "en": "Births outside Kenya are registered through Kenyan missions abroad.",
        "sw": "Waliozaliwa nje ya Kenya husajiliwa kupitia balozi za Kenya.",
    },
    # Readiness
    "ready.yes": {
        "en": "You have everything required. Bring originals and copies.",
        "sw": "Una kila kinachohitajika. Beba nakala halisi na nakala za ziada.",
    },
    "ready.no": {
        "en": "Not ready yet. Missing: {missing}",
        "sw": "Bado haujawa tayari. Kinakosekana: {missing}",
    },
    "group.proof_of_age": {
        "en": "one proof of date of birth",
        "sw": "uthibitisho mmoja wa tarehe ya kuzaliwa",
    },
    # SMS
    "sms.notification_received": {
        "en": "Birth recorded (ref {reference}). Register your child by {deadline} at the Civil Registration office. Dial the CRS USSD code for the document list.",
        "sw": "Kuzaliwa kumerekodiwa (kumb. {reference}). Sajili mtoto wako kabla ya {deadline} katika ofisi ya Usajili wa Raia. Piga msimbo wa USSD wa CRS kupata orodha ya nyaraka.",
    },
    "sms.reminder": {
        "en": "Reminder: {days} day(s) left to register your child's birth (ref {reference}, deadline {deadline}). Registration on time avoids extra paperwork.",
        "sw": "Kumbusho: zimebaki siku {days} kusajili kuzaliwa kwa mtoto wako (kumb. {reference}, mwisho {deadline}). Kusajili kwa wakati huepusha nyaraka za ziada.",
    },
    "sms.overdue": {
        "en": "The registration deadline for ref {reference} passed on {deadline}. You can still register through late registration; dial the CRS USSD code to see what to bring.",
        "sw": "Muda wa kusajili kwa kumb. {reference} uliisha {deadline}. Bado unaweza kusajili kupitia usajili wa kuchelewa; piga msimbo wa USSD wa CRS kuona cha kubeba.",
    },
    "sms.appointment_booked": {
        "en": "Appointment {reference}: {office}, {day} at {slot}. Bring the documents on your checklist.",
        "sw": "Miadi {reference}: {office}, {day} saa {slot}. Beba nyaraka zilizo kwenye orodha yako.",
    },
    "disclaimer": {
        "en": "Guidance only. Requirements can vary by office; confirm with your local registrar.",
        "sw": "Huu ni mwongozo tu. Mahitaji yanaweza kutofautiana kwa ofisi; thibitisha na msajili wa eneo lako.",
    },
}


def normalise_lang(lang: str | None) -> str:
    lang = (lang or "en").lower()[:2]
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def t(key: str, lang: str = "en", **params) -> str:
    entry = MESSAGES[key]
    text = entry.get(normalise_lang(lang)) or entry["en"]
    return text.format(**params) if params else text
