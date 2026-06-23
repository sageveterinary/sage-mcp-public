"""Patient prep data for all SVI imaging modalities.

Structured, standardized prep instructions derived from EzyVet email templates
across all 3 SVI locations (Round Rock TX, Spring TX, Sandy UT).

Static data — 8 modalities. Updated manually when prep procedures change.
"""

PREP_DATA: dict[str, dict] = {
    "mri": {
        "modality": "mri",
        "modality_label": "MRI",
        "requires_anesthesia": True,
        "species": ["dog", "cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK until morning. Morning medications are OK to give.",
            "diabetic_exception": "If your pet is diabetic, please contact us for modified fasting instructions.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese. If your pet doesn't have a prescription, ask your primary veterinarian before the appointment.",
        },
        "estimated_duration": {
            "standard": "3-4 hours",
            "stat": "1.5-2 hours",
            "note": "Includes anesthesia recovery time.",
        },
        "what_to_bring": [
            "All prior imaging on CD or USB drive",
            "Vaccination records",
            "Medical records from recent veterinary visits related to the current problem",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will greet you, discuss the visit, and obtain consent forms. Your pet will be taken to the treatment area.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "General anesthesia is required for MRI.",
            "A contrast agent may be used during the study.",
            "A small area of fur will be shaved for IV catheter placement.",
            "Additional imaging may be recommended if results are inconclusive. You will never be pressured.",
        ],
        "aftercare": [
            "Your pet may be groggy for 4-6 hours post-anesthesia.",
            "Monitor your pet for any unusual behavior and keep them in a safe, quiet space.",
            "If urgent findings are identified, our doctor will call your veterinarian directly.",
            "A formal radiology report will be sent to your veterinarian within 24 hours.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
            "insurance_note": "Trupanion same-day claim processing may be available. Bring all related medical records to increase approval chances.",
        },
        "resources": {
            "faq_links": ["MRI FAQ"],
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
    "ct": {
        "modality": "ct",
        "modality_label": "CT",
        "requires_anesthesia": True,
        "species": ["dog", "cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK until morning. Morning medications are OK to give.",
            "diabetic_exception": "If your pet is diabetic, please contact us for modified fasting instructions.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese.",
        },
        "estimated_duration": {
            "standard": "3-4 hours",
            "stat": "1.5-2 hours",
            "note": "Includes anesthesia recovery time.",
        },
        "what_to_bring": [
            "All prior imaging on CD or USB drive",
            "Vaccination records",
            "Medical records related to the current problem",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will greet you, discuss the visit, and obtain consent forms.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "General anesthesia is required for CT.",
            "A contrast agent may be used during the study.",
            "A small area of fur will be shaved for IV catheter placement.",
            "Additional imaging may be recommended if results are inconclusive.",
        ],
        "aftercare": [
            "Your pet may be groggy for 4-6 hours post-anesthesia.",
            "Monitor your pet for any unusual behavior.",
            "Urgent findings will be communicated to your veterinarian immediately.",
            "Formal radiology report within 24 hours.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
            "insurance_note": "Trupanion same-day claim processing may be available.",
        },
        "resources": {
            "faq_links": ["CT FAQ"],
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
    "ultrasound": {
        "modality": "ultrasound",
        "modality_label": "Ultrasound",
        "requires_anesthesia": False,
        "species": ["dog", "cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK until morning. Morning medications are OK to give.",
            "diabetic_exception": "If your pet is diabetic, please contact us for modified fasting instructions.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese. Additional sedation drugs may be needed if your pet is very nervous, which may result in an additional charge.",
        },
        "estimated_duration": {
            "standard": "2-3 hours",
            "stat": "1.5-2 hours",
        },
        "what_to_bring": [
            "All prior imaging on CD or USB drive",
            "Medical records related to the current problem",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will greet you, discuss the visit, and obtain consent forms.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "A section of hair will be shaved in the area being imaged. This is essential for diagnostic-quality images.",
            "Razor burn may occur — this is normal and heals quickly. We will apply Arnicare if needed.",
            "Additional imaging (e.g., CT) may be recommended if results are inconclusive. You will never be pressured.",
        ],
        "aftercare": [
            "If razor burn occurred, we will apply Arnicare. Monitor the area for a few days and prevent licking.",
            "Urgent findings will be communicated to your veterinarian immediately.",
            "Formal radiology report within 24 hours.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
            "insurance_note": "Trupanion same-day claim processing may be available.",
        },
        "resources": {
            "faq_links": ["Ultrasound FAQ"],
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
    "radiograph": {
        "modality": "radiograph",
        "modality_label": "Radiograph (X-ray)",
        "requires_anesthesia": False,
        "species": ["dog", "cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK until morning. Morning medications are OK to give.",
            "diabetic_exception": "If your pet is diabetic, please contact us for modified fasting instructions.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese.",
        },
        "estimated_duration": {
            "standard": "2-3 hours",
            "stat": "1.5-2 hours",
        },
        "what_to_bring": [
            "All prior imaging on CD or USB drive",
            "Medical records related to the current problem",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will greet you, discuss the visit, and obtain consent forms.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "Sedation (not general anesthesia) is typically used for radiographs to ensure clear images.",
            "Additional imaging may be recommended if results are inconclusive.",
        ],
        "aftercare": [
            "Your pet may be mildly drowsy from sedation.",
            "Urgent findings will be communicated to your veterinarian immediately.",
            "Formal radiology report within 24 hours.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
            "insurance_note": "Trupanion same-day claim processing may be available.",
        },
        "resources": {
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
    "echocardiogram": {
        "modality": "echocardiogram",
        "modality_label": "Echocardiogram",
        "requires_anesthesia": False,
        "species": ["dog", "cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK. Although echocardiograms don't always require fasting, we ask that you fast your pet in case additional imaging is recommended.",
            "diabetic_exception": "If your pet is diabetic, please contact us.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese.",
        },
        "estimated_duration": {
            "standard": "2-3 hours",
            "stat": "1.5-2 hours",
        },
        "what_to_bring": [
            "All prior imaging or cardiac records",
            "Medical records related to the current problem",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will greet you, discuss the visit, and obtain consent forms.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "A small area of fur on the chest will be shaved for the ultrasound probe.",
            "Your pet will be gently positioned on their side for the exam.",
            "Additional imaging may be recommended if results are inconclusive.",
        ],
        "aftercare": [
            "Urgent findings will be communicated to your veterinarian immediately.",
            "Formal cardiology report within 24 hours.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
            "insurance_note": "Trupanion same-day claim processing may be available.",
        },
        "resources": {
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
    "scintigraphy": {
        "modality": "scintigraphy",
        "modality_label": "Scintigraphy (Nuclear Scan)",
        "requires_anesthesia": False,
        "species": ["cat"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK. Morning medications are OK EXCEPT thyroid medications.",
            "special": "Withhold all thyroid medications (such as methimazole/Felimazole) for 7-10 days prior to the appointment. Consult your veterinarian before stopping any medications.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "Only give if previously discussed with Sage Veterinary staff. Contact your referring veterinarian for a prescription.",
        },
        "estimated_duration": {
            "standard": "2-3 hours",
        },
        "what_to_bring": [
            "All prior imaging and lab work",
            "Medical records related to thyroid condition",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will discuss the procedure at check-in.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time.",
        },
        "procedure_notes": [
            "A small amount of radioactive tracer is injected to image the thyroid glands.",
            "The procedure does not require general anesthesia.",
            "Your pet must remain calm and still during imaging.",
        ],
        "aftercare": [
            "Formal report will be sent to your veterinarian within 24 hours.",
            "Results will help determine if I-131 treatment is appropriate.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
        },
        "resources": {
            "chatbot": "CATTBot — https://catt-bot.zapier.app/",
        },
    },
    "catt_i131": {
        "modality": "catt_i131",
        "modality_label": "CATT / I-131 Treatment",
        "requires_anesthesia": False,
        "species": ["cat"],
        "fasting": {
            "required": False,
            "instruction": "Please feed your pet a full meal the night before AND the morning of their I-131 treatment.",
        },
        "anxiety_medication": {
            "recommended": False,
            "note": "Not typically required for I-131 boarding. Discuss with your veterinarian if your cat is particularly anxious.",
        },
        "estimated_duration": {
            "standard": "Multi-day boarding: 7-14 days depending on radiation levels",
            "note": "Your cat will board with us for the duration of treatment. A team member will call or text daily with updates.",
        },
        "what_to_bring": [
            "Enough food for the duration of the stay (typically 7-14 days)",
            "All current medications with dosing instructions",
            "A comfort item from home (e.g., a t-shirt with your scent, small cardboard scratcher)",
            "NOTE: Personal items will not be returned due to potential radiation contamination",
        ],
        "arrival": {
            "process": "Check-in at reception. Our team will discuss the treatment plan and boarding arrangements.",
            "owner_accompaniment": False,
        },
        "procedure_notes": [
            "I-131 is a one-time radioactive iodine treatment for feline hyperthyroidism.",
            "Your cat will receive a single injection and then board with us while radiation levels decrease to safe levels.",
            "Daily updates will be provided by phone or text.",
        ],
        "aftercare": [
            "Upon discharge, you will receive detailed radiation safety instructions for home.",
            "Limit close contact (within 3 feet) for the time period specified at discharge.",
            "Keep your cat indoors and away from pregnant women and young children for the specified period.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
        },
        "resources": {
            "videos": [
                "CATT Overview",
                "First Appointment Instructions",
                "Second Appointment Instructions",
                "After Treatment Instructions",
                "FAQ",
            ],
            "chatbot": "CATTBot — https://catt-bot.zapier.app/",
        },
    },
    "synovetin_oa": {
        "modality": "synovetin_oa",
        "modality_label": "Synovetin OA (Joint Treatment)",
        "requires_anesthesia": True,
        "species": ["dog"],
        "fasting": {
            "required": True,
            "duration_hours": 12,
            "instruction": "No food after midnight the night before. Water is OK. Morning medications are OK to give.",
            "diabetic_exception": "If your pet is diabetic, please contact us.",
        },
        "anxiety_medication": {
            "recommended": True,
            "drugs": ["Gabapentin", "Trazodone"],
            "schedule": "Give the night before, then again 2 hours before appointment time.",
            "note": "It is OK to wrap the medication in a small piece of meat or cheese.",
        },
        "estimated_duration": {
            "standard": "2-3 hours",
            "note": "Synovetin is a joint injection procedure, shorter than diagnostic imaging.",
        },
        "what_to_bring": [
            "Prior imaging of affected joint(s) on CD or USB",
            "Medical records related to the joint condition",
        ],
        "arrival": {
            "process": "Drop-off appointment. Our team will discuss the procedure and obtain consent.",
            "owner_accompaniment": False,
            "note": "You are free to leave and return at your scheduled pickup time, or as late as 5pm.",
        },
        "procedure_notes": [
            "Synovetin OA is a radioactive injection into the affected joint(s) to treat osteoarthritis.",
            "Light sedation or anesthesia is required for precise needle placement.",
            "The procedure targets inflammation at the source for long-lasting relief.",
        ],
        "aftercare": [
            "Your pet may be drowsy from sedation for a few hours.",
            "Limit close prolonged contact for the time period specified at discharge.",
            "Follow your veterinarian's instructions for activity restriction.",
            "Many pets show improvement within 1-3 months.",
        ],
        "payment": {
            "accepted": ["Visa", "Mastercard", "Discover", "American Express", "Apple Pay"],
            "not_accepted": ["Cash", "Checks"],
            "financing": ["Cherry Finance (same-day approval, no credit impact)", "CareCredit"],
        },
        "resources": {
            "chatbot": "Sagent — https://sage-veterinary-website-support.zapier.app/",
        },
    },
}

# Aliases for common query variations
MODALITY_ALIASES: dict[str, str] = {
    "mri": "mri",
    "magnetic resonance": "mri",
    "ct": "ct",
    "cat scan": "ct",
    "computed tomography": "ct",
    "ultrasound": "ultrasound",
    "us": "ultrasound",
    "sono": "ultrasound",
    "sonogram": "ultrasound",
    "radiograph": "radiograph",
    "x-ray": "radiograph",
    "xray": "radiograph",
    "x ray": "radiograph",
    "echocardiogram": "echocardiogram",
    "echo": "echocardiogram",
    "cardiac ultrasound": "echocardiogram",
    "scintigraphy": "scintigraphy",
    "nuclear scan": "scintigraphy",
    "thyroid scan": "scintigraphy",
    "nuclear medicine": "scintigraphy",
    "catt": "catt_i131",
    "catt_i131": "catt_i131",
    "i-131": "catt_i131",
    "i131": "catt_i131",
    "radioactive iodine": "catt_i131",
    "hyperthyroidism treatment": "catt_i131",
    "synovetin": "synovetin_oa",
    "synovetin_oa": "synovetin_oa",
    "synovetin oa": "synovetin_oa",
    "joint injection": "synovetin_oa",
    "osteoarthritis treatment": "synovetin_oa",
}


def resolve_modality(query: str) -> str | None:
    """Resolve a modality query to a canonical key."""
    q = query.strip().lower()
    if q in PREP_DATA:
        return q
    return MODALITY_ALIASES.get(q)


def get_prep(modality_key: str) -> dict | None:
    """Get prep data for a modality."""
    return PREP_DATA.get(modality_key)


def list_modalities() -> list[dict]:
    """List all available modalities with labels."""
    return [
        {
            "modality": k,
            "label": v["modality_label"],
            "requires_anesthesia": v["requires_anesthesia"],
            "species": v["species"],
        }
        for k, v in PREP_DATA.items()
    ]
