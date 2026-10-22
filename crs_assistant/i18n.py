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
    "category.death_timely": {
        "en": "Death registration within the 6-month window",
        "sw": "Usajili wa kifo ndani ya kipindi cha miezi 6",
    },
    "category.death_late": {
        "en": "Late death registration (more than 6 months after the death)",
        "sw": "Usajili wa kifo uliochelewa (zaidi ya miezi 6 baada ya kifo)",
    },
    "category.death_replacement": {
        "en": "Replacement of a lost death certificate",
        "sw": "Kubadilisha cheti cha kifo kilichopotea",
    },
    "category.death_abroad": {
        "en": "Death outside Kenya",
        "sw": "Kifo nje ya Kenya",
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
    "step.collect_death_notification": {
        "en": "Get the notification of death (D1) from the hospital",
        "sw": "Chukua taarifa ya kifo (D1) kutoka hospitali",
    },
    "step.report_death_chief": {
        "en": "Report the death to your Assistant Chief and get a confirmation letter",
        "sw": "Ripoti kifo kwa Chifu Msaidizi na upate barua ya uthibitisho",
    },
    "step.report_death_police": {
        "en": "Report the death at the nearest police station; a post-mortem may be required",
        "sw": "Ripoti kifo katika kituo cha polisi kilicho karibu; uchunguzi wa maiti unaweza kuhitajika",
    },
    "step.register_death": {
        "en": "Take the documents to the Civil Registration office to register the death",
        "sw": "Peleka nyaraka kwenye ofisi ya Usajili wa Raia kusajili kifo",
    },
    "step.collect_burial_permit": {
        "en": "Get the burial permit before the burial",
        "sw": "Pata kibali cha mazishi kabla ya mazishi",
    },
    "step.apply_death_certificate": {
        "en": "Apply and pay for the death certificate on eCitizen (ecitizen.go.ke)",
        "sw": "Omba na ulipie cheti cha kifo kwenye eCitizen (ecitizen.go.ke)",
    },
    "step.gather_death_evidence": {
        "en": "Gather at least one proof of the death (D1, burial permit, chief's letter or affidavit)",
        "sw": "Kusanya angalau uthibitisho mmoja wa kifo (D1, kibali cha mazishi, barua ya chifu au kiapo)",
    },
    "step.apply_death_replacement": {
        "en": "Apply and pay for a replacement death certificate on eCitizen",
        "sw": "Omba na ulipie cheti mbadala cha kifo kwenye eCitizen",
    },
    "step.death_abroad": {
        "en": "Register the death in the country where it happened and contact the nearest Kenyan embassy for guidance",
        "sw": "Sajili kifo katika nchi kilipotokea na uwasiliane na ubalozi wa Kenya ulio karibu kwa mwongozo",
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
    "warn.burial_permit": {
        "en": "A burial permit is needed before the burial. Register the death first.",
        "sw": "Kibali cha mazishi kinahitajika kabla ya mazishi. Sajili kifo kwanza.",
    },
    "warn.unnatural_death": {
        "en": "Deaths from accident, violence or an unknown cause must be reported to the police.",
        "sw": "Vifo vilivyotokana na ajali, vurugu au sababu isiyojulikana lazima viripotiwe polisi.",
    },
    "warn.death_abroad": {
        "en": "Deaths outside Kenya are registered in the country where they happened.",
        "sw": "Vifo vilivyotokea nje ya Kenya husajiliwa katika nchi vilipotokea.",
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
    # USSD screens (keep each under ~160 characters)
    "ussd.main": {
        "en": "Birth Registration Assistant\n1. What documents do I need?\n2. Check registration deadline\n3. Book office appointment\n4. Check my appointment",
        "sw": "Msaidizi wa Usajili wa Kuzaliwa\n1. Nahitaji nyaraka gani?\n2. Angalia muda wa mwisho\n3. Weka miadi ofisini\n4. Angalia miadi yangu",
    },
    "ussd.service": {
        "en": "Which service?\n1. Register a birth\n2. Replace lost certificate\n3. Correct certificate details",
        "sw": "Huduma gani?\n1. Sajili kuzaliwa\n2. Badilisha cheti kilichopotea\n3. Sahihisha maelezo ya cheti",
    },
    "ussd.applicant": {
        "en": "Who is applying?\n1. Parent\n2. Guardian\n3. Myself (adult)",
        "sw": "Nani anaomba?\n1. Mzazi\n2. Mlezi\n3. Mimi mwenyewe (mtu mzima)",
    },
    "ussd.birth_place": {
        "en": "Where was the child born?\n1. Hospital / clinic\n2. At home\n3. Outside Kenya",
        "sw": "Mtoto alizaliwa wapi?\n1. Hospitali / kliniki\n2. Nyumbani\n3. Nje ya Kenya",
    },
    "ussd.dob": {
        "en": "Enter date of birth as DDMMYYYY (e.g. 05032026)",
        "sw": "Weka tarehe ya kuzaliwa kama DDMMYYYY (mf. 05032026)",
    },
    "ussd.father": {
        "en": "Father's details?\n1. Parents married\n2. Not married, father to be listed\n3. Father not to be listed",
        "sw": "Maelezo ya baba?\n1. Wazazi wameoana\n2. Hawajaoana, baba aandikwe\n3. Baba asiandikwe",
    },
    "ussd.checklist_sent": {
        "en": "{category}. {count} document(s) needed. Full list sent by SMS.",
        "sw": "{category}. Nyaraka {count} zinahitajika. Orodha kamili imetumwa kwa SMS.",
    },
    "ussd.deadline_open": {
        "en": "Register by {deadline}: {days} day(s) left.",
        "sw": "Sajili kabla ya {deadline}: zimebaki siku {days}.",
    },
    "ussd.deadline_passed": {
        "en": "The deadline was {deadline}. You need late registration. Choose option 1 for the document list.",
        "sw": "Mwisho ulikuwa {deadline}. Unahitaji usajili wa kuchelewa. Chagua 1 kupata orodha ya nyaraka.",
    },
    "ussd.county": {
        "en": "Enter your county number (1-47, e.g. 47 for Nairobi)",
        "sw": "Weka nambari ya kaunti yako (1-47, mf. 47 kwa Nairobi)",
    },
    "ussd.pick_day": {
        "en": "Choose a day:",
        "sw": "Chagua siku:",
    },
    "ussd.pick_slot": {
        "en": "Choose a time:",
        "sw": "Chagua saa:",
    },
    "ussd.no_slots": {
        "en": "No free slots on that day. Please dial again and choose another day.",
        "sw": "Hakuna nafasi siku hiyo. Tafadhali piga tena uchague siku nyingine.",
    },
    "ussd.booked": {
        "en": "Booked {reference}: {day} {slot}. Details sent by SMS.",
        "sw": "Miadi {reference}: {day} {slot}. Maelezo yametumwa kwa SMS.",
    },
    "ussd.reference": {
        "en": "Enter your appointment reference (e.g. APT-AB23CD)",
        "sw": "Weka kumbukumbu ya miadi yako (mf. APT-AB23CD)",
    },
    "ussd.appointment": {
        "en": "{reference}: {office}, {day} {slot} ({status})",
        "sw": "{reference}: {office}, {day} {slot} ({status})",
    },
    "ussd.not_found": {
        "en": "No appointment found for this number with that reference.",
        "sw": "Hakuna miadi iliyopatikana kwa nambari hii na kumbukumbu hiyo.",
    },
    "ussd.invalid": {
        "en": "Invalid input. Please dial again.",
        "sw": "Ingizo si sahihi. Tafadhali piga tena.",
    },
    "sms.checklist_header": {
        "en": "{category}. Bring:",
        "sw": "{category}. Beba:",
    },
    "sms.optional": {
        "en": "(if available)",
        "sw": "(kama kipo)",
    },
    "group.proof_of_death": {
        "en": "one proof of the death",
        "sw": "uthibitisho mmoja wa kifo",
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
