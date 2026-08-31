/**
 * Predefined Common Requirement & Eligibility Rule Templates
 * Used as UI shortcuts for Procurement Officers. Stored dynamically in PostgreSQL.
 */

export interface RequirementTemplate {
  id: string;
  name: string;
  code: string;
  description: string;
  category: "STATUTORY" | "FINANCIAL" | "TECHNICAL" | "EXPERIENCE" | "LOCAL_CONTENT" | "DOCUMENT" | "BLACKLISTING" | "OTHER";
  requirement_type: "BOOLEAN" | "NUMBER" | "TEXT" | "DATE" | "DOCUMENT" | "STATUS";
  operator: "EQUALS" | "NOT_EQUALS" | "GREATER_THAN" | "GREATER_THAN_OR_EQUAL" | "LESS_THAN" | "LESS_THAN_OR_EQUAL" | "CONTAINS" | "EXISTS" | "NOT_EXISTS";
  expected_value: any;
  is_mandatory: boolean;
  weight: number;
}

export const REQUIREMENT_TEMPLATES: RequirementTemplate[] = [
  {
    id: "gst",
    name: "Valid GST Registration Certificate",
    code: "GST_REQUIRED",
    description: "Bidder must possess a valid, active GSTIN registration verified against government records.",
    category: "STATUTORY",
    requirement_type: "STATUS",
    operator: "EQUALS",
    expected_value: "ACTIVE",
    is_mandatory: true,
    weight: 10,
  },
  {
    id: "pan",
    name: "Permanent Account Number (PAN)",
    code: "PAN_REQUIRED",
    description: "Copy of valid corporate PAN card must be submitted and active.",
    category: "STATUTORY",
    requirement_type: "DOCUMENT",
    operator: "EXISTS",
    expected_value: true,
    is_mandatory: true,
    weight: 10,
  },
  {
    id: "udyam",
    name: "Udyam / MSME Registration",
    code: "UDYAM_REQUIRED",
    description: "Valid MSME/Udyam registration certificate for public procurement preference eligibility.",
    category: "STATUTORY",
    requirement_type: "STATUS",
    operator: "EQUALS",
    expected_value: "ACTIVE",
    is_mandatory: true,
    weight: 10,
  },
  {
    id: "oem_auth",
    name: "OEM Manufacturer Authorization Form (MAF)",
    code: "OEM_AUTH_REQUIRED",
    description: "Direct OEM authorization certificate explicitly validating authorized reseller status for tendered goods.",
    category: "DOCUMENT",
    requirement_type: "DOCUMENT",
    operator: "EXISTS",
    expected_value: true,
    is_mandatory: true,
    weight: 15,
  },
  {
    id: "local_content",
    name: "Minimum Local Content (Make in India)",
    code: "LOCAL_CONTENT",
    description: "Minimum percentage of domestic value addition required under the Public Procurement (Preference to Make in India) Order.",
    category: "LOCAL_CONTENT",
    requirement_type: "NUMBER",
    operator: "GREATER_THAN_OR_EQUAL",
    expected_value: 50,
    is_mandatory: true,
    weight: 15,
  },
  {
    id: "turnover",
    name: "Minimum Annual Financial Turnover",
    code: "MIN_TURNOVER",
    description: "Audited average annual financial turnover over the previous three financial years (in INR).",
    category: "FINANCIAL",
    requirement_type: "NUMBER",
    operator: "GREATER_THAN_OR_EQUAL",
    expected_value: 50000000,
    is_mandatory: true,
    weight: 15,
  },
  {
    id: "experience",
    name: "Prior Public Sector Experience",
    code: "MIN_EXPERIENCE_YEARS",
    description: "Minimum number of years of experience in executing similar supply or works contracts for public entities.",
    category: "EXPERIENCE",
    requirement_type: "NUMBER",
    operator: "GREATER_THAN_OR_EQUAL",
    expected_value: 3,
    is_mandatory: false,
    weight: 5,
  },
  {
    id: "blacklisting",
    name: "Non-Debarment & Non-Blacklisting Undertaking",
    code: "NOT_BLACKLISTED",
    description: "Self-declaration undertaking confirming the bidder is not blacklisted by any Central/State Govt body.",
    category: "BLACKLISTING",
    requirement_type: "BOOLEAN",
    operator: "EQUALS",
    expected_value: false,
    is_mandatory: true,
    weight: 20,
  },
];
