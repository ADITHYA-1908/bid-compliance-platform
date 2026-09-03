"""
Deterministic Mock Fixtures for Part 5B, 5C, 5D & 5E Verification Adapters
Contains synthetic, clearly designated mock registry records for:
- GST, PAN, Udyam MSME (Part 5B)
- MCA, Startup India, NSIC, EPFO, ESIC (Part 5C)
- OEM Authorization, Local Content, BIS, DPIIT (Part 5D)
- Blacklisting, Debarment (Part 5E)
These fixtures provide deterministic results without calling external government APIs.
"""

from typing import Any, Dict


# ---------------------------------------------------------------------------
# Synthetic Mock GST Registry Fixtures (Part 5B)
# ---------------------------------------------------------------------------
MOCK_GST_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 0. BidVerify AI Demo GSTIN
    "33BCDEF2345G1Z5": {
        "status": "VERIFIED",
        "gstin": "33BCDEF2345G1Z5",
        "legal_name": "Example Test Technologies Pvt. Ltd.",
        "trade_name": "Example Test Technologies",
        "registration_date": "2024-04-01",
        "taxpayer_type": "Regular",
        "gst_status": "ACTIVE",
        "state_code": "33",
        "state": "Tamil Nadu",
        "address": "Synthetic Demo Address, Tamil Nadu",
        "nature_of_business": ["IT Solutions", "Hardware Supply"],
    },
    # 1. Standard Active Matching GSTINs
    "33ABCDE1234F1Z5": {
        "status": "VERIFIED",
        "gstin": "33ABCDE1234F1Z5",
        "legal_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "trade_name": "TECHFLOW INDIA",
        "registration_date": "2018-07-01",
        "taxpayer_type": "Regular",
        "gst_status": "ACTIVE",
        "state_code": "33",
        "state": "Tamil Nadu",
        "address": "123 Anna Salai, Chennai, Tamil Nadu - 600002",
        "nature_of_business": ["Services", "IT Solutions"],
    },
    "07AAAAA0000A1Z5": {
        "status": "VERIFIED",
        "gstin": "07AAAAA0000A1Z5",
        "legal_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "trade_name": "ALPHA SERVICES",
        "registration_date": "2017-09-15",
        "taxpayer_type": "Regular",
        "gst_status": "ACTIVE",
        "state_code": "07",
        "state": "Delhi",
        "address": "45 Connaught Place, New Delhi - 110001",
        "nature_of_business": ["Supplier", "Government Procurement"],
    },
    "29ABCDE1234F1Z5": {
        "status": "VERIFIED",
        "gstin": "29ABCDE1234F1Z5",
        "legal_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "trade_name": "INNOVATIVE SYSTEMS",
        "registration_date": "2019-04-10",
        "taxpayer_type": "Regular",
        "gst_status": "ACTIVE",
        "state_code": "29",
        "state": "Karnataka",
        "address": "77 Electronics City, Bengaluru, Karnataka - 560100",
        "nature_of_business": ["Hardware", "OEM Manufacturing"],
    },

    # 2. Cancelled / Inactive GSTIN in Registry
    "33ABCDE1234F1Z9": {
        "status": "VERIFIED",
        "gstin": "33ABCDE1234F1Z9",
        "legal_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "trade_name": "DORMANT TECH SERVICES",
        "registration_date": "2019-01-10",
        "taxpayer_type": "Regular",
        "gst_status": "CANCELLED",
        "cancellation_date": "2023-01-10",
        "state_code": "33",
        "state": "Tamil Nadu",
        "address": "123 Anna Salai, Chennai, Tamil Nadu - 600002",
        "reason": "GSTIN registration has been cancelled by tax authorities.",
    },

    # 3. Simulated Provider Outage Identifier
    "27UNAVA9999A1Z1": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock GST Registry service is experiencing a scheduled maintenance window.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock PAN Registry Fixtures (Part 5B)
# ---------------------------------------------------------------------------
MOCK_PAN_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Standard Valid PANs
    "ABCDE1234F": {
        "status": "VERIFIED",
        "pan_number": "ABCDE1234F",
        "name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "entity_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "pan_category": "Company",
        "pan_status": "ACTIVE",
        "issuance_date": "2015-05-20",
        "aadhaar_seeding_status": "NOT_APPLICABLE",
    },
    "AAAAA0000A": {
        "status": "VERIFIED",
        "pan_number": "AAAAA0000A",
        "name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "entity_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "pan_category": "Company",
        "pan_status": "ACTIVE",
        "issuance_date": "2012-08-11",
        "aadhaar_seeding_status": "NOT_APPLICABLE",
    },
    "AABCP1234D": {
        "status": "VERIFIED",
        "pan_number": "AABCP1234D",
        "name": "RAJESH KUMAR SHARMA",
        "entity_name": "RAJESH KUMAR SHARMA",
        "pan_category": "Individual / Proprietorship",
        "pan_status": "ACTIVE",
        "issuance_date": "2010-01-15",
        "aadhaar_seeding_status": "LINKED",
    },

    # 2. Inactive / Deactivated PAN in Registry
    "ABCDE9999X": {
        "status": "VERIFIED",
        "pan_number": "ABCDE9999X",
        "name": "DEACTIVATED ENTITY HOLDINGS",
        "entity_name": "DEACTIVATED ENTITY HOLDINGS",
        "pan_category": "Company",
        "pan_status": "INACTIVE",
        "reason": "PAN is marked inoperative or deactivated in the registry.",
    },

    # 3. Simulated Outage PAN
    "UNAVA9999X": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock Income Tax PAN verification registry is temporarily unreachable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock Udyam MSME Registry Fixtures (Part 5B)
# ---------------------------------------------------------------------------
MOCK_UDYAM_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Standard Valid Udyam Registrations
    "UDYAM-TN-01-0012345": {
        "status": "VERIFIED",
        "udyam_registration_number": "UDYAM-TN-01-0012345",
        "udyam_number": "UDYAM-TN-01-0012345",
        "enterprise_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "enterprise_classification": "Micro",
        "enterprise_type": "Micro",
        "major_activity": "Services",
        "organization_type": "Private Limited Company",
        "incorporation_date": "2018-06-15",
        "registration_date": "2020-07-10",
        "udyam_registration_date": "2020-07-10",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "nic_code": "62011",
        "dic_name": "CHENNAI",
        "is_active": True,
    },
    "UDYAM-KR-03-0098765": {
        "status": "VERIFIED",
        "udyam_registration_number": "UDYAM-KR-03-0098765",
        "udyam_number": "UDYAM-KR-03-0098765",
        "enterprise_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "enterprise_classification": "Small",
        "enterprise_type": "Small",
        "major_activity": "Manufacturing",
        "organization_type": "Private Limited Company",
        "incorporation_date": "2019-03-01",
        "registration_date": "2020-08-22",
        "udyam_registration_date": "2020-08-22",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "nic_code": "26201",
        "dic_name": "BENGALURU URBAN",
        "is_active": True,
    },
    "UDYAM-MH-01-0044556": {
        "status": "VERIFIED",
        "udyam_registration_number": "UDYAM-MH-01-0044556",
        "udyam_number": "UDYAM-MH-01-0044556",
        "enterprise_name": "WESTERN INFOTECH SOLUTIONS",
        "enterprise_classification": "Medium",
        "enterprise_type": "Medium",
        "major_activity": "Services",
        "organization_type": "Partnership",
        "incorporation_date": "2016-11-20",
        "registration_date": "2020-09-05",
        "udyam_registration_date": "2020-09-05",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "nic_code": "62099",
        "dic_name": "MUMBAI",
        "is_active": True,
    },

    # 2. Cancelled / Revoked Udyam in Registry
    "UDYAM-DL-00-9999999": {
        "status": "VERIFIED",
        "udyam_registration_number": "UDYAM-DL-00-9999999",
        "udyam_number": "UDYAM-DL-00-9999999",
        "enterprise_name": "NORTHERN DIGITAL NETWORKS",
        "enterprise_classification": "Micro",
        "enterprise_type": "Micro",
        "major_activity": "Services",
        "organization_type": "Proprietorship",
        "registration_date": "2021-03-15",
        "is_active": False,
        "reason": "MSME registration certificate has been revoked by MSME DIC.",
    },

    # 3. Simulated Outage Udyam
    "UDYAM-XX-00-0000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock MSME Udyam verification endpoint timed out.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock MCA Registry Fixtures (Part 5C)
# ---------------------------------------------------------------------------
MOCK_MCA_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Companies
    "U72900TN2018PTC123456": {
        "status": "VERIFIED",
        "cin": "U72900TN2018PTC123456",
        "company_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "company_status": "ACTIVE",
        "company_type": "Private Limited Company",
        "company_category": "Company limited by shares",
        "company_subcategory": "Non-govt company",
        "class_of_company": "Private",
        "date_of_incorporation": "2018-06-15",
        "registered_office_address": "123 Anna Salai, Chennai, Tamil Nadu - 600002",
        "registered_office_state": "Tamil Nadu",
        "roc": "RoC-Chennai",
        "authorized_capital": 5000000.0,
        "paid_up_capital": 2500000.0,
    },
    "L72900DL2012PLC000001": {
        "status": "VERIFIED",
        "cin": "L72900DL2012PLC000001",
        "company_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "company_status": "ACTIVE",
        "company_type": "Public Limited Company",
        "company_category": "Company limited by shares",
        "company_subcategory": "Non-govt company",
        "class_of_company": "Public",
        "date_of_incorporation": "2012-08-11",
        "registered_office_address": "45 Connaught Place, New Delhi - 110001",
        "registered_office_state": "Delhi",
        "roc": "RoC-Delhi",
        "authorized_capital": 50000000.0,
        "paid_up_capital": 30000000.0,
    },
    "AAA-1234": {
        "status": "VERIFIED",
        "llpin": "AAA-1234",
        "company_name": "INNOVATIVE SYSTEMS LLP",
        "company_status": "ACTIVE",
        "company_type": "Limited Liability Partnership",
        "date_of_incorporation": "2019-04-10",
        "registered_office_state": "Karnataka",
        "registered_office_address": "77 Electronics City, Bengaluru, Karnataka - 560100",
        "roc": "RoC-Bangalore",
    },

    # 2. Dormant / Strike-Off Companies in Registry
    "U72900TN2015PTC999999": {
        "status": "VERIFIED",
        "cin": "U72900TN2015PTC999999",
        "company_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "company_status": "DORMANT",
        "company_type": "Private Limited Company",
        "date_of_incorporation": "2015-01-20",
        "registered_office_state": "Tamil Nadu",
        "roc": "RoC-Chennai",
        "reason": "Company status is recorded as DORMANT under Section 455 of the Companies Act.",
    },

    # 3. Simulated Outage CIN (21 characters)
    "U99999XX0000UNA000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock MCA V3 Registry endpoint is temporarily unavailable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock Startup India / DPIIT Registry Fixtures (Part 5C)
# ---------------------------------------------------------------------------
MOCK_STARTUP_INDIA_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Recognized Startups
    "DIPP123456": {
        "status": "VERIFIED",
        "recognition_number": "DIPP123456",
        "startup_india_number": "DIPP123456",
        "entity_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "recognition_date": "2021-03-10",
        "valid_until": "2031-03-09",
        "startup_status": "RECOGNIZED",
        "sector": "IT Services & Cloud Computing",
        "state": "Tamil Nadu",
        "dpiit_certificate_url": "https://mock.startupindia.gov.in/cert/DIPP123456.pdf",
    },
    "DIPP654321": {
        "status": "VERIFIED",
        "recognition_number": "DIPP654321",
        "startup_india_number": "DIPP654321",
        "entity_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "recognition_date": "2022-07-15",
        "valid_until": "2032-07-14",
        "startup_status": "RECOGNIZED",
        "sector": "Hardware & IoT",
        "state": "Karnataka",
    },

    # 2. Expired / Inactive Recognition in Registry
    "DIPP987654": {
        "status": "VERIFIED",
        "recognition_number": "DIPP987654",
        "startup_india_number": "DIPP987654",
        "entity_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "recognition_date": "2014-01-10",
        "valid_until": "2024-01-09",
        "startup_status": "EXPIRED",
        "sector": "E-Commerce",
        "reason": "10-year startup recognition eligibility window has elapsed.",
    },

    # 3. Simulated Outage Recognition
    "DIPP000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock Startup India DPIIT portal is unreachable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock NSIC Registry Fixtures (Part 5C)
# ---------------------------------------------------------------------------
MOCK_NSIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Valid NSIC Registrations
    "NSIC-TN-2025-001234": {
        "status": "VERIFIED",
        "registration_number": "NSIC-TN-2025-001234",
        "nsic_registration_number": "NSIC-TN-2025-001234",
        "enterprise_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "valid_from": "2025-01-01",
        "valid_until": "2028-01-01",
        "category": "Micro Services Enterprise",
        "products_services": "IT System Integration, Data Analytics",
        "nsic_branch": "NSIC Branch Office Chennai",
        "registration_status": "VALID",
        "state": "Tamil Nadu",
    },
    "NSIC-KR-2024-005678": {
        "status": "VERIFIED",
        "registration_number": "NSIC-KR-2024-005678",
        "nsic_registration_number": "NSIC-KR-2024-005678",
        "enterprise_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "valid_from": "2024-06-01",
        "valid_until": "2027-05-31",
        "category": "Small Manufacturing Enterprise",
        "products_services": "Server Racks & Edge Computing Appliances",
        "registration_status": "VALID",
        "state": "Karnataka",
    },

    # 2. Expired NSIC Registration in Registry
    "NSIC-DL-2020-009876": {
        "status": "VERIFIED",
        "registration_number": "NSIC-DL-2020-009876",
        "nsic_registration_number": "NSIC-DL-2020-009876",
        "enterprise_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "valid_from": "2020-01-01",
        "valid_until": "2023-12-31",
        "category": "Small Enterprise",
        "registration_status": "EXPIRED",
        "reason": "NSIC Single Point Registration Certificate validity period has expired.",
    },

    # 3. Simulated Outage NSIC
    "NSIC-XX-0000-000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock NSIC verification database is temporarily down for backup.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock EPFO Registry Fixtures (Part 5C)
# ---------------------------------------------------------------------------
MOCK_EPFO_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Establishments
    "TNMAS1234567000": {
        "status": "VERIFIED",
        "registration_number": "TNMAS1234567000",
        "epfo_registration_number": "TNMAS1234567000",
        "establishment_code": "TNMAS1234567000",
        "establishment_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "coverage_status": "ACTIVE",
        "registration_status": "ACTIVE",
        "office_name": "MAS - Chennai (Central)",
        "state": "Tamil Nadu",
        "coverage_date": "2018-08-01",
        "member_count_range": "50-100",
    },
    "DLCPM0098765000": {
        "status": "VERIFIED",
        "registration_number": "DLCPM0098765000",
        "epfo_registration_number": "DLCPM0098765000",
        "establishment_code": "DLCPM0098765000",
        "establishment_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "coverage_status": "ACTIVE",
        "registration_status": "ACTIVE",
        "office_name": "CPM - Delhi Central",
        "state": "Delhi",
        "coverage_date": "2013-05-15",
    },

    # 2. Inactive / Closed Establishment in Registry
    "MHBAN0011223000": {
        "status": "VERIFIED",
        "registration_number": "MHBAN0011223000",
        "epfo_registration_number": "MHBAN0011223000",
        "establishment_code": "MHBAN0011223000",
        "establishment_name": "WESTERN INFOTECH SOLUTIONS",
        "coverage_status": "INACTIVE",
        "registration_status": "INACTIVE",
        "state": "Maharashtra",
        "reason": "EPFO establishment marked inactive or surrendered.",
    },

    # 3. Simulated Outage EPFO
    "XXUNAV000000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock EPFO Unified Portal service is temporarily unavailable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock ESIC Registry Fixtures (Part 5C)
# ---------------------------------------------------------------------------
MOCK_ESIC_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Employers
    "51001234560001001": {
        "status": "VERIFIED",
        "registration_number": "51001234560001001",
        "esic_registration_number": "51001234560001001",
        "employer_code": "51001234560001001",
        "employer_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "registration_status": "ACTIVE",
        "state": "Tamil Nadu",
        "regional_office": "Chennai",
        "registration_date": "2018-09-01",
        "insured_persons_range": "25-50",
    },
    "11000987650001001": {
        "status": "VERIFIED",
        "registration_number": "11000987650001001",
        "esic_registration_number": "11000987650001001",
        "employer_code": "11000987650001001",
        "employer_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "registration_status": "ACTIVE",
        "state": "Delhi",
        "regional_office": "New Delhi",
        "registration_date": "2013-06-20",
    },

    # 2. Inactive Employer in Registry
    "31000099990001001": {
        "status": "VERIFIED",
        "registration_number": "31000099990001001",
        "esic_registration_number": "31000099990001001",
        "employer_code": "31000099990001001",
        "employer_name": "WESTERN INFOTECH SOLUTIONS",
        "registration_status": "INACTIVE",
        "state": "Maharashtra",
        "reason": "ESIC employer code is marked inactive.",
    },

    # 3. Simulated Outage ESIC
    "99000000000001001": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock ESIC Insurance Portal endpoint timed out.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock OEM Registry Fixtures (Part 5D)
# ---------------------------------------------------------------------------
MOCK_OEM_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Valid OEM Authorizations
    "OEM-AUTH-2026-001": {
        "status": "VERIFIED",
        "reference_number": "OEM-AUTH-2026-001",
        "authorization_number": "OEM-AUTH-2026-001",
        "oem_name": "ABC MANUFACTURING PRIVATE LIMITED",
        "authorized_entity": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "valid_from": "2026-01-01",
        "valid_until": "2027-12-31",
        "product_scope": "Industrial Sensor Model X100, Edge Gateway E500",
        "authorization_status": "VALID",
        "signatory_name": "Rajesh Varma, Director of Sales",
        "issuer_country": "India",
    },
    "OEM-AUTH-2026-002": {
        "status": "VERIFIED",
        "reference_number": "OEM-AUTH-2026-002",
        "authorization_number": "OEM-AUTH-2026-002",
        "oem_name": "GLOBAL TECH HARDWARE CORP",
        "authorized_entity": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "valid_from": "2025-06-01",
        "valid_until": "2028-05-31",
        "product_scope": "Enterprise Server Racks, High Density Storage Blades",
        "authorization_status": "VALID",
        "signatory_name": "Sarah Connor, Head of OEM Channels",
        "issuer_country": "India",
    },

    # 2. Expired OEM Authorization in Registry
    "OEM-AUTH-2024-009": {
        "status": "VERIFIED",
        "reference_number": "OEM-AUTH-2024-009",
        "authorization_number": "OEM-AUTH-2024-009",
        "oem_name": "ABC MANUFACTURING PRIVATE LIMITED",
        "authorized_entity": "ALPHA PROCUREMENT SERVICES LIMITED",
        "valid_from": "2023-01-01",
        "valid_until": "2024-12-31",
        "product_scope": "Legacy Power Modules",
        "authorization_status": "EXPIRED",
        "reason": "OEM authorization validity period has elapsed.",
    },

    # 3. Simulated Outage OEM
    "OEM-UNAV-0000-000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock OEM Manufacturer Verification Database is temporarily unavailable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock Local Content Registry Fixtures (Part 5D)
# ---------------------------------------------------------------------------
MOCK_LOCAL_CONTENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Valid Local Content Declarations
    "LC-2026-0101": {
        "status": "VERIFIED",
        "reference_number": "LC-2026-0101",
        "declaration_id": "LC-2026-0101",
        "entity_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "product_name": "Industrial Controller Unit",
        "local_content_percentage": 55.0,
        "supplier_class": "CLASS_I",
        "declaration_date": "2026-01-15",
        "location_of_value_addition": "Chennai, Tamil Nadu",
        "certifying_authority": "Self Declaration / Independent Statutory Auditor",
        "status": "VALID",
    },
    "LC-2026-0202": {
        "status": "VERIFIED",
        "reference_number": "LC-2026-0202",
        "declaration_id": "LC-2026-0202",
        "entity_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "product_name": "Edge Computing Server",
        "local_content_percentage": 25.0,
        "supplier_class": "CLASS_II",
        "declaration_date": "2026-02-10",
        "location_of_value_addition": "Bengaluru, Karnataka",
        "status": "VALID",
    },

    # 2. Simulated Outage Local Content
    "LC-UNAV-0000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock Local Content MII Registry is temporarily unreachable.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock BIS Registry Fixtures (Part 5D)
# ---------------------------------------------------------------------------
MOCK_BIS_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Valid BIS Licenses / Registrations
    "R-12345678": {
        "status": "VERIFIED",
        "registration_number": "R-12345678",
        "bis_registration_number": "R-12345678",
        "manufacturer_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "standard_number": "IS 13252",
        "product_name": "Power Supply Unit & Industrial Adapter",
        "model_number": "TF-PSU-100",
        "valid_from": "2024-04-01",
        "valid_until": "2027-03-31",
        "registry_status": "VALID",
        "country": "India",
    },
    "CM/L-9876543": {
        "status": "VERIFIED",
        "registration_number": "CM/L-9876543",
        "bis_registration_number": "CM/L-9876543",
        "manufacturer_name": "INNOVATIVE SYSTEMS PRIVATE LIMITED",
        "standard_number": "IS 16046",
        "product_name": "Lithium-ion Battery Pack",
        "model_number": "IS-BAT-500",
        "valid_from": "2025-01-01",
        "valid_until": "2028-01-01",
        "registry_status": "VALID",
        "country": "India",
    },

    # 2. Expired BIS License in Registry
    "R-99999999": {
        "status": "VERIFIED",
        "registration_number": "R-99999999",
        "bis_registration_number": "R-99999999",
        "manufacturer_name": "ALPHA PROCUREMENT SERVICES LIMITED",
        "standard_number": "IS 13252",
        "product_name": "Legacy IT Terminal",
        "registry_status": "EXPIRED",
        "valid_until": "2023-12-31",
        "reason": "BIS Standard Mark certificate has expired.",
    },

    # 3. Simulated Outage BIS
    "R-00000000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock BIS e-BIS Portal endpoint timed out.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock DPIIT Public Procurement MII Registry Fixtures (Part 5D)
# ---------------------------------------------------------------------------
MOCK_DPIIT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "DPIIT-MII-2026-001": {
        "status": "VERIFIED",
        "recognition_number": "DPIIT-MII-2026-001",
        "entity_name": "TECHFLOW ENTERPRISES PRIVATE LIMITED",
        "recognition_type": "Public Procurement Preference MII Order",
        "recognition_date": "2025-05-10",
        "status": "VALID",
        "state": "Tamil Nadu",
    },
    "DPIIT-MII-UNAV": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock DPIIT Public Procurement Verification Gateway is offline.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock Blacklisting Registry Fixtures (Part 5E)
# ---------------------------------------------------------------------------
MOCK_BLACKLISTING_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Blacklisted Entities (Indexed by PAN / GSTIN / CIN / Legal Name)
    "BL-PAN-XYZ9999X": {
        "status": "VERIFIED",
        "registry_status": "BLACKLISTED",
        "entity_name": "XYZ SUPPLIERS PRIVATE LIMITED",
        "pan": "XYZ9999X",
        "gstin": "33XYZ9999X1Z5",
        "cin": "U72900DL2010PTC999999",
        "authority": "GeM Procurement Vigilance Authority",
        "reference_number": "BL-2026-001",
        "effective_from": "2025-01-01",
        "effective_until": "2027-01-01",
        "reason_summary": "Furnishing fraudulent experience certificates during bid qualification.",
    },
    "BL-PAN-BAD1234B": {
        "status": "VERIFIED",
        "registry_status": "BLACKLISTED",
        "entity_name": "DEF DEBARRED ENTERPRISES",
        "pan": "BAD1234B",
        "gstin": "27BAD1234B1Z9",
        "authority": "Central Vigilance Department",
        "reference_number": "BL-2025-088",
        "effective_from": "2024-06-01",
        "effective_until": "2026-12-31",
        "reason_summary": "Material breach of integrity pact.",
    },

    # 2. Simulated Outage Blacklisting Provider
    "BL-UNAV-0000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock Central Blacklisting Registry is currently down for maintenance.",
    },
}


# ---------------------------------------------------------------------------
# Synthetic Mock Debarment Registry Fixtures (Part 5E)
# ---------------------------------------------------------------------------
MOCK_DEBARMENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 1. Active Debarment Record
    "DB-CIN-U72900TN2024PTC123456": {
        "status": "VERIFIED",
        "registry_status": "DEBARRED",
        "entity_name": "ABC CONTRACTORS PRIVATE LIMITED",
        "cin": "U72900TN2024PTC123456",
        "pan": "ABCDE9999D",
        "authority": "Ministry of Public Works",
        "reference_number": "DB-2026-010",
        "effective_from": "2025-03-01",
        "effective_until": "2027-03-01",
        "reason_summary": "Non-performance and contractual default.",
    },

    # 2. Expired Debarment Record
    "DB-PAN-EXP9999P": {
        "status": "VERIFIED",
        "registry_status": "EXPIRED",
        "entity_name": "REHABILITATED TRADERS LIMITED",
        "pan": "EXP9999P",
        "authority": "Department of Commerce",
        "reference_number": "DB-2022-005",
        "effective_from": "2022-01-01",
        "effective_until": "2024-12-31",
        "reason_summary": "Debarment period has concluded.",
    },

    # 3. Simulated Outage Debarment Provider
    "DB-UNAV-0000": {
        "status": "UNAVAILABLE",
        "error_code": "SOURCE_UNAVAILABLE",
        "error_message": "Mock Debarment Database is temporarily unreachable.",
    },
}
