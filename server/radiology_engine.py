"""
Radiology Imaging Recommendation Engine — Python Port

Covers all 6 clinical pathways: Neuro, MSK, Masses, Abdominal/GI, Specialty, Metabolic.
Ported from findvetimaging.com TypeScript implementation (radiologyEngine.ts).

Used by the clinical_decision_support MCP tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Pricing defaults ─────────────────────────────────────────────────
PRICING = {
    "mri1": 3445,
    "mri_pkg": 3820,
    "mri_add": 950,
    "ct": 1530,
    "ct_con": 1895,
    "ct_add": 595,
    "us": 635,
    "us_add": 635,
    "echo": 750,
    "echo_us": 1485,
    "bw": 375,
    "stat_mri": 320,
    "stat_ct": 240,
    "stat_us": 135,
}

# ── Breed predisposition arrays ──────────────────────────────────────
WOBBLER_BREEDS = ["doberman", "great dane", "weimaraner", "boxer", "boston terrier"]
IVDD_BREEDS = [
    "french bulldog", "frenchie", "dachshund", "doxie", "corgi", "beagle",
    "shih tzu", "miniature poodle", "miniature australian shepherd", "cocker spaniel",
]
BRACHY_BREEDS = [
    "french bulldog", "pug", "boston terrier", "english bulldog", "shih tzu",
    "cavalier king charles", "bulldog", "boxer", "persian",
]
SMALL_BREEDS = [
    "yorkshire terrier", "yorkie", "maltese", "chihuahua",
    "miniature schnauzer", "pomeranian", "miniature poodle", "shih tzu",
]


def _breed_match(breed: str, candidates: list[str]) -> bool:
    b = breed.lower().strip()
    return any(c in b for c in candidates)


# ── Symptom category tags ────────────────────────────────────────────
NEURO_TAGS = {
    "back_pain", "hind_weakness", "paralysis", "neck_pain", "seizures",
    "head_tilt", "circling", "incontinence", "hemiparesis", "behavior_change",
    "muscle_wasting", "reluctance_jump",
}
MSK_TAGS = {
    "forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee",
    "elbow_ocd", "digit_lame", "bone_tumor",
}
MASS_TAGS = {
    "mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw",
    "neck_mass", "eye_issue", "anal_sac", "thyroid_mass", "mediastinal",
    "adrenal_kidney", "facial_swelling", "nasal", "nosebleed",
}
METABOLIC_TAGS = {"hypoglycemia", "hypercalcemia"}

# ── Clinical Sign Groups ─────────────────────────────────────────────
CLINICAL_SIGN_GROUPS = [
    {
        "id": "neuro", "label": "Neurological / Spinal", "emoji": "🧠",
        "signs": [
            {"id": "seizures", "label": "Seizures / Convulsions"},
            {"id": "head_tilt", "label": "Head Tilt"},
            {"id": "circling", "label": "Circling / Disorientation"},
            {"id": "behavior_change", "label": "Behavior Change"},
            {"id": "hemiparesis", "label": "One-Sided Weakness"},
            {"id": "back_pain", "label": "Back Pain / Hunched Posture"},
            {"id": "neck_pain", "label": "Neck Pain / Stiffness"},
            {"id": "hind_weakness", "label": "Hind Limb Weakness / Ataxia"},
            {"id": "paralysis", "label": "Paralysis / Non-Ambulatory"},
            {"id": "incontinence", "label": "Urinary Incontinence"},
            {"id": "reluctance_jump", "label": "Reluctance to Jump / Stairs"},
            {"id": "muscle_wasting", "label": "Muscle Wasting / Atrophy"},
        ],
    },
    {
        "id": "msk", "label": "Musculoskeletal / Lameness", "emoji": "🦴",
        "signs": [
            {"id": "forelimb_lame", "label": "Forelimb Lameness"},
            {"id": "hindlimb_lame", "label": "Hindlimb Lameness"},
            {"id": "shoulder_pain", "label": "Shoulder Pain"},
            {"id": "stifle_knee", "label": "Stifle / Knee Issue"},
            {"id": "elbow_ocd", "label": "Elbow Dysplasia / OCD"},
            {"id": "digit_lame", "label": "Digit / Paw / Toe Issue"},
            {"id": "bone_tumor", "label": "Bone Mass / Swelling"},
            {"id": "limb_swelling", "label": "Limb Swelling"},
        ],
    },
    {
        "id": "onco", "label": "Oncologic / Masses", "emoji": "🔬",
        "signs": [
            {"id": "mass_lump", "label": "Mass / Lump / Growth"},
            {"id": "abd_mass", "label": "Abdominal Mass"},
            {"id": "splenic_mass", "label": "Splenic Mass"},
            {"id": "liver_mass", "label": "Liver / Hepatic Mass"},
            {"id": "oral_jaw", "label": "Oral / Jaw Mass"},
            {"id": "neck_mass", "label": "Neck Mass"},
            {"id": "anal_sac", "label": "Anal Sac Mass"},
            {"id": "thyroid_mass", "label": "Thyroid Mass"},
            {"id": "mediastinal", "label": "Mediastinal / Thoracic Mass"},
            {"id": "adrenal_kidney", "label": "Adrenal / Kidney Mass"},
        ],
    },
    {
        "id": "head", "label": "Head / Face / Ears", "emoji": "👂",
        "signs": [
            {"id": "ear_issue", "label": "Ear Infection / Otitis"},
            {"id": "nasal", "label": "Nasal Discharge / Sneezing"},
            {"id": "nosebleed", "label": "Nosebleed / Epistaxis"},
            {"id": "facial_swelling", "label": "Facial Swelling"},
            {"id": "eye_issue", "label": "Eye Issue / Retrobulbar"},
        ],
    },
    {
        "id": "abdominal", "label": "Abdominal / GI", "emoji": "🩺",
        "signs": [
            {"id": "vomiting_gi", "label": "Vomiting / GI Distress"},
            {"id": "foreign_body", "label": "Suspected Foreign Body"},
            {"id": "pancreatitis", "label": "Pancreatitis"},
            {"id": "chronic_diarrhea", "label": "Chronic Diarrhea"},
            {"id": "liver_issue", "label": "Liver Disease / Elevated Enzymes"},
            {"id": "liver_shunt", "label": "Portosystemic Shunt"},
            {"id": "effusion", "label": "Abdominal Fluid / Effusion"},
            {"id": "weight_loss", "label": "Weight Loss / Anorexia"},
            {"id": "prostate", "label": "Prostate Issue"},
        ],
    },
    {
        "id": "resp", "label": "Respiratory / Cardiac", "emoji": "🫁",
        "signs": [
            {"id": "breathing", "label": "Labored Breathing / Dyspnea"},
            {"id": "tracheal", "label": "Coughing / Tracheal Collapse"},
            {"id": "resp_distress", "label": "Respiratory Distress"},
            {"id": "heart", "label": "Heart Murmur / Cardiac"},
        ],
    },
    {
        "id": "metabolic", "label": "Metabolic / Paraneoplastic", "emoji": "⚗️",
        "signs": [
            {"id": "hypoglycemia", "label": "Hypoglycemia / Low Blood Sugar"},
            {"id": "hypercalcemia", "label": "Hypercalcemia / High Calcium"},
        ],
    },
]

# Build flat lookup for all valid sign IDs
ALL_SIGN_IDS = set()
for grp in CLINICAL_SIGN_GROUPS:
    for sign in grp["signs"]:
        ALL_SIGN_IDS.add(sign["id"])

# ── Body Region definitions ──────────────────────────────────────────
BODY_REGIONS = [
    {"id": "head_brain", "label": "Head (brain)"},
    {"id": "head_nasal", "label": "Head (nasal / sinus)"},
    {"id": "head_ear", "label": "Head (tympanic bulla)"},
    {"id": "head_oral", "label": "Head (oral / mandible)"},
    {"id": "c_spine", "label": "C-spine"},
    {"id": "tl_spine", "label": "T-L spine"},
    {"id": "ls_spine", "label": "L-S spine / pelvis"},
    {"id": "shoulder", "label": "Shoulder"},
    {"id": "elbow", "label": "Elbow"},
    {"id": "forelimb", "label": "Thoracic limb (distal)"},
    {"id": "hip", "label": "Hip"},
    {"id": "stifle", "label": "Stifle"},
    {"id": "hindlimb", "label": "Pelvic limb (distal)"},
    {"id": "thorax", "label": "Thorax"},
    {"id": "abdomen", "label": "Abdomen"},
    {"id": "neck_soft", "label": "Cervical soft tissue"},
]

HEAD_TAGS_REGION = {"head_brain", "head_nasal", "head_ear", "head_oral"}

REGION_MAP = {
    "head_brain": "Head (brain)", "head_nasal": "Head (nasal/sinus)",
    "head_ear": "Head (tympanic bulla)", "head_oral": "Head (oral/mandible)",
    "c_spine": "C-spine", "tl_spine": "T-L spine", "ls_spine": "L-S spine",
    "shoulder": "Shoulder", "elbow": "Elbow", "forelimb": "Thoracic limb",
    "hip": "Hip", "stifle": "Stifle", "hindlimb": "Pelvic limb",
    "thorax": "Thorax", "abdomen": "Abdomen", "neck_soft": "Cervical soft tissue",
}


def calc_sites_from_regions(region_tags: list[str]) -> tuple[int, list[str]]:
    """Collapse multiple head sub-regions into a single 'Head' count."""
    head_labels = [REGION_MAP[t] for t in region_tags if t in HEAD_TAGS_REGION]
    non_head = [t for t in region_tags if t not in HEAD_TAGS_REGION]
    labels: list[str] = []
    if head_labels:
        if len(head_labels) > 1:
            sub = [l.replace("Head (", "").replace(")", "") for l in head_labels]
            labels.append(f"Head ({', '.join(sub)})")
        else:
            labels.append(head_labels[0])
    for t in non_head:
        if t in REGION_MAP:
            labels.append(REGION_MAP[t])
    return len(labels), labels


# ── Synonym dictionary (426 entries) ─────────────────────────────────
SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "abdomen": ["abd_mass", "splenic_mass", "liver_mass", "effusion", "vomiting_gi"],
    "abdominal": ["abd_mass", "splenic_mass", "liver_mass", "effusion", "vomiting_gi"],
    "accidents": ["incontinence"],
    "acl": ["stifle_knee"],
    "acting strange": ["behavior_change", "circling"],
    "acting weird": ["behavior_change", "circling"],
    "addison": ["adrenal_kidney"],
    "adrenal": ["adrenal_kidney", "hypercalcemia"],
    "aggression": ["behavior_change"],
    "aggressive": ["behavior_change"],
    "airway": ["tracheal", "breathing", "resp_distress"],
    "anal": ["anal_sac"],
    "anal gland": ["anal_sac"],
    "anorexia": ["weight_loss", "vomiting_gi"],
    "arched back": ["back_pain"],
    "arthritis": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd"],
    "ascites": ["effusion", "abd_mass"],
    "ataxia": ["hind_weakness", "hemiparesis", "head_tilt", "circling"],
    "ataxic": ["hind_weakness", "hemiparesis", "head_tilt", "circling"],
    "ate something": ["foreign_body", "vomiting_gi"],
    "atrophy": ["muscle_wasting"],
    "back": ["back_pain", "reluctance_jump", "hind_weakness"],
    "back leg": ["hindlimb_lame", "stifle_knee", "hind_weakness"],
    "back legs": ["hindlimb_lame", "stifle_knee", "hind_weakness"],
    "back legs giving out": ["hind_weakness", "paralysis"],
    "balance": ["head_tilt", "circling", "hind_weakness"],
    "belly": ["vomiting_gi", "abd_mass", "splenic_mass", "liver_mass", "pancreatitis", "effusion"],
    "bile acids": ["liver_issue", "liver_shunt"],
    "blockage": ["foreign_body", "vomiting_gi"],
    "blood in urine": ["prostate", "adrenal_kidney"],
    "blood sugar": ["hypoglycemia"],
    "bloody nose": ["nosebleed", "nasal"],
    "boas": ["tracheal", "breathing", "resp_distress"],
    "bone cancer": ["bone_tumor"],
    "bone tumor": ["bone_tumor", "limb_swelling"],
    "brachycephalic": ["tracheal", "breathing"],
    "brain": ["seizures", "head_tilt", "circling", "behavior_change", "hemiparesis"],
    "breathing": ["breathing", "resp_distress", "tracheal", "heart"],
    "bulging disc": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "bulging eye": ["eye_issue"],
    "bump": ["mass_lump", "oral_jaw", "anal_sac", "neck_mass", "facial_swelling"],
    "calcium": ["hypercalcemia"],
    "can't walk": ["paralysis", "hind_weakness"],
    "cancer": ["mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw", "bone_tumor", "anal_sac", "thyroid_mass", "mediastinal", "adrenal_kidney", "neck_mass"],
    "cardiac": ["heart", "resp_distress", "effusion"],
    "ccl": ["stifle_knee"],
    "circling": ["circling", "behavior_change"],
    "collapse": ["hind_weakness", "paralysis", "heart", "resp_distress", "hypoglycemia"],
    "collapsing trachea": ["tracheal", "breathing"],
    "confused": ["circling", "behavior_change"],
    "convulsion": ["seizures"],
    "convulsions": ["seizures"],
    "cough": ["tracheal", "breathing", "heart"],
    "coughing": ["tracheal", "breathing", "heart"],
    "cruciate": ["stifle_knee"],
    "crying": ["back_pain", "neck_pain", "bone_tumor"],
    "cushing": ["adrenal_kidney", "liver_issue"],
    "cushings": ["adrenal_kidney", "liver_issue"],
    "dcm": ["heart", "resp_distress", "effusion"],
    "dementia": ["behavior_change", "circling"],
    "diarrhea": ["chronic_diarrhea", "weight_loss"],
    "difficulty breathing": ["breathing", "resp_distress", "heart"],
    "digit": ["digit_lame"],
    "disc": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "disk": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "dragging": ["paralysis", "hind_weakness"],
    "dysplasia": ["elbow_ocd", "hindlimb_lame", "stifle_knee"],
    "dyspnea": ["breathing", "resp_distress", "heart"],
    "ear": ["ear_issue"],
    "ear infection": ["ear_issue"],
    "effusion": ["effusion", "heart", "abd_mass"],
    "elbow": ["elbow_ocd", "forelimb_lame"],
    "enlarged heart": ["heart", "resp_distress"],
    "epilepsy": ["seizures"],
    "epistaxis": ["nosebleed"],
    "eye": ["eye_issue"],
    "face": ["facial_swelling", "oral_jaw"],
    "facial": ["facial_swelling"],
    "fainting": ["heart", "resp_distress", "hypoglycemia"],
    "falling over": ["head_tilt", "hind_weakness", "paralysis"],
    "fce": ["paralysis", "hind_weakness", "hemiparesis"],
    "fit": ["seizures"],
    "fits": ["seizures"],
    "fluid": ["effusion", "abd_mass", "heart"],
    "foot": ["digit_lame"],
    "foreign body": ["foreign_body", "vomiting_gi"],
    "foreign object": ["foreign_body"],
    "front leg": ["forelimb_lame", "shoulder_pain", "elbow_ocd"],
    "gasping": ["resp_distress", "breathing"],
    "gi": ["vomiting_gi", "foreign_body", "chronic_diarrhea"],
    "glucose": ["hypoglycemia"],
    "gme": ["seizures", "head_tilt", "circling", "behavior_change", "hemiparesis"],
    "growth": ["mass_lump", "abd_mass", "oral_jaw", "anal_sac", "thyroid_mass", "neck_mass"],
    "gum": ["oral_jaw"],
    "hacking": ["tracheal", "breathing"],
    "hcm": ["heart", "resp_distress", "effusion"],
    "head shaking": ["ear_issue"],
    "head tilt": ["head_tilt", "circling"],
    "heart": ["heart", "resp_distress", "effusion"],
    "heart failure": ["heart", "resp_distress", "effusion"],
    "heart murmur": ["heart"],
    "heavy breathing": ["breathing", "resp_distress", "heart"],
    "hemangiosarcoma": ["splenic_mass", "liver_mass", "heart", "abd_mass"],
    "hepatic": ["liver_issue", "liver_mass"],
    "herniated disc": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "high calcium": ["hypercalcemia"],
    "hind leg": ["hindlimb_lame", "stifle_knee", "hind_weakness"],
    "hip": ["hindlimb_lame", "stifle_knee", "hind_weakness"],
    "holding up leg": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "digit_lame"],
    "honking": ["tracheal"],
    "hsa": ["splenic_mass", "liver_mass", "heart", "abd_mass"],
    "hunched": ["back_pain", "reluctance_jump"],
    "hypercalcemia": ["hypercalcemia"],
    "hypoglycemia": ["hypoglycemia"],
    "ibd": ["chronic_diarrhea", "vomiting_gi", "weight_loss"],
    "incontinence": ["incontinence"],
    "insulinoma": ["hypoglycemia", "abd_mass"],
    "ivdd": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "jaundice": ["liver_issue", "liver_shunt"],
    "jaw": ["oral_jaw", "facial_swelling"],
    "joint": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd"],
    "kidney": ["adrenal_kidney"],
    "knee": ["stifle_knee", "hindlimb_lame"],
    "knuckling": ["paralysis", "hind_weakness", "hemiparesis"],
    "labored breathing": ["breathing", "resp_distress", "heart"],
    "lame": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd", "digit_lame"],
    "lameness": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd", "digit_lame"],
    "leaking urine": ["incontinence"],
    "leg pain": ["forelimb_lame", "hindlimb_lame", "bone_tumor"],
    "leg swelling": ["limb_swelling", "bone_tumor"],
    "lethargy": ["weight_loss", "heart", "liver_issue", "hypoglycemia"],
    "limb swelling": ["limb_swelling", "bone_tumor"],
    "limp": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd", "digit_lame"],
    "limping": ["forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd", "digit_lame"],
    "liver": ["liver_issue", "liver_mass", "liver_shunt", "weight_loss"],
    "losing weight": ["weight_loss", "chronic_diarrhea"],
    "loss of balance": ["head_tilt", "circling", "hind_weakness"],
    "low blood sugar": ["hypoglycemia"],
    "lump": ["mass_lump", "abd_mass", "oral_jaw", "anal_sac", "thyroid_mass", "neck_mass", "facial_swelling"],
    "luxating patella": ["stifle_knee"],
    "lymphadenopathy": ["neck_mass", "mediastinal", "abd_mass", "mass_lump"],
    "lymphoma": ["mediastinal", "abd_mass", "splenic_mass", "liver_mass", "neck_mass", "mass_lump"],
    "mass": ["mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw", "anal_sac", "thyroid_mass", "mediastinal", "adrenal_kidney", "neck_mass"],
    "mast cell": ["mass_lump", "splenic_mass", "abd_mass"],
    "meningitis": ["neck_pain", "back_pain", "seizures"],
    "metastasis": ["mass_lump", "mediastinal", "abd_mass"],
    "mouth": ["oral_jaw"],
    "muo": ["seizures", "head_tilt", "circling", "behavior_change", "hemiparesis"],
    "murmur": ["heart"],
    "muscle loss": ["muscle_wasting"],
    "muscle wasting": ["muscle_wasting"],
    "myelopathy": ["paralysis", "hind_weakness", "back_pain"],
    "nasal": ["nasal", "nosebleed"],
    "neck": ["neck_pain", "neck_mass"],
    "neoplasia": ["mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw", "bone_tumor", "anal_sac", "thyroid_mass", "mediastinal", "adrenal_kidney"],
    "nerve": ["back_pain", "neck_pain", "hind_weakness", "paralysis", "hemiparesis"],
    "neuro": ["seizures", "head_tilt", "circling", "behavior_change", "hemiparesis", "back_pain", "neck_pain", "paralysis", "hind_weakness", "incontinence"],
    "neurological": ["seizures", "head_tilt", "circling", "behavior_change", "hemiparesis", "back_pain", "neck_pain", "paralysis", "hind_weakness", "incontinence"],
    "no appetite": ["weight_loss", "vomiting_gi"],
    "nodule": ["mass_lump", "thyroid_mass", "neck_mass"],
    "nose": ["nasal", "nosebleed"],
    "nosebleed": ["nosebleed", "nasal"],
    "not eating": ["weight_loss", "vomiting_gi", "oral_jaw"],
    "nystagmus": ["head_tilt"],
    "obstruction": ["foreign_body", "vomiting_gi"],
    "ocd": ["elbow_ocd"],
    "one sided weakness": ["hemiparesis", "paralysis"],
    "oral": ["oral_jaw"],
    "osteosarcoma": ["bone_tumor"],
    "otitis": ["ear_issue"],
    "otitis interna": ["ear_issue", "head_tilt", "circling"],
    "otitis media": ["ear_issue", "head_tilt"],
    "pacing": ["circling", "behavior_change"],
    "pain": ["back_pain", "neck_pain", "shoulder_pain", "stifle_knee", "bone_tumor"],
    "pancreas": ["pancreatitis", "vomiting_gi"],
    "pancreatitis": ["pancreatitis", "vomiting_gi"],
    "panting": ["breathing", "heart", "resp_distress"],
    "paralysis": ["paralysis", "hind_weakness"],
    "paralyzed": ["paralysis", "hind_weakness"],
    "paraparesis": ["hind_weakness", "paralysis"],
    "paresis": ["hind_weakness", "hemiparesis", "paralysis"],
    "patella": ["stifle_knee"],
    "patellar luxation": ["stifle_knee"],
    "pericardial effusion": ["heart", "effusion"],
    "pinched nerve": ["back_pain", "neck_pain", "hind_weakness", "paralysis"],
    "pleural effusion": ["effusion", "resp_distress", "mediastinal"],
    "portosystemic": ["liver_shunt"],
    "portosystemic shunt": ["liver_shunt", "liver_issue"],
    "prostate": ["prostate", "incontinence"],
    "pss": ["liver_shunt", "liver_issue"],
    "rear weakness": ["hind_weakness", "paralysis"],
    "regurgitation": ["vomiting_gi", "mediastinal"],
    "reluctant to jump": ["reluctance_jump", "back_pain"],
    "respiratory distress": ["resp_distress", "breathing", "heart"],
    "retrobulbar": ["eye_issue"],
    "seizure": ["seizures"],
    "seizures": ["seizures"],
    "shaking": ["seizures"],
    "short of breath": ["breathing", "resp_distress", "heart"],
    "shoulder": ["shoulder_pain", "forelimb_lame"],
    "shunt": ["liver_shunt", "liver_issue"],
    "slipped disc": ["back_pain", "neck_pain", "paralysis", "hind_weakness"],
    "sneezing": ["nasal"],
    "sore": ["back_pain", "neck_pain", "shoulder_pain", "forelimb_lame", "hindlimb_lame"],
    "sore back": ["back_pain", "reluctance_jump"],
    "sore leg": ["forelimb_lame", "hindlimb_lame", "bone_tumor"],
    "sore neck": ["neck_pain"],
    "spinal": ["back_pain", "neck_pain", "hind_weakness", "paralysis", "incontinence", "reluctance_jump", "muscle_wasting"],
    "spine": ["back_pain", "neck_pain", "hind_weakness", "paralysis", "incontinence", "reluctance_jump", "muscle_wasting"],
    "spleen": ["splenic_mass", "abd_mass"],
    "splenic": ["splenic_mass", "abd_mass"],
    "stairs": ["reluctance_jump", "back_pain", "hind_weakness"],
    "stiffness": ["forelimb_lame", "hindlimb_lame", "back_pain"],
    "stifle": ["stifle_knee", "hindlimb_lame"],
    "stomach": ["vomiting_gi", "foreign_body", "abd_mass", "pancreatitis"],
    "stumbling": ["hind_weakness", "hemiparesis", "paralysis", "head_tilt"],
    "swallowed": ["foreign_body", "vomiting_gi"],
    "swelling": ["limb_swelling", "facial_swelling", "bone_tumor", "mass_lump", "abd_mass"],
    "swollen belly": ["abd_mass", "effusion"],
    "swollen eye": ["eye_issue"],
    "swollen face": ["facial_swelling"],
    "swollen leg": ["limb_swelling", "bone_tumor", "hindlimb_lame"],
    "syncope": ["heart", "resp_distress"],
    "tetraparesis": ["hind_weakness", "hemiparesis", "paralysis", "neck_pain"],
    "throwing up": ["vomiting_gi", "foreign_body", "pancreatitis"],
    "thymoma": ["mediastinal"],
    "thyroid": ["thyroid_mass", "neck_mass"],
    "tilting head": ["head_tilt"],
    "toe": ["digit_lame"],
    "torn ligament": ["stifle_knee"],
    "trachea": ["tracheal", "breathing"],
    "tracheal": ["tracheal", "breathing"],
    "tremor": ["seizures"],
    "tremors": ["seizures"],
    "trouble urinating": ["prostate", "incontinence"],
    "tumor": ["mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw", "bone_tumor", "anal_sac", "thyroid_mass", "mediastinal", "adrenal_kidney", "neck_mass"],
    "twitching": ["seizures"],
    "uncoordinated": ["hind_weakness", "hemiparesis", "head_tilt", "circling"],
    "urinary": ["prostate", "incontinence", "adrenal_kidney"],
    "vestibular": ["head_tilt", "circling"],
    "vomit": ["vomiting_gi", "foreign_body", "pancreatitis"],
    "vomiting": ["vomiting_gi", "foreign_body", "pancreatitis"],
    "weak": ["hind_weakness", "hemiparesis", "paralysis"],
    "weakness": ["hind_weakness", "hemiparesis", "paralysis"],
    "weight loss": ["weight_loss", "chronic_diarrhea", "vomiting_gi"],
    "wobbly": ["hind_weakness", "hemiparesis", "head_tilt", "neck_pain"],
    "wobbler": ["neck_pain", "hind_weakness", "hemiparesis"],
    "won't jump": ["reluctance_jump", "back_pain", "hind_weakness"],
    "won't walk": ["paralysis", "hind_weakness", "reluctance_jump"],
    "yelping": ["back_pain", "neck_pain", "bone_tumor"],
}

# ── Search stop words ────────────────────────────────────────────────
SEARCH_STOP_WORDS = {
    "my", "is", "am", "are", "was", "were", "be", "been", "being", "a", "an", "the",
    "in", "on", "at", "to", "for", "of", "with", "and", "or", "but", "not", "no",
    "it", "its", "he", "she", "we", "they", "i", "me", "do", "does", "did",
    "has", "have", "had", "can", "will", "would", "should", "could",
    "dog", "cat", "pet", "puppy", "kitten", "animal", "vet", "doctor",
    "help", "think", "need", "want", "see", "go", "get", "got", "just", "very",
    "so", "if", "up", "out", "about", "like", "been", "having", "going",
}


def search_symptoms(query: str) -> set[str]:
    """Map natural-language symptom description → set of clinical sign IDs."""
    q = query.lower().strip()
    if not q:
        return set()

    matched: set[str] = set()
    words = q.split()
    meaningful = [w for w in words if w not in SEARCH_STOP_WORDS and len(w) >= 3]
    if not meaningful:
        return set()

    # Check synonym dictionary
    for key, symptom_ids in SYMPTOM_SYNONYMS.items():
        key_norm = key.lower()
        if " " in key_norm:
            # Multi-word: check if query contains the full phrase
            if key_norm in q:
                matched.update(symptom_ids)
        else:
            for w in meaningful:
                if key_norm == w or (len(w) >= 4 and key_norm.startswith(w)) or (len(w) >= 4 and w.startswith(key_norm) and len(key_norm) >= 4):
                    matched.update(symptom_ids)

    # Also check sign labels directly
    if meaningful:
        for group in CLINICAL_SIGN_GROUPS:
            for sign in group["signs"]:
                label_norm = sign["label"].lower()
                id_norm = sign["id"].replace("_", " ")
                if all(w in label_norm or w in id_norm for w in meaningful):
                    matched.add(sign["id"])

    return matched


# ── Clinical Rationale ───────────────────────────────────────────────

def _get_clinical_rationale(tags: list[str], modality: str) -> dict[str, str]:
    neuro = {"back_pain", "hind_weakness", "paralysis", "neck_pain", "seizures", "head_tilt", "circling", "incontinence", "hemiparesis", "behavior_change", "muscle_wasting", "reluctance_jump"}
    mass = {"mass_lump", "abd_mass", "splenic_mass", "liver_mass", "oral_jaw", "neck_mass", "bone_tumor", "nosebleed", "eye_issue", "anal_sac", "thyroid_mass", "mediastinal", "adrenal_kidney", "facial_swelling"}
    msk = {"forelimb_lame", "hindlimb_lame", "shoulder_pain", "stifle_knee", "elbow_ocd"}
    resp = {"nasal", "breathing", "tracheal", "resp_distress"}
    cardiac = {"heart"}
    gi = {"vomiting_gi", "liver_issue", "weight_loss", "foreign_body", "pancreatitis", "chronic_diarrhea", "effusion", "prostate", "liver_shunt"}

    tag_set = set(tags)
    if tag_set & neuro:
        return {"title": "Clinical Rationale: Why MRI", "message": "MRI is the only modality capable of directly visualizing the spinal cord, nerve roots, intervertebral discs, and intracranial structures with sufficient soft tissue contrast to differentiate compression, inflammation, neoplasia, and vascular events. For surgical candidates, MRI localizes the lesion precisely and characterizes severity, directly influencing surgical approach and prognosis."}
    if tag_set & mass:
        return {"title": "Clinical Rationale: Why CT Staging", "message": "CT provides comprehensive oncologic staging in a single scan — evaluating the primary mass, regional lymph nodes, and distant metastatic sites (lungs, liver, spleen) simultaneously. This is essential for accurate TNM staging, surgical planning, and prognostication."}
    if tag_set & msk:
        return {"title": "Clinical Rationale: Why Advanced Imaging", "message": "Radiographs evaluate bone but cannot visualize ligaments, menisci, tendons, cartilage, or joint effusion with diagnostic accuracy. MRI provides definitive evaluation of soft tissue structures within and around joints. For elbow dysplasia and bone lesions, CT provides superior osseous detail."}
    if tag_set & resp:
        return {"title": "Clinical Rationale: Why CT", "message": "CT provides cross-sectional evaluation of the nasal passages, paranasal sinuses, cribriform plate, trachea, and pulmonary parenchyma with far greater sensitivity than radiographs. For nasal disease, CT is the accepted gold standard."}
    if tag_set & cardiac:
        return {"title": "Clinical Rationale: Why Echocardiography", "message": "Echocardiography provides real-time evaluation of cardiac chamber dimensions, wall motion, valve morphology and function, and hemodynamics via Doppler. It is the gold standard for differentiating and grading valvular disease, cardiomyopathy, pericardial effusion, and congenital defects."}
    if tag_set & gi:
        return {"title": "Clinical Rationale: Why Abdominal Imaging", "message": "Abdominal ultrasound provides real-time, multiplanar evaluation of all abdominal organs, mesenteric lymph nodes, and vascular structures without general anesthesia. For portosystemic shunts, CT angiography is the gold standard for definitive identification and surgical planning."}
    return {"title": "Clinical Rationale", "message": "Advanced imaging provides diagnostic information beyond the capability of radiographs, enabling definitive diagnosis and targeted treatment planning. Each study is interpreted on-site by a board-certified veterinary radiologist."}


# ── Output dataclass ─────────────────────────────────────────────────

@dataclass
class DualRec:
    modality: str = ""
    contrast: bool = False
    sites: int = 0
    sites_max: int = 0
    regions: list[str] = field(default_factory=list)
    notes: str = ""
    price_min: int = 0
    price_max: int = 0

    def to_dict(self) -> dict:
        return {
            "modality": self.modality,
            "contrast": self.contrast,
            "sites": self.sites,
            "sites_max": self.sites_max,
            "regions": self.regions,
            "notes": self.notes,
            "price_range": f"${self.price_min:,} – ${self.price_max:,}" if self.price_min != self.price_max else f"${self.price_min:,}",
        }


@dataclass
class Recommendation:
    modality: str = ""
    contrast: bool = False
    sites: int = 0
    sites_max: int = 0
    regions: list[str] = field(default_factory=list)
    notes: str = ""
    may_convert: str = ""
    complex_alert: str = ""
    price_min: int = 0
    price_max: int = 0
    stat_fee: int = 0
    bloodwork_text: str = ""
    bloodwork_cost: str = ""
    duration: str = ""
    urgency: str = "standard"
    included: list[str] = field(default_factory=list)
    breed_alert: str = ""
    rationale: dict[str, str] = field(default_factory=dict)
    dual_rec: DualRec | None = None

    def to_dict(self) -> dict:
        d: dict = {
            "modality": self.modality,
            "contrast": self.contrast,
            "sites": self.sites,
            "regions": self.regions,
            "notes": self.notes,
            "price_range": f"${self.price_min:,} – ${self.price_max:,}" if self.price_min != self.price_max else f"${self.price_min:,}",
            "price_min": self.price_min,
            "price_max": self.price_max,
            "bloodwork": self.bloodwork_text,
            "duration": self.duration,
            "urgency": self.urgency,
            "included_in_price": self.included,
            "clinical_rationale": self.rationale,
        }
        if self.sites_max > 0 and self.sites_max != self.sites:
            d["sites_range"] = f"{self.sites}–{self.sites_max}"
        if self.stat_fee > 0:
            d["stat_fee"] = self.stat_fee
        if self.bloodwork_cost:
            d["bloodwork_notes"] = self.bloodwork_cost
        if self.breed_alert:
            d["breed_alert"] = self.breed_alert
        if self.complex_alert:
            d["complex_alert"] = self.complex_alert
        if self.may_convert:
            d["may_convert_to"] = self.may_convert
        if self.dual_rec:
            d["dual_modality_recommendation"] = self.dual_rec.to_dict()
        return d


# ── Main recommendation engine ───────────────────────────────────────

def get_recommendation(
    tags: list[str],
    breed: str = "",
    species: str = "dog",
    urgency: str = "standard",
    bilateral: bool = False,
    body_regions: list[str] | None = None,
) -> Recommendation:
    """Generate imaging recommendation from clinical sign tags."""
    if not tags:
        return Recommendation(urgency=urgency)

    body_regions = body_regions or []
    is_wobbler = _breed_match(breed, WOBBLER_BREEDS)
    is_ivdd = _breed_match(breed, IVDD_BREEDS)
    is_brachy = _breed_match(breed, BRACHY_BREEDS)
    is_small = _breed_match(breed, SMALL_BREEDS)

    modality = ""
    sites = 1
    sites_max = 0
    regions: list[str] = []
    notes = ""
    contrast = False
    may_convert = ""
    complex_alert = ""
    breed_alert = ""

    # Breed alert
    if is_wobbler:
        breed_alert = "Wobbler-predisposed breed — cervical spine evaluation recommended."
    elif is_ivdd:
        breed_alert = "IVDD-predisposed breed — high index of suspicion for disc disease."
    elif is_brachy:
        breed_alert = "Brachycephalic breed — airway and ear pathology predisposition."
    elif is_small:
        breed_alert = "Small breed — consider portosystemic shunt if liver signs present."

    tag_set = set(tags)
    has_neuro = bool(tag_set & NEURO_TAGS)
    has_msk = bool(tag_set & MSK_TAGS)
    has_mass = bool(tag_set & MASS_TAGS)
    has_metabolic = bool(tag_set & METABOLIC_TAGS)
    pathway_count = sum([has_neuro, has_msk, has_mass, has_metabolic])
    if pathway_count >= 2:
        complex_alert = "Multi-pathway case detected. Our radiologist will confirm the final imaging protocol and may adjust regions based on clinical history."

    # ── PATHWAY A: Neurological / Spinal ──
    if tag_set & {"back_pain", "hind_weakness", "paralysis", "reluctance_jump", "muscle_wasting"}:
        modality = "MRI"
        if is_wobbler:
            sites = 2; regions = ["T-L spine", "C-spine"]
            notes = "Wobbler-predisposed breed — cervical spine included per protocol."
        else:
            sites = 1; sites_max = 2; regions = ["T-L spine", "+/- L-S or C-spine"]
            notes = "Standard spinal MRI. Radiologist extends to additional region based on clinical localization and initial findings."
        if is_ivdd:
            notes += " IVDD-predisposed breed — high index of suspicion for disc extrusion/protrusion."
    elif "neck_pain" in tag_set:
        modality = "MRI"; sites = 2; regions = ["C-spine", "T-L spine"]
        notes = "Cervical pain — primary C-spine with T-L to rule out multi-level disease."
    elif "seizures" in tag_set or "behavior_change" in tag_set:
        modality = "MRI"; sites = 1; regions = ["Head (brain)"]
        notes = "Brain MRI — R/O structural epilepsy, neoplasia, encephalitis." if "seizures" in tag_set else "Brain MRI — R/O intracranial neoplasia, inflammatory CNS disease."
    elif tag_set & {"head_tilt", "circling"}:
        if "ear_issue" in tag_set:
            modality = "MRI"; sites = 1; regions = ["Head"]
            notes = "Vestibular signs with otitis history — MRI for otitis interna/media extension, brainstem involvement."
        else:
            modality = "MRI"; sites = 1; regions = ["Head"]
            notes = "Vestibular signs — MRI to differentiate central vs. peripheral vestibular disease."
    elif "hemiparesis" in tag_set:
        modality = "MRI"; sites = 2; regions = ["Head (brain)", "C-spine"]
        notes = "One-sided weakness — rule out brain or cervical lesion."
    elif "incontinence" in tag_set:
        modality = "MRI"; sites = 2; regions = ["L-S spine", "T-L spine"]
        notes = "LMN bladder — L-S primary, T-L to assess for ascending disease."
    # ── PATHWAY B: MSK / Lameness ──
    elif tag_set & {"forelimb_lame", "shoulder_pain"}:
        modality = "MRI"; sites = 2; sites_max = 3; regions = ["Shoulder", "Elbow", "+/- C-spine"]
        notes = "Thoracic limb lameness — MRI evaluates soft tissue. C-spine added if nerve root involvement suspected."
        if "neck_pain" in tag_set:
            regions = ["C-spine", "Shoulder", "Elbow"]
            notes = "Cervical pain with thoracic limb lameness — R/O disc herniation with nerve root compression."
    elif "stifle_knee" in tag_set:
        modality = "MRI"; sites = 2; regions = ["Stifle", "Pelvis"]
        notes = "Stifle MRI — evaluates cruciate ligaments, menisci, cartilage, joint effusion."
    elif "hindlimb_lame" in tag_set:
        modality = "MRI"; sites = 2; regions = ["Hip / stifle", "L-S spine"]
        notes = "Pelvic limb lameness — MRI differentiates joint vs. spinal origin."
    elif "digit_lame" in tag_set:
        modality = "CT"; sites = 1; regions = ["Affected digit / limb"]
        notes = "CT — superior osseous detail for phalangeal fractures, P3 lysis, nail bed neoplasia."
    elif "elbow_ocd" in tag_set:
        modality = "CT"; sites = 2; regions = ["Elbows (bilateral)"]
        notes = "CT is gold standard for elbow dysplasia evaluation — FCP, OCD, UAP, incongruity."
    elif "bone_tumor" in tag_set:
        modality = "CT"; sites = 2; sites_max = 3; contrast = True
        regions = ["Affected limb", "Thorax", "+/- Abdomen"]
        notes = "Appendicular bone lesion staging — CT maps lesion extent and screens for pulmonary metastasis."
    # ── PATHWAY C: Masses / Cancer ──
    elif tag_set & {"mass_lump", "abd_mass", "splenic_mass", "liver_mass", "adrenal_kidney"}:
        modality = "CT"; sites = 2; contrast = True; regions = ["Thorax", "Abdomen"]
        notes = "CT staging — evaluates primary mass, regional LN, and distant metastatic sites."
        if "splenic_mass" in tag_set:
            notes = "Splenic mass — CT for hepatic/pulmonary mets screening and surgical planning."
        if "liver_mass" in tag_set:
            notes = "Hepatic mass — CT angiography for vascular mapping and mets screening."
    elif "anal_sac" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Abdomen / pelvis", "Thorax"]
        notes = "AGASACA staging — sublumbar LN assessment + thoracic mets screening."
    elif "thyroid_mass" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Neck", "Thorax"]
        notes = "Thyroid staging — vascular invasion assessment + thoracic mets."
    elif "mediastinal" in tag_set:
        modality = "CT"; sites = 1; sites_max = 2; contrast = True
        regions = ["Thorax", "+/- Abdomen"]
        notes = "Mediastinal mass characterization and CT-guided biopsy planning."
    elif tag_set & {"nasal", "nosebleed", "facial_swelling"}:
        modality = "CT"; sites = 1; sites_max = 2; contrast = True
        regions = ["Head", "+/- Thorax"]
        notes = "CT gold standard for nasal disease — bone destruction, cribriform plate integrity, soft tissue extent."
    elif "oral_jaw" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Head", "Thorax"]
        notes = "Oral/mandibular mass — CT for bone involvement, tumor margins, pulmonary staging."
    elif "ear_issue" in tag_set:
        if has_neuro:
            modality = "MRI"; sites = 1; regions = ["Head"]
            notes = "Otitis with neurological signs — MRI for otitis interna/brainstem extension."
        else:
            modality = "CT"; sites = 1; regions = ["Head"]
            notes = "CT — bulla evaluation, ear canal assessment, surgical planning."
            if is_brachy:
                notes += " Brachycephalic breed — increased incidence of otitis media."
    elif "eye_issue" in tag_set:
        modality = "CT"; sites = 1; sites_max = 2; contrast = True
        regions = ["Head", "+/- Thorax"]
        notes = "Retrobulbar/orbital CT — evaluates space-occupying lesions, bony orbit."
    elif "neck_mass" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Head / neck", "Thorax"]
        notes = "Cervical mass staging — vascular relationships + thoracic mets."
    # ── PATHWAY D: Abdominal / GI ──
    elif tag_set & {"vomiting_gi", "pancreatitis", "chronic_diarrhea", "prostate"}:
        modality = "Ultrasound"; sites = 1; regions = ["Abdomen"]
        if "pancreatitis" in tag_set:
            notes = "Abdominal US — pancreatic evaluation, peripancreatic fat, effusion."
        else:
            notes = "Abdominal US — comprehensive organ evaluation without GA."
    elif "foreign_body" in tag_set:
        modality = "Ultrasound"; sites = 1; regions = ["Abdomen"]
        notes = "US first-line for GI foreign body — visualizes obstruction, plication, bowel wall changes."
        may_convert = "If US inconclusive, CT recommended for definitive localization."
    elif "liver_issue" in tag_set or "liver_shunt" in tag_set:
        if is_small or "liver_shunt" in tag_set:
            modality = "CT"; sites = 1; contrast = True; regions = ["Abdomen (CT angiogram)"]
            notes = "CT angiography — gold standard for PSS identification and surgical planning."
        else:
            modality = "Ultrasound"; sites = 1; regions = ["Abdomen"]
            notes = "Abdominal US — hepatic parenchyma, biliary system, portal vasculature."
            may_convert = "If mass or vascular abnormality identified, CT recommended for mapping."
    elif "effusion" in tag_set:
        modality = "Ultrasound"; sites = 1; regions = ["Abdomen"]
        notes = "US for effusion characterization and US-guided abdominocentesis if indicated."
    elif "weight_loss" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Abdomen", "Thorax"]
        notes = "CT for comprehensive assessment of weight loss with elevated liver values."
    # ── PATHWAY E: Specialty ──
    elif "heart" in tag_set:
        modality = "Echocardiogram"; sites = 1; regions = ["Cardiac"]
        notes = "Echocardiogram. No anesthesia needed."
    elif tag_set & {"breathing", "tracheal", "resp_distress"}:
        modality = "CT"; sites = 1; sites_max = 2; regions = ["Thorax", "+/- Neck/head"]
        notes = "CT for airway/respiratory evaluation."
        if "tracheal" in tag_set:
            notes = "CT dynamic study for tracheal collapse evaluation."; contrast = False
        if "resp_distress" in tag_set:
            notes = "CT thorax — rule out diaphragmatic hernia, effusion, mass."
    elif "limb_swelling" in tag_set:
        modality = "CT"; sites = 2; sites_max = 3
        regions = ["Affected limb", "Thorax", "+/- Abdomen"]
        notes = "CT with possible lymphangiogram."
    # ── PATHWAY F: Metabolic ──
    elif "hypoglycemia" in tag_set:
        modality = "CT"; sites = 2; sites_max = 3; contrast = True
        regions = ["Abdomen", "Thorax", "+/- Head"]
        notes = "Hypoglycemia with neuro signs — R/O insulinoma. CT for staging."
    elif "hypercalcemia" in tag_set:
        modality = "CT"; sites = 2; contrast = True; regions = ["Thorax", "Abdomen"]
        notes = "Hypercalcemia — R/O lymphoma, anal sac adenocarcinoma. CT for staging."
    # ── Fallback ──
    else:
        modality = "MRI"; sites = 1; regions = ["To be determined by radiologist"]
        notes = "Insufficient symptom data — confirm with radiologist."

    # ── Body region override ──
    if body_regions:
        count, labels = calc_sites_from_regions(body_regions)
        sites = count; sites_max = 0; regions = labels

    # ── Bilateral modifier ──
    if bilateral:
        bilateral_targets = {"stifle_knee", "shoulder_pain", "elbow_ocd", "forelimb_lame", "hindlimb_lame"}
        if tag_set & bilateral_targets:
            sites += 1
            if sites_max > 0:
                sites_max += 1
            notes += " Bilateral modifier applied — imaging both sides."

    # ── Dual-modality for complex cases ──
    dual_rec: DualRec | None = None
    if complex_alert and pathway_count >= 2:
        neuro_mod = "MRI" if has_neuro else None
        if has_msk:
            msk_mod = "CT" if tag_set & {"digit_lame", "elbow_ocd", "bone_tumor"} else "MRI"
        else:
            msk_mod = None
        mass_mod = "CT" if (has_mass or has_metabolic) else None
        mod_set = [m for m in [neuro_mod, msk_mod, mass_mod] if m]
        uniq = list(set(mod_set))
        if len(uniq) > 1 and "MRI" in mod_set and "CT" in mod_set:
            sec = DualRec(modality="CT", contrast=True)
            if has_mass:
                if tag_set & {"mass_lump", "abd_mass", "splenic_mass", "liver_mass", "adrenal_kidney"}:
                    sec.sites = 2; sec.regions = ["Thorax", "Abdomen"]; sec.notes = "CT staging — thorax + abdomen."
                elif "anal_sac" in tag_set:
                    sec.sites = 2; sec.regions = ["Abdomen / pelvis", "Thorax"]; sec.notes = "AGASACA staging."
                elif tag_set & {"nasal", "nosebleed", "facial_swelling", "oral_jaw"}:
                    sec.sites = 2; sec.regions = ["Head", "Thorax"]; sec.notes = "CT staging for head mass."
                else:
                    sec.sites = 2; sec.regions = ["Thorax", "Abdomen"]; sec.notes = "CT staging."
            if has_metabolic and sec.sites == 0:
                if "hypoglycemia" in tag_set:
                    sec.sites = 2; sec.sites_max = 3; sec.regions = ["Abdomen", "Thorax", "+/- Head"]; sec.notes = "CT metabolic workup."
                else:
                    sec.sites = 2; sec.regions = ["Thorax", "Abdomen"]; sec.notes = "CT metabolic screening."
            if has_msk and tag_set & {"bone_tumor", "digit_lame", "elbow_ocd"} and sec.sites == 0:
                sec.sites = 2; sec.sites_max = 3; sec.regions = ["Affected limb", "Thorax"]; sec.notes = "CT bone detail + staging."
            if sec.sites > 0:
                sec_base = PRICING["ct_con"] if sec.contrast else PRICING["ct"]
                sec_max_sites = sec.sites_max if sec.sites_max > 0 else sec.sites
                sec.price_min = sec_base
                sec.price_max = sec_base + (sec_max_sites - 1) * PRICING["ct_add"]
                dual_rec = sec
                complex_alert = "Multi-pathway case — may benefit from both MRI and CT. Both can be performed same-day under single anesthetic event."

    # ── Pricing ──
    effective_max = sites_max if sites_max > 0 else sites
    price_min = 0
    price_max = 0
    bloodwork_text = ""
    bloodwork_cost = ""

    if "MRI" in modality:
        price_min = PRICING["mri_pkg"]
        price_max = PRICING["mri_pkg"] + (effective_max - 1) * PRICING["mri_add"]
        bloodwork_text = "Required — CBC + Chem within 30 days"
        bloodwork_cost = f"MRI Package (${PRICING['mri_pkg']:,}) includes bloodwork. If patient has qualifying labs on file, base MRI price (${PRICING['mri1']:,}) applies."
    elif "CT" in modality:
        ct_base = PRICING["ct_con"] if contrast else PRICING["ct"]
        price_min = ct_base
        price_max = ct_base + (effective_max - 1) * PRICING["ct_add"]
        bloodwork_text = "Required — Chem 10 minimum within 30 days"
        bloodwork_cost = f"In-house bloodwork available (${PRICING['bw']}). If patient has qualifying labs, send with referral."
    elif "Ultrasound" in modality:
        price_min = PRICING["us"]
        price_max = PRICING["us"] + (sites - 1) * PRICING["us_add"]
        bloodwork_text = "Not required — light sedation / no GA"
        bloodwork_cost = ""
    elif "Echocardiogram" in modality:
        price_min = PRICING["echo"]
        price_max = PRICING["echo"]
        if tag_set & {"vomiting_gi", "liver_issue"}:
            price_min = PRICING["echo_us"]; price_max = PRICING["echo_us"]
            regions.append("Abdomen"); sites = 2
            modality = "Echo + Abdominal US"
            notes = "Combo pricing — both studies, no GA required."
        bloodwork_text = "Not required — no GA"
        bloodwork_cost = ""

    # ── STAT fee ──
    stat_fee = 0
    if urgency == "stat":
        if "MRI" in modality:
            stat_fee = PRICING["stat_mri"]
        elif "CT" in modality:
            stat_fee = PRICING["stat_ct"]
        else:
            stat_fee = PRICING["stat_us"]
        price_min += stat_fee
        price_max += stat_fee

    # ── Included in price ──
    included: list[str] = []
    if "MRI" in modality:
        included = ["3T MRI", "General anesthesia + monitoring", "IV catheter + fluids", "DACVR on-site interpretation", "Direct call to rDVM same day", "Written report within 24 hrs", "Same-day discharge"]
    elif "CT" in modality:
        included = ["128-slice CT", "IV contrast study" if contrast else "Non-contrast", "General anesthesia + monitoring", "DACVR on-site interpretation", "Direct call to rDVM same day", "Written report within 24 hrs", "Same-day discharge"]
    elif "Ultrasound" in modality:
        included = ["Complete abdominal US", "Light sedation PRN", "DACVR on-site", "Report within 24 hrs", "30–60 min appointment", "No general anesthesia"]
    elif "Echo" in modality:
        included = ["Full echocardiogram", "DACVR + cardiologist interpretation", "Report within 24 hrs", "No sedation required", "30–60 min appointment"]

    # ── Duration ──
    if "MRI" in modality:
        duration = "2–4 hours (scan + recovery)"
    elif "CT" in modality:
        duration = "1.5–2.5 hours"
    else:
        duration = "30–60 minutes"

    rationale = _get_clinical_rationale(tags, modality)

    return Recommendation(
        modality=modality, contrast=contrast, sites=sites, sites_max=sites_max,
        regions=regions, notes=notes, may_convert=may_convert, complex_alert=complex_alert,
        price_min=price_min, price_max=price_max, stat_fee=stat_fee,
        bloodwork_text=bloodwork_text, bloodwork_cost=bloodwork_cost,
        duration=duration, urgency=urgency, included=included,
        breed_alert=breed_alert, rationale=rationale, dual_rec=dual_rec,
    )


def list_available_symptoms() -> list[dict]:
    """Return all clinical sign groups with their signs for tool discovery."""
    return [
        {
            "group": g["label"],
            "emoji": g["emoji"],
            "signs": [{"id": s["id"], "label": s["label"]} for s in g["signs"]],
        }
        for g in CLINICAL_SIGN_GROUPS
    ]
